# 03 · Code Map

> Where things live. Two top-level modules: `web/` (Next.js client) and `server/` (FastAPI backend + `/llm` sub-app). Orchestration is in the root `package.json`.

## Root

| Path                  | Responsibility                                                        |
| --------------------- | --------------------------------------------------------------------- |
| `package.json`        | Bun workspace; `setup`, `dev`, `doctor*`, `verify*`, `clean` scripts. |
| `README.md`           | Setup, run modes, env, troubleshooting.                               |
| `ARCHITECTURE.md`     | System shape, smart-home engine detail, API table.                    |
| `AGENTS.md`           | Coding-agent handbook + How to Load / Git Conventions / Doc Commands. |
| `Dockerfile`          | Backend-only image (`:8000`).                                         |
| `.github/workflows/`  | `ci.yml` (backend pytest matrix + web verify), `docker.yml`, `nightly.yml`. |

## `server/` — FastAPI backend (:8000)

| Path                              | Responsibility                                                                 |
| --------------------------------- | ------------------------------------------------------------------------------ |
| `src/server.py`                   | FastAPI app, CORS, route handlers, error mapping, `/llm` mount, uvicorn entry.|
| `src/agent.py`                    | `Agent` class: `AsyncAgora` client, `CustomLLM`/`DeepgramSTT`/`MiniMaxTTS` vendor build, `start()`/`stop()`, `_sessions`. |
| `src/llm.py`                      | Provider-agnostic smart-home sub-app: room modes, keyword scenes, SQLite state, `run_agent_turn()`, SSE streaming. No `agora-agents` dependency. |
| `scripts/run_fake_server.py`      | Boots `server.app` with a `FakeAgent` for the local FastAPI smoke test.        |
| `tests/test_agent_construction.py`| Builds the real `AgoraAgent`, fakes the SDK session, asserts shape.            |
| `tests/test_llm.py`               | Contract tests for the mock LLM endpoint in isolation (health, SSE, non-streaming rejection). |
| `tests/test_llm_mount.py`         | Asserts `/llm` is mounted under `server.app`; verifies `llm.py` has no agora imports. |
| `tests/test_smarthome.py`         | Behavioural tests: default mode, mode switching, device gating, scenes, status recall. |
| `tests/conftest.py`               | `fake_env` fixture + `FakeAgent`; no cloud, no real creds.                     |
| `.env.example`                    | Env template (do not add `PORT`).                                              |
| `requirements*.txt`               | Runtime + dev (pytest) deps.                                                   |

## `server/src/server.py` routes

- `GET /get_config` — token + channel/UID config.
- `POST /startAgent` — start the agent session with `CustomLLM` vendor.
- `POST /stopAgent` — stop by `agent_id`.
- `POST /llm/chat/completions` — OpenAI-compatible smart-home completion (streaming). Mounted from `llm.py`.
- `GET /llm/health` — health check for the `/llm` sub-app.

## `web/` — Next.js client (:3000)

| Path                                      | Responsibility                                                    |
| ----------------------------------------- | ----------------------------------------------------------------- |
| `next.config.ts`                          | `/api/*` rewrites to `AGENT_BACKEND_URL`; strict mode; Turbopack root. |
| `src/services/api.ts`                     | Browser API client: `getConfig`, `startAgent`, `stopAgent`.       |
| `src/lib/conversation.ts`                 | Transcript normalization, timestamp/UID mapping, visualizer state.|
| `src/lib/agora.ts`                        | `DEFAULT_AGENT_UID` constant.                                     |
| `src/components/LandingPage.tsx`          | Conversation entry: config fetch, agent start, RTM login, teardown.|
| `src/components/ConversationComponent.tsx`| RTC join, mic publish, transcript/metrics/state listeners.        |
| `src/components/Quickstart*.tsx`          | Pre-call, transcript, metrics, layout panels.                     |
| `scripts/verify-api-contracts.ts`         | Asserts rewrites + client paths + response envelope (no network). |
| `scripts/verify-local-proxy.ts`           | Stub backend; proxies `/api/*` through the rewrite map.           |
| `scripts/verify-local-fastapi.ts`         | Spawns real FastAPI with `FakeAgent`; proxies routes end-to-end.  |
| `scripts/verify-local-llm.ts`             | Spawns the `/llm` sub-app standalone; asserts SSE contract.       |
| `scripts/doctor.ts`                       | Web prerequisite check.                                           |
| `.claude/skill-*.md`                      | Contributor reference notes for RTC/RTM/ConvoAI integration.      |

## Related Deep Dives

- None. For runtime flow see [02_architecture](02_architecture.md); for contracts see [06_interfaces](06_interfaces.md).
