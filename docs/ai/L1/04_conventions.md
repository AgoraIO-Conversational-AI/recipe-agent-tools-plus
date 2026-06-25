# 04 · Conventions

> Coding patterns shared across `server/` and `web/`. Follow these to keep local and deployed modes aligned.

## Boundary ownership

- Browser code calls only `/api/*`. Backend placement is hidden behind Next rewrites (`web/next.config.ts`).
- **Never** add `web/app/api/**/route.ts` for agent/token logic — `verify-api-contracts.ts` fails the build if a `route.ts` appears under `app/api`.
- Token generation and the App Certificate stay in `server/`.
- The `/llm` sub-app lives in `server/src/llm.py` and is **provider-agnostic** — no `agora-agents` import. `test_llm_mount.py` enforces this with an AST check.

## Backend (Python / FastAPI)

- Async throughout: route handlers are `async def`; the agent uses `AsyncAgora` and `create_async_session`.
- Request bodies are Pydantic models (`StartAgentRequest`, `StopAgentRequest`). Field names are **camelCase** (`channelName`, `rtcUid`, `userUid`) to match the browser client.
- Error mapping is centralized: `_to_http_error()` maps `ValueError → 400`, `RuntimeError → 500`, else 500. `_log_route_error()` logs with safe context + traceback. Raise plain `ValueError`/`RuntimeError`; let the route convert.
- Logging via `logging.getLogger("uvicorn.error")`.
- Env read with `os.getenv`; `.env.local` then `.env` loaded with `override=True` in `server.py` (FastAPI app). `llm.py` loads with `override=False` so an injected `CUSTOM_LLM_PORT` takes precedence.

## Response envelope

All backend JSON responses (token routes) use:

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` is present only when the route returns a payload. The `/llm/chat/completions` endpoint returns OpenAI SSE chunks — not the envelope format.

## Agent vendor chain

The agent uses a **cascading** STT → LLM → TTS pipeline:

- **STT:** `DeepgramSTT(model="nova-3", language="en")` — Agora-managed.
- **LLM:** `CustomLLM(base_url=CUSTOM_LLM_URL, api_key=..., model=..., ...)` — points at the in-process `/llm` sub-app.
- **TTS:** `MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")` — Agora-managed.

Both `CUSTOM_LLM_URL` and `CUSTOM_LLM_API_KEY` are validated in `Agent.__init__` — the server does **not** boot without them. The `CUSTOM_LLM_URL` must be a public URL.

## Turn detection

`turn_detection` is configured on `AgoraAgent(...)` directly with `start_of_speech`/`end_of_speech` VAD config — not on the vendor. Do not move it to the `CustomLLM` vendor.

## Smart-home engine (`llm.py`)

- All home-engine functions (`get_db`, `get_mode`, `set_mode`, `set_device`, `activate_scene`, `get_status`, `run_agent_turn`) stay in `server/src/llm.py`.
- State (room mode + device states) lives in SQLite at `HOME_DB_PATH` (not `MESSAGE_DB_PATH`).
- `run_agent_turn()` resolves the full reply string before the streaming generator runs — the generator never touches the DB.

## Web (TypeScript / Next.js)

- Lint/format with Biome (`bun run lint`, `bun run lint:fix` in `web/`).
- RTC client creation must be StrictMode-safe (strict mode is on).
- Transcript speaker mapping: `normalizeTranscript` maps `uid === '0'` to the local UID; do not heuristically guess speakers.
- API client lives in `src/services/api.ts`; UI never calls `fetch` to the backend directly.

## Testing approach

- Backend: `pytest` in `server/`, standalone — `conftest.py` fakes env and SDK session, so no cloud or real creds are needed.
- Web: contract/proxy/fastapi smoke scripts under `web/scripts/` run without live Agora calls.
- Run the **narrowest** relevant verify command before finishing (see [05_workflows](05_workflows.md)).

## Doc upkeep

When you change request/response contracts, env vars, or workflow, update the web client, backend, contract checks, README, **and** the matching `docs/ai/L1/` file together, then bump `Last Reviewed` in [L0](../L0_repo_card.md).

## Related Deep Dives

- None.
