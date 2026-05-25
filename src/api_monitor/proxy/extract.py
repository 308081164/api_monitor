"""Extract assistant text and metadata from LLM API JSON payloads."""

from __future__ import annotations

import json
from typing import Any


def parse_request_model(body: bytes) -> str | None:
    if not body:
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        model = data.get("model")
        if isinstance(model, str):
            return model
    return None


def extract_response_text(body: bytes) -> str:
    if not body:
        return ""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body.decode("utf-8", errors="replace").strip()

    if not isinstance(data, dict):
        return str(data)

    # OpenAI chat / responses API
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message") or first.get("delta") or {}
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(str(block.get("text", "")))
                    return "\n".join(p for p in parts if p)

    # Anthropic messages
    content_blocks = data.get("content")
    if isinstance(content_blocks, list):
        texts = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
        if texts:
            return "\n".join(texts)

    output = data.get("output")
    if isinstance(output, list):
        texts = []
        for item in output:
            if isinstance(item, dict):
                c = item.get("content")
                if isinstance(c, list):
                    for block in c:
                        if isinstance(block, dict) and block.get("text"):
                            texts.append(str(block["text"]))
        if texts:
            return "\n".join(texts)

    return ""


def extract_metadata(body: bytes) -> dict[str, Any]:
    if not body:
        return {}
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}

    meta: dict[str, Any] = {}
    for key in (
        "id",
        "model",
        "system_fingerprint",
        "object",
        "service_tier",
        "stop_reason",
    ):
        if key in data and data[key] is not None:
            meta[key] = data[key]

    usage = data.get("usage")
    if usage is not None:
        meta["usage"] = usage

    return meta


def merge_streaming_chunks(chunks: list[bytes]) -> bytes:
    """Merge OpenAI-style SSE streaming chunks into one JSON object when possible."""
    full_text_parts: list[str] = []
    last_obj: dict[str, Any] | None = None

    for raw in chunks:
        text = raw.decode("utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if not isinstance(obj, dict):
                continue
            last_obj = obj
            choices = obj.get("choices")
            if isinstance(choices, list) and choices:
                delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                if isinstance(delta, dict):
                    piece = delta.get("content")
                    if isinstance(piece, str):
                        full_text_parts.append(piece)

    if last_obj is None:
        return b""

    if full_text_parts:
        choices = last_obj.setdefault("choices", [{}])
        if choices and isinstance(choices[0], dict):
            choices[0]["message"] = {"role": "assistant", "content": "".join(full_text_parts)}
            choices[0].pop("delta", None)

    return json.dumps(last_obj, ensure_ascii=False).encode("utf-8")
