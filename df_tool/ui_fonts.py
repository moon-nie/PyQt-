"""OS별 UI/HTML 폰트 스택 (PyQt·matplotlib 무관).

Mac에서 Segoe UI / Consolas만 지정하면 한글이 네모(□)로 깨질 수 있어
플랫폼별 기본 한글·모노스페이스 후보를 한곳에서 고른다.
차트(Matplotlib) 폰트는 `analysis.preferred_korean_matplotlib_font`가 SSOT.
"""
from __future__ import annotations

import sys


def ui_font_css_stack() -> str:
    """Qt stylesheet `font-family` 값 (따옴표·쉼표 포함)."""
    if sys.platform == "darwin":
        return '"Apple SD Gothic Neo", "AppleGothic", "Helvetica Neue", sans-serif'
    if sys.platform == "win32":
        return '"Segoe UI", "Malgun Gothic", sans-serif'
    return '"Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "DejaVu Sans", sans-serif'


def monospace_font_family() -> str:
    """QFont 등에 넘길 모노스페이스 1순위 family."""
    if sys.platform == "darwin":
        return "Menlo"
    if sys.platform == "win32":
        return "Consolas"
    return "DejaVu Sans Mono"


def monospace_css_stack() -> str:
    """Qt stylesheet용 모노스페이스 스택."""
    if sys.platform == "darwin":
        return '"Menlo", "Monaco", "Courier New", monospace'
    if sys.platform == "win32":
        return '"Consolas", "Courier New", monospace'
    return '"DejaVu Sans Mono", "Liberation Mono", "Courier New", monospace'


def html_body_font_css_stack() -> str:
    """HTML 리포트용 — 브라우저가 첫 가용 폰트를 고르도록 전 OS 후보를 나열."""
    return (
        '"Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic", '
        '"Segoe UI", "Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", sans-serif'
    )
