"""Embedding model selection for lite vs precise analysis modes."""

from __future__ import annotations

LITE_MODEL = "all-MiniLM-L6-v2"
PRECISE_MODEL = "all-mpnet-base-v2"


def model_name_for_mode(mode: str) -> str:
    mode = (mode or "lite").lower().strip()
    if mode == "precise":
        return PRECISE_MODEL
    return LITE_MODEL
