# recipe-agent-tools-plus — Repo Card

> Next.js web client + Python FastAPI backend for an Agora Conversational AI voice agent driven by a custom OpenAI-compatible `/llm` endpoint — a smart-home mock with room modes, keyword scenes, and SQLite device state. No external LLM key required.

## Identity

| Field          | Value                                                                                        |
| -------------- | -------------------------------------------------------------------------------------------- |
| Repo           | `AgoraIO-Conversational-AI/recipe-agent-tools-plus`                                          |
| Type           | `distributed-system` (single repo, two co-located processes)                                 |
| Language       | Python 3.10+ (FastAPI + uvicorn) backend + Next.js 16 / React 19 web                         |
| Deploy Target  | `web/` as Next.js app, `server/` as a reachable FastAPI service (also serves `/llm`)         |
| Owner          | Agora Conversational AI DevEx                                                                |
| Last Reviewed  | 2026-06-25                                                                                   |
| Recipe Role    | `base`                                                                                       |
| Recipe Version | `1.0.0`                                                                                      |
| Recipe Status  | `experimental`                                                                               |

## L1 — Summaries

The Audience column helps agents prioritise: **Use** = consuming the recipe's behavior, **Maintain** = modifying internals.

| File                                     | Purpose                                                                                       | Audience       |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- | -------------- |
| [01_setup](L1/01_setup.md)               | bun + venv + pip setup, env vars (incl. required `CUSTOM_LLM_URL`), ngrok tunnel, commands   | Use & Maintain |
| [02_architecture](L1/02_architecture.md) | Single-process topology, `/api/*` rewrite proxy, STT→LLM→TTS cascade, `/llm` sub-app flow   | Maintain       |
| [03_code_map](L1/03_code_map.md)         | `web/` and `server/` trees with key file responsibilities                                     | Maintain       |
| [04_conventions](L1/04_conventions.md)   | Python async + FastAPI patterns, Biome, JSON envelope, llm.py agora-free contract             | Maintain       |
| [05_workflows](L1/05_workflows.md)       | Add a route, change LLM config, extend the home engine, verify, deploy                       | Use            |
| [06_interfaces](L1/06_interfaces.md)     | FastAPI route contracts, rewrites, env vars, `/llm/chat/completions` SSE contract            | Use & Maintain |
| [07_gotchas](L1/07_gotchas.md)           | Public-URL requirement, no localhost default, PORT in env, llm.py agora-free, turn detection  | Maintain       |
| [08_security](L1/08_security.md)         | Token007, App Certificate server-only, bearer token, co-public caveat, CORS                  | Maintain       |

## Recipe Profile

This repo declares `Recipe Role: base`. See [RECIPE.md](RECIPE.md) for extension points, invariants, and stable contracts before changing reusable surfaces.
