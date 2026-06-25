# Docs Test Results

**Date:** 2026-06-25
**Branch:** docs/progressive-disclosure
**Reviewer:** progressive-disclosure workflow

---

## Structural Checks

| Check | Result |
| ----- | ------ |
| L0 exists | PASS |
| L0 <= 50 lines (36 lines) | PASS |
| L1/01_setup.md exists | PASS |
| L1/02_architecture.md exists | PASS |
| L1/03_code_map.md exists | PASS |
| L1/04_conventions.md exists | PASS |
| L1/05_workflows.md exists | PASS |
| L1/06_interfaces.md exists | PASS |
| L1/07_gotchas.md exists | PASS |
| L1/08_security.md exists | PASS |
| RECIPE.md exists | PASS |
| L2/_index.md exists | PASS |
| L2/tool_execution_flow.md exists | PASS |
| L2/session_lifecycle.md exists | PASS |
| L2/custom_llm_vendor.md exists | PASS |
| AGENTS.md has `## How to Load` | PASS |
| AGENTS.md has `## Git Conventions` | PASS |
| AGENTS.md has `## Doc Commands` | PASS |
| AGENTS.md Recipe Role is `base` | PASS |
| AGENTS.md no stale "docs/ai not present" note | PASS |
| L0 Recipe Role = `base` | PASS |
| L0 Last Reviewed = 2026-06-25 | PASS |
| All 8 L1 files have `## Related Deep Dives` | PASS (8/8) |

**Structural: 30 PASS, 0 FAIL**

---

## Relative Link Check

39 relative links checked across all `docs/ai/` files.

**Links: 39 checked, 0 broken**

---

## pytest (server/tests)

Run in throwaway venv `/tmp/v_tools_plus` (Python 3.14.4, pytest 9.1.1).
Install: `pip install -r requirements.txt -r requirements-dev.txt`

```
tests/test_agent_construction.py::test_start_constructs_real_agent_and_returns_shape PASSED
tests/test_llm.py::test_health PASSED
tests/test_llm.py::test_streaming_sse_contract PASSED
tests/test_llm.py::test_non_streaming_rejected PASSED
tests/test_llm_mount.py::test_llm_health_is_mounted_under_slash_llm PASSED
tests/test_llm_mount.py::test_llm_chat_completions_reachable_through_mount PASSED
tests/test_llm_mount.py::test_llm_module_has_no_agora_dependency PASSED
tests/test_smarthome.py::test_default_mode_is_living_room PASSED
tests/test_smarthome.py::test_set_mode_changes_available_tools PASSED
tests/test_smarthome.py::test_device_control_gated_by_mode PASSED
tests/test_smarthome.py::test_scene_keyword_runs_batch_regardless_of_mode PASSED
tests/test_smarthome.py::test_status_recall_persists_across_connections PASSED

12 passed, 1 warning in 2.58s
```

Note: 1 deprecation warning (httpx/starlette.testclient); does not affect correctness.
Venv removed after run.

**pytest: 12/12 PASS**

---

## Q&A — Source-Verified

### Category 1: Setup & Configuration

**Q1: What env vars must be set before `bun run dev` will work?**
A: `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, and `CUSTOM_LLM_API_KEY`. All four are validated in `Agent.__init__`; missing any raises `ValueError` at server boot.
Source: `server/src/agent.py` lines 61–74; `server/.env.example`.
Result: **PASS**

**Q2: Why does the agent start successfully but never speak?**
A: `CUSTOM_LLM_URL` is not publicly reachable. Agora cloud — not the browser — POSTs to `/llm/chat/completions`. A `localhost` URL lets the agent start while LLM turns silently fail cloud-side. Use ngrok or a public tunnel.
Source: `server/src/agent.py` comment lines 53–57; README Troubleshooting table.
Result: **PASS**

**Q3: What does `doctor:local` check?**
A: bun present, python3 present, `server/.env.local` exists, `AGORA_APP_ID` and `AGORA_APP_CERTIFICATE` configured, `CUSTOM_LLM_URL` configured, and warns if `CUSTOM_LLM_URL` contains `localhost` or `127.0.0.1`.
Source: `package.json` `doctor:local` script.
Result: **PASS**

### Category 2: Architecture

**Q4: Does this recipe use a cascading STT→LLM→TTS pipeline or a single MLLM?**
A: Cascading. `DeepgramSTT` → `CustomLLM` → `MiniMaxTTS` via `.with_stt()`, `.with_llm()`, `.with_tts()`. Unlike the realtime recipe (single `OpenAIRealtime` MLLM), this recipe has three separate vendor stages.
Source: `server/src/agent.py` lines 112–170.
Result: **PASS**

**Q5: How does `server/src/llm.py` get served on the same port as the token endpoints?**
A: `app.mount("/llm", llm_app)` in `server/src/server.py` (line 198). The FastAPI app mounts the sub-app in-process; no second port or separate process.
Source: `server/src/server.py` line 198.
Result: **PASS**

**Q6: Does Agora cloud ever receive a `tool_call` response chunk?**
A: No. `run_agent_turn()` executes all home-engine logic internally and streams only the spoken reply text. Agora cloud receives only the assistant's spoken content in OpenAI SSE format.
Source: `server/src/llm.py` `run_agent_turn()` and `generate()` functions; ARCHITECTURE.md.
Result: **PASS**

### Category 3: Tool Execution & Home Engine

**Q7: What happens when a user says "turn on the TV" while in the bedroom mode?**
A: `set_device()` reads the current mode (`bedroom`) on every call and checks `TOOLS_BY_MODE["bedroom"]` = `("lamp", "fan")`. Since `tv` is not in that set, it returns a "not available here" message listing the available devices.
Source: `server/src/llm.py` lines 171–178 (`set_device` function).
Result: **PASS**

**Q8: Which SQLite tables store state? What is the env var for the DB path?**
A: Two tables — `devices(room, device, state)` and `settings(key, value)`. The env var is `HOME_DB_PATH` (not `MESSAGE_DB_PATH`); default is `/tmp/home.db` when not set (with a fallback to `server/home.db` in the code via `os.path.join(_base_dir, "home.db")`).
Source: `server/src/llm.py` lines 124, 142–151 (`DB_PATH`, `get_db`).
Result: **PASS**

**Q9: What is the intent routing priority order in `run_agent_turn()`?**
A: (1) Recall keywords → `get_status()`, (2) Scene keywords → `activate_scene()`, (3) Room keyword + switch intent → `set_mode()`, (4) Device keyword → `set_device()`, (5) Fallback help text.
Source: `server/src/llm.py` lines 228–245 (`run_agent_turn` function).
Result: **PASS**

### Category 4: Interfaces & Contracts

**Q10: What is the exact SSE termination sequence for `/llm/chat/completions`?**
A: Role chunk (`delta.role="assistant"`, `delta.content=""`), content chunks (one word per token, 50ms delay), stop chunk (`delta={}`, `finish_reason="stop"`), then `data: [DONE]`.
Source: `server/src/llm.py` `generate()` async function (lines 329–343).
Result: **PASS**

**Q11: What does `verify-api-contracts.ts` assert about the rewrite map?**
A: It asserts that `/api/get_config` rewrites to `/get_config`, `/api/startAgent` rewrites to `/startAgent`, and `/api/stopAgent` rewrites to `/stopAgent` on the backend URL. It also fails if any `route.ts` exists under `web/app/api`.
Source: `web/scripts/verify-api-contracts.ts` lines 52–98.
Result: **PASS**

### Category 5: Security & Gotchas

**Q12: Why is the co-public caveat important?**
A: Because `server/` serves both `/llm/chat/completions` (called by Agora cloud) and the token endpoints (`/get_config`, `/startAgent`, `/stopAgent`) on the same port. Exposing the backend publicly for Agora cloud also exposes the token endpoints. For production, add auth or split behind a reverse proxy.
Source: `ARCHITECTURE.md` co-public caveat section; `server/src/server.py`.
Result: **PASS**

---

## Summary by Category

| Category | Questions | Pass | Fail |
| -------- | --------- | ---- | ---- |
| Setup & Configuration | 3 | 3 | 0 |
| Architecture | 3 | 3 | 0 |
| Tool Execution & Home Engine | 3 | 3 | 0 |
| Interfaces & Contracts | 2 | 2 | 0 |
| Security & Gotchas | 1 | 1 | 0 |
| **Total** | **12** | **12** | **0** |

---

## Fix / Retest Section

No failures — no fixes required.
