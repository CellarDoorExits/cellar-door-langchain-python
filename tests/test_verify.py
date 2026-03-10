"""Tests for verify_marker convenience function."""

import pytest
from exit_door import quick_exit, to_json
from exit_door.errors import ValidationError
from exit_door_langchain import verify_marker


def test_verify_valid_marker():
    result = quick_exit("test-platform")
    marker_json = to_json(result.marker)
    vr = verify_marker(marker_json)
    assert vr.valid is True


def test_verify_invalid_json():
    with pytest.raises((ValidationError, Exception)):
        verify_marker('{"not": "a marker"}')
