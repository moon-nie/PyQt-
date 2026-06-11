"""분석 탭 matplotlib 차트 스타일 — 저장·불러오기."""
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, fields

from df_tool.branding import CONFIG_DIR, resolve_config_path
from df_tool.theme import COLORS

CHART_STYLE_FILENAME = "chart_style.json"

CMAP_OPTIONS = (
    "RdBu_r",
    "viridis",
    "plasma",
    "coolwarm",
    "YlOrRd",
    "Blues",
    "PuOr",
    "Spectral",
)

LEGEND_POSITIONS: dict[str, str] = {
    "best": "자동 (best)",
    "upper right": "오른쪽 위",
    "upper left": "왼쪽 위",
    "lower right": "오른쪽 아래",
    "lower left": "왼쪽 아래",
    "right": "오른쪽",
    "center left": "왼쪽 가운데",
}


@dataclass
class ChartStyle:
    """EDA 차트 색·레이아웃 설정."""

    color_primary: str = COLORS["primary"]
    color_accent: str = COLORS["accent"]
    color_fill: str = COLORS["primary_soft"]
    color_edge: str = COLORS["text_secondary"]
    color_warning: str = COLORS["warning"]
    color_text: str = COLORS["text"]
    color_muted: str = COLORS["text_muted"]
    color_border: str = COLORS["border"]
    figure_bg: str = COLORS["surface"]
    axes_bg: str = COLORS["surface_alt"]
    grid_color: str = COLORS["border_subtle"]

    show_title: bool = True
    title_override: str = ""
    title_font_size: int = 12
    label_font_size: int = 11
    tick_font_size: int = 10
    show_grid: bool = True
    grid_alpha: float = 0.45
    bar_alpha: float = 0.88
    scatter_alpha: float = 0.55
    scatter_size: int = 22
    legend_position: str = "best"
    x_label_rotation: int = 35
    cmap_heatmap: str = "RdBu_r"
    cmap_count: str = "viridis"
    cmap_hexbin: str = "plasma"
    show_colorbar: bool = True
    dpi: int = 110
    figure_width: float = 6.5

    def resolve_title(self, default: str) -> str | None:
        if not self.show_title:
            return None
        custom = self.title_override.strip()
        return custom if custom else default


def default_chart_style() -> ChartStyle:
    return ChartStyle()


def _valid_hex(value: str) -> bool:
    text = value.strip()
    if len(text) != 7 or not text.startswith("#"):
        return False
    try:
        int(text[1:], 16)
        return True
    except ValueError:
        return False


def chart_style_from_dict(data: dict) -> ChartStyle:
    style = default_chart_style()
    valid_keys = {f.name for f in fields(ChartStyle)}
    for key, value in data.items():
        if key not in valid_keys:
            continue
        if key.startswith("color_") or key.endswith("_bg") or key == "grid_color":
            if isinstance(value, str) and _valid_hex(value):
                setattr(style, key, value.lower())
            continue
        if key == "show_title" or key == "show_grid" or key == "show_colorbar":
            setattr(style, key, bool(value))
            continue
        if key in {"title_font_size", "label_font_size", "tick_font_size", "scatter_size", "x_label_rotation", "dpi"}:
            try:
                setattr(style, key, int(value))
            except (TypeError, ValueError):
                pass
            continue
        if key in {"grid_alpha", "bar_alpha", "scatter_alpha", "figure_width"}:
            try:
                setattr(style, key, float(value))
            except (TypeError, ValueError):
                pass
            continue
        if key == "legend_position" and isinstance(value, str) and value in LEGEND_POSITIONS:
            setattr(style, key, value)
            continue
        if key in {"cmap_heatmap", "cmap_count", "cmap_hexbin"} and isinstance(value, str) and value in CMAP_OPTIONS:
            setattr(style, key, value)
            continue
        if key == "title_override" and isinstance(value, str):
            setattr(style, key, value)
    return style


def load_chart_style() -> ChartStyle:
    path = resolve_config_path(CHART_STYLE_FILENAME)
    if not path.exists():
        return default_chart_style()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return chart_style_from_dict(data)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return default_chart_style()


def save_chart_style(style: ChartStyle) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = resolve_config_path(CHART_STYLE_FILENAME)
    path.write_text(
        json.dumps(asdict(style), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def reset_chart_style() -> ChartStyle:
    style = default_chart_style()
    save_chart_style(style)
    return style
