"""표 선택 상태 — Tk/Qt viewer 공용."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SelectionScope:
    mode: str = "none"
    cells: set[tuple[object, str]] = field(default_factory=set)
    rows: set[object] = field(default_factory=set)
    columns: set[str] = field(default_factory=set)
    anchor_cell: tuple[object, str] | None = None
    anchor_row: object | None = None
    anchor_column: str | None = None

    def describe(self) -> str:
        if self.mode in {"column", "columns"} and self.columns:
            cols = ", ".join(sorted(self.columns))
            n = len(self.columns)
            return f"열 {n}개: {cols}" if n <= 2 else f"열 {n}개 선택 ({cols[:40]}…)"
        if self.mode in {"row", "rows"} and self.rows:
            return f"행 {len(self.rows)}개 선택"
        if self.mode == "cell" and self.cells:
            if len(self.cells) == 1:
                idx, col = next(iter(self.cells))
                return f"셀: [{idx}, {col}]"
            return f"셀 {len(self.cells)}개 선택 (범위)"
        return "선택 없음 — 클릭 · Shift/Ctrl · 드래그 · 방향키"

    def row_indices(self) -> list | None:
        if self.rows:
            return list(self.rows)
        if self.cells:
            return list({idx for idx, _ in self.cells})
        return None

    def column_names(self) -> list[str] | None:
        if self.columns:
            return list(self.columns)
        if self.cells:
            return list({col for _, col in self.cells})
        return None
