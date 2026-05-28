"""앱 이름 · 설정 경로 등 브랜딩 상수."""

from pathlib import Path

APP_NAME = "Gridloom"
APP_NAME_KO = "그리드룸"
APP_TAGLINE = "표 데이터를 엮는 데스크톱 도구"
APP_SLUG = "gridloom"
ENTRY_SCRIPT = "gridloom.pyw"

CONFIG_DIR = Path.home() / f".{APP_SLUG}"
LEGACY_CONFIG_DIR = Path.home() / ".dataframe_tool"
THEME_CONFIG_PATH = CONFIG_DIR / "theme.json"
WINDOW_CONFIG_PATH = CONFIG_DIR / "window.json"


def resolve_config_path(filename: str) -> Path:
    """새 설정 경로 우선, 없으면 이전(.dataframe_tool) 경로."""
    new_path = CONFIG_DIR / filename
    if new_path.exists():
        return new_path
    legacy = LEGACY_CONFIG_DIR / filename
    if legacy.exists():
        return legacy
    return new_path
