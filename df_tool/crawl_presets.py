"""크롤링 규칙(프리셋) 저장 — PyQt 금지, ~/.gridloom/crawl_presets.json."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from df_tool.branding import CONFIG_DIR, resolve_config_path

PRESETS_FILENAME = "crawl_presets.json"
_MAX_PRESETS = 40


@dataclass
class CrawlPreset:
    name: str
    url: str = ""
    selector: str = ""
    attr: str = "text"
    limit: int = 100
    column: str = "value"
    batch_template: str = ""
    batch_param_key: str = "code"
    batch_fields: str = ""
    batch_delay_ms: int = 350
    batch_max: int = 100
    batch_params: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CrawlPreset:
        return cls(
            name=str(data.get("name") or "이름 없음").strip() or "이름 없음",
            url=str(data.get("url") or ""),
            selector=str(data.get("selector") or ""),
            attr=str(data.get("attr") or "text"),
            limit=int(data.get("limit") or 100),
            column=str(data.get("column") or "value"),
            batch_template=str(data.get("batch_template") or ""),
            batch_param_key=str(data.get("batch_param_key") or "code"),
            batch_fields=str(data.get("batch_fields") or ""),
            batch_delay_ms=int(data.get("batch_delay_ms") or 350),
            batch_max=int(data.get("batch_max") or 100),
            batch_params=str(data.get("batch_params") or ""),
        )


def presets_path() -> Path:
    return resolve_config_path(PRESETS_FILENAME)


def load_presets(path: Path | None = None) -> list[CrawlPreset]:
    target = path or presets_path()
    if not target.exists():
        return []
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    items = raw.get("presets") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return []
    out: list[CrawlPreset] = []
    for item in items:
        if isinstance(item, dict) and item.get("name"):
            out.append(CrawlPreset.from_dict(item))
    return out


def save_presets(presets: list[CrawlPreset], path: Path | None = None) -> Path:
    target = path or (CONFIG_DIR / PRESETS_FILENAME)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    trimmed = presets[:_MAX_PRESETS]
    payload = {"presets": [p.to_dict() for p in trimmed]}
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def upsert_preset(preset: CrawlPreset, path: Path | None = None) -> list[CrawlPreset]:
    """같은 이름이 있으면 교체, 없으면 앞에 추가."""
    items = load_presets(path)
    name = preset.name.strip()
    items = [p for p in items if p.name != name]
    items.insert(0, preset)
    save_presets(items, path)
    return items


def delete_preset(name: str, path: Path | None = None) -> list[CrawlPreset]:
    items = [p for p in load_presets(path) if p.name != name]
    save_presets(items, path)
    return items
