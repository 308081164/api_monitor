from pathlib import Path

from api_monitor.storage.logger import ResponseLogger


def test_logger_roundtrip(tmp_path: Path):
    db = tmp_path / "test.db"
    logger = ResponseLogger(db)
    rid = logger.log(
        method="POST",
        path="/v1/chat/completions",
        upstream_url="https://api.example.com/v1/chat/completions",
        model_requested="gpt-4o",
        response_text="A" * 40,
        metadata={"model": "gpt-4o"},
        timing={"total_ms": 120.0},
    )
    assert rid == 1
    assert logger.count() == 1
    records = logger.fetch_all()
    assert len(records) == 1
    assert records[0].model_requested == "gpt-4o"
