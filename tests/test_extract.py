import json

from api_monitor.proxy.extract import (
    extract_metadata,
    extract_response_text,
    merge_streaming_chunks,
    parse_request_model,
)


def test_parse_request_model():
    body = json.dumps({"model": "gpt-4o", "messages": []}).encode()
    assert parse_request_model(body) == "gpt-4o"


def test_extract_openai_chat():
    body = json.dumps(
        {
            "id": "chatcmpl-1",
            "model": "gpt-4o",
            "system_fingerprint": "fp_abc",
            "choices": [
                {"message": {"role": "assistant", "content": "Hello from GPT"}}
            ],
        }
    ).encode()
    assert extract_response_text(body) == "Hello from GPT"
    meta = extract_metadata(body)
    assert meta["system_fingerprint"] == "fp_abc"
    assert meta["model"] == "gpt-4o"


def test_extract_anthropic():
    body = json.dumps(
        {
            "content": [{"type": "text", "text": "Hello from Claude"}],
            "stop_reason": "end_turn",
        }
    ).encode()
    assert extract_response_text(body) == "Hello from Claude"


def test_extract_gemini():
    body = json.dumps(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello from Gemini"}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ],
            "modelVersion": "gemini-1.5-pro",
        }
    ).encode()
    assert extract_response_text(body) == "Hello from Gemini"
    meta = extract_metadata(body)
    assert meta["modelVersion"] == "gemini-1.5-pro"


def test_merge_streaming_chunks():
    chunk = (
        b'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    merged, itts = merge_streaming_chunks([chunk])
    assert merged
    assert extract_response_text(merged) == "Hi"
    assert isinstance(itts, list)
