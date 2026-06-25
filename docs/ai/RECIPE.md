---
recipe_version: 1.0.0
recipe_status: experimental
extension_points:
  - id: api.routes
    name: Browser-facing API routes
  - id: agent.vendor-chain
    name: CustomLLM base_url/api_key/model, DeepgramSTT model/language, MiniMaxTTS model/voice, AgoraAgent parameters
  - id: llm.home-engine
    name: Room modes, keyword scenes, device functions, and SQLite schema in llm.py
  - id: web.conversation-ui
    name: Conversation UI panels and controls
  - id: verification.contracts
    name: Contract, proxy, and local FastAPI smoke verification
invariants:
  - id: api.rewrite-boundary
    summary: Browser calls stay on /api/* and Next rewrites to FastAPI; no Route Handlers for agent/token logic.
  - id: secrets.server-only
    summary: Agora App Certificate and CUSTOM_LLM_API_KEY stay in the Python backend.
  - id: llm.agora-free
    summary: server/src/llm.py must not import agora-agents; it is provider-agnostic.
  - id: llm.url-public
    summary: CUSTOM_LLM_URL must be a public URL; there is no localhost default.
  - id: llm.no-tool-calls-on-wire
    summary: The /llm sub-app streams only the spoken reply; Agora cloud never sees a tool_call chunk.
  - id: token.uid-concrete
    summary: Backend resolves missing, zero, or negative UIDs before issuing an RTC+RTM token.
  - id: db.env-var
    summary: SQLite path uses HOME_DB_PATH (not MESSAGE_DB_PATH); default /tmp/home.db.
stable_contracts:
  - id: env.required
    summary: AGORA_APP_ID, AGORA_APP_CERTIFICATE, CUSTOM_LLM_URL, and CUSTOM_LLM_API_KEY are required; AGENT_BACKEND_URL is required by deployed web rewrites.
  - id: api.core-routes
    summary: GET /api/get_config, POST /api/startAgent, and POST /api/stopAgent remain the browser-facing contract.
  - id: llm.core-route
    summary: POST /llm/chat/completions and GET /llm/health are the Agora-cloud-facing contract.
  - id: response.envelope
    summary: Successful backend token-route responses use { code, msg, data }.
  - id: llm.sse-format
    summary: The /llm endpoint streams role chunk → content chunks → stop chunk → data:[DONE] in OpenAI SSE format.
---

# Recipe Contract

This base recipe defines the reusable surface for a Python-backed Agora Conversational AI **tools-plus** quickstart: a cascading STT→LLM→TTS pipeline where the LLM stage is a custom OpenAI-compatible endpoint (in-process `/llm` sub-app) backed by a zero-key smart-home mock.

## Recipe Role

- Role: `base` recipe (self-contained, clone-and-run; no `Extends` pin).
- Target audience: developers building a voice agent with custom LLM logic — tool execution, domain routing, or integration with external services — using a Python FastAPI backend and Next.js web client.
- Reuse model: clone, bind project, expose via tunnel, set `CUSTOM_LLM_URL`, run, then replace `run_agent_turn()` and the home-engine functions in `llm.py` with real integration logic.

## Recipe Scope

- Python FastAPI token generation and managed agent session lifecycle.
- A cascading `DeepgramSTT` → `CustomLLM` → `MiniMaxTTS` vendor chain; the `CustomLLM` vendor points at the in-process `/llm` sub-app.
- A provider-agnostic `/llm` sub-app (`server/src/llm.py`) that implements the OpenAI Chat Completions SSE contract; no `agora-agents` dependency.
- A smart-home mock engine with room modes (update_tools pattern), keyword scenes, and SQLite device/mode state — zero external API key required.
- Next.js browser UI with RTC audio, RTM transcript/metrics, connection status.
- Rewrite-only `/api/*` browser facade hiding backend placement.
- Contract, proxy, and local FastAPI smoke verification that need no live Agora calls.

## Baseline Implementation Guidance

Use this repo's source and progressive disclosure docs as the starting point, then customize. Do not recreate the Agora ConvoAI integration from memory — vendor schemas, SDK builder fields, token behavior, and RTM details drift. Copy verified patterns from this repo.

## Extension Points

| ID | Surface | How to extend | Required follow-up |
| -- | ------- | ------------- | ------------------ |
| `api.routes` | `server/src/server.py`, `web/next.config.ts`, `web/src/services/api.ts` | Add FastAPI route, add rewrite, add browser fetch helper. | Extend `web/scripts/verify-api-contracts.ts`; add proxy/fastapi coverage if it belongs in local verification. |
| `agent.vendor-chain` | `server/src/agent.py` | Change `CUSTOM_LLM_URL`, `CUSTOM_LLM_MODEL`, STT model/language, TTS model/voice, `AgoraAgent` parameters. | Run `verify:backend` + `pytest tests`; document new env in `server/.env.example` (never add `PORT`). |
| `llm.home-engine` | `server/src/llm.py` | Add rooms to `TOOLS_BY_MODE`, add scenes to `SCENES`, add device functions, replace mock with real API calls. | Keep `llm.py` agora-free; update `test_smarthome.py`; verify SSE contract. |
| `web.conversation-ui` | `web/src/components/*`, `web/src/lib/conversation.ts` | Customize pre-call, transcript, metrics, connection status, mic, or visualizer UI. | Preserve RTC/RTM lifecycle ownership and transcript UID normalization. |
| `verification.contracts` | `web/scripts/*.ts`, root `package.json` | Add checks for new browser/backend boundaries. | Keep checks runnable without live Agora credentials. |

## Invariants

- Browser code calls only `/api/get_config`, `/api/startAgent`, and `/api/stopAgent` for the default flow.
- Next.js owns `/api/*` through rewrites only; no `web/app/api/**/route.ts` for agent/token logic.
- FastAPI owns token generation, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_API_KEY`, and agent lifecycle.
- `server/src/llm.py` must not import `agora-agents`; the AST check in `test_llm_mount.py` enforces this.
- `CUSTOM_LLM_URL` must be a public URL; there is no localhost default.
- The `/llm` sub-app streams only the spoken reply — Agora cloud never sees a `tool_call`.
- The backend issues one RTC+RTM-capable token for a concrete non-zero UID.
- SQLite path is `HOME_DB_PATH`, not `MESSAGE_DB_PATH`.

## Stable Contracts

| Contract | Stable shape |
| -------- | ------------ |
| Required backend env | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, `CUSTOM_LLM_API_KEY` |
| Optional backend env | `CUSTOM_LLM_MODEL`, `AGENT_GREETING`, `HOME_DB_PATH`, `PORT` (env only) |
| Required web deploy env | `AGENT_BACKEND_URL` |
| `GET /api/get_config` | Query `channel?`, `uid?`; returns `data.app_id`, `data.token`, `data.uid`, `data.channel_name`, `data.agent_uid`. |
| `POST /api/startAgent` | Body `{ channelName, rtcUid, userUid, parameters? }`; returns `data.agent_id`, `data.channel_name`, `data.status`. |
| `POST /api/stopAgent` | Body `{ agentId }`; returns `{ code: 0, msg: "success" }`. |
| `POST /llm/chat/completions` | OpenAI SSE: role chunk → content chunks → stop chunk → `data: [DONE]`. Only `stream: true` accepted. |
| `GET /llm/health` | Returns `{ "status": "ok", "service": "smarthome-mock" }`. |
| Success envelope | `{ "code": 0, "msg": "success", "data": ... }` where the route has data. |
| Verification entry points | `bun run verify:web`, `bun run verify:backend`, `bun run verify:web:proxy`, `bun run verify:local:fastapi`, `bun run verify:local`. |

## Internal / Subject to Change

- Visual layout, component composition, Tailwind classes, and assets under `web/src/components/`.
- Exact room names, device lists, scene keywords, and `run_agent_turn()` routing logic, as long as they stay documented extension points.
- In-memory `Agent._sessions` details; the stable behavior is start by channel/user and stop by returned `agent_id`.
- Verification internals under `web/scripts/`; the stable surface is the root script names and what they assert.
- `agora-agents` SDK minor-version behavior; this recipe lower-bounds `>=2.3.0` but does not freeze every field.

## Related Progressive Disclosure Docs

- `L1/01_setup.md` — setup, env, tunnel, and commands.
- `L1/02_architecture.md` — request flow and topology.
- `L1/05_workflows.md` — common modification workflows.
- `L1/06_interfaces.md` — route, rewrite, env, and SSE contracts.
- `L1/L2/tool_execution_flow.md` — home-engine routing and SSE streaming detail.
- `L1/L2/custom_llm_vendor.md` — `CustomLLM` vendor build and public-URL requirement.
- `L1/L2/session_lifecycle.md` — RTC/RTM/session orchestration.
