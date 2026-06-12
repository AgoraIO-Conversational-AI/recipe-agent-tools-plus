# Smart-Home LLM Endpoint — Mock

An OpenAI-compatible `POST /chat/completions` server (port 8001) that Agora cloud
calls during a conversation. This mock implements a smart-home assistant with
**no LLM API key** required. It demonstrates three capabilities:

- **Room modes (update_tools)** — switching rooms changes the active device set.
  Mode is stored in SQLite; `set_device()` rejects commands for devices not in
  the current room.
- **Keyword scenes** — "movie night", "good night", and "i'm home" run preset
  batches of device commands regardless of the current room.
- **Mocked home API** — device and mode state are stored in a SQLite database
  (`HOME_DB_PATH`, default `home.db`). `get_status()` recalls the current state
  across reconnects.

Only the spoken reply is streamed back; Agora cloud never sees a `tool_call`.

It has no `agora-agents` dependency — it is a plain FastAPI app. Replace the
mock routing in `run_agent_turn()` with calls to a real home automation system.

## Rooms and devices

| Room | Available devices |
| --- | --- |
| `living_room` | tv, lamp, ac |
| `bedroom` | lamp, fan |
| `kitchen` | light, kettle |

## Scenes

| Phrase | Actions |
| --- | --- |
| `movie night` | living_room tv on + living_room lamp dim |
| `good night` | bedroom lamp off + living_room tv off |
| `i'm home` | living_room lamp on + kitchen light on |

## The contract

Implement `POST /chat/completions` returning OpenAI-style SSE:

- first chunk sets `delta.role = "assistant"`
- content chunks carry `delta.content`
- a final chunk sets `finish_reason = "stop"`
- the stream terminates with `data: [DONE]`

Only streaming (`stream: true`) is supported; non-streaming requests return 400.

## Run

```bash
cd llm
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/custom_llm_server.py     # serves on CUSTOM_LLM_PORT (default 8001)
```

## Tests

```bash
cd llm
. venv/bin/activate
pip install -r requirements-dev.txt
pytest tests -v   # 5 tests, no external deps
```

## Expose it publicly

Agora cloud — not the browser — calls this server, so it must be reachable from
the public internet. For local dev, tunnel it:

```bash
ngrok http 8001
```

Then set `CUSTOM_LLM_URL=https://<tunnel>/chat/completions` in `server/.env.local`.

## Auth

This mock does **not** authenticate. A production endpoint should validate the
`Authorization: Bearer <CUSTOM_LLM_API_KEY>` header that Agora cloud forwards.

## Replace the mock

Edit `run_agent_turn()` and the home-API functions in `src/custom_llm_server.py`
to call a real home automation system (e.g. Home Assistant REST API, Matter,
or your own device registry). The endpoint must keep speaking the OpenAI
streaming `/chat/completions` contract.
