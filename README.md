# exit-door-langchain 𓉸

[![PyPI](https://img.shields.io/pypi/v/exit-door-langchain)](https://pypi.org/project/exit-door-langchain/)
[![tests](https://img.shields.io/badge/tests-36_passing-brightgreen)]()
[![Python](https://img.shields.io/pypi/pyversions/exit-door-langchain)](https://pypi.org/project/exit-door-langchain/)
[![license](https://img.shields.io/badge/license-Apache--2.0-blue)](./LICENSE)

> **[𓉸 Passage Protocol](https://cellar-door.dev)** · [exit-door](https://github.com/CellarDoorExits/exit-door) · [entry-door](https://github.com/CellarDoorExits/entry-door) · [mcp](https://github.com/CellarDoorExits/mcp-server) · [langchain](https://github.com/CellarDoorExits/langchain) · [vercel](https://github.com/CellarDoorExits/vercel-ai-sdk) · [eliza](https://github.com/CellarDoorExits/eliza-exit) · [eas](https://github.com/CellarDoorExits/eas-adapter) · [erc-8004](https://github.com/CellarDoorExits/erc-8004-adapter) · [sign](https://github.com/CellarDoorExits/sign-protocol-adapter) · [python](https://github.com/CellarDoorExits/exit-python)

> **⚠️ Pre-release software -- no formal security audit has been conducted.**

LangChain callback handler for EXIT Protocol departure markers. Automatically creates signed departure records when chains or agents complete execution. Thread-safe, fail-safe, works with LCEL and LangGraph.

## Quick Start

```bash
pip install exit-door-langchain
```

```python
from exit_door_langchain import ExitCallbackHandler

handler = ExitCallbackHandler(origin="my-app")

# Use with any LangChain chain
chain.invoke({"input": "hello"}, config={"callbacks": [handler]})

# Markers are collected automatically
print(handler.markers[-1].id)  # urn:exit:abc123...
```

## Configuration

```python
from exit_door import ExitType

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

## Ecosystem

| Package | Language | Description |
|---------|----------|-------------|
| [exit-door](https://github.com/CellarDoorExits/exit-door) | TypeScript | Core protocol (reference impl) |
| [exit-door](https://github.com/CellarDoorExits/exit-python) | Python | Core protocol |
| [cellar-door-entry](https://github.com/CellarDoorExits/entry-door) | TypeScript | Arrival/entry markers |
| [@cellar-door/langchain](https://github.com/CellarDoorExits/langchain) | TypeScript | LangChain integration |
| **[exit-door-langchain](https://github.com/CellarDoorExits/exit-door-langchain-python)** | **Python** | **LangChain integration ← you are here** |
| [@cellar-door/vercel-ai-sdk](https://github.com/CellarDoorExits/vercel-ai-sdk) | TypeScript | Vercel AI SDK |
| [@cellar-door/mcp-server](https://github.com/CellarDoorExits/mcp-server) | TypeScript | MCP server |
| [@cellar-door/eliza](https://github.com/CellarDoorExits/eliza-exit) | TypeScript | ElizaOS plugin |
| [@cellar-door/eas](https://github.com/CellarDoorExits/eas-adapter) | TypeScript | EAS attestation anchoring |
| [@cellar-door/erc-8004](https://github.com/CellarDoorExits/erc-8004-adapter) | TypeScript | ERC-8004 identity/reputation |
| [@cellar-door/sign-protocol](https://github.com/CellarDoorExits/sign-protocol-adapter) | TypeScript | Sign Protocol attestation |

**[Paper](https://cellar-door.dev/paper/) · [Website](https://cellar-door.dev)**

## License

Apache-2.0
