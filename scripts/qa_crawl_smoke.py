"""crawl.py headless smoke — 네트워크 없이 HTML 문자열로 검증."""
from __future__ import annotations

import sys

import pandas as pd

from df_tool.crawl import (
    CrawlField,
    crawl_batch,
    crawl_to_dataframe,
    extract_by_css,
    extract_fields,
    fetch_html,
    parse_fields_text,
    parse_param_list,
    render_url_template,
    scan_structure,
    series_to_param_list,
)


SAMPLE_HTML = """
<html><body>
  <ul class="items">
    <li><a href="/a">Alpha</a></li>
    <li><a href="/b">Beta</a></li>
    <li><a href="/c">Gamma</a></li>
  </ul>
  <div class="wrap_company"><h2><a href="/x">삼성전자</a></h2></div>
  <div class="no_today"><span class="blind">264000</span></div>
  <img class="pic" src="/img.png" />
</body></html>
"""


def main() -> int:
    texts = extract_by_css(SAMPLE_HTML, "ul.items a", attr="text")
    assert texts == ["Alpha", "Beta", "Gamma"], texts

    hrefs = extract_by_css(SAMPLE_HTML, "ul.items a", attr="href", limit=2)
    assert hrefs == ["/a", "/b"], hrefs

    srcs = extract_by_css(SAMPLE_HTML, "img.pic", attr="src")
    assert srcs == ["/img.png"], srcs

    df = crawl_to_dataframe(SAMPLE_HTML, "ul.items a", attr="text", column="title")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["title"]
    assert df["title"].tolist() == ["Alpha", "Beta", "Gamma"]

    empty = crawl_to_dataframe(SAMPLE_HTML, ".missing", attr="text")
    assert empty.empty and list(empty.columns) == ["value"]

    try:
        extract_by_css(SAMPLE_HTML, "", attr="text")
        raise AssertionError("빈 selector는 ValueError여야 함")
    except ValueError:
        pass

    try:
        fetch_html("not-a-url")
        raise AssertionError("잘못된 URL은 ValueError여야 함")
    except ValueError:
        pass

    candidates = scan_structure(SAMPLE_HTML, min_items=3)
    assert candidates, "반복 li 후보가 있어야 함"
    selectors = {c.selector for c in candidates}
    assert any("li" in s for s in selectors), selectors
    top = candidates[0]
    assert top.count >= 3 and top.score > 0
    assert top.suggested_attr in {"text", "href"}

    # URL 템플릿 · 필드 파싱 · 일괄(로컬 HTML은 fetch 없이 extract_fields)
    assert render_url_template(
        "https://finance.naver.com/item/main.naver?code={code}", code="005930"
    ).endswith("code=005930")
    assert parse_param_list("005930\n# skip\n000660\n005930") == ["005930", "000660"]
    assert series_to_param_list(pd.Series(["005930", None, "000660", "005930"])) == ["005930", "000660"]
    fields = parse_fields_text("종목명|.wrap_company h2 a|text\n현재가|.no_today .blind|text")
    assert len(fields) == 2 and fields[0].name == "종목명"
    extracted = extract_fields(SAMPLE_HTML, fields)
    assert extracted["종목명"] == "삼성전자"
    assert "264000" in extracted["현재가"]

    # crawl_batch는 네트워크가 필요하므로 템플릿에 자리표시자 없이 실패 경로만
    # — 대신 로직 단위로 이미 검증. 빈 params는 에러.
    try:
        crawl_batch("https://example.com/{code}", [], [CrawlField("a", "b")])
        raise AssertionError("빈 params는 ValueError")
    except ValueError:
        pass

    print("qa_crawl_smoke: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
