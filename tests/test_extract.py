import json

from api_monitor.proxy.extract import (
    extract_metadata,
    extract_response_text,
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
