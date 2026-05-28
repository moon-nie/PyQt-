"""표 뷰 상태."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ViewState:
    sort_column: str | None = None
    sort_ascending: bool = True
    search_query: str = ""
    search_column: str = "전체 열"
    search_exact: bool = False
    search_exclude: bool = False
    col_offset: int = 0
