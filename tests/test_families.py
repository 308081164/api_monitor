from api_monitor.analyzer.families import infer_expected_family
from api_monitor.analyzer.lexicon import collect_lexicon_evidence


def test_infer_gpt():
    assert infer_expected_family("gpt-4o") == "gpt"


def test_infer_claude():
    assert infer_expected_family("claude-sonnet-4-20250514") == "claude"


def test_lexicon_evidence():
    text = "I'd be happy to help you delve into this tapestry."
    evidence = collect_lexicon_evidence(
        text, expected="claude", predicted="gpt"
    )
    assert any("GPT" in e for e in evidence)
