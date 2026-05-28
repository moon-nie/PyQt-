"""파일 열기/저장 — load_file(), save_file() 이 엔드포인트.

연결: app.open_file() → load_file() / app.save_file() → save_file()
연결 지도: PROJECT_MAP.md § loader.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

# 복합 확장자 (압축 등) — 긴 것부터 매칭
COMPOUND_SUFFIXES: tuple[str, ...] = (
    ".csv.gz",
    ".tsv.gz",
    ".txt.gz",
    ".json.gz",
    ".parquet.gz",
)

EXCEL_SUFFIXES: frozenset[str] = frozenset(
    {
        ".xlsx",
        ".xlsm",
        ".xltx",
        ".xltm",
        ".xls",
        ".xlt",
        ".xlsb",
        ".ods",
    }
)

SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".csv": "CSV",
    ".tsv": "TSV",
    ".txt": "텍스트",
    ".dat": "텍스트",
    ".log": "텍스트",
    ".psv": "PSV",
    ".csv.gz": "CSV (gzip)",
    ".tsv.gz": "TSV (gzip)",
    ".txt.gz": "텍스트 (gzip)",
    ".xlsx": "Excel",
    ".xlsm": "Excel",
    ".xltx": "Excel",
    ".xltm": "Excel",
    ".xls": "Excel",
    ".xlt": "Excel",
    ".xlsb": "Excel",
    ".ods": "OpenDocument",
    ".parquet": "Parquet",
    ".parquet.gz": "Parquet (gzip)",
    ".json": "JSON",
    ".jsonl": "JSON Lines",
    ".ndjson": "JSON Lines",
    ".json.gz": "JSON (gzip)",
    ".feather": "Feather",
    ".arrow": "Arrow",
    ".pkl": "Pickle",
    ".pickle": "Pickle",
    ".html": "HTML",
    ".htm": "HTML",
    ".xml": "XML",
    ".dta": "Stata",
    ".sas7bdat": "SAS",
    ".xpt": "SAS XPT",
    ".h5": "HDF5",
    ".hdf5": "HDF5",
}

_DIALOG_WILDCARD = ";".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS, key=len, reverse=True))

FILE_DIALOG_TYPES = [
    ("지원 파일", _DIALOG_WILDCARD),
    ("Excel / 스프레드시트", "*.xlsx;*.xlsm;*.xltx;*.xltm;*.xls;*.xlt;*.xlsb;*.ods"),
    ("CSV / TSV / 텍스트", "*.csv;*.tsv;*.txt;*.dat;*.log;*.psv;*.csv.gz;*.tsv.gz;*.txt.gz"),
    ("Parquet / Feather / Arrow", "*.parquet;*.parquet.gz;*.feather;*.arrow"),
    ("JSON", "*.json;*.jsonl;*.ndjson;*.json.gz"),
    ("HTML / XML", "*.html;*.htm;*.xml"),
    ("Stata / SAS / HDF5", "*.dta;*.sas7bdat;*.xpt;*.h5;*.hdf5"),
    ("Pickle", "*.pkl;*.pickle"),
    ("모든 파일", "*.*"),
]

SAVE_FORMATS: list[tuple[str, str, str]] = [
    ("csv_utf8_sig", "CSV — UTF-8 BOM (Excel 권장)", ".csv"),
    ("csv_utf8", "CSV — UTF-8", ".csv"),
    ("csv_cp949", "CSV — CP949 (한글 Windows / Excel)", ".csv"),
    ("tsv", "TSV — 탭 구분", ".tsv"),
    ("xlsx", "Excel — .xlsx", ".xlsx"),
    ("parquet", "Parquet", ".parquet"),
    ("json", "JSON", ".json"),
]

SAVE_FORMAT_LABELS = [label for _, label, _ in SAVE_FORMATS]
SAVE_FORMAT_BY_LABEL = {label: key for key, label, _ in SAVE_FORMATS}
SAVE_EXT_BY_FORMAT = {key: ext for key, _, ext in SAVE_FORMATS}


@dataclass
class LoadedData:
    path: Path
    dataframe: pd.DataFrame
    sheet_names: list[str] | None = None
    active_sheet: str | None = None
    save_format: str = "csv_utf8_sig"
    sheet_frames: dict[str, pd.DataFrame] = field(default_factory=dict)

    def remember_current_sheet(self) -> None:
        if self.active_sheet:
            self.sheet_frames[self.active_sheet] = self.dataframe.copy()

    def load_sheet(self, sheet_name: str) -> pd.DataFrame:
        if sheet_name in self.sheet_frames:
            return self.sheet_frames[sheet_name]
        df = _read_excel(self.path, sheet_name=sheet_name)
        self.sheet_frames[sheet_name] = df
        return df

    def delete_sheet(self, sheet_name: str) -> None:
        if not self.sheet_names:
            raise ValueError("Excel 시트가 없습니다.")
        if sheet_name not in self.sheet_names:
            raise ValueError(f"시트 '{sheet_name}'을(를) 찾을 수 없습니다.")
        if len(self.sheet_names) <= 1:
            raise ValueError("마지막 시트는 삭제할 수 없습니다.")

        idx = self.sheet_names.index(sheet_name)
        self.sheet_frames.pop(sheet_name, None)
        self.sheet_names = [name for name in self.sheet_names if name != sheet_name]

        if self.active_sheet != sheet_name:
            return

        next_idx = min(idx, len(self.sheet_names) - 1)
        next_sheet = self.sheet_names[next_idx]
        self.active_sheet = next_sheet
        self.dataframe = self.load_sheet(next_sheet)


def resolve_file_suffix(path: Path) -> str:
    name = path.name.lower()
    for compound in COMPOUND_SUFFIXES:
        if name.endswith(compound):
            return compound
    if name.endswith(".parquet.gz"):
        return ".parquet.gz"
    return path.suffix.lower()


def _engines_for_suffix(suffix: str) -> list[str]:
    if suffix in {".xls", ".xlt"}:
        return ["calamine", "xlrd", "openpyxl"]
    if suffix == ".xlsb":
        return ["calamine", "pyxlsb"]
    if suffix == ".ods":
        return ["calamine", "odf"]
    return ["calamine", "openpyxl"]


def _engine_import_name(engine: str) -> str:
    return {"odf": "odfpy", "calamine": "python-calamine"}.get(engine, engine)


def _engine_available(engine: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(_engine_import_name(engine)) is not None


def _peek_is_html_excel(path: Path) -> bool:
    try:
        head = path.read_bytes()[:512].lower()
    except OSError:
        return False
    if b"<html" in head or b"<table" in head:
        return True
    return b"<?xml" in head and (b"spreadsheet" in head or b"worksheet" in head)


def _missing_dependency_hint(exc: ImportError, *, suffix: str) -> str:
    pkg_map = {
        "calamine": "python-calamine",
        "xlrd": "xlrd",
        "openpyxl": "openpyxl",
        "pyxlsb": "pyxlsb",
        "odf": "odfpy",
        "odfpy": "odfpy",
        "pyarrow": "pyarrow",
        "fastparquet": "pyarrow 또는 fastparquet",
        "tables": "tables (pip install tables)",
        "lxml": "lxml",
        "html5lib": "html5lib",
        "bs4": "beautifulsoup4",
    }
    msg = str(exc).lower()
    for key, label in pkg_map.items():
        if key in msg:
            return f"{suffix} 파일을 열려면 '{label}' 패키지가 필요합니다. (pip install -r requirements.txt)"
    return f"{suffix} 파일을 여는 데 필요한 패키지가 없습니다. (pip install -r requirements.txt)"


def _open_excel_file(path: Path) -> pd.ExcelFile:
    suffix = resolve_file_suffix(path)
    errors: list[str] = []

    for engine in _engines_for_suffix(suffix):
        if not _engine_available(engine):
            errors.append(f"{engine}: 패키지 없음")
            continue
        try:
            return pd.ExcelFile(path, engine=engine)
        except ImportError as exc:
            raise ValueError(_missing_dependency_hint(exc, suffix=suffix)) from exc
        except Exception as exc:
            errors.append(f"{engine}: {exc}")

    detail = errors[-1] if errors else "지원되는 Excel 엔진 없음"
    raise ValueError(f"Excel 파일을 열 수 없습니다. ({detail})")


def _read_excel(path: Path, sheet_name: str | None = None) -> pd.DataFrame:
    suffix = resolve_file_suffix(path)

    if suffix in {".xls", ".xlt"} and _peek_is_html_excel(path):
        return _read_html(path)

    errors: list[str] = []
    for engine in _engines_for_suffix(suffix):
        if not _engine_available(engine):
            errors.append(f"{engine}: 패키지 없음")
            continue
        try:
            return pd.read_excel(path, sheet_name=sheet_name, engine=engine)
        except ImportError as exc:
            raise ValueError(_missing_dependency_hint(exc, suffix=suffix)) from exc
        except Exception as exc:
            errors.append(f"{engine}: {exc}")

    if suffix in {".xls", ".xlt"}:
        try:
            return _read_html(path)
        except Exception as exc:
            errors.append(f"html: {exc}")

    detail = errors[-1] if errors else "지원되는 Excel 엔진 없음"
    raise ValueError(f"Excel 파일을 열 수 없습니다. ({detail})")


def list_sheets(path: Path) -> list[str] | None:
    suffix = resolve_file_suffix(path)
    if suffix not in EXCEL_SUFFIXES:
        return None
    if suffix in {".xls", ".xlt"} and _peek_is_html_excel(path):
        return None
    excel = _open_excel_file(path)
    return excel.sheet_names


def load_file(path: Path, sheet_name: str | None = None, *, nrows: int | None = None) -> LoadedData:
    path = Path(path)
    suffix = resolve_file_suffix(path)

    sheet_names = list_sheets(path)

    if suffix in EXCEL_SUFFIXES:
        if sheet_name is None:
            sheet_name = sheet_names[0] if sheet_names else None
        df = _read_excel(path, sheet_name=sheet_name)
    elif suffix in {".csv", ".csv.gz", ".tsv", ".tsv.gz", ".txt.gz", ".txt", ".dat", ".log", ".psv"}:
        sep = "\t" if suffix in {".tsv", ".tsv.gz"} else "|" if suffix == ".psv" else None
        if sep == "|":
            df = _read_csv_auto(path, sep="|", nrows=nrows)
        elif sep == "\t":
            df = _read_csv_auto(path, sep="\t", nrows=nrows)
        else:
            df = _read_csv_auto(path, nrows=nrows)
    elif suffix in _LOADERS:
        df = _LOADERS[suffix](path)
    elif suffix:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {suffix}")
    else:
        df = _load_by_fallback(path)

    if nrows is not None and len(df) > nrows:
        df = df.iloc[:nrows].copy()

    df = _normalize_dataframe_columns(df)

    save_format = guess_save_format(path)

    loaded = LoadedData(
        path=path,
        dataframe=df,
        sheet_names=sheet_names,
        active_sheet=sheet_name,
        save_format=save_format,
    )
    if sheet_name:
        loaded.sheet_frames[sheet_name] = loaded.dataframe
    return loaded


def _read_csv_auto(path: Path, *, sep: str | None = None, nrows: int | None = None) -> pd.DataFrame:
    kwargs: dict = {"compression": "infer", "low_memory": True}
    if sep is not None:
        kwargs["sep"] = sep
    if nrows is not None:
        kwargs["nrows"] = nrows
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding="utf-8", errors="replace", **kwargs)


def _load_delimited_text(path: Path) -> pd.DataFrame:
    for sep in [",", "\t", ";", "|"]:
        try:
            return _read_csv_auto(path, sep=sep)
        except Exception:
            continue
    return pd.read_csv(path, sep=None, engine="python", compression="infer")


def _read_json(path: Path) -> pd.DataFrame:
    suffix = resolve_file_suffix(path)
    if suffix in {".jsonl", ".ndjson"}:
        return pd.read_json(path, lines=True)
    try:
        return pd.read_json(path)
    except ValueError:
        return pd.read_json(path, lines=True)


def _normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """정수·numpy 등 비문자열 열 이름을 문자열로 통일 (HTML 위장 xls 등)."""
    if all(isinstance(c, str) for c in df.columns):
        return df
    result = df.copy()
    seen: dict[str, int] = {}
    names: list[str] = []
    for col in result.columns:
        name = str(col)
        if name not in seen:
            seen[name] = 0
            names.append(name)
        else:
            seen[name] += 1
            names.append(f"{name}_{seen[name]}")
    result.columns = names
    return result


def _read_html(path: Path) -> pd.DataFrame:
    try:
        tables = pd.read_html(path)
    except ImportError as exc:
        raise ValueError(_missing_dependency_hint(exc, suffix=".html")) from exc
    if not tables:
        raise ValueError("HTML 파일에서 표를 찾을 수 없습니다.")
    return _normalize_dataframe_columns(tables[0])


def _read_xml(path: Path) -> pd.DataFrame:
    try:
        return pd.read_xml(path)
    except ImportError as exc:
        raise ValueError(_missing_dependency_hint(exc, suffix=".xml")) from exc


def _read_hdf(path: Path) -> pd.DataFrame:
    try:
        return pd.read_hdf(path)
    except ImportError as exc:
        raise ValueError(_missing_dependency_hint(exc, suffix=".hdf5")) from exc


def _read_pickle(path: Path) -> pd.DataFrame:
    obj = pd.read_pickle(path)
    if isinstance(obj, pd.DataFrame):
        return obj
    raise ValueError("Pickle 파일에 DataFrame이 없습니다.")


def _load_by_fallback(path: Path) -> pd.DataFrame:
    errors: list[str] = []
    for loader in (
        lambda p: _read_csv_auto(p),
        lambda p: _load_delimited_text(p),
        lambda p: _read_excel(p),
        lambda p: _read_json(p),
        lambda p: pd.read_parquet(p),
        lambda p: pd.read_feather(p),
        lambda p: _read_pickle(p),
        lambda p: _read_html(p),
        lambda p: pd.read_stata(p),
        lambda p: pd.read_sas(p),
        lambda p: _read_hdf(p),
    ):
        try:
            return loader(path)
        except Exception as exc:
            errors.append(str(exc))
    detail = errors[-1] if errors else "알 수 없는 형식"
    raise ValueError(f"파일 형식을 자동으로 인식하지 못했습니다. ({detail})")


_LOADERS: dict[str, Callable[[Path], pd.DataFrame]] = {
    ".csv": _read_csv_auto,
    ".csv.gz": _read_csv_auto,
    ".tsv": lambda p: _read_csv_auto(p, sep="\t"),
    ".tsv.gz": lambda p: _read_csv_auto(p, sep="\t"),
    ".txt": _load_delimited_text,
    ".txt.gz": _load_delimited_text,
    ".dat": _load_delimited_text,
    ".log": _load_delimited_text,
    ".psv": lambda p: _read_csv_auto(p, sep="|"),
    ".parquet": pd.read_parquet,
    ".parquet.gz": pd.read_parquet,
    ".json": _read_json,
    ".jsonl": _read_json,
    ".ndjson": _read_json,
    ".json.gz": _read_json,
    ".feather": pd.read_feather,
    ".arrow": pd.read_feather,
    ".pkl": _read_pickle,
    ".pickle": _read_pickle,
    ".html": _read_html,
    ".htm": _read_html,
    ".xml": _read_xml,
    ".dta": pd.read_stata,
    ".sas7bdat": pd.read_sas,
    ".xpt": pd.read_sas,
    ".h5": _read_hdf,
    ".hdf5": _read_hdf,
}


def guess_save_format(path: Path) -> str:
    suffix = resolve_file_suffix(path)
    mapping = {
        ".csv": "csv_utf8_sig",
        ".csv.gz": "csv_utf8_sig",
        ".tsv": "tsv",
        ".tsv.gz": "tsv",
        ".xlsx": "xlsx",
        ".xlsm": "xlsx",
        ".xltx": "xlsx",
        ".xltm": "xlsx",
        ".xls": "xlsx",
        ".xlsb": "xlsx",
        ".ods": "xlsx",
        ".parquet": "parquet",
        ".parquet.gz": "parquet",
        ".json": "json",
        ".jsonl": "json",
        ".ndjson": "json",
        ".json.gz": "json",
    }
    return mapping.get(suffix, "csv_utf8_sig")


def ensure_extension(path: Path, save_format: str) -> Path:
    path = Path(path)
    ext = SAVE_EXT_BY_FORMAT.get(save_format, ".csv")
    if path.suffix.lower() != ext:
        return path.with_suffix(ext)
    return path


def save_file(
    path: Path,
    df: pd.DataFrame,
    *,
    save_format: str = "csv_utf8_sig",
    sheet_name: str = "Sheet1",
    sheet_names: list[str] | None = None,
    sheet_frames: dict[str, pd.DataFrame] | None = None,
    source_path: Path | None = None,
) -> Path:
    path = Path(path)

    if save_format == "csv_utf8_sig":
        path = ensure_extension(path, save_format)
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif save_format == "csv_utf8":
        path = ensure_extension(path, save_format)
        df.to_csv(path, index=False, encoding="utf-8")
    elif save_format == "csv_cp949":
        path = ensure_extension(path, save_format)
        df.to_csv(path, index=False, encoding="cp949")
    elif save_format == "tsv":
        path = ensure_extension(path, save_format)
        df.to_csv(path, index=False, sep="\t", encoding="utf-8-sig")
    elif save_format == "xlsx":
        path = ensure_extension(path, save_format)
        if sheet_names and len(sheet_names) > 1:
            frames = dict(sheet_frames or {})
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                for name in sheet_names:
                    if name in frames:
                        frames[name].to_excel(writer, sheet_name=name, index=False)
                    elif source_path is not None:
                        _read_excel(source_path, sheet_name=name).to_excel(
                            writer, sheet_name=name, index=False
                        )
                    else:
                        df.to_excel(writer, sheet_name=name, index=False)
        else:
            df.to_excel(path, index=False, sheet_name=sheet_name or "Sheet1")
    elif save_format == "parquet":
        path = ensure_extension(path, save_format)
        df.to_parquet(path, index=False)
    elif save_format == "json":
        path = ensure_extension(path, save_format)
        df.to_json(path, orient="records", force_ascii=False, indent=2)
    else:
        raise ValueError(f"지원하지 않는 저장 형식: {save_format}")

    return path
