"""Standalone EXIT marker verification for LangChain integrations."""

from __future__ import annotations

from exit_door import (
    ExitMarker,
    VerificationResult,
    quick_verify,
    from_json,
)


def verify_marker(marker_json: str) -> VerificationResult:
    """Verify an EXIT marker's cryptographic signature and structure.

    Convenience wrapper around ``exit_door.quick_verify`` for use in
    LangChain pipelines, callbacks, or standalone scripts.

    Args:
        marker_json: JSON string of the EXIT marker to verify.

    Returns:
        VerificationResult with ``.valid`` bool and ``.errors`` list.

    Example:
        >>> from exit_door_langchain import verify_marker
        >>> result = verify_marker(marker_json)
        >>> assert result.valid
    """
    return quick_verify(marker_json)
