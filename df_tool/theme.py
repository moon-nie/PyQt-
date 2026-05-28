"""색상 테마 — COLORS dict 및 theme.json 로드/저장."""
from __future__ import annotations

import json
from copy import deepcopy

from df_tool.branding import CONFIG_DIR, THEME_CONFIG_PATH, resolve_config_path

DEFAULT_COLORS: dict[str, str] = {
    "bg": "#0f1117",
    "surface": "#181b24",
    "surface_alt": "#1a1f2e",
    "sidebar": "#181b24",
    "border": "#2a3142",
    "border_subtle": "#252a38",
    "border_focus": "#6366f1",
    "text": "#e2e8f0",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "primary": "#818cf8",
    "primary_hover": "#6366f1",
    "primary_light": "#312e81",
    "primary_soft": "#1e1b4b",
    "accent": "#22d3ee",
    "success": "#34d399",
    "warning": "#fbbf24",
    "danger": "#f87171",
    "header_bg": "#1e2230",
    "header_fg": "#cbd5e1",
    "header_border": "#2a3142",
    "tree_grid": "#94a3b8",
    "cell_grid": "#252a38",
    "row_alt": "#1a1f2e",
    "row_selected": "#312e81",
    "row_index_bg": "#1a2332",
    "row_index_bg_alt": "#1d2738",
    "row_index_bg_sel": "#3d3a6b",
    "row_index_header_bg": "#222b3d",
    "row_index_fg": "#7889a8",
    "row_index_fg_sel": "#c4b5fd",
    "row_cell": "#1e1b4b",
    "col_selected": "#1f2840",
    "code_bg": "#0d0d12",
    "code_fg": "#cdd6f4",
    "stat_bg": "#1e2230",
    "toolbar_bg": "#181b24",
    "status_bg": "#181b24",
    "shadow": "#0a0a0f",
    "cursor": "#22d3ee",
    "scrollbar_thumb": "#3d465c",
    "scrollbar_hover": "#4a5570",
    "scrollbar_trough": "#181b24",
}

COLORS: dict[str, str] = deepcopy(DEFAULT_COLORS)

THEME_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "배경 · 레이아웃",
        [
            ("bg", "앱 배경"),
            ("surface", "표 / 카드 배경"),
            ("surface_alt", "입력창 · 보조 배경"),
            ("sidebar", "사이드바"),
            ("border", "테두리"),
            ("toolbar_bg", "상단 메뉴·툴바"),
            ("status_bg", "하단 상태바"),
            ("stat_bg", "통계 박스"),
        ],
    ),
    (
        "글자",
        [
            ("text", "본문"),
            ("text_secondary", "보조 글자"),
            ("text_muted", "흐린 글자"),
            ("header_fg", "표 헤더 글자"),
        ],
    ),
    (
        "강조 · 선택",
        [
            ("primary", "강조색 (버튼·링크)"),
            ("primary_hover", "버튼 hover"),
            ("primary_light", "선택 하이라이트"),
            ("primary_soft", "헤더 hover"),
            ("cursor", "입력 커서"),
            ("row_selected", "행 선택 배경"),
            ("col_selected", "열 선택 배경"),
        ],
    ),
    (
        "데이터 표",
        [
            ("header_bg", "열 헤더 배경"),
            ("tree_grid", "표 격자선"),
            ("cell_grid", "셀 경계선"),
            ("row_alt", "짝수 행 배경"),
            ("row_index_bg", "행 번호 열 배경"),
            ("row_index_header_bg", "행 번호 헤더 배경"),
            ("row_index_fg", "행 번호 글자"),
        ],
    ),
    (
        "코드 패널",
        [
            ("code_bg", "코드 배경"),
            ("code_fg", "코드 글자"),
        ],
    ),
]


def load_theme_config() -> None:
    path = resolve_config_path("theme.json")
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for key, value in data.items():
                if key in DEFAULT_COLORS and isinstance(value, str) and value.startswith("#"):
                    COLORS[key] = value
    except (OSError, json.JSONDecodeError, TypeError):
        pass


def save_theme_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {key: COLORS[key] for key in DEFAULT_COLORS}
    THEME_CONFIG_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def reset_theme_colors() -> None:
    COLORS.clear()
    COLORS.update(deepcopy(DEFAULT_COLORS))
