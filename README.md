# cellar-door-langchain 𓉸

[![PyPI](https://img.shields.io/pypi/v/cellar-door-langchain)](https://pypi.org/project/cellar-door-langchain/)
[![tests](https://img.shields.io/badge/tests-19_passing-brightgreen)]()
[![Python](https://img.shields.io/pypi/pyversions/cellar-door-langchain)](https://pypi.org/project/cellar-door-langchain/)
[![license](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)

> **⚠️ Pre-release software -- no formal security audit has been conducted.**

LangChain callback handler for EXIT Protocol departure markers. Automatically creates signed departure records when chains or agents complete execution. Thread-safe, fail-safe, works with LCEL and LangGraph.

## Quick Start

```bash
pip install cellar-door-langchain
```

```python
from cellar_door_langchain import ExitCallbackHandler

handler = ExitCallbackHandler(origin="my-app")

# Use with any LangChain chain
chain.invoke({"input": "hello"}, config={"callbacks": [handler]})

# Markers are collected automatically
print(handler.markers[-1].id)  # urn:exit:abc123...
```

## Configuration

```python
from cellar_door_exit import ExitType

handler = ExitCallbackHandler(
    origin="my-platform",              # Platform name (default: "langchain")
    exit_type=ExitType.VOLUNTARY,      # Exit type for success (default: VOLUNTARY)
    error_exit_type=ExitType.FORCED,   # Exit type for errors (default: FORCED)
    on_marker=my_callback,             # Called on each new marker
    max_markers=500,                   # Memory limit (default: 1000)
    root_only=True,                    # Skip subchain markers (default: True)
    fail_safe=True,                    # Never break user's chain (default: True)
)
```

## API

| Method / Property | Description |
|-------------------|-------------|
| `handler.markers` | Deque of collected `ExitMarker` objects |
| `handler.markers_to_json()` | Export all markers as JSON array |
| `handler.clear()` | Remove all stored markers and reset state |

## How It Works

The handler hooks into LangChain's callback system:

| Callback | When | Exit Type |
|----------|------|-----------|
| `on_chain_end` | Chain completes successfully | `exit_type` (default: VOLUNTARY) |
| `on_chain_error` | Chain fails with exception | `error_exit_type` (default: FORCED) |
| `on_agent_finish` | Agent completes (deduplicated) | `exit_type` (default: VOLUNTARY) |

**root_only mode** (default): Only creates markers for root-level chain completions, not nested subchains. Set `root_only=False` to get a marker for every chain/subchain.

**fail_safe mode** (default): Marker creation errors are logged but never propagated to the user's chain. Set `fail_safe=False` to let exceptions bubble up.

**Thread safety**: Safe for concurrent chain invocations sharing one handler instance.

## Web Server Usage

In web server contexts, create a **new handler per request** to prevent marker accumulation across users:

```python
@app.post("/chat")
async def chat(request: ChatRequest):
    handler = ExitCallbackHandler(origin="my-api")
    result = chain.invoke(request.input, config={"callbacks": [handler]})
    return {"result": result, "departures": len(handler.markers)}
```

## 🗺️ Ecosystem

| Package | Description |
|---------|-------------|
| [cellar-door-exit](https://github.com/CellarDoorExits/exit-python) (Python) | Core protocol -- departure markers |
| **[cellar-door-langchain](https://github.com/CellarDoorExits/cellar-door-langchain-python) (Python)** | **← you are here** |
| [cellar-door-exit](https://github.com/CellarDoorExits/exit-door) (TypeScript) | Core protocol (reference implementation) |
| [@cellar-door/langchain](https://github.com/CellarDoorExits/langchain) (TypeScript) | LangChain integration (TypeScript) |

**[Paper](https://cellar-door.dev/paper/) · [Website](https://cellar-door.dev)**

## License

MIT
