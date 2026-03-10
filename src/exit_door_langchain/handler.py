"""LangChain callback handler for EXIT Protocol departure markers.

Automatically creates EXIT markers when chains or agents complete execution.
"""

from __future__ import annotations

import json
import logging
import threading
from collections import OrderedDict, deque
from typing import Any, Callable
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.agents import AgentFinish

from exit_door import (
    ExitMarker,
    ExitType,
    quick_exit,
    to_json,
)

logger = logging.getLogger(__name__)


class ExitCallbackHandler(BaseCallbackHandler):
    """A LangChain callback handler that creates EXIT markers on completion.

    Automatically generates signed departure records when chains or agents
    finish execution. Thread-safe for concurrent chain invocations.

    Example:
        >>> from exit_door_langchain import ExitCallbackHandler
        >>> handler = ExitCallbackHandler(origin="my-app")
        >>> # Use with any LangChain chain or agent
        >>> chain.invoke({"input": "hello"}, config={"callbacks": [handler]})
        >>> print(handler.markers[-1].id)  # urn:exit:abc123...

    Args:
        origin: Platform/system name. Defaults to "langchain".
        exit_type: Exit type for auto-generated markers. Defaults to VOLUNTARY.
        on_marker: Called whenever a new marker is created.
        max_markers: Maximum markers to retain in memory. Default 1000.
        root_only: If True (default), only create markers for root-level chain
            completions, not nested subchains. Set to False to get a marker for
            every chain/subchain.
        fail_safe: If True (default), marker creation errors are logged but
            never propagated to the user's chain. Set to False to let
            exceptions bubble up.
        error_exit_type: Exit type for on_chain_error markers. Defaults to
            INVOLUNTARY (distinguishes errors from normal completions).
    """

    name: str = "ExitCallbackHandler"

    def __init__(
        self,
        *,
        origin: str = "langchain",
        exit_type: ExitType = ExitType.VOLUNTARY,
        on_marker: Callable[[ExitMarker], None] | None = None,
        max_markers: int = 1000,
        root_only: bool = True,
        fail_safe: bool = True,
        error_exit_type: ExitType = ExitType.FORCED,
    ) -> None:
        super().__init__()
        self.origin = origin
        self.exit_type = exit_type
        self.error_exit_type = error_exit_type
        self.markers: deque[ExitMarker] = deque(maxlen=max_markers)
        self.max_markers = max_markers
        self.root_only = root_only
        self.fail_safe = fail_safe
        self._on_marker = on_marker
        self._lock = threading.Lock()
        self._chain_depths: dict[UUID | None, int] = {}
        self._agent_runs: OrderedDict[UUID | None, None] = OrderedDict()

    def _record_marker(self, exit_type: ExitType | None = None) -> ExitMarker | None:
        """Create and store a new EXIT marker.

        In fail_safe mode (default), exceptions are logged but swallowed
        so the user's chain is never broken by EXIT marker failures.
        """
        try:
            result = quick_exit(self.origin, exit_type=exit_type or self.exit_type)
            marker = result.marker
            with self._lock:
                self.markers.append(marker)
            if self._on_marker:
                self._on_marker(marker)
            return marker
        except Exception:
            logger.exception("Failed to create EXIT marker")
            if not self.fail_safe:
                raise
            return None

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Track chain nesting depth per run."""
        with self._lock:
            self._chain_depths[parent_run_id] = (
                self._chain_depths.get(parent_run_id, 0) + 1
            )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Create an EXIT marker when a chain completes.

        If root_only=True (default), only fires for the outermost chain.
        """
        is_root = parent_run_id is None
        with self._lock:
            depth = self._chain_depths.get(parent_run_id, 1)
            self._chain_depths[parent_run_id] = max(0, depth - 1)
            if self._chain_depths[parent_run_id] == 0:
                self._chain_depths.pop(parent_run_id, None)

        if self.root_only and not is_root:
            return
        self._record_marker()

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID | None = None,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Create an EXIT marker when a chain fails.

        Failed chains still generate departure records (with the configured
        exit_type). Override exit_type to INVOLUNTARY for error-specific markers.
        """
        is_root = parent_run_id is None
        with self._lock:
            depth = self._chain_depths.get(parent_run_id, 1)
            self._chain_depths[parent_run_id] = max(0, depth - 1)
            if self._chain_depths[parent_run_id] == 0:
                self._chain_depths.pop(parent_run_id, None)

        if self.root_only and not is_root:
            return
        self._record_marker(exit_type=self.error_exit_type)

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Create an EXIT marker when an agent finishes.

        Deduplicates against on_chain_end: if an agent's run_id already
        produced a marker via on_chain_end, this is a no-op.
        """
        with self._lock:
            if run_id in self._agent_runs:
                return
            self._agent_runs[run_id] = None
            # Evict oldest entries (FIFO)
            while len(self._agent_runs) > self.max_markers:
                self._agent_runs.popitem(last=False)
        self._record_marker()

    def clear(self) -> None:
        """Remove all stored markers and reset state."""
        with self._lock:
            self.markers.clear()
            self._chain_depths.clear()
            self._agent_runs.clear()

    def markers_to_json(self) -> str:
        """Export all markers as a JSON array string."""
        with self._lock:
            snapshot = list(self.markers)
        return json.dumps(
            [json.loads(to_json(m)) for m in snapshot],
            indent=2,
        )
