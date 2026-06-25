# 08 · Security

> Trust boundaries, secret handling, and auth for the tools-plus recipe.

## Trust boundaries

| Hop                                  | Auth                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------- |
| Browser → agent backend              | None in local dev (the `/api/*` rewrite is same-origin).                  |
| Agent backend → Agora cloud          | Token007, generated from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.        |
| Agora cloud → `/llm/chat/completions`| `Authorization: Bearer <CUSTOM_LLM_API_KEY>` forwarded by Agora cloud.   |

## Secret handling

- **Server-only secrets:** `AGORA_APP_CERTIFICATE` and `CUSTOM_LLM_API_KEY` live only in `server/.env.local` and never reach the browser. The browser receives a short-lived token, never the certificate or the LLM key.
- `server/.env.local` is gitignored; `server/.env.example` ships placeholders only.
- Tokens (`generate_convo_ai_token`) expire after 3600s and are minted per `get_config` call for a concrete non-zero UID.
- `CUSTOM_LLM_URL` is a public URL by design — it is the address Agora cloud uses to call the `/llm` sub-app.

## Bearer token validation

The mock `/llm` sub-app accepts any `Authorization` header (or none) — it does **not** validate the bearer token. A production sub-app should validate `Authorization: Bearer <CUSTOM_LLM_API_KEY>` to prevent unauthenticated callers from invoking the completion endpoint.

## Co-public caveat

Because `/llm/chat/completions` and the token endpoints (`/get_config`, `/startAgent`, `/stopAgent`) share one port and one public URL, exposing the backend publicly for Agora cloud also exposes the token endpoints. For production, add authentication to the token endpoints or split the service behind a reverse proxy that routes `/llm` separately.

## CORS

The backend sets `CORSMiddleware` with `allow_origins=["*"]` — open by design for a local/dev recipe. **Lock this down to known origins before any production deployment.**

## Validation

- `Agent.__init__` rejects missing `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, or `CUSTOM_LLM_API_KEY`.
- `Agent.start()` rejects empty `channel_name` and non-positive `agent_uid`/`user_uid`.
- Route errors are sanitized: `_log_route_error` logs only non-`None` context; SDK exceptions map to 400/500 without leaking internals to the client beyond the message.

## Deployment notes

- Set `AGENT_BACKEND_URL` only to a backend you control; the rewrite forwards browser requests there verbatim.
- The published Docker image is **backend-only** (`:8000`); it does not bundle secrets. Point `CUSTOM_LLM_URL` at `<public-url>/llm/chat/completions` after deployment.

## Related Deep Dives

- None.
