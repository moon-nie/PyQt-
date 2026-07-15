"""웹 페이지 CSS selector 크롤링 — 순수 로직 (PyQt 금지).

기본 `fetch_html`은 정적 HTML만 가져옵니다. JS SPA·관리자 로그인이 필요하면
UI 계층(`qt_webengine_crawl`)에서 렌더된 HTML을 받은 뒤 이 모듈의
`extract_by_css` / `crawl_to_dataframe` / `extract_fields`를 사용합니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_USER_AGENT = (
    "Gridloom/0.8 (+https://github.com/moon-nie/PyQt-; desktop tabular workbench)"
)
ALLOWED_ATTRS = ("text", "href", "src")
MULTI_VALUE_JOIN = " | "

_SKIP_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "svg",
        "path",
        "meta",
        "link",
        "head",
        "br",
        "hr",
        "input",
        "button",
        "option",
    }
)
_LISTISH_TAGS = frozenset({"li", "tr", "article", "section", "item", "a", "h1", "h2", "h3", "h4"})


@dataclass(frozen=True)
class StructureCandidate:
    """구조 스캔으로 찾은 반복 블록 후보."""

    selector: str
    count: int
    score: float
    sample_texts: tuple[str, ...]
    suggested_attr: str
    label: str


@dataclass(frozen=True)
class CrawlField:
    """일괄 수집 시 페이지에서 뽑을 한 열."""

    name: str
    selector: str
    attr: str = "text"


def fetch_html(
    url: str,
    *,
    timeout: float = 30.0,
    user_agent: str = DEFAULT_USER_AGENT,
    cookie: str | None = None,
) -> str:
    """URL에서 HTML 문자열을 가져옵니다."""
    target = (url or "").strip()
    if not target:
        raise ValueError("URL이 비어 있습니다.")
    if not target.lower().startswith(("http://", "https://")):
        raise ValueError("URL은 http:// 또는 https:// 로 시작해야 합니다.")
    headers = {"User-Agent": user_agent}
    cookie_text = (cookie or "").strip()
    if cookie_text:
        headers["Cookie"] = cookie_text
    req = Request(target, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — 사용자 지정 URL
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read()
    except HTTPError as exc:
        raise ValueError(f"HTTP {exc.code}: {exc.reason}") from exc
    except URLError as exc:
        raise ValueError(f"요청 실패: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ValueError(f"시간 초과 ({timeout:.0f}초)") from exc
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _element_value(el, attr: str) -> str:
    key = (attr or "text").strip().lower()
    if key == "text":
        return " ".join(el.stripped_strings)
    if key in {"href", "src"}:
        value = el.get(key)
        return "" if value is None else str(value).strip()
    raise ValueError(f"지원하지 않는 속성입니다: {attr} (text/href/src)")


def extract_by_css(
    html: str,
    selector: str,
    *,
    attr: str = "text",
    limit: int | None = None,
) -> list[str]:
    """HTML에서 CSS selector로 값을 추출합니다."""
    sel = (selector or "").strip()
    if not sel:
        raise ValueError("CSS selector가 비어 있습니다.")
    if attr.strip().lower() not in ALLOWED_ATTRS:
        raise ValueError(f"지원하지 않는 속성입니다: {attr} (text/href/src)")
    soup = BeautifulSoup(html or "", "lxml")
    try:
        nodes = soup.select(sel)
    except Exception as exc:  # BeautifulSoup/cssselect 구문 오류
        raise ValueError(f"잘못된 CSS selector: {exc}") from exc
    values = [_element_value(el, attr) for el in nodes]
    if limit is not None and limit >= 0:
        values = values[:limit]
    return values


def crawl_to_dataframe(
    html: str,
    selector: str,
    *,
    attr: str = "text",
    limit: int | None = None,
    column: str = "value",
) -> pd.DataFrame:
    """추출 결과를 한 열 DataFrame으로 만듭니다."""
    values = extract_by_css(html, selector, attr=attr, limit=limit)
    name = (column or "value").strip() or "value"
    return pd.DataFrame({name: values})


def crawl_url_to_dataframe(
    url: str,
    selector: str,
    *,
    attr: str = "text",
    limit: int | None = None,
    column: str = "value",
    timeout: float = 30.0,
    cookie: str | None = None,
) -> pd.DataFrame:
    """URL을 가져와 selector로 추출한 DataFrame을 반환합니다."""
    html = fetch_html(url, timeout=timeout, cookie=cookie)
    return crawl_to_dataframe(html, selector, attr=attr, limit=limit, column=column)


def parse_param_list(text: str) -> list[str]:
    """줄 단위 파라미터 목록(# 주석·빈 줄 무시)."""
    values: list[str] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw not in seen:
            values.append(raw)
            seen.add(raw)
    return values


def series_to_param_list(series: pd.Series) -> list[str]:
    """DataFrame 열 값을 파라미터 목록으로 변환(결측·중복 제거, 순서 유지)."""
    values: list[str] = []
    seen: set[str] = set()
    for raw in series.tolist():
        if pd.isna(raw):
            continue
        text = str(raw).strip()
        if not text or text in seen:
            continue
        values.append(text)
        seen.add(text)
    return values


def load_params_from_file(path: str | Path, *, column: str | None = None) -> list[str]:
    """텍스트/표 파일에서 파라미터 목록을 읽습니다.

    - .txt/.csv 한 줄 값, 또는 표면 ``column``(없으면 첫 열) 사용
    """
    from pathlib import Path as _Path

    from df_tool.loader import load_file

    target = _Path(path)
    if not target.is_file():
        raise ValueError(f"파일이 없습니다: {target}")
    suffix = target.suffix.lower()
    if suffix in {".txt", ".list"}:
        return parse_param_list(target.read_text(encoding="utf-8-sig"))
    loaded = load_file(target)
    df = loaded.dataframe
    if df is None or df.empty:
        raise ValueError("파일에 데이터가 없습니다.")
    if column:
        key = column if column in df.columns else str(column)
        if key not in df.columns:
            # int 열명 등
            from df_tool.operations import resolve_column_key

            resolved = resolve_column_key(df, column)
            if resolved is None:
                raise ValueError(f"열 '{column}'을(를) 찾을 수 없습니다.")
            key = resolved
        return series_to_param_list(df[key])
    return series_to_param_list(df.iloc[:, 0])


def parse_fields_text(text: str) -> list[CrawlField]:
    """열 매핑 텍스트: `열이름|selector` 또는 `열이름|selector|attr`."""
    fields: list[CrawlField] = []
    for line in (text or "").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = [p.strip() for p in raw.split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            raise ValueError(f"열 매핑 형식 오류: {raw!r} (열이름|selector|attr)")
        name, selector = parts[0], parts[1]
        attr = parts[2] if len(parts) >= 3 and parts[2] else "text"
        if attr.lower() not in ALLOWED_ATTRS:
            raise ValueError(f"지원하지 않는 속성: {attr} (text/href/src)")
        fields.append(CrawlField(name=name, selector=selector, attr=attr.lower()))
    if not fields:
        raise ValueError("열 매핑이 비어 있습니다. 예: 종목명|.wrap_company h2 a|text")
    return fields


def render_url_template(template: str, **params: str) -> str:
    """`{code}` 등 자리표시자를 채운 URL을 만듭니다."""
    tpl = (template or "").strip()
    if not tpl:
        raise ValueError("URL 템플릿이 비어 있습니다.")
    if "{" not in tpl:
        # 자리표시자 없으면 그대로(단일 URL 반복 방지용으로는 params 무시)
        return tpl
    try:
        return tpl.format(**params)
    except KeyError as exc:
        raise ValueError(
            f"URL 템플릿 자리표시자 {{{exc.args[0]}}} 에 값이 없습니다. "
            "예: ...?code={{code}}"
        ) from exc
    except ValueError as exc:
        raise ValueError(f"잘못된 URL 템플릿: {exc}") from exc


def format_cookie_header(cookies: dict[str, str]) -> str:
    """이름→값 딕셔너리를 HTTP Cookie 헤더 문자열로 만듭니다."""
    parts = []
    for name, value in cookies.items():
        n = str(name).strip()
        if not n:
            continue
        parts.append(f"{n}={value}")
    return "; ".join(parts)


def _crawl_join_key(value) -> object:
    """크롤 병합용 키 정규화 (숫자 13 과 문자열 '13'을 같게)."""
    if value is None:
        return pd.NA
    try:
        if pd.isna(value):
            return pd.NA
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        if float(value) == int(value):
            return str(int(value))
        return str(value).strip()
    text = str(value).strip()
    return text if text else pd.NA


def merge_crawl_into_base(
    base: pd.DataFrame,
    crawl: pd.DataFrame,
    *,
    left_on: str,
    right_on: str,
) -> pd.DataFrame:
    """열린 표(base)에 크롤 결과(crawl)를 키로 left-join 합니다.

    base 행 수·순서는 유지하고, crawl의 추가 열만 붙입니다.
    같은 키가 crawl에 여러 행이면 첫 행만 사용합니다.
    """
    if base is None or not isinstance(base, pd.DataFrame) or base.empty:
        raise ValueError("열린 표가 비어 있습니다.")
    if crawl is None or not isinstance(crawl, pd.DataFrame) or crawl.empty:
        raise ValueError("크롤 결과가 비어 있습니다.")
    if left_on not in base.columns:
        raise ValueError(f"열린 표에 열 '{left_on}'이(가) 없습니다.")
    if right_on not in crawl.columns:
        raise ValueError(f"크롤 결과에 키 열 '{right_on}'이(가) 없습니다.")

    left = base.copy()
    right = crawl.copy()
    left_tmp = "__gl_crawl_lkey__"
    right_tmp = "__gl_crawl_rkey__"
    left[left_tmp] = left[left_on].map(_crawl_join_key)
    right[right_tmp] = right[right_on].map(_crawl_join_key)
    # 결측 키는 매칭하지 않음 (모든 빈 키가 하나로 붙는 것 방지)
    right = right[right[right_tmp].notna()].copy()
    right = right.drop_duplicates(subset=[right_tmp], keep="first")

    bring = [c for c in right.columns if c not in {right_tmp, right_on}]
    right_slim = right[[right_tmp, *bring]].copy()
    # 열린 표와 이름 충돌 시 _crawl 접미사
    rename = {}
    for col in bring:
        if col in left.columns:
            rename[col] = f"{col}_crawl"
    if rename:
        right_slim = right_slim.rename(columns=rename)

    merged = left.merge(right_slim, how="left", left_on=left_tmp, right_on=right_tmp)
    return merged.drop(columns=[left_tmp, right_tmp], errors="ignore")


def extract_fields(
    html: str,
    fields: list[CrawlField],
    *,
    join_multi: bool = True,
    join_separator: str = MULTI_VALUE_JOIN,
) -> dict[str, str]:
    """페이지에서 필드별 값을 추출합니다.

    ``join_multi=True``이면 매칭이 여러 개일 때 구분자로 이어 붙입니다
    (상세 이미지 src 여러 장 등). False면 첫 매칭만 사용합니다.
    """
    result: dict[str, str] = {}
    for field in fields:
        limit = None if join_multi else 1
        values = [v for v in extract_by_css(html, field.selector, attr=field.attr, limit=limit) if v]
        if not values:
            result[field.name] = ""
        elif len(values) == 1 or not join_multi:
            result[field.name] = values[0]
        else:
            result[field.name] = join_separator.join(values)
    return result


def crawl_batch(
    url_template: str,
    params: list[str],
    fields: list[CrawlField],
    *,
    param_key: str = "code",
    delay_sec: float = 0.35,
    timeout: float = 30.0,
    cookie: str | None = None,
    max_items: int | None = None,
) -> pd.DataFrame:
    """URL 템플릿 + 파라미터 목록으로 여러 페이지를 순회해 표로 만듭니다.

    예::
        template = "https://finance.naver.com/item/main.naver?code={code}"
        params = ["005930", "000660"]
        fields = [CrawlField("종목명", ".wrap_company h2 a")]
    """
    import time

    key = (param_key or "code").strip() or "code"
    values = list(params)
    if max_items is not None and max_items >= 0:
        values = values[:max_items]
    if not values:
        raise ValueError("파라미터 목록이 비어 있습니다.")
    if not fields:
        raise ValueError("열 매핑이 비어 있습니다.")

    rows: list[dict[str, str]] = []
    for i, value in enumerate(values):
        url = render_url_template(url_template, **{key: value})
        row: dict[str, str] = {key: value, "url": url}
        try:
            html = fetch_html(url, timeout=timeout, cookie=cookie)
            row.update(extract_fields(html, fields))
            row["error"] = ""
        except Exception as exc:
            for field in fields:
                row.setdefault(field.name, "")
            row["error"] = str(exc)
        rows.append(row)
        if delay_sec > 0 and i < len(values) - 1:
            time.sleep(delay_sec)

    columns = [key, "url", *[f.name for f in fields], "error"]
    return pd.DataFrame(rows, columns=columns)


def _safe_css_ident(token: str) -> str | None:
    text = (token or "").strip()
    if not text:
        return None
    if any(ch in text for ch in " .#:[],()>\"'`"):
        return None
    return text


def _element_classes(el: Tag) -> tuple[str, ...]:
    raw = el.get("class") or []
    classes: list[str] = []
    for item in raw:
        ident = _safe_css_ident(str(item))
        if ident and ident not in classes:
            classes.append(ident)
        if len(classes) >= 2:
            break
    return tuple(classes)


def _fingerprint(el: Tag) -> tuple[str, tuple[str, ...]]:
    return el.name.lower(), _element_classes(el)


def _css_for_element(el: Tag) -> str:
    tag = el.name.lower()
    el_id = _safe_css_ident(str(el.get("id") or ""))
    if el_id:
        return f"#{el_id}"
    classes = _element_classes(el)
    if classes:
        return tag + "".join(f".{c}" for c in classes)
    return tag


def _child_selector(parent: Tag, tag: str, classes: tuple[str, ...]) -> str:
    parent_css = _css_for_element(parent)
    child = tag
    if classes:
        child += "".join(f".{c}" for c in classes)
    return f"{parent_css} > {child}"


def _sample_text(el: Tag, *, max_len: int = 80) -> str:
    text = " ".join(el.stripped_strings)
    text = " ".join(text.split())
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _score_group(tag: str, classes: tuple[str, ...], nodes: list[Tag]) -> tuple[float, str]:
    count = len(nodes)
    texts = [_sample_text(n) for n in nodes]
    nonempty = sum(1 for t in texts if t)
    text_ratio = nonempty / count if count else 0.0
    href_hits = 0
    for n in nodes:
        if n.name.lower() == "a" and n.get("href"):
            href_hits += 1
        elif n.find("a", href=True) is not None:
            href_hits += 1
    href_ratio = href_hits / count if count else 0.0

    score = min(count, 40) / 40.0 * 45.0
    score += text_ratio * 30.0
    score += href_ratio * 15.0
    if tag in _LISTISH_TAGS:
        score += 8.0
    if classes:
        score += 6.0
    elif tag in {"div", "span"}:
        score -= 12.0

    suggested = "href" if href_ratio >= 0.5 else "text"
    return max(score, 0.0), suggested


def scan_structure(
    html: str,
    *,
    min_items: int = 3,
    max_candidates: int = 12,
    sample_size: int = 3,
) -> list[StructureCandidate]:
    """HTML에서 반복되는 형제 블록을 찾아 점수순 후보를 반환합니다."""
    soup = BeautifulSoup(html or "", "lxml")
    body = soup.body or soup
    best: dict[str, StructureCandidate] = {}

    for parent in body.find_all(True):
        if not isinstance(parent, Tag):
            continue
        if parent.name.lower() in _SKIP_TAGS:
            continue
        groups: dict[tuple[str, tuple[str, ...]], list[Tag]] = {}
        for child in parent.children:
            if isinstance(child, NavigableString) or not isinstance(child, Tag):
                continue
            if child.name.lower() in _SKIP_TAGS:
                continue
            key = _fingerprint(child)
            groups.setdefault(key, []).append(child)

        for (tag, classes), nodes in groups.items():
            if len(nodes) < min_items:
                continue
            selector = _child_selector(parent, tag, classes)
            try:
                matched = soup.select(selector)
            except Exception:
                continue
            if len(matched) < min_items:
                continue
            if len(matched) > max(len(nodes) * 3, len(nodes) + 10):
                continue

            score, suggested = _score_group(tag, classes, matched[:50])
            if score < 8.0:
                continue
            samples = tuple(t for t in (_sample_text(n) for n in matched[:sample_size]) if t)
            if not samples:
                href_samples: list[str] = []
                for n in matched[:sample_size]:
                    if n.name.lower() == "a" and n.get("href"):
                        href_samples.append(str(n.get("href")))
                    else:
                        a = n.find("a", href=True)
                        if a is not None:
                            href_samples.append(str(a.get("href")))
                samples = tuple(href_samples[:sample_size])
            label = f"{selector}  ·  {len(matched)}개  ·  점수 {score:.0f}"
            cand = StructureCandidate(
                selector=selector,
                count=len(matched),
                score=round(score, 2),
                sample_texts=samples,
                suggested_attr=suggested,
                label=label,
            )
            prev = best.get(selector)
            if prev is None or cand.score > prev.score:
                best[selector] = cand

    ranked = sorted(best.values(), key=lambda c: (-c.score, -c.count, c.selector))
    return ranked[:max_candidates]


def scan_url_structure(
    url: str,
    *,
    min_items: int = 3,
    max_candidates: int = 12,
    sample_size: int = 3,
    timeout: float = 30.0,
    cookie: str | None = None,
) -> list[StructureCandidate]:
    """URL을 가져와 구조 스캔 후보를 반환합니다."""
    html = fetch_html(url, timeout=timeout, cookie=cookie)
    return scan_structure(
        html,
        min_items=min_items,
        max_candidates=max_candidates,
        sample_size=sample_size,
    )
