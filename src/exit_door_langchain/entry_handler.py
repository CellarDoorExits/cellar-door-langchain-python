"""LangChain callback handler for ENTRY Protocol arrival markers.

Automatically verifies incoming EXIT markers and creates arrival markers
when chains start execution.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any, Callable
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

from entry_door import (
    ArrivalMarker,
    QuickEntryResult,
    quick_entry,
    OPEN_DOOR,
)
from exit_door import to_json

logger = logging.getLogger(__name__)


class EntryCallbackHandler(BaseCallbackHandler):
    """A LangChain callback handler that creates arrival markers on chain start.

    Verifies an incoming EXIT marker and creates a signed arrival record
    when a chain begins execution.

    Example:
        >>> from exit_door_langchain import EntryCallbackHandler
        >>> handler = EntryCallbackHandler(
        ...     exit_marker_json=marker_json,
        ...     destination="my-service",
        ... )
        >>> chain.invoke({"input": "hello"}, config={"callbacks": [handler]})
        >>> print(handler.last_arrival.id)

    Args:
        exit_marker_json: JSON string of the EXIT marker to verify on arrival.
        destination: Destination identifier for the arrival marker.
        policy: Admission policy (from entry_door presets). Defaults to OPEN_DOOR.
        on_arrival: Called when an arrival marker is successfully created.
        on_admission_rejected: Called when admission is rejected (entry fails).
        max_markers: Maximum arrival markers to retain. Default 1000.
        root_only: If True (default), only process root-level chain starts.
        fail_safe: If True (default), errors are logged but not propagated.
    """

    name: str = "EntryCallbackHandler"

    def __init__(
        self,
        *,
        exit_marker_json: str,
        destination: str = "langchain",
        policy: Any | None = None,
        on_arrival: Callable[[ArrivalMarker], None] | None = None,
        on_admission_rejected: Callable[[Exception], None] | None = None,
        max_markers: int = 1000,
        root_only: bool = True,
        fail_safe: bool = True,
    ) -> None:
        super().__init__()
        self.exit_marker_json = exit_marker_json
        self.destination = destination
        self.policy = policy or OPEN_DOOR
        self.arrivals: deque[ArrivalMarker] = deque(maxlen=max_markers)
        self.max_markers = max_markers
        self.root_only = root_only
        self.fail_safe = fail_safe
        self.last_arrival: ArrivalMarker | None = None
        self._on_arrival = on_arrival
        self._on_admission_rejected = on_admission_rejected
        self._lock = threading.Lock()
        self._processed_roots: set[UUID | None] = set()

    def _record_arrival(self) -> ArrivalMarker | None:
        """Verify the exit marker and create an arrival marker."""
        try:
            result: QuickEntryResult = quick_entry(
                self.exit_marker_json,
                self.destination,
            )
            marker = result.arrival_marker
            with self._lock:
                self.arrivals.append(marker)
                self.last_arrival = marker
            if self._on_arrival:
                self._on_arrival(marker)
            return marker
        except Exception as exc:
            logger.exception("Failed to create arrival marker")
            if self._on_admission_rejected:
                self._on_admission_rejected(exc)
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
        """Verify exit marker and create arrival on chain start.

        If root_only=True (default), only fires for the outermost chain.
        """
        is_root = parent_run_id is None
        if self.root_only and not is_root:
            return

        # Avoid duplicate arrivals for the same root
        with self._lock:
            if run_id in self._processed_roots:
                return
            self._processed_roots.add(run_id)
            # Evict old entries
            while len(self._processed_roots) > self.max_markers:
                self._processed_roots.pop()

        self._record_arrival()

    def clear(self) -> None:
        """Remove all stored arrivals and reset state."""
        with self._lock:
            self.arrivals.clear()
            self._processed_roots.clear()
            self.last_arrival = None
