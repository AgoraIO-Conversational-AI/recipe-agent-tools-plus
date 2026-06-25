# 05 · Workflows

> Step-by-step guides for the common changes in this recipe. Each ends with the narrowest verify command to run.

## Add or change a browser-facing route

1. Add the FastAPI handler in `server/src/server.py` (return the `{ code, msg, data }` envelope).
2. Add the `/api/<name>` → `/<name>` mapping in `web/next.config.ts` `rewrites()`.
3. Add a client helper in `web/src/services/api.ts`.
4. Extend `web/scripts/verify-api-contracts.ts` with the new path + envelope assertions.
5. Verify: `bun run verify:web` (and `bun run verify:local:fastapi` if it should go through the real backend).

## Change the agent prompt / greeting / model

1. Greeting: set `AGENT_GREETING` (env) or edit the default in `server/src/agent.py`.
2. LLM model name: set `CUSTOM_LLM_MODEL` (env, default `smarthome-mock`).
3. STT/TTS vendor parameters: edit `Agent.start()` in `server/src/agent.py` — `DeepgramSTT` and `MiniMaxTTS` vendor constructors.
4. Verify: `bun run verify:backend` (compile) + `cd server && pytest tests -v`.

## Extend the smart-home engine

1. Add rooms to `ROOMS` / `TOOLS_BY_MODE`, add scenes to `SCENES`, or add device functions in `server/src/llm.py`.
2. Keep `llm.py` free of `agora-agents` imports — `test_llm_mount.py::test_llm_module_has_no_agora_dependency` asserts this.
3. Update `test_smarthome.py` to cover new behavior.
4. Verify: `cd server && pytest tests -v`.

## Replace the mock with a real home integration

1. Replace the home-engine functions in `server/src/llm.py` with real home-automation API calls (e.g. Home Assistant REST).
2. Keep the `POST /chat/completions` SSE contract intact — Agora cloud expects it.
3. Add `Authorization: Bearer` validation to the endpoint (the mock skips it).
4. Verify: `cd server && pytest tests -v`.

## Adjust session parameters (codec, VAD)

1. Edit the `parameters` dict or `turn_detection` dict in `Agent.start()` (`server/src/agent.py`). `output_audio_codec` is also accepted per-request via `parameters` on `POST /startAgent`.
2. Verify: `bun run verify:local:fastapi`.

## Run / debug locally

```bash
bun run dev              # both processes
bun run doctor:local     # check creds + .env.local before a live call
```

`doctor:local` warns if `CUSTOM_LLM_URL` points at localhost — replace it with your tunnel URL.

## Verify before finishing

| Change touches…                 | Run                                                                 |
| ------------------------------- | ------------------------------------------------------------------- |
| Web only                        | `bun run verify:web`                                                |
| Backend logic / vendor config   | `bun run verify:backend` + `cd server && pytest tests -v`           |
| Route/proxy boundary            | `bun run verify:web:proxy` and/or `bun run verify:local:fastapi`    |
| Anything end-to-end (local)     | `bun run verify:local`                                              |

## Deploy

1. Deploy `web/` as a Next.js app.
2. Deploy `server/` as a single publicly reachable FastAPI process (it also serves `/llm`). The published backend-only image is `ghcr.io/AgoraIO-Conversational-AI/recipe-agent-tools-plus` on `v*` tags.
3. Set `AGENT_BACKEND_URL` in the web deployment so rewrites reach the backend.
4. Set `CUSTOM_LLM_URL` to `<public-url>/llm/chat/completions` so Agora cloud can reach the endpoint.

## Related Deep Dives

- [tool_execution_flow](L2/tool_execution_flow.md) — home-engine routing and SSE streaming detail.
- [session_lifecycle](L2/session_lifecycle.md) — client-side join/renewal/teardown.
