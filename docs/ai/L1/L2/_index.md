# Deep Dives Index

| Document                                              | Summary                                                                           | Load When                                                                         |
| ----------------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| [tool_execution_flow.md](tool_execution_flow.md)      | How `run_agent_turn()` routes intents, the update_tools pattern, SQLite state, and SSE streaming | Changing the home engine, adding rooms/scenes/devices, or debugging LLM turn flow |
| [session_lifecycle.md](session_lifecycle.md)          | Browser orchestration of get_config + start/stop, RTC/RTM, transcript             | Touching client-side join, token renewal, or mid-call control                     |
| [custom_llm_vendor.md](custom_llm_vendor.md)          | `CustomLLM` vendor build, `CUSTOM_LLM_URL` public-URL requirement, agent chain   | Changing the LLM vendor, URL, model name, or wiring STT/TTS vendors               |
