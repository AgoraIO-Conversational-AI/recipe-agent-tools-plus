# 02 · Architecture

> Single backend process. The browser talks only to Next.js `/api/*`, which rewrites to the FastAPI agent backend. The backend owns Agora tokens, the agent session, and the `/llm` sub-app. Agora cloud calls `/llm/chat/completions` on the same public URL; STT (Deepgram) and TTS (MiniMax) remain Agora-managed.

## Topology

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js (web/)  ──rewrite──▶  Agent backend (server/, :8000)
                                 │  builds CustomLLM vendor (base_url=CUSTOM_LLM_URL)
                                 │  also serves /llm (in-process sub-app, same port)
                                 ▼
                              Agora ConvoAI Cloud
                                 │  user speech → Deepgram STT (managed)
                                 │  POST <CUSTOM_LLM_URL>/chat/completions (Bearer key)
                                 ▼
                              /llm sub-app (server/src/llm.py, public via ngrok tunnel)
                                 │  room mode gates device tools (update_tools pattern)
                                 │  keyword scenes run device batches
                                 │  SQLite stores device + mode state
                                 │  streams only spoken reply (OpenAI SSE)
                                 ▼
                              Agora ConvoAI Cloud → MiniMax TTS → user hears speech
                                                  → RTM transcript + metrics → web UI
```

- **`web/`** — Next.js 16 / React 19 / TypeScript. Owns UI plus the RTC/RTM client lifecycle. Calls only `/api/*`.
- **`server/`** — Python FastAPI (:8000). Owns Agora token generation, agent session lifecycle, and the `/llm` sub-app. SDK: `agora-agents>=2.3.0` (`import agora_agent`).
- **`server/src/llm.py`** — provider-agnostic FastAPI app mounted at `/llm`. No `agora-agents` dependency; Agora cloud never sees a `tool_call`.

## Request lifecycle

1. Browser `GET /api/get_config` → Next rewrites to backend `/get_config`; backend mints a Token007 and returns channel + UIDs.
2. Browser joins the RTC channel, then `POST /api/startAgent`; backend builds the `CustomLLM` vendor and starts an async agent session.
3. User speaks → Deepgram STT → Agora sends transcript to `/llm/chat/completions` as an OpenAI-format POST.
4. `/llm` sub-app routes the turn (recall → scene → mode → device), updates SQLite, and streams only the spoken reply in OpenAI SSE chunks.
5. Agora runs MiniMax TTS on the streamed reply and delivers it into the channel. RTM carries transcript + metrics to the web UI.
6. `POST /api/stopAgent { agentId }` ends the session.

## Why a single process

`server/src/llm.py` is mounted into the FastAPI app at `/llm` (`app.mount("/llm", llm_app)`). Both the token endpoints and the smart-home completion endpoint are served by the same process on the same port. There is no second port, no supervisor, and no inter-process communication.

> **Co-public caveat:** because `/llm/chat/completions` and `/get_config` share one port, the same tunnel that exposes `/llm` to Agora cloud also exposes the token endpoints. For production, add authentication or split behind a reverse proxy.

## Key abstractions

- **`Agent`** (`server/src/agent.py`) — async wrapper around `AgoraAgent`; uses `CustomLLM`, `DeepgramSTT`, and `MiniMaxTTS` vendors. Owns the `AsyncAgora` client, env, and the in-memory `_sessions` map keyed by `agent_id`.
- **`run_agent_turn(conn, messages)`** (`server/src/llm.py`) — top-level router inside the `/llm` sub-app; dispatches by keyword to recall → scene → mode → device → help, then streams the reply.
- **Rewrite proxy** (`web/next.config.ts`) — the only browser→backend boundary; no Next Route Handlers exist for agent/token logic.

## Tech decisions

- **Cascading STT→LLM→TTS** — unlike MLLM recipes, this one uses `DeepgramSTT` + `CustomLLM` + `MiniMaxTTS` as three separate vendors. The LLM stage is the custom `/llm` endpoint.
- **In-process `/llm` sub-app** — avoids a second port, second venv, or inter-process communication. The sub-app is provider-agnostic (no `agora-agents` import).
- **Zero-key mock** — `HOME_DB_PATH` SQLite store means no external API key is needed to run the full pipeline.
- **VAD on `AgoraAgent`** — turn detection config (`start_of_speech`/`end_of_speech` with VAD mode) is set directly on `AgoraAgent(...)`, not on the vendor.

## Related Deep Dives

- [tool_execution_flow](L2/tool_execution_flow.md) — how `run_agent_turn()` routes intents, executes home-engine logic, and streams the reply.
- [session_lifecycle](L2/session_lifecycle.md) — browser orchestration of config + start/stop, RTC/RTM, transcript mapping.
