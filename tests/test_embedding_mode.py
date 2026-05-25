from api_monitor.analyzer.embedding_model import model_name_for_mode


def test_lite_mode():
    assert "MiniLM" in model_name_for_mode("lite")


def test_precise_mode():
    assert "mpnet" in model_name_for_mode("precise")
