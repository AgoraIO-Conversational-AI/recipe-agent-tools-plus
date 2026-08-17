# Agora Conversational AI — Tools Plus Recipe (Python)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Bun](https://img.shields.io/badge/bun-latest-black)](https://bun.sh/)

The **tools-plus** recipe in the Agora Conversational AI recipes family. This
recipe demonstrates a smart-home voice assistant backed by a custom
OpenAI-compatible `POST /chat/completions` endpoint. The endpoint implements
three novel capabilities on top of the base tool-calling pattern:

- **Room modes (update_tools)** — the user switches rooms ("go to the bedroom")
  and the active device set changes. Only the devices available in the current
  room can be controlled. Room + device state is stored in SQLite and survives
  restarts.
- **Keyword scenes** — saying "movie night", "good night", or "i'm home" runs a
  preset batch of device commands regardless of the current room.
- **Mocked home API** — a zero-key SQLite-backed home assistant simulates
  real device state. `get_status` recalls the current state across reconnects.

Agora cloud never sees a `tool_call` — the home engine runs entirely inside the
`/llm` endpoint (mounted into the same backend process) and streams back only the
spoken reply. STT (Deepgram nova-3) and TTS (MiniMax) stay Agora-managed.

## Prerequisites

- [Python 3.10+](https://www.python.org/)
- [Bun](https://bun.sh/)
- [Agora CLI](https://github.com/AgoraIO/cli) — makes generating an App ID + App Certificate easy
- [ngrok](https://ngrok.com/) — the backend must be publicly reachable so Agora cloud can call `/llm`

The same commands work on macOS, Linux, and Windows. On macOS/Linux, setup uses
`python3`; on Windows, it uses the Python launcher (`py`) or `python`. WSL and
virtualenv activation are not required.

## Run It

```bash
# 1. Install + create the Python venv
bun run setup

# 2. Add Agora credentials (CLI), or edit server/.env.local by hand
agora login
agora project use <your-project>          # select which project to use
agora project env write server/.env.local # writes App ID/Certificate

# 3. Expose the backend publicly (Agora cloud calls /llm/chat/completions directly)
ngrok http 8000

# 4. Add the tunnel URL to server/.env.local
#    CUSTOM_LLM_URL=https://<your-tunnel>.ngrok-free.dev/llm/chat/completions

# 5. Run backend + frontend
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) → **Start Conversation** → speak.

Try: "turn on the TV", "go to the bedroom", "movie night", "what's on".

### Working from a clone

If you cloned this repo directly, the steps above are complete as written.
`bun run setup` creates the Python venv and installs web dependencies, then
`bun run dev` brings up the backend and frontend. You still need Agora credentials
in `server/.env.local` and a public `CUSTOM_LLM_URL` tunnel before a conversation
can connect.

Services:

- Frontend — http://localhost:3000
- Backend — http://localhost:8000 (also serves `/llm`)
- API docs — http://localhost:8000/docs

## Deploy

Deploy `web` (Next.js) and `server` (a single publicly reachable FastAPI process
that also serves `/llm`, so Agora cloud can reach `/llm/chat/completions`). Set
`AGENT_BACKEND_URL` in the web deployment so the Next rewrites reach the backend.

**Docker image** — `ghcr.io/AgoraIO-Conversational-AI/recipe-agent-tools-plus`
is published on `v*` tags. The image runs a single process on :8000; it serves
both the token endpoints and the `/llm` sub-app. Point `CUSTOM_LLM_URL` at
`<public-url>/llm/chat/completions`.

> **Co-public caveat:** because `/llm/chat/completions` and `/get_config` share
> one port, the same tunnel or load-balancer rule that exposes `/llm` to Agora
> cloud also exposes the token endpoints. For production, add authentication or
> split behind a reverse proxy.

## Environment variables

Backend env file: [`server/.env.example`](server/.env.example).

| Variable | Required | Default | Notes |
| --- | :---: | :---: | --- |
| `AGORA_APP_ID` | ✅ | — | Agora Console → Project → App ID |
| `AGORA_APP_CERTIFICATE` | ✅ | — | Agora Console → Project → App Certificate (server only) |
| `CUSTOM_LLM_URL` | ✅ | — | **Public** URL of the `/llm/chat/completions` sub-app — same host as the backend, e.g. `https://<tunnel>/llm/chat/completions`. Agora cloud calls it; cannot be `localhost`. |
| `CUSTOM_LLM_API_KEY` | ✅ | `any-key-here` | Forwarded by Agora cloud as `Authorization: Bearer`. Required by the `CustomLLM` vendor. |
| `CUSTOM_LLM_MODEL` |  | `smarthome-mock` | Model name passed to the endpoint |
| `AGENT_GREETING` |  | built-in | Optional opening line override |
| `HOME_DB_PATH` |  | `/tmp/home.db` | SQLite file for device and mode state |
| `PORT` |  | `8000` | Backend port |
| `AGENT_BACKEND_URL` (web deploy) | ✅ | — | Required in a deployed `web` app when proxying to the backend |

## Commands

```bash
bun run setup            # install web deps + create server/ venv
bun run dev              # run backend (:8000, also /llm) + web (:3000)

bun run doctor           # prerequisite check (no creds needed)
bun run doctor:local     # + .env.local + credentials + CUSTOM_LLM_URL checks

bun run verify           # web-only gate (no Agora creds needed)
bun run verify:local     # full local gate: backend compile + smoke tests + web build
bun run clean            # remove venv and build artifacts
```

Tests run standalone (no Agora cloud needed): `pytest` in `server/` (11 tests), plus
`bun run verify` in `web/`.

## Architecture

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js  ──rewrite──▶  Agent backend  (server/, localhost:8000)
                          │  starts agent session (CustomLLM vendor)
                          │  also serves /llm/chat/completions (in-process)
                          ▼
                       Agora ConvoAI Cloud
                          │  POST <CUSTOM_LLM_URL>   (Authorization: Bearer)
                          ▼
                       /llm sub-app  (same process, same port)
                          ▲  public via ngrok tunnel
                          │  room modes + scenes + SQLite state, streams reply
```

The browser only ever calls Next `/api/*`, which rewrites to the agent backend.
The agent backend owns Agora tokens, agent lifecycle, and the `/llm` sub-app.
See [ARCHITECTURE.md](./ARCHITECTURE.md).

## What You Get

- A **Next.js** web client (:3000) that drives the RTC/RTM lifecycle and only
  ever calls `/api/*`.
- A **FastAPI** agent backend (:8000) that owns Agora token generation, the
  agent session lifecycle, and the `/llm` sub-app.
- The `/api/get_config` · `/api/startAgent` · `/api/stopAgent` contract between
  the web client and the backend (Next rewrites, no Route Handlers).
- A **smart-home engine** inside `server/src/llm.py` with:
  - Room modes that gate available device tools (update_tools pattern).
  - Keyword scenes that run device batches ("movie night", "good night", "i'm home").
  - A mocked home API backed by SQLite for device and mode state.
  - `get_status` recall so the user can ask what devices are on.
- A **zero-key mock** so the full pipeline runs with no external API key.

## How It Works

1. The browser calls `/api/get_config`, which Next rewrites to the backend; the
   backend mints an Agora token from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.
2. The browser joins the RTC channel, then calls `/api/startAgent`; the backend
   starts an agent session using the `CustomLLM` vendor pointed at
   `CUSTOM_LLM_URL`.
3. The user speaks. Agora runs STT (Deepgram nova-3), then sends the transcript
   to `/llm/chat/completions` as an OpenAI `POST /chat/completions` request,
   forwarding `CUSTOM_LLM_API_KEY` as `Authorization: Bearer`.
4. Inside the sub-app, `run_agent_turn()` routes the turn:
   - Status recall keywords → `get_status()` reads device states from SQLite.
   - Keyword scenes → `activate_scene()` runs a batch of device commands.
   - Room keywords + switch/go-to → `set_mode()` changes the active room mode
     and updates available device tools (update_tools pattern).
   - Device keywords → `set_device()` controls the device if it's in the current
     room, or returns a friendly "not available here" message.
   - The sub-app streams **only** the spoken reply in OpenAI SSE chunk format.
5. Agora runs TTS (MiniMax) on the streamed reply and plays it back in the
   channel. Agora cloud never observes the internal tool execution.
6. `/api/stopAgent` ends the session.

### Replacing the mock

Edit `run_agent_turn()` and the home-API functions in
[`server/src/llm.py`](server/src/llm.py) to call a real home automation system
(e.g. Home Assistant REST API). The sub-app must keep speaking the OpenAI
streaming `/chat/completions` contract. A production sub-app should also validate
the `Authorization: Bearer` header.

## Repo Map

- `web/` — Next.js frontend (:3000); RTC/RTM lifecycle and UI.
- `server/` — FastAPI backend (:8000); Agora tokens + agent lifecycle + `/llm` sub-app.
- `server/src/llm.py` — OpenAI-compatible smart-home mock; room modes, keyword scenes, SQLite device + mode state.
- `ARCHITECTURE.md` — system shape and component boundaries.
- `AGENTS.md` — guide for coding agents working in this repo.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Agent starts but never speaks | `CUSTOM_LLM_URL` is not public or omits `/llm/chat/completions`. Use your ngrok URL. |
| `doctor:local` warns about localhost | Replace the local URL with your public tunnel URL. |
| Local calls fail / hang under a global proxy | Configure your proxy to send `127.0.0.1`, `localhost`, and RFC-1918 ranges DIRECT. |

## More Docs

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [AGENTS.md](./AGENTS.md)

## License

Released under the [MIT License](./LICENSE).
