"""exit-door-langchain -- LangChain integration for EXIT Protocol.

Provides a callback handler that automatically creates EXIT markers
when LangChain chains or agents complete execution.

Example:
    >>> from exit_door_langchain import ExitCallbackHandler
    >>> handler = ExitCallbackHandler(origin="my-app")
    >>> chain.invoke({"input": "hello"}, config={"callbacks": [handler]})
    >>> assert len(handler.markers) > 0
"""

from entry_door import ArrivalMarker
from exit_door import ExitMarker, ExitType

from .countersign import counter_sign_marker
from .entry_handler import EntryCallbackHandler
from .handler import ExitCallbackHandler
from .verify import verify_marker

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "ArrivalMarker",
    "EntryCallbackHandler",
    "ExitCallbackHandler",
    "ExitMarker",
    "ExitType",
    "counter_sign_marker",
    "verify_marker",
]
