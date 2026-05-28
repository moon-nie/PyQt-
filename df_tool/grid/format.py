"""셀 표시 문자열 변환."""
from __future__ import annotations

import pandas as pd

DISPLAY_TEXT_MAX = 120
DISPLAY_TEXT_MAX_HEAVY = 64


def format_cell_value(value: object, *, heavy: bool = False) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    else:
        text = str(value)
    limit = DISPLAY_TEXT_MAX_HEAVY if heavy else DISPLAY_TEXT_MAX
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def raw_value(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
