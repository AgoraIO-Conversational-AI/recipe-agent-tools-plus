# Deep Dive — Tool Execution Flow

> **When to Read This:** You are changing the smart-home engine, adding rooms or scenes, debugging LLM turn routing, or modifying the SSE streaming contract. For the high-level picture, start at [02_architecture](../02_architecture.md).

Agora cloud calls `POST /llm/chat/completions` (the in-process `/llm` sub-app) after Deepgram STT transcribes the user's speech. The sub-app routes the turn, updates SQLite, and streams only the spoken reply. **Agora cloud never sees a `tool_call`** — all tool execution is internal.

## Intent routing in `run_agent_turn()`

`run_agent_turn(conn, messages)` extracts the last user message text and dispatches by keyword priority:

```
1. Recall keywords ("status", "what's on", "which devices") → get_status()
2. Scene keywords ("movie night", "good night", "i'm home")  → activate_scene()
3. Room keywords + switch intent ("go to", "switch", "i'm in", "mode") → set_mode()
4. Device keyword present                                    → set_device()
5. Fallback                                                  → help text
```

All routing is pure keyword matching — no LLM or embedding call.

## Room modes (update_tools pattern)

The current room mode is stored in SQLite `settings` table (key `'mode'`, default `'living_room'`). `set_device()` reads the current mode on **every** call and rejects commands for devices not in the active room's tool set.

| Room          | Devices            |
| ------------- | ------------------ |
| `living_room` | tv, lamp, ac       |
| `bedroom`     | lamp, fan          |
| `kitchen`     | light, kettle      |

When the user switches rooms, `set_mode(conn, room)` updates the `settings` row and returns a confirmation listing the now-available devices.

## Keyword scenes

`activate_scene(conn, name)` runs a batch of device commands directly in SQLite, regardless of current room mode:

| Scene        | Actions                                              |
| ------------ | ---------------------------------------------------- |
| `movie night`| living_room tv → on; living_room lamp → dim          |
| `good night` | bedroom lamp → off; living_room tv → off             |
| `i'm home`   | living_room lamp → on; kitchen light → on            |

## SQLite state model

Two tables in `HOME_DB_PATH` (default `/tmp/home.db`):

- `devices(room TEXT, device TEXT, state TEXT)` — PRIMARY KEY `(room, device)`.
- `settings(key TEXT, value TEXT)` — holds `mode = <room>`.

`get_db(path)` creates tables and seeds the default mode on first open. `get_status()` reads all `devices` rows and formats a summary string.

## SSE streaming contract

After `run_agent_turn()` resolves the reply string, the streaming generator yields:

1. A **role chunk**: `delta = { "role": "assistant", "content": "" }`, `finish_reason = null`.
2. **Content chunks**: one word per chunk (50ms delay), `delta = { "content": "<word>" }`, `finish_reason = null`.
3. A **stop chunk**: `delta = {}`, `finish_reason = "stop"`.
4. The **DONE terminator**: `data: [DONE]`.

The DB connection is opened and closed **before** the generator runs — the generator is DB-free. This avoids SQLite threading issues under FastAPI's async runtime.

## Replacing the mock

To connect a real home-automation API:

1. Replace the home-engine functions (`set_device`, `activate_scene`, `get_status`, etc.) with real API calls.
2. Keep the `POST /chat/completions` SSE contract intact — the chunk format is asserted by `test_llm.py::test_streaming_sse_contract`.
3. Add `Authorization: Bearer` validation to the endpoint.
4. Keep `llm.py` free of `agora-agents` imports.

## Related L1

- [02_architecture](../02_architecture.md) · [04_conventions](../04_conventions.md) · [06_interfaces](../06_interfaces.md) · [07_gotchas](../07_gotchas.md)
