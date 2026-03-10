"""Counter-signing support for EXIT markers in LangChain integrations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from exit_door import (
    ExitMarker,
    Identity,
    add_counter_signature,
    from_json,
    generate_identity,
    to_json,
)


@dataclass
class CounterSignResult:
    """Result of counter-signing an EXIT marker."""
    marker: ExitMarker
    identity: Identity


def counter_sign_marker(
    marker_json: str,
) -> CounterSignResult:
    """Counter-sign an EXIT marker as a witness.

    Parses the marker JSON, generates an ephemeral identity, adds a
    counter-signature, and returns the result.

    Args:
        marker_json: JSON string of the signed EXIT marker.

    Returns:
        CounterSignResult with the counter-signed marker and identity.

    Example:
        >>> from exit_door_langchain import counter_sign_marker
        >>> result = counter_sign_marker(marker_json)
        >>> print(to_json(result.marker))
    """
    marker = from_json(marker_json)
    identity = generate_identity()
    updated = add_counter_signature(
        marker,
        identity.private_key,
        identity.public_key,
    )
    return CounterSignResult(marker=updated, identity=identity)
