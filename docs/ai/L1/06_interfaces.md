# 06 · Interfaces

> Boundary contracts: backend routes, the `/api/*` rewrite map, env vars, the response envelope, and the `/llm/chat/completions` SSE contract.

## Backend routes (port 8000)

The browser calls the first three as `/api/<name>`; Next rewrites to the backend `/<name>`. The last two are reached directly by Agora cloud.

### `GET /get_config`

- Query (optional): `channel?: string`, `uid?: int` (≤ 0 or missing → backend generates one).
- Returns `data`: `{ app_id, token, uid (string), channel_name, agent_uid (string) }`.
- Token is a Token007 RTC+RTM token, expiry 3600s, for a concrete non-zero UID.

### `POST /startAgent`

- Body: `{ channelName: string, rtcUid: int, userUid: int, parameters?: object }`.
  - `parameters.output_audio_codec?: string` is the only honored parameter field.
- Returns `data`: `{ agent_id, channel_name, status: "started" }`.
- 400 if `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, or `CUSTOM_LLM_API_KEY` is unset at boot, or if `channelName`/`rtcUid`/`userUid` are invalid.

### `POST /stopAgent`

- Body: `{ agentId: string }`.
- Returns `{ code: 0, msg: "success" }` (no `data`).

### `POST /llm/chat/completions`

- Receives: OpenAI-format `{ model, messages, stream: true, ... }`. Only `stream: true` is accepted.
- Returns: `text/event-stream` SSE response in OpenAI chunk format.
  - First chunk: `delta.role = "assistant"`, `delta.content = ""`.
  - Content chunks: `delta.content = <word>`, one per token.
  - Final chunk: `delta.content = ""`, `finish_reason = "stop"`.
  - Terminator: `data: [DONE]`.
- Authorization: `Authorization: Bearer <CUSTOM_LLM_API_KEY>` forwarded by Agora cloud. The mock does not validate it; a production sub-app should.
- 400 if `stream: false`.

### `GET /llm/health`

- Returns `{ "status": "ok", "service": "smarthome-mock" }`.

## Response envelope

All backend token-route JSON responses use:

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` omitted when the route has no payload. Non-zero `code` or missing `data` = error on the client side.

## Rewrite map (`web/next.config.ts`)

| Browser path        | Backend destination |
| ------------------- | ------------------- |
| `/api/get_config`   | `/get_config`       |
| `/api/startAgent`   | `/startAgent`       |
| `/api/stopAgent`    | `/stopAgent`        |

`rewrites()` returns `[]` when `AGENT_BACKEND_URL` is unset. The contract is asserted by `verify-api-contracts.ts` and exercised by `verify-local-proxy.ts`.

## Browser API client (`web/src/services/api.ts`)

- `getConfig({ channel?, uid? }) → GetConfigResponse`
- `startAgent(channelName, rtcUid, userUid) → agent_id`
- `stopAgent(agentId) → void`

## Environment variables

| Variable                | Scope              | Required | Default                      |
| ----------------------- | ------------------ | :------: | ---------------------------- |
| `AGORA_APP_ID`          | backend            |    ✅    | —                            |
| `AGORA_APP_CERTIFICATE` | backend            |    ✅    | —                            |
| `CUSTOM_LLM_URL`        | backend            |    ✅    | — (must be public, no localhost) |
| `CUSTOM_LLM_API_KEY`    | backend            |    ✅    | `any-key-here`               |
| `CUSTOM_LLM_MODEL`      | backend            |          | `smarthome-mock`             |
| `AGENT_GREETING`        | backend            |          | built-in line                |
| `HOME_DB_PATH`          | backend            |          | `/tmp/home.db`               |
| `AGENT_BACKEND_URL`     | web (deploy)       |    ✅\*  | `http://localhost:8000` (dev) |
| `PORT`                  | backend (env only) |          | `8000` — do **not** put in `.env.example` |

\* Required wherever the web app is deployed; rewrites are empty without it.

## `CustomLLM` vendor config (`agent.py`)

`CustomLLM(base_url, api_key, model, greeting_message, failure_message, max_history, max_tokens, temperature, top_p)` stamps `vendor: "custom"` in the wire config. Both `base_url` and `api_key` are required by the SDK.

## Related Deep Dives

- [tool_execution_flow](L2/tool_execution_flow.md) — full SSE streaming and home-engine routing detail.
