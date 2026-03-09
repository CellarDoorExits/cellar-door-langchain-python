"""Tests for ExitCallbackHandler."""

import json
import threading
from uuid import uuid4

from langchain_core.agents import AgentFinish

from cellar_door_exit import ExitMarker, ExitType
from cellar_door_langchain import ExitCallbackHandler


class TestExitCallbackHandler:
    def test_default_construction(self) -> None:
        handler = ExitCallbackHandler()
        assert handler.origin == "langchain"
        assert handler.exit_type == ExitType.VOLUNTARY
        assert len(handler.markers) == 0
        assert handler.max_markers == 1000
        assert handler.fail_safe is True

    def test_custom_origin(self) -> None:
        handler = ExitCallbackHandler(origin="my-platform")
        assert handler.origin == "my-platform"

    def test_on_chain_end_creates_marker(self) -> None:
        handler = ExitCallbackHandler()
        handler.on_chain_end(outputs={"result": "done"}, parent_run_id=None)
        assert len(handler.markers) == 1
        marker = handler.markers[0]
        assert isinstance(marker, ExitMarker)
        assert marker.id.startswith("urn:exit:")
        assert marker.origin == "langchain"

    def test_on_agent_finish_creates_marker(self) -> None:
        handler = ExitCallbackHandler()
        finish = AgentFinish(return_values={"output": "done"}, log="")
        handler.on_agent_finish(finish, run_id=uuid4())
        assert len(handler.markers) == 1

    def test_multiple_chain_ends(self) -> None:
        handler = ExitCallbackHandler()
        for _ in range(5):
            handler.on_chain_end(outputs={}, parent_run_id=None)
        assert len(handler.markers) == 5

    def test_max_markers_eviction(self) -> None:
        handler = ExitCallbackHandler(max_markers=3)
        for _ in range(5):
            handler.on_chain_end(outputs={}, parent_run_id=None)
        assert len(handler.markers) == 3
        ids = [m.id for m in handler.markers]
        assert len(set(ids)) == 3

    def test_root_only_skips_subchains(self) -> None:
        handler = ExitCallbackHandler(root_only=True)
        root_id = uuid4()
        child_id = uuid4()
        # Root chain starts
        handler.on_chain_start(serialized={}, inputs={}, run_id=root_id, parent_run_id=None)
        # Subchain starts (has parent)
        handler.on_chain_start(serialized={}, inputs={}, run_id=child_id, parent_run_id=root_id)
        # Subchain ends — should NOT create marker (has parent)
        handler.on_chain_end(outputs={}, run_id=child_id, parent_run_id=root_id)
        assert len(handler.markers) == 0
        # Root chain ends — SHOULD create marker (no parent)
        handler.on_chain_end(outputs={}, run_id=root_id, parent_run_id=None)
        assert len(handler.markers) == 1

    def test_root_only_false_fires_on_all(self) -> None:
        handler = ExitCallbackHandler(root_only=False)
        root_id = uuid4()
        child_id = uuid4()
        handler.on_chain_start(serialized={}, inputs={}, run_id=root_id, parent_run_id=None)
        handler.on_chain_start(serialized={}, inputs={}, run_id=child_id, parent_run_id=root_id)
        handler.on_chain_end(outputs={}, run_id=child_id, parent_run_id=root_id)
        handler.on_chain_end(outputs={}, run_id=root_id, parent_run_id=None)
        assert len(handler.markers) == 2

    def test_on_marker_callback(self) -> None:
        received: list[ExitMarker] = []
        handler = ExitCallbackHandler(on_marker=received.append)
        handler.on_chain_end(outputs={}, parent_run_id=None)
        assert len(received) == 1
        assert received[0].id == handler.markers[0].id

    def test_clear(self) -> None:
        handler = ExitCallbackHandler()
        handler.on_chain_end(outputs={}, parent_run_id=None)
        assert len(handler.markers) == 1
        handler.clear()
        assert len(handler.markers) == 0

    def test_markers_to_json(self) -> None:
        handler = ExitCallbackHandler()
        handler.on_chain_end(outputs={}, parent_run_id=None)
        handler.on_chain_end(outputs={}, parent_run_id=None)
        json_str = handler.markers_to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert all("exitType" in m for m in parsed)
        assert all("@context" in m for m in parsed)

    def test_custom_exit_type(self) -> None:
        handler = ExitCallbackHandler(exit_type=ExitType.FORCED)
        handler.on_chain_end(outputs={}, parent_run_id=None)
        assert handler.markers[0].exit_type == ExitType.FORCED

    def test_handler_name(self) -> None:
        handler = ExitCallbackHandler()
        assert handler.name == "ExitCallbackHandler"

    def test_on_chain_error_creates_marker(self) -> None:
        handler = ExitCallbackHandler()
        handler.on_chain_error(RuntimeError("boom"), parent_run_id=None)
        assert len(handler.markers) == 1

    def test_on_chain_error_skips_subchains(self) -> None:
        handler = ExitCallbackHandler(root_only=True)
        handler.on_chain_error(RuntimeError("boom"), parent_run_id=uuid4())
        assert len(handler.markers) == 0

    def test_fail_safe_swallows_errors(self) -> None:
        """In fail_safe mode, marker creation errors don't propagate."""
        handler = ExitCallbackHandler(fail_safe=True)
        # Corrupt the origin to something that might cause issues
        # but quick_exit is resilient — test the callback instead
        errors: list[Exception] = []

        def bad_callback(marker: ExitMarker) -> None:
            raise RuntimeError("callback exploded")

        handler._on_marker = bad_callback
        # Should NOT raise
        handler.on_chain_end(outputs={}, parent_run_id=None)

    def test_fail_safe_false_raises(self) -> None:
        """With fail_safe=False, callback errors propagate."""
        handler = ExitCallbackHandler(fail_safe=False)

        def bad_callback(marker: ExitMarker) -> None:
            raise RuntimeError("callback exploded")

        handler._on_marker = bad_callback
        try:
            handler.on_chain_end(outputs={}, parent_run_id=None)
            assert False, "Should have raised"
        except RuntimeError:
            pass

    def test_thread_safety(self) -> None:
        """Concurrent chain ends should not corrupt state."""
        handler = ExitCallbackHandler()
        errors: list[Exception] = []

        def run_chains(n: int) -> None:
            try:
                for _ in range(n):
                    handler.on_chain_end(outputs={}, parent_run_id=None)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_chains, args=(20,)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(handler.markers) == 100

    def test_agent_finish_deduplication(self) -> None:
        """Same run_id should not produce duplicate markers from on_agent_finish."""
        handler = ExitCallbackHandler()
        run_id = uuid4()
        finish = AgentFinish(return_values={"output": "done"}, log="")
        handler.on_agent_finish(finish, run_id=run_id)
        handler.on_agent_finish(finish, run_id=run_id)
        assert len(handler.markers) == 1
