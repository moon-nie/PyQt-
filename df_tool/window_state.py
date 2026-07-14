"""창 위치·크기 저장/복원 — ~/.gridloom/window.json SSOT."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from df_tool.branding import CONFIG_DIR, WINDOW_CONFIG_PATH, resolve_config_path

WINDOW_STATE_KEYS = ("x", "y", "width", "height", "maximized")


def _normalize_state(data: dict[str, Any]) -> dict[str, Any] | None:
    try:
        width = int(data["width"])
        height = int(data["height"])
        x = int(data.get("x", 0))
        y = int(data.get("y", 0))
        maximized = bool(data.get("maximized", False))
    except (KeyError, TypeError, ValueError):
        return None
    if width < 400 or height < 300:
        return None
    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "maximized": maximized,
    }


def load_window_state(path: Path | None = None) -> dict[str, Any] | None:
    """window.json을 읽어 정규화된 dict를 반환. 없거나 깨지면 None."""
    target = path if path is not None else resolve_config_path("window.json")
    if not target.exists():
        return None
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    return _normalize_state(raw)


def save_window_state(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    maximized: bool = False,
    path: Path | None = None,
) -> Path | None:
    """창 기하를 JSON으로 저장. 성공 시 경로, 실패 시 None."""
    payload = _normalize_state(
        {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "maximized": maximized,
        }
    )
    if payload is None:
        return None
    target = path if path is not None else WINDOW_CONFIG_PATH
    try:
        if path is None:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        return None
    return target
