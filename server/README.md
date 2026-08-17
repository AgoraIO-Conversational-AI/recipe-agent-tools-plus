# Agora Agent Backend — Smart Home Tools-Plus Recipe

FastAPI service that owns Agora token generation, agent session lifecycle, and the
`/llm` sub-app for the smart-home tools-plus recipe. It is the service the web
client reaches through the Next.js `/api/*` rewrite proxy (port 8000).

## What's different from the base quickstart

The LLM stage uses the SDK's `CustomLLM` vendor instead of a managed
`OpenAI(model="gpt-4o-mini")`. It points the agent at the smart-home `/llm`
sub-app via `CUSTOM_LLM_URL`. The sub-app (`server/src/llm.py`) is mounted
in-process at `/llm` — same port, no second process. STT (Deepgram) and TTS
(MiniMax) remain Agora-managed. The smart-home sub-app handles room modes,
keyword scenes, and device state internally.

## Run

Use the repo-root `README.md` for the full local flow (`bun run dev`). To work on
this module directly:

The root commands below select the correct virtualenv interpreter on macOS,
Linux, and Windows, so activation is not required:

```shell
bun run setup:server
bun run backend
```

## Environment

`server/.env.example` is the template. Required:

- `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE` — Agora project credentials.
- `CUSTOM_LLM_URL` — the **public** `/llm/chat/completions` URL (e.g.
  `https://<tunnel>/llm/chat/completions`). Agora cloud calls this directly, so
  it cannot be `localhost`.
- `CUSTOM_LLM_API_KEY` — forwarded by Agora cloud as `Authorization: Bearer`.
  Required by the `CustomLLM` vendor.

Optional: `CUSTOM_LLM_MODEL` (default `smarthome-mock`), `AGENT_GREETING`,
`HOME_DB_PATH` (default `/tmp/home.db`), `PORT` (default `8000`).

## API

- `GET /get_config` — token + channel/UID config
- `POST /startAgent` — start an agent session
- `POST /stopAgent` — stop an agent session
- `GET /llm/health` — health check for the `/llm` sub-app
- `POST /llm/chat/completions` — OpenAI-compatible smart-home completion (streaming)

The repo-root `bun run verify:local:fastapi` exercises the main routes through the
Next proxy using a fake agent (`scripts/run_fake_server.py`), so no live Agora
session is required.
