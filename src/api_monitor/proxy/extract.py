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
    if isinstance(content_blocks, list) and content_blocks:
        first = content_blocks[0]
        if isinstance(first, dict) and first.get("type") == "text":
            texts = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
            if texts:
                return "\n".join(texts)

    # OpenAI responses API output
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

    # Google Gemini generateContent
    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates:
        texts = []
        for cand in candidates:
            if not isinstance(cand, dict):
                continue
            content = cand.get("content") or {}
            if isinstance(content, dict):
                parts = content.get("parts") or []
                for part in parts:
                    if isinstance(part, dict) and part.get("text"):
                        texts.append(str(part["text"]))
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
        "modelVersion",
    ):
        if key in data and data[key] is not None:
            meta[key] = data[key]

    usage = data.get("usage")
    if usage is not None:
        meta["usage"] = usage

    usage_meta = data.get("usageMetadata")
    if usage_meta is not None:
        meta["usageMetadata"] = usage_meta

    candidates = data.get("candidates")
    if isinstance(candidates, list) and candidates:
        first = candidates[0]
        if isinstance(first, dict):
            if first.get("finishReason"):
                meta["finishReason"] = first["finishReason"]

    return meta


def merge_streaming_chunks(chunks: list[bytes]) -> tuple[bytes, list[float]]:
    """Merge SSE chunks; return merged body and inter-chunk intervals (ms)."""
    full_text_parts: list[str] = []
    last_obj: dict[str, Any] | None = None
    itts_ms: list[float] = []
    last_event_ts: float | None = None

    import time

    for raw in chunks:
        text = raw.decode("utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            now = time.perf_counter()
            if last_event_ts is not None:
                itts_ms.append((now - last_event_ts) * 1000)
            last_event_ts = now

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

            # OpenAI delta
            choices = obj.get("choices")
            if isinstance(choices, list) and choices:
                delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
                if isinstance(delta, dict):
                    piece = delta.get("content")
                    if isinstance(piece, str):
                        full_text_parts.append(piece)

            # Gemini streaming candidates
            candidates = obj.get("candidates")
            if isinstance(candidates, list) and candidates:
                cand = candidates[0]
                if isinstance(cand, dict):
                    content = cand.get("content") or {}
                    if isinstance(content, dict):
                        for part in content.get("parts") or []:
                            if isinstance(part, dict) and part.get("text"):
                                full_text_parts.append(str(part["text"]))

    if last_obj is None:
        return b"", itts_ms

    if full_text_parts:
        merged_text = "".join(full_text_parts)
        if last_obj.get("candidates"):
            cands = last_obj.setdefault("candidates", [{}])
            if cands and isinstance(cands[0], dict):
                cands[0]["content"] = {"parts": [{"text": merged_text}]}
        elif last_obj.get("choices"):
            choices = last_obj.setdefault("choices", [{}])
            if choices and isinstance(choices[0], dict):
                choices[0]["message"] = {"role": "assistant", "content": merged_text}
                choices[0].pop("delta", None)

    return json.dumps(last_obj, ensure_ascii=False).encode("utf-8"), itts_ms
