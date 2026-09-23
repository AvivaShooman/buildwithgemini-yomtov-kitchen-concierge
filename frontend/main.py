"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.
"""

import json
import logging
import os
import re
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/821049907373/locations/us-east1/reasoningEngines/5254198832257826816",
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"
_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# Compatibility across a2a-sdk versions
try:
    from a2a.client import ClientConfig, create_client
    from a2a.types import Message, Part, Role, SendMessageRequest
    from a2a.utils.constants import PROTOCOL_VERSION_1_0, VERSION_HEADER, TransportProtocol
    from google.protobuf.json_format import MessageToDict

    A2A_SDK_V1 = True
except ImportError:
    from a2a.client import ClientConfig, ClientFactory
    from a2a.types import (
        AgentCard,
        Message,
        Part,
        Role,
        TaskArtifactUpdateEvent,
        TextPart,
        TransportProtocol,
    )

    A2A_SDK_V1 = False


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    headers = {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }
    if A2A_SDK_V1:
        headers[VERSION_HEADER] = PROTOCOL_VERSION_1_0
    return headers


app = FastAPI(title="YomTov Kitchen Concierge Frontend Proxy")


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    logger.exception("Proxy error: %s", exc)
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}
_card = None


async def _get_card(client: httpx.AsyncClient):
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card


def _extract_part_data(p) -> list[dict]:
    """Turn response part into structured parts for the chat UI."""
    out = []

    # Protobuf Part (a2a-sdk 1.x)
    if hasattr(p, "HasField"):
        if p.HasField("data"):
            data_dict = MessageToDict(p.data)
            if isinstance(data_dict, dict) and "data" in data_dict:
                out.append({"kind": "a2ui", "data": data_dict["data"]})
            else:
                out.append({"kind": "a2ui", "data": data_dict})
            return out

        if p.text:
            text = p.text
            if "<a2a_datapart_json>" in text:
                matches = re.findall(
                    r"<a2a_datapart_json>(.*?)</a2a_datapart_json>", text, re.DOTALL
                )
                for m in matches:
                    try:
                        payload = json.loads(m.strip())
                        if isinstance(payload, dict) and "data" in payload:
                            out.append({"kind": "a2ui", "data": payload["data"]})
                        elif isinstance(payload, dict):
                            out.append({"kind": "a2ui", "data": payload})
                    except Exception:
                        pass
                clean_text = re.sub(
                    r"<a2a_datapart_json>.*?</a2a_datapart_json>", "", text, flags=re.DOTALL
                ).strip()
                if clean_text:
                    out.append({"kind": "text", "text": clean_text})
            else:
                out.append({"kind": "text", "text": text})
            return out

        if p.url:
            out.append({"kind": "text", "text": p.url})
            return out

        return out

    # Legacy SDK Part (a2a-sdk 0.3.x)
    root = getattr(p, "root", p)
    text = getattr(root, "text", None)
    if text:
        out.append({"kind": "text", "text": text})
        return out

    data = getattr(root, "data", None)
    if data is not None:
        if isinstance(data, dict) and "data" in data:
            out.append({"kind": "a2ui", "data": data["data"]})
        else:
            out.append({"kind": "a2ui", "data": data})
        return out

    uri = getattr(getattr(root, "file", None), "uri", None)
    if uri:
        out.append({"kind": "text", "text": uri})
        return out

    return out


@app.post("/reset")
async def reset(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    user_id = body.get("user_id") or "web-user"
    _contexts.pop(user_id, None)
    return JSONResponse({"status": "reset", "user_id": user_id})


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    if body.get("reset"):
        _contexts.pop(user_id, None)
    parts: list[dict] = []

    headers = _auth_headers()

    if A2A_SDK_V1:
        async with httpx.AsyncClient(headers=headers, timeout=120) as client:
            config = ClientConfig(
                httpx_client=client,
                supported_protocol_bindings=[
                    TransportProtocol.JSONRPC,
                    TransportProtocol.HTTP_JSON,
                ],
            )
            a2a_client = await create_client(A2A_BASE, config)
            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.ROLE_USER,
                parts=[Part(text=message)],
                context_id=_contexts.get(user_id) or "",
            )
            async for chunk in a2a_client.send_message(SendMessageRequest(message=msg)):
                for field in ("artifact_update", "task", "status_update"):
                    if chunk.HasField(field):
                        cid = getattr(getattr(chunk, field), "context_id", None)
                        if cid:
                            _contexts[user_id] = cid

                if chunk.HasField("artifact_update"):
                    for p in chunk.artifact_update.artifact.parts:
                        parts.extend(_extract_part_data(p))
                elif chunk.HasField("task"):
                    for a in chunk.task.artifacts:
                        for p in a.parts:
                            parts.extend(_extract_part_data(p))
                elif chunk.HasField("message"):
                    for p in chunk.message.parts:
                        parts.extend(_extract_part_data(p))
    else:
        async with httpx.AsyncClient(headers=headers, timeout=120) as client:
            card = await _get_card(client)
            factory = ClientFactory(
                ClientConfig(
                    supported_transports=[
                        TransportProtocol.jsonrpc,
                        TransportProtocol.http_json,
                    ],
                    httpx_client=client,
                )
            )
            a2a_client = factory.create(card)
            msg = Message(
                message_id=str(uuid.uuid4()),
                role=Role.user,
                parts=[Part(root=TextPart(text=message))],
                context_id=_contexts.get(user_id),
            )
            last_task = None
            got_artifact_update = False
            async for event in a2a_client.send_message(msg):
                if not isinstance(event, tuple):
                    continue
                task, update = event
                if task is not None:
                    last_task = task
                    if getattr(task, "context_id", None):
                        _contexts[user_id] = task.context_id
                if isinstance(update, TaskArtifactUpdateEvent):
                    got_artifact_update = True
                    for p in update.artifact.parts:
                        parts.extend(_extract_part_data(p))

            if not got_artifact_update and last_task is not None:
                for artifact in getattr(last_task, "artifacts", None) or []:
                    for p in artifact.parts:
                        parts.extend(_extract_part_data(p))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
