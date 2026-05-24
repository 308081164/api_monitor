"""Model family inference from requested model names."""

from __future__ import annotations

import re

FAMILIES = ("gpt", "claude", "gemini", "llama", "mistral", "unknown")

_FAMILY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("gpt", re.compile(r"gpt|o1|o3|o4|chatgpt", re.I)),
    ("claude", re.compile(r"claude", re.I)),
    ("gemini", re.compile(r"gemini", re.I)),
    ("llama", re.compile(r"llama|meta-llama", re.I)),
    ("mistral", re.compile(r"mistral|mixtral", re.I)),
]


def infer_expected_family(model_name: str | None) -> str | None:
    if not model_name:
        return None
    for family, pattern in _FAMILY_PATTERNS:
        if pattern.search(model_name):
            return family
    return "unknown"


# Reference phrases used to bootstrap embedding centroids (MiniLM MVP).
FAMILY_REFERENCE_TEXTS: dict[str, list[str]] = {
    "gpt": [
        "Certainly! I'd be happy to help you delve into this topic step by step.",
        "Here's a concise overview of the key points and practical next steps.",
    ],
    "claude": [
        "I'd be happy to help with that. Let me walk through the reasoning carefully.",
        "Certainly — here is a structured answer with clear sections and caveats.",
    ],
    "gemini": [
        "Great question. Here is a helpful breakdown with examples and summaries.",
        "I can help with that. Below is an organized explanation of the idea.",
    ],
    "llama": [
        "Sure! Here is a direct answer with bullet points and short explanations.",
        "Of course. I'll explain the concept plainly and include a quick example.",
    ],
    "mistral": [
        "Happy to help. Below is a compact explanation with actionable tips.",
        "Here is a straightforward answer focusing on the essentials.",
    ],
}
