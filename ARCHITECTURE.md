# Architecture — Smart Home Tools-Plus Recipe

Three processes. The browser talks only to Next.js `/api/*`, which rewrites to the
agent backend. The agent backend owns Agora tokens and agent lifecycle. The
smart-home LLM endpoint is a separate service that **Agora cloud** calls directly.

## Request flow

```
Browser
  │  GET /api/get_config            → token + channel/UIDs
  │  POST /api/startAgent           → start agent session
  ▼
Next.js  (rewrites /api/* → AGENT_BACKEND_URL)
  ▼
Agent backend (server/, :8000)
  │  builds session with CustomLLM(base_url=CUSTOM_LLM_URL)
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT (managed)
  │  POST <CUSTOM_LLM_URL>/chat/completions   (Authorization: Bearer <key>)
  ▼
Smart-home LLM endpoint (llm/, :8001, public via tunnel)
  │  room mode gates device tools (update_tools pattern)
  │  keyword scenes run device batches
  │  SQLite stores device + mode state
  │  streams only spoken reply (OpenAI SSE)
  ▼
Agora ConvoAI Cloud → MiniMax TTS (managed) → user hears speech
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## Smart-home engine (llm/)

The smart-home engine runs entirely inside the `llm/` endpoint. It owns a SQLite
database with two tables: `devices` (room, device, state) and `settings` (the
current room mode). Agora cloud never sees a `tool_call` chunk — only the final
spoken reply is streamed.

### Room modes (update_tools pattern)

The current mode is stored in SQLite. When the user switches rooms, `set_mode()`
updates the mode and returns a confirmation listing the devices now available.
`set_device()` reads the current mode on every call and rejects commands for
devices not in the active room's tool set.

Available rooms and their devices:

| Room | Devices |
| --- | --- |
| `living_room` | tv, lamp, ac |
| `bedroom` | lamp, fan |
| `kitchen` | light, kettle |

### Keyword scenes

Saying a scene keyword triggers `activate_scene()`, which writes all the scene's
device commands directly to SQLite regardless of the current room mode.

| Scene | Actions |
| --- | --- |
| `movie night` | living_room tv → on; living_room lamp → dim |
| `good night` | bedroom lamp → off; living_room tv → off |
| `i'm home` | living_room lamp → on; kitchen light → on |

### Status recall

`get_status()` reads all device rows from SQLite and returns a summary. Keywords
like "status", "what is on", "what's on", and "which devices" trigger it.

## Why two backends

`server/` and `llm/` are split because of an **exposure asymmetry**:

- `llm/` must be reachable by **Agora cloud over the public internet** (hence the
  ngrok tunnel). It is the part you replace with your own real home automation
  integration, and it has no Agora dependency.
- `server/` only needs to be reachable by your web tier. It holds the Agora App
  Certificate and all token logic.

In production the two could be co-deployed, but keeping them separate makes the
public-exposure requirement explicit and keeps the home engine independently
testable.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |

The browser calls these as `/api/*`; Next rewrites them to `AGENT_BACKEND_URL`.

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007, generated from `AGORA_APP_ID` +
  `AGORA_APP_CERTIFICATE`.
- Agora cloud → smart-home LLM endpoint: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
  The mock endpoint does not validate it; a production endpoint should.
