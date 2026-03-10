"""Tests for counter_sign_marker convenience function."""

from exit_door import quick_exit, to_json
from exit_door_langchain import counter_sign_marker


def test_counter_sign_marker():
    result = quick_exit("test-platform")
    marker_json = to_json(result.marker)
    cs_result = counter_sign_marker(marker_json)
    assert cs_result.marker is not None
    assert cs_result.identity is not None
    assert cs_result.identity.did.startswith("did:key:")
