# Architecture — Smart Home Tools-Plus Recipe

Single backend process. The browser talks only to Next.js `/api/*`, which rewrites
to the agent backend. The agent backend owns Agora tokens, agent lifecycle, and the
`/llm` sub-app. **Agora cloud** calls `/llm/chat/completions` on the same public URL.

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
  │  also serves /llm (in-process sub-app, same port)
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT (managed)
  │  POST <CUSTOM_LLM_URL>/chat/completions   (Authorization: Bearer <key>)
  ▼
/llm sub-app (server/src/llm.py, same process, public via tunnel)
  │  room mode gates device tools (update_tools pattern)
  │  keyword scenes run device batches
  │  SQLite stores device + mode state (HOME_DB_PATH)
  │  streams only spoken reply (OpenAI SSE)
  ▼
Agora ConvoAI Cloud → MiniMax TTS (managed) → user hears speech
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## Smart-home engine (server/src/llm.py)

The smart-home engine runs entirely inside the `/llm` sub-app. It owns a SQLite
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

## Single-process design

`server/src/llm.py` is mounted into the FastAPI app at `/llm` (`app.mount("/llm",
llm_app)`). Both the token endpoints and the smart-home completion endpoint are
served by the same process on the same port (:8000). There is no second port,
no supervisor, and no inter-process communication.

> **Co-public caveat:** because `/llm/chat/completions` and `/get_config` share
> one port, exposing the backend publicly (for Agora cloud to reach `/llm`) also
> exposes the token endpoints. For production, add authentication or split behind
> a reverse proxy.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |
| `/llm/chat/completions` | POST | OpenAI-compatible smart-home completion (streaming) |
| `/llm/health` | GET | Health check for the `/llm` sub-app |

The browser calls the first three as `/api/*`; Next rewrites them to
`AGENT_BACKEND_URL`.

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007, generated from `AGORA_APP_ID` +
  `AGORA_APP_CERTIFICATE`.
- Agora cloud → `/llm/chat/completions`: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
  The mock sub-app does not validate it; a production sub-app should.
