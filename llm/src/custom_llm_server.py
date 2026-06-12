"""
Smart Home Tools-Plus LLM Server — Mock Implementation

This server demonstrates how to implement an OpenAI-compatible Chat Completions
endpoint that works with Agora Conversational AI Engine.

Key points:
- Must implement POST /chat/completions
- Must support streaming responses (Server-Sent Events)
- Must follow OpenAI Chat Completions response format
- Agora cloud sends Authorization header with the api_key you configured

This mock version powers a smart-home assistant with:
- Room modes (living_room / bedroom / kitchen) that gate which device tools run
  (update_tools pattern: switching rooms changes the active device set)
- Keyword scenes ("movie night", "good night", "i'm home") that run batches of
  device commands independent of the current room
- A mocked home API backed by SQLite (devices + mode state, zero-key)
- get_status recall so users can ask what devices are currently on

Replace the mock logic with your own real home-assistant integration.
"""
import asyncio
import json
import logging
import os
import sqlite3
import time
import uuid
from typing import Dict, List, Optional, Union

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load environment variables.
# override=False so an explicitly-exported value (e.g. CUSTOM_LLM_PORT injected by
# the verify:local:llm harness, or a process manager) takes precedence over a
# checked-in .env.local. In normal `dev` no port is exported, so .env.local wins.
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, ".env.local"), override=False)
load_dotenv(os.path.join(_base_dir, ".env"), override=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Home Tools-Plus",
    description=(
        "OpenAI-compatible Chat Completions endpoint for Agora Conversational AI Engine. "
        "This mock implementation powers a smart-home assistant with room modes, keyword "
        "scenes, and SQLite-backed device state — no API key required."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request Models — These match what Agora ConvoAI Engine sends
# =============================================================================

class TextContent(BaseModel):
    type: str = "text"
    text: str


class SystemMessage(BaseModel):
    role: str = "system"
    content: Union[str, List[str]]


class UserMessage(BaseModel):
    role: str = "user"
    content: Union[str, List[Union[TextContent, Dict]]]


class AssistantMessage(BaseModel):
    role: str = "assistant"
    content: Union[str, List[TextContent], None] = None
    tool_calls: Optional[List[Dict]] = None


class ToolMessage(BaseModel):
    role: str = "tool"
    content: Union[str, List[str]]
    tool_call_id: str


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Union[SystemMessage, UserMessage, AssistantMessage, ToolMessage]]
    stream: bool = True
    stream_options: Optional[Dict] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[Union[str, Dict]] = None
    response_format: Optional[Dict] = None


# =============================================================================
# Smart-home engine (mock, zero-key) — room modes + keyword scenes over SQLite
# -----------------------------------------------------------------------------
# Room mode gates which device tools are available (update_tools pattern).
# Keyword scenes run batches of device commands regardless of current mode.
# All state (mode + device states) is persisted to SQLite so get_status works
# across connections.
#
# run_agent_turn() routes by keyword and returns only the spoken reply; Agora
# cloud never sees a tool_call. A real endpoint would call a real home API.
# =============================================================================

DB_PATH = os.getenv("HOME_DB_PATH") or os.path.join(_base_dir, "home.db")

ROOMS = ("living_room", "bedroom", "kitchen")
TOOLS_BY_MODE = {
    "living_room": ("tv", "lamp", "ac"),
    "bedroom": ("lamp", "fan"),
    "kitchen": ("light", "kettle"),
}
SCENES = {
    "movie night": (("living_room", "tv", "on"), ("living_room", "lamp", "dim")),
    "good night": (("bedroom", "lamp", "off"), ("living_room", "tv", "off")),
    "i'm home": (("living_room", "lamp", "on"), ("kitchen", "light", "on")),
}
_RECALL_KW = ("status", "what is on", "what's on", "what did i", "which devices")
_ON = ("on", "turn on", "switch on", "enable")
_OFF = ("off", "turn off", "switch off", "disable")


def get_db(path: str = DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS devices (
        room TEXT NOT NULL, device TEXT NOT NULL, state TEXT NOT NULL,
        PRIMARY KEY (room, device))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('mode','living_room')")
    conn.commit()
    return conn


def get_mode(conn) -> str:
    return conn.execute("SELECT value FROM settings WHERE key='mode'").fetchone()[0]


def set_mode(conn, room: str) -> str:
    conn.execute("UPDATE settings SET value=? WHERE key='mode'", (room,))
    conn.commit()
    devices = ", ".join(TOOLS_BY_MODE[room])
    return f"You're now in the {room.replace('_',' ')}. I can control: {devices}."


def _set_device(conn, room, device, state) -> None:
    conn.execute("INSERT OR REPLACE INTO devices (room, device, state) VALUES (?,?,?)",
                 (room, device, state))
    conn.commit()


def set_device(conn, device: str, state: str) -> str:
    mode = get_mode(conn)
    if device not in TOOLS_BY_MODE[mode]:
        avail = ", ".join(TOOLS_BY_MODE[mode])
        return (f"The {device} isn't available in the {mode.replace('_',' ')}. "
                f"Here you can control: {avail}.")
    _set_device(conn, mode, device, state)
    return f"Turned {state} the {device} in the {mode.replace('_',' ')}."


def activate_scene(conn, name: str) -> str:
    for room, device, state in SCENES[name]:
        _set_device(conn, room, device, state)
    return f"Activated '{name}'. Enjoy!"


def get_status(conn) -> str:
    rows = conn.execute("SELECT room, device, state FROM devices ORDER BY room, device").fetchall()
    if not rows:
        return "Nothing's been changed yet — all devices are at their defaults."
    items = "; ".join(f"{r.replace('_',' ')} {d}: {st}" for r, d, st in rows)
    return f"Current status — {items}."


def _detect_room(text: str):
    for r in ROOMS:
        if r.replace("_", " ") in text or r in text:
            return r
    if "living room" in text:
        return "living_room"
    return None


def _detect_device(text: str):
    for devs in TOOLS_BY_MODE.values():
        for d in devs:
            if d in text:
                return d
    return None


def _extract_last_user_text(messages: list) -> str:
    for msg in reversed(messages):
        if getattr(msg, "role", None) == "user":
            content = msg.content
            if isinstance(content, str):
                return content
            if isinstance(content, list) and content:
                first = content[0]
                if isinstance(first, dict):
                    return first.get("text", "")
                if hasattr(first, "text"):
                    return first.text
            return ""
    return ""


def run_agent_turn(conn, messages: list) -> str:
    text = _extract_last_user_text(messages).lower()
    if any(k in text for k in _RECALL_KW):
        return get_status(conn)
    for scene in SCENES:
        if scene in text:
            return activate_scene(conn, scene)
    room = _detect_room(text)
    if room and ("switch" in text or "go to" in text or "mode" in text or "i'm in" in text or "im in" in text):
        return set_mode(conn, room)
    device = _detect_device(text)
    if device:
        state = "on" if any(k in text for k in _ON) else ("off" if any(k in text for k in _OFF) else "on")
        if "dim" in text:
            state = "dim"
        return set_device(conn, device, state)
    return ("I'm your smart-home assistant. Try 'turn on the tv', 'switch to the "
            "kitchen', 'movie night', or 'what's on'.")


# =============================================================================
# Streaming Response — Must follow OpenAI SSE format exactly
# =============================================================================
# Agora ConvoAI Engine expects:
# 1. Each chunk as "data: {json}\n\n"
# 2. Final "data: [DONE]\n\n"
# 3. Each chunk has: id, object, created, model, choices[{delta, index, finish_reason}]
# =============================================================================

def make_chunk(chunk_id: str, model: str, content: str, finish_reason=None) -> str:
    """Build a single SSE chunk in OpenAI format."""
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model or "mock-model",
        "choices": [
            {
                "index": 0,
                "delta": {"content": content} if content else {},
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n"


def make_role_chunk(chunk_id: str, model: str) -> str:
    """First chunk that sets the assistant role."""
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model or "mock-model",
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": ""},
                "finish_reason": None,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n"


@app.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    OpenAI-compatible chat completions endpoint.

    This is the endpoint that Agora Conversational AI Engine calls.
    It must:
    - Accept the OpenAI Chat Completions request format
    - Return streaming SSE responses in OpenAI chunk format
    - End with "data: [DONE]"
    """
    logger.info(
        f"Received request: model={request.model}, "
        f"messages={len(request.messages)}, stream={request.stream}"
    )

    # Agora ConvoAI always uses streaming
    if not request.stream:
        raise HTTPException(
            status_code=400,
            detail="Only streaming mode is supported. Set stream=true.",
        )

    # Run the smart-home agent turn. DB work fully materializes the reply string
    # before the streaming generator runs, so the generator never touches the DB.
    conn = get_db()
    try:
        response_text = run_agent_turn(conn, request.messages)
    finally:
        conn.close()
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    model = request.model or "mock-model"

    async def generate():
        """Stream the response word by word to simulate real LLM behavior."""
        # First chunk: role
        yield make_role_chunk(chunk_id, model)

        # Stream content word by word with small delays (simulates token generation)
        words = response_text.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else f" {word}"
            yield make_chunk(chunk_id, model, token)
            await asyncio.sleep(0.05)  # 50ms per token, ~realistic speed

        # Final chunk: finish_reason
        yield make_chunk(chunk_id, model, "", finish_reason="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "smarthome-mock"}


if __name__ == "__main__":
    port = int(os.getenv("CUSTOM_LLM_PORT", "8001"))
    logger.info(f"Starting Smart Home Tools-Plus LLM Server (Mock) on port {port}")
    logger.info("This server returns mock responses — no LLM API key needed.")
    logger.info(f"Endpoint: http://0.0.0.0:{port}/chat/completions")
    uvicorn.run(app, host="0.0.0.0", port=port)
