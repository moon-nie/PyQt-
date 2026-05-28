"""대용량·넓은 표 성능 관련 상수·헬퍼."""

from __future__ import annotations

LARGE_FILE_WARN_BYTES = 10 * 1024 * 1024
LARGE_FILE_FORCE_PROMPT_BYTES = 50 * 1024 * 1024
LARGE_DF_ROWS = 20_000
LARGE_FILE_WARN_ROWS = 25_000
LARGE_FILE_PREVIEW_ROWS = 30_000
SCROLL_RENDER_DELAY_MS = 8
OVERLAY_THROTTLE_MS = 20
OVERLAY_SCROLL_DEBOUNCE_MS = 40

WIDE_DF_COLS = 50
COLUMN_WINDOW_THRESHOLD = 40
HEAVY_DF_CELLS = 150_000

INFO_PANEL_DEFER_STATS_ROWS = 8_000
INFO_PANEL_DEFER_STATS_COLS = 40


def adaptive_undo_depth(row_count: int, col_count: int, *, default: int = 20) -> int:
    cells = row_count * max(col_count, 1)
    if row_count >= 100_000 or cells >= 5_000_000:
        return 2
    if row_count >= 50_000 or cells >= 1_000_000:
        return 3
    if row_count >= 10_000:
        return 5
    return default


def cell_count(row_count: int, col_count: int) -> int:
    return row_count * max(col_count, 1)


def is_wide_dataframe(col_count: int) -> bool:
    return col_count >= WIDE_DF_COLS


def is_heavy_dataframe(row_count: int, col_count: int) -> bool:
    return (
        row_count >= LARGE_DF_ROWS
        or col_count >= WIDE_DF_COLS
        or cell_count(row_count, col_count) >= HEAVY_DF_CELLS
    )


def should_defer_info_stats(row_count: int, col_count: int) -> bool:
    return row_count >= INFO_PANEL_DEFER_STATS_ROWS or col_count >= INFO_PANEL_DEFER_STATS_COLS


def should_show_detailed_stats_by_default(row_count: int, col_count: int) -> bool:
    """작은 표는 결측·고유값 등 상세 통계 기본 표시."""
    return not should_defer_info_stats(row_count, col_count)


def should_prompt_large_file(file_size: int, *, is_excel: bool) -> bool:
    if file_size < LARGE_FILE_WARN_BYTES:
        return False
    if is_excel:
        return True
    return file_size >= LARGE_FILE_FORCE_PROMPT_BYTES


def format_file_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.1f} MB"
    if num_bytes >= 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes} B"
