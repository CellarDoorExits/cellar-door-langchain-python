"""Tests for EntryCallbackHandler."""

import threading
from uuid import uuid4

import pytest

from entry_door import ArrivalMarker, OPEN_DOOR, STRICT
from exit_door import quick_exit, to_json
from exit_door_langchain import EntryCallbackHandler


def _make_exit_json(origin: str = "test-origin") -> str:
    """Create a valid EXIT marker JSON for testing."""
    result = quick_exit(origin)
    return to_json(result.marker)


class TestEntryCallbackHandler:
    def test_default_construction(self) -> None:
        marker_json = _make_exit_json()
        handler = EntryCallbackHandler(exit_marker_json=marker_json)
        assert handler.destination == "langchain"
        assert handler.last_arrival is None
        assert len(handler.arrivals) == 0
        assert handler.fail_safe is True
        assert handler.root_only is True

    def test_custom_destination(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
            destination="my-service",
        )
        assert handler.destination == "my-service"

    def test_on_chain_start_creates_arrival(self) -> None:
        marker_json = _make_exit_json()
        handler = EntryCallbackHandler(
            exit_marker_json=marker_json,
            destination="test-dest",
        )
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=uuid4(), parent_run_id=None
        )
        assert len(handler.arrivals) == 1
        assert handler.last_arrival is not None
        assert isinstance(handler.last_arrival, ArrivalMarker)

    def test_root_only_skips_subchains(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
            root_only=True,
        )
        root_id = uuid4()
        child_id = uuid4()
        # Root chain start
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=root_id, parent_run_id=None
        )
        assert len(handler.arrivals) == 1
        # Subchain start — should NOT create arrival
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=child_id, parent_run_id=root_id
        )
        assert len(handler.arrivals) == 1

    def test_root_only_false_fires_on_all(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
            root_only=False,
        )
        root_id = uuid4()
        child_id = uuid4()
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=root_id, parent_run_id=None
        )
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=child_id, parent_run_id=root_id
        )
        assert len(handler.arrivals) == 2

    def test_on_arrival_callback(self) -> None:
        received: list[ArrivalMarker] = []
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
            on_arrival=received.append,
        )
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=uuid4(), parent_run_id=None
        )
        assert len(received) == 1
        assert received[0] is handler.last_arrival

    def test_on_admission_rejected_callback(self) -> None:
        errors: list[Exception] = []
        handler = EntryCallbackHandler(
            exit_marker_json="not-valid-json!!!",
            on_admission_rejected=errors.append,
            fail_safe=True,
        )
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=uuid4(), parent_run_id=None
        )
        assert len(errors) == 1
        assert handler.last_arrival is None

    def test_fail_safe_swallows_errors(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json="invalid",
            fail_safe=True,
        )
        # Should NOT raise
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=uuid4(), parent_run_id=None
        )
        assert len(handler.arrivals) == 0

    def test_fail_safe_false_raises(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json="invalid",
            fail_safe=False,
        )
        with pytest.raises(Exception):
            handler.on_chain_start(
                serialized={}, inputs={}, run_id=uuid4(), parent_run_id=None
            )

    def test_deduplication_same_run_id(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
        )
        run_id = uuid4()
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=run_id, parent_run_id=None
        )
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=run_id, parent_run_id=None
        )
        assert len(handler.arrivals) == 1

    def test_clear(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
        )
        handler.on_chain_start(
            serialized={}, inputs={}, run_id=uuid4(), parent_run_id=None
        )
        assert len(handler.arrivals) == 1
        handler.clear()
        assert len(handler.arrivals) == 0
        assert handler.last_arrival is None

    def test_max_markers_eviction(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
            max_markers=3,
        )
        for _ in range(5):
            handler.on_chain_start(
                serialized={}, inputs={}, run_id=uuid4(), parent_run_id=None
            )
        assert len(handler.arrivals) == 3

    def test_handler_name(self) -> None:
        handler = EntryCallbackHandler(exit_marker_json=_make_exit_json())
        assert handler.name == "EntryCallbackHandler"

    def test_thread_safety(self) -> None:
        handler = EntryCallbackHandler(
            exit_marker_json=_make_exit_json(),
            root_only=False,
        )
        errors: list[Exception] = []

        def run_starts(n: int) -> None:
            try:
                for _ in range(n):
                    handler.on_chain_start(
                        serialized={},
                        inputs={},
                        run_id=uuid4(),
                        parent_run_id=None,
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_starts, args=(10,)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(handler.arrivals) == 50
