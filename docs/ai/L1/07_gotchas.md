# 07 · Gotchas

> Non-obvious pitfalls specific to the tools-plus recipe. Read before changing the agent, env, verify scripts, or the smart-home engine.

## `CUSTOM_LLM_URL` must be public — there is no localhost default

Agora cloud (not the browser) calls `/llm/chat/completions`. A `localhost` URL starts the agent but all LLM turns silently fail cloud-side. `Agent.__init__` raises `ValueError` if `CUSTOM_LLM_URL` is unset. `doctor:local` warns if the configured URL contains `localhost` or `127.0.0.1`. Use ngrok or a similar public tunnel.

## Both `CUSTOM_LLM_URL` and `CUSTOM_LLM_API_KEY` are validated at boot

Unlike the realtime recipe (where `OPENAI_API_KEY` is validated at agent start), both `CUSTOM_LLM_URL` and `CUSTOM_LLM_API_KEY` are checked in `Agent.__init__` — the server does **not** boot without them. Keep `CUSTOM_LLM_API_KEY` set to at least `any-key-here` even in dev.

## `llm.py` must stay agora-free

`test_llm_mount.py::test_llm_module_has_no_agora_dependency` does an AST walk and fails if any `agora*` root import appears in `llm.py`. Do not add `agora-agents` to the `/llm` sub-app.

## Do not put `PORT` in `server/.env.example`

`verify:local:fastapi` injects a random `PORT` and loads env with `load_dotenv(override=True)`. A `PORT` line in `.env.example` (copied to `.env.local`) would clobber the injected port and break the smoke test.

## Keep `/api/*` ownership in rewrites

Adding `web/app/api/**/route.ts` for agent/token logic breaks the boundary — `verify-api-contracts.ts` explicitly fails if a `route.ts` exists under `app/api`. Token logic belongs in `server/`.

## camelCase request fields

`StartAgentRequest` uses `channelName`, `rtcUid`, `userUid` (camelCase) to match the browser client. Renaming one side without the other breaks the contract tests.

## UID normalization in transcripts

`normalizeTranscript` maps `uid === '0'` to the local UID. Token issuance also rejects zero/negative UIDs and generates a concrete one. Preserve both — speaker mapping and tokens depend on concrete UIDs.

## Use `HOME_DB_PATH`, not `MESSAGE_DB_PATH`

This recipe stores device and room mode state under `HOME_DB_PATH` (default `/tmp/home.db`). Do not reference `MESSAGE_DB_PATH` or `messages.db` — those belong to a different recipe variant.

## Co-public caveat

Because `/llm/chat/completions` and `/get_config` share one port, exposing the backend publicly also exposes the token endpoints. For production, add authentication or split behind a reverse proxy.

## Turn detection is on `AgoraAgent`, not the vendor

`turn_detection` (with `start_of_speech`/`end_of_speech` VAD config) is set on `AgoraAgent(...)` directly, not on the `CustomLLM` vendor. This is the opposite of the realtime MLLM recipe where turn detection is vendor-owned.

## Local calls under a global proxy

Global proxies (Clash, etc.) can break `localhost`/RFC-1918 traffic. Configure the proxy to send `127.0.0.1`, `localhost`, and private ranges DIRECT, or `socksio` (in `requirements.txt`) plus `all_proxy` to route the backend through SOCKS.

## Related Deep Dives

- [tool_execution_flow](L2/tool_execution_flow.md) — correct routing and SSE wiring.
