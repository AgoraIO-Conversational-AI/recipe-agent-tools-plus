# Deep Dive — CustomLLM Vendor

> **When to Read This:** You are changing the LLM vendor, URL configuration, model name, or the STT/TTS vendor chain. For the high-level pipeline, start at [02_architecture](../02_architecture.md).

This recipe uses a **cascading** STT → LLM → TTS pipeline via the `agora-agents` SDK. The LLM stage uses the `CustomLLM` vendor to point at the in-process `/llm` sub-app.

## The vendor chain

Built in `Agent.start()` (`server/src/agent.py`):

```python
llm = CustomLLM(
    base_url=self.custom_llm_url,      # CUSTOM_LLM_URL — must be public
    api_key=self.custom_llm_api_key,   # CUSTOM_LLM_API_KEY
    model=self.custom_llm_model,       # CUSTOM_LLM_MODEL, default "smarthome-mock"
    greeting_message=self.greeting,
    failure_message="Please wait a moment.",
    max_history=15,
    max_tokens=1024,
    temperature=0.7,
    top_p=0.95,
)
stt = DeepgramSTT(model="nova-3", language="en")
tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")

agora_agent = AgoraAgent(
    client=self.client,
    instructions=CUSTOM_LLM_PROMPT,
    greeting=self.greeting,
    failure_message="Please wait a moment.",
    max_history=50,
    turn_detection={ ... },            # VAD config — on AgoraAgent, not the vendor
    advanced_features={"enable_rtm": True},
    parameters=parameters,
).with_stt(stt).with_llm(llm).with_tts(tts)
```

`CustomLLM` stamps `vendor: "custom"` in the Agora wire config and requires **both** `base_url` and `api_key`. Both are validated in `Agent.__init__`; missing either raises `ValueError` at boot.

## `CUSTOM_LLM_URL` public-URL requirement

Agora cloud — not the local FastAPI process — POSTs to `CUSTOM_LLM_URL`. The URL must be publicly reachable. There is intentionally no `localhost` default: a local URL lets the agent "start" while LLM calls silently fail cloud-side.

For local development, use a tunnel:

```bash
ngrok http 8000
# CUSTOM_LLM_URL=https://<id>.ngrok-free.app/llm/chat/completions
```

`doctor:local` warns if `CUSTOM_LLM_URL` contains `localhost` or `127.0.0.1`.

## Session `parameters`

Set in `Agent.start()` and passed to `AgoraAgent`:

| Key                    | Value     | Why                                              |
| ---------------------- | --------- | ------------------------------------------------ |
| `audio_scenario`       | `chorus`  | Ultra-low-latency profile for web clients.       |
| `data_channel`         | `rtm`     | Transcript + metrics delivered over RTM.         |
| `enable_error_message` | `true`    | Surface agent-side errors to the client.         |
| `enable_metrics`       | `true`    | Emit pipeline metrics to the UI.                 |
| `output_audio_codec`   | optional  | Forwarded from `POST /startAgent` `parameters`.  |

## Changing the LLM endpoint

To point at a different backend (e.g. production home-automation service):

1. Set `CUSTOM_LLM_URL` to the new public URL.
2. Set `CUSTOM_LLM_API_KEY` to the key expected by the new endpoint.
3. Keep the endpoint's response in OpenAI SSE format — Agora cloud requires it.

## Changing STT or TTS vendors

Replace `DeepgramSTT` or `MiniMaxTTS` in `Agent.start()` with any vendor the SDK supports. Keep the three `.with_stt()`, `.with_llm()`, `.with_tts()` calls in sequence.

## Related L1

- [02_architecture](../02_architecture.md) · [06_interfaces](../06_interfaces.md) · [07_gotchas](../07_gotchas.md)
