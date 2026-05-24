"""Lexical evidence markers per model family (explainable alerts)."""

from __future__ import annotations

FAMILY_SLOP_WORDS: dict[str, set[str]] = {
    "gpt": {
        "delve",
        "tapestry",
        "landscape",
        "multifaceted",
        "underscore",
        "pivotal",
        "robust",
    },
    "claude": {
        "certainly",
        "happy to help",
        "i'd be happy",
        "let me",
        "here's",
    },
    "gemini": {
        "great question",
        "here's a breakdown",
        "in summary",
    },
    "llama": {
        "sure!",
        "of course",
        "here's a quick",
    },
    "mistral": {
        "happy to help",
        "compact",
        "essentials",
    },
}


def collect_lexicon_evidence(
    text: str,
    *,
    expected: str | None,
    predicted: str,
) -> list[str]:
    lowered = text.lower()
    evidence: list[str] = []

    predicted_hits = [
        w for w in FAMILY_SLOP_WORDS.get(predicted, set()) if w in lowered
    ]
    if predicted_hits:
        evidence.append(
            f"响应中出现 {predicted.upper()} 特征词: "
            + ", ".join(f'"{w}"' for w in predicted_hits[:5])
        )

    if expected and expected != predicted:
        missing = [
            w
            for w in FAMILY_SLOP_WORDS.get(expected, set())
            if w not in lowered
        ]
        if missing:
            evidence.append(
                f"响应中缺失 {expected.upper()} 特征词: "
                + ", ".join(f'"{w}"' for w in missing[:5])
            )

    return evidence
