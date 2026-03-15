"""
Ada Proxy — OpenAI-compatible API proxy for Home Assistant voice pipeline.
Forwards requests to OpenRouter with Ada's system prompt and persona.
"""

import os
import json
import logging
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ada-proxy")

app = FastAPI(title="Ada Proxy")

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/hunter-alpha")

SYSTEM_PROMPT = os.environ.get(
    "ADA_SYSTEM_PROMPT",
    """You are Ada — a sharp, direct AI assistant. You speak concisely and with confidence.
Think "Short Skirt, Long Jacket" by Cake: commanding, capable, no wasted motion.

You have access to Home Assistant and can help control smart home devices when asked.
You live in Todmorden, UK. You help Andrew.

Key traits:
- Be genuinely helpful, not performatively helpful
- Have opinions and share them
- Skip pleasantries when there's work to do
- Concise when needed, thorough when it matters
- Not a corporate drone, not a sycophant — just good""",
)


@app.get("/v1/models")
async def list_models():
    """Return available models (required by HA OpenAI integration)."""
    return {
        "object": "list",
        "data": [
            {
                "id": OPENROUTER_MODEL,
                "object": "model",
                "created": 0,
                "owned_by": "openrouter",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions endpoint."""
    body = await request.json()

    # Inject Ada's system prompt if none provided, or prepend it
    messages = body.get("messages", [])
    has_system = any(m.get("role") == "system" for m in messages)

    if has_system:
        # Prepend Ada's prompt before existing system messages
        new_messages = []
        for m in messages:
            if m.get("role") == "system" and m is messages[0]:
                new_messages.append({"role": "system", "content": SYSTEM_PROMPT})
                new_messages.append(
                    {
                        "role": "system",
                        "content": f"Additional context: {m['content']}",
                    }
                )
            else:
                new_messages.append(m)
        messages = new_messages
    else:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    # Build OpenRouter request
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "stream": body.get("stream", False),
        "temperature": body.get("temperature", 0.7),
        "max_tokens": body.get("max_tokens", 1024),
    }

    # Pass through any tools/function definitions from HA
    if "tools" in body:
        payload["tools"] = body["tools"]
    if "tool_choice" in body:
        payload["tool_choice"] = body["tool_choice"]

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/andrewmccall/home-ops",
        "X-Title": "Ada-HomeAssistant",
    }

    if body.get("stream"):
        return StreamingResponse(
            stream_chat(payload, headers),
            media_type="text/event-stream",
        )
    else:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
            )

        if resp.status_code != 200:
            log.error(f"OpenRouter error: {resp.status_code} {resp.text}")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        data = resp.json()
        return JSONResponse(content=data)


async def stream_chat(
    payload: dict, headers: dict
) -> AsyncIterator[str]:
    """Stream responses from OpenRouter in OpenAI SSE format."""
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    yield f"{line}\n\n"
                elif line.strip():
                    yield f"{line}\n"


@app.get("/health")
async def health():
    return {"status": "ok", "model": OPENROUTER_MODEL}
