"""EDA HTML 리포트 생성 (PyQt import 금지)."""
from __future__ import annotations

import base64
from io import BytesIO
from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd

from df_tool.analysis import (
    PLOT_MAX_ROWS,
    categorical_columns,
    eda_overview,
    format_stat_number,
    missing_summary,
    numeric_columns,
    outlier_summary,
    univariate_categorical_freq,
    univariate_categorical_stats,
)
from df_tool.operations import resolve_column_key
from df_tool.ui_fonts import html_body_font_css_stack

# 리포트 차트·표 상한
_MAX_DIST_CHARTS = 6
_MAX_CAT_CHARTS = 4
_MAX_CORR_HEATMAP = 10
_MAX_CORR_PAIRS = 25
_MAX_MISSING_ROWS = 30
_MAX_OUTLIER_ROWS = 30
_MAX_CAT_TABLE_COLS = 8
_CAT_TOP_N = 10


def default_eda_report_filename(source_path: Path | str | None) -> str:
    """저장 대화상자용 기본 파일명: ``{stem}_report.html``."""
    if source_path is None:
        return "untitled_report.html"
    path = Path(source_path)
    stem = path.stem.strip() or "untitled"
    return f"{stem}_report.html"


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    th = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        tds = "".join(f"<td>{escape(str(c))}</td>" for c in row)
        body_rows.append(f"<tr>{tds}</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _fig_to_data_uri(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _chart_img(src: str, alt: str) -> str:
    return (
        f'<figure class="chart">'
        f'<img src="{src}" alt="{escape(alt)}"/>'
        f"<figcaption>{escape(alt)}</figcaption>"
        f"</figure>"
    )


def _pick_categorical_for_charts(df: pd.DataFrame, cats: list[str]) -> list[str]:
    """고유값 2~30인 범주 열을 우선해 최대 N개."""
    scored: list[tuple[int, str]] = []
    fallback: list[str] = []
    for name in cats:
        key = resolve_column_key(df, name)
        if key is None:
            continue
        nunique = int(df[key].nunique(dropna=True))
        if 2 <= nunique <= 30:
            scored.append((nunique, str(key)))
        elif nunique >= 2:
            fallback.append(str(key))
    scored.sort(key=lambda x: x[0])
    picked = [c for _, c in scored[:_MAX_CAT_CHARTS]]
    for name in fallback:
        if len(picked) >= _MAX_CAT_CHARTS:
            break
        if name not in picked:
            picked.append(name)
    return picked


def _render_charts(
    df: pd.DataFrame,
    missing: list[tuple[str, int, float]],
    nums: list[str],
    cats: list[str],
) -> str:
    """리포트용 핵심 차트. 실패 시 리포트 본문은 계속 생성."""
    try:
        from matplotlib.figure import Figure

        from df_tool.analysis import configure_matplotlib_font, sample_for_plot

        configure_matplotlib_font()
    except Exception as exc:
        return f'<p class="warn">차트 생성 생략: {escape(str(exc))}</p>'

    figures: list[str] = []
    try:
        if missing:
            fig = Figure(figsize=(8, 4), dpi=130)
            ax = fig.add_subplot(111)
            top = missing[:15]
            ax.barh([m[0] for m in top], [m[2] for m in top], color="#6366f1")
            ax.set_xlabel("결측 비율 (%)")
            ax.set_title("결측 비율 상위 열")
            ax.invert_yaxis()
            figures.append(_chart_img(_fig_to_data_uri(fig), "결측 비율 상위 열"))

        dist_count = 0
        for col_name in nums:
            if dist_count >= _MAX_DIST_CHARTS:
                break
            key = resolve_column_key(df, col_name)
            if key is None:
                continue
            plot_df, sampled = sample_for_plot(df[[key]], max_rows=PLOT_MAX_ROWS)
            vals = pd.to_numeric(plot_df[key], errors="coerce").dropna()
            if len(vals) == 0:
                continue
            fig = Figure(figsize=(7, 3.6), dpi=130)
            ax = fig.add_subplot(111)
            ax.hist(
                vals,
                bins=min(40, max(10, len(vals) // 20)),
                color="#06b6d4",
                edgecolor="#64748b",
            )
            ax.set_title(f"{key} 분포")
            ax.set_xlabel(str(key))
            ax.set_ylabel("빈도")
            sample_note = (
                f" (표본 n={len(plot_df):,})" if sampled else f" (전체 n={len(plot_df):,})"
            )
            figures.append(_chart_img(_fig_to_data_uri(fig), f"{key} 분포{sample_note}"))
            dist_count += 1

        for col_name in _pick_categorical_for_charts(df, cats):
            key = resolve_column_key(df, col_name)
            if key is None:
                continue
            plot_df, sampled = sample_for_plot(df[[key]], max_rows=PLOT_MAX_ROWS)
            freq = univariate_categorical_freq(plot_df[key], top_n=12)
            if not freq:
                continue
            labels = [f[0] for f in freq]
            counts = [f[1] for f in freq]
            fig = Figure(figsize=(7, 3.6), dpi=130)
            ax = fig.add_subplot(111)
            ax.barh(labels[::-1], counts[::-1], color="#8b5cf6")
            ax.set_xlabel("빈도")
            ax.set_title(f"{key} 상위 범주")
            sample_note = (
                f" (표본 n={len(plot_df):,})" if sampled else f" (전체 n={len(plot_df):,})"
            )
            figures.append(
                _chart_img(_fig_to_data_uri(fig), f"{key} 상위 범주{sample_note}")
            )

        if len(nums) >= 2:
            keys = [resolve_column_key(df, c) for c in nums[:_MAX_CORR_HEATMAP]]
            keys = [k for k in keys if k is not None]
            if len(keys) >= 2:
                corr = df[keys].apply(pd.to_numeric, errors="coerce").corr()
                if not corr.empty:
                    fig = Figure(figsize=(7, 5), dpi=130)
                    ax = fig.add_subplot(111)
                    im = ax.imshow(
                        corr.values, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto"
                    )
                    labels = [str(c) for c in corr.columns]
                    ax.set_xticks(range(len(labels)))
                    ax.set_xticklabels(labels, rotation=45, ha="right")
                    ax.set_yticks(range(len(labels)))
                    ax.set_yticklabels(labels)
                    fig.colorbar(im, ax=ax, fraction=0.046)
                    ax.set_title("상관 행렬")
                    figures.append(_chart_img(_fig_to_data_uri(fig), "상관 행렬"))
    except Exception as exc:
        figures.append(f'<p class="warn">일부 차트 생성 생략: {escape(str(exc))}</p>')

    if not figures:
        return '<p class="meta">표시할 차트가 없습니다.</p>'
    return '<div class="chart-grid">\n' + "\n".join(figures) + "\n</div>"


def _top_corr_pairs(
    df: pd.DataFrame, nums: list[str], *, limit: int = _MAX_CORR_PAIRS
) -> list[tuple[str, str, float]]:
    keys = [resolve_column_key(df, c) for c in nums[:12]]
    keys = [k for k in keys if k is not None]
    if len(keys) < 2:
        return []
    corr = df[keys].apply(pd.to_numeric, errors="coerce").corr()
    pairs: list[tuple[str, str, float]] = []
    for i, row_name in enumerate(corr.index):
        for j, col_name in enumerate(corr.columns):
            if j <= i:
                continue
            val = corr.iloc[i, j]
            if pd.notna(val):
                pairs.append((str(row_name), str(col_name), float(val)))
    pairs.sort(key=lambda p: -abs(p[2]))
    return pairs[:limit]


def _build_insights(
    *,
    overview,
    missing: list[tuple[str, int, float]],
    nums: list[str],
    cats: list[str],
    outliers: list[tuple[str, int, float]],
    top_corr: list[tuple[str, str, float]],
) -> list[str]:
    lines: list[str] = []
    lines.append(
        f"데이터는 {overview.row_count:,}행 × {overview.col_count:,}열이며, "
        f"수치 열 {len(nums)}개·범주 열 {len(cats)}개입니다."
    )
    if missing:
        top_name, top_cnt, top_pct = missing[0]
        lines.append(
            f"결측이 있는 열은 {len(missing)}개입니다. "
            f"가장 결측이 많은 열은 '{top_name}'({top_pct:.1f}%, {top_cnt:,}건)입니다."
        )
    else:
        lines.append("결측치가 있는 열이 없습니다.")

    strong = [p for p in top_corr if abs(p[2]) >= 0.7]
    if strong:
        a, b, r = strong[0]
        lines.append(
            f"강한 상관(|r|≥0.7)이 {len(strong)}쌍 있으며, "
            f"가장 큰 쌍은 '{a}' ↔ '{b}' (r={r:.3f})입니다."
        )
    elif top_corr:
        a, b, r = top_corr[0]
        lines.append(
            f"수치 열 간 상관 중 |r|가 가장 큰 쌍은 '{a}' ↔ '{b}' (r={r:.3f})입니다."
        )

    outlier_hits = [o for o in outliers if o[1] > 0]
    if outlier_hits:
        outlier_hits_sorted = sorted(outlier_hits, key=lambda x: -x[1])
        name, cnt, pct = outlier_hits_sorted[0]
        lines.append(
            f"IQR(1.5×) 기준 이상치가 있는 수치 열은 {len(outlier_hits)}개입니다. "
            f"가장 많은 열은 '{name}'({cnt:,}행, {pct:.1f}%)입니다."
        )
    elif nums:
        lines.append("IQR(1.5×) 기준 이상치가 감지된 수치 열이 없습니다.")

    return lines


def _kpi_cards(
    overview,
    nums: list[str],
    cats: list[str],
    missing: list[tuple[str, int, float]],
    outlier_hits: int,
) -> str:
    cells = [
        ("행", f"{overview.row_count:,}"),
        ("열", f"{overview.col_count:,}"),
        ("수치 열", f"{len(nums)}"),
        ("범주 열", f"{len(cats)}"),
        ("결측 열", f"{len(missing)}"),
        ("이상치 열", f"{outlier_hits}"),
    ]
    parts = []
    for label, value in cells:
        parts.append(
            f'<div class="kpi"><div class="kpi-value">{escape(value)}</div>'
            f'<div class="kpi-label">{escape(label)}</div></div>'
        )
    return '<div class="kpi-grid">' + "".join(parts) + "</div>"


def _categorical_section(df: pd.DataFrame, cats: list[str]) -> str:
    if not cats:
        return "<p class=\"meta\">범주형 열이 없습니다.</p>"
    blocks: list[str] = []
    for name in cats[:_MAX_CAT_TABLE_COLS]:
        key = resolve_column_key(df, name)
        if key is None:
            continue
        stats = univariate_categorical_stats(df[key])
        freq = univariate_categorical_freq(df[key], top_n=_CAT_TOP_N)
        if stats is None or not freq:
            continue
        header = (
            f"<h3>'{escape(str(key))}'</h3>"
            f'<p class="meta">유효 {stats.count:,} · 고유 {stats.unique:,} · '
            f"최빈 '{escape(stats.mode)}' ({stats.mode_pct:.1f}%)</p>"
        )
        rows = [[v, f"{c:,}", f"{p:.1f}%"] for v, c, p in freq]
        blocks.append(header + _html_table(["값", "건수", "비율"], rows))
    if not blocks:
        return "<p class=\"meta\">표시할 범주 요약이 없습니다.</p>"
    return "\n".join(blocks)


def _css() -> str:
    font = html_body_font_css_stack()
    return f"""
body {{ font-family: {font}; margin: 0; color: #0f172a; background: #eef2ff; }}
.page {{ max-width: 1100px; margin: 0 auto; padding: 28px 24px 48px; }}
.cover {{
  background: linear-gradient(135deg, #312e81 0%, #4338ca 55%, #6366f1 100%);
  color: #f8fafc; border-radius: 14px; padding: 28px 32px; margin-bottom: 24px;
  box-shadow: 0 10px 30px rgba(49, 46, 129, 0.25);
}}
.cover .brand {{ font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase;
  opacity: 0.85; margin-bottom: 8px; }}
.cover h1 {{ margin: 0 0 10px; font-size: 28px; font-weight: 700; border: none; color: #fff; }}
.cover .meta {{ color: #e0e7ff; margin: 0; }}
h2 {{ color: #312e81; margin-top: 36px; margin-bottom: 12px; font-size: 20px;
  border-bottom: 2px solid #c7d2fe; padding-bottom: 6px; }}
h3 {{ color: #4338ca; margin-top: 20px; margin-bottom: 6px; font-size: 15px; }}
.meta {{ color: #64748b; margin-bottom: 12px; }}
.warn {{ color: #92400e; background: #fef3c7; border: 1px solid #f59e0b;
  padding: 10px 12px; border-radius: 8px; }}
.section {{
  background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 18px 20px; margin-bottom: 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}}
.kpi-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px; margin: 8px 0 4px;
}}
.kpi {{
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 14px 12px; text-align: center;
}}
.kpi-value {{ font-size: 22px; font-weight: 700; color: #312e81; }}
.kpi-label {{ font-size: 12px; color: #64748b; margin-top: 4px; }}
.insights {{
  background: #eef2ff; border-left: 4px solid #6366f1; border-radius: 0 10px 10px 0;
  padding: 14px 18px; margin: 0;
}}
.insights ul {{ margin: 8px 0 0; padding-left: 18px; }}
.insights li {{ margin: 6px 0; line-height: 1.45; }}
.chart-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px; align-items: start;
}}
figure.chart {{
  background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
  padding: 12px; margin: 0;
}}
figcaption {{ color: #64748b; font-size: 12px; margin-top: 8px; }}
img {{ max-width: 100%; height: auto; display: block; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0 18px; background: #fff; }}
th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; font-size: 13px; }}
th {{ background: #e0e7ff; color: #312e81; }}
tr:nth-child(even) {{ background: #f8fafc; }}
.footer {{ color: #94a3b8; font-size: 12px; margin-top: 32px; text-align: center; }}
"""


def build_eda_html(
    df: pd.DataFrame,
    *,
    title: str = "Gridloom EDA 리포트",
    source_name: str | None = None,
) -> str:
    """데이터프레임 EDA 요약 HTML 문자열."""
    overview = eda_overview(df)
    missing = missing_summary(df)
    nums = numeric_columns(df)
    cats = categorical_columns(df)
    outliers = outlier_summary(df, nums, "iqr") if nums else []
    outlier_hits = sum(1 for _, cnt, _ in outliers if cnt > 0)
    top_corr = _top_corr_pairs(df, nums)
    chart_section = _render_charts(df, missing, nums, cats)
    insights = _build_insights(
        overview=overview,
        missing=missing,
        nums=nums,
        cats=cats,
        outliers=outliers,
        top_corr=top_corr,
    )

    overview_rows = [
        [
            col.name,
            col.kind,
            col.dtype,
            f"{col.null_count:,}",
            f"{col.null_pct:.1f}%",
            f"{col.unique_count:,}",
            format_stat_number(col.mean) if col.mean is not None else "—",
            format_stat_number(col.std) if col.std is not None else "—",
        ]
        for col in overview.columns
    ]
    missing_rows = [
        [name, f"{cnt:,}", f"{pct:.1f}%"] for name, cnt, pct in missing[:_MAX_MISSING_ROWS]
    ]
    outlier_rows = [
        [name, f"{cnt:,}", f"{pct:.1f}%"]
        for name, cnt, pct in sorted(outliers, key=lambda x: -x[1])[:_MAX_OUTLIER_ROWS]
        if cnt > 0
    ]

    corr_section = ""
    if top_corr:
        corr_rows = [[a, b, f"{r:.4f}"] for a, b, r in top_corr]
        corr_section = f"""
<section class="section">
<h2>수치 열 상관 (|r| 큰 순, 상위 {_MAX_CORR_PAIRS}쌍)</h2>
<p class="meta">수치 열 최대 12개 기준 피어슨 상관입니다.</p>
{_html_table(["열 A", "열 B", "피어슨 r"], corr_rows)}
</section>
"""

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    source_line = escape(source_name) if source_name else "—"
    insight_items = "".join(f"<li>{escape(line)}</li>" for line in insights)
    kpi = _kpi_cards(overview, nums, cats, missing, outlier_hits)
    cat_html = _categorical_section(df, cats)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<title>{escape(title)}</title>
<style>{_css()}</style>
</head>
<body>
<div class="page">
  <header class="cover">
    <div class="brand">Gridloom · EDA Report</div>
    <h1>{escape(title)}</h1>
    <p class="meta">출처: {source_line} · 생성: {generated} · 행×열 {overview.row_count:,} × {overview.col_count:,}</p>
  </header>

  <section class="section">
    <h2>요약 KPI</h2>
    {kpi}
  </section>

  <section class="section">
    <h2>핵심 인사이트</h2>
    <div class="insights"><ul>{insight_items}</ul></div>
  </section>

  <section class="section">
    <h2>핵심 차트</h2>
    <p class="meta">수치 분포 최대 {_MAX_DIST_CHARTS}열 · 범주 빈도 최대 {_MAX_CAT_CHARTS}열 ·
    데이터가 많을 경우 차트는 최대 {PLOT_MAX_ROWS:,}행 무작위 표본입니다. 표·결측·이상치 요약은 전체 데이터 기준입니다.</p>
    {chart_section}
  </section>

  <section class="section">
    <h2>열 개요</h2>
    {_html_table(["컬럼", "종류", "타입", "결측", "결측%", "고유값", "평균", "표준편차"], overview_rows)}
  </section>

  <section class="section">
    <h2>결측 현황 (상위 {_MAX_MISSING_ROWS}열)</h2>
    {"<p class='meta'>결측치 없음</p>" if not missing_rows else _html_table(["컬럼", "결측 수", "결측%"], missing_rows)}
  </section>

  <section class="section">
    <h2>범주형 요약</h2>
    <p class="meta">열당 상위 {_CAT_TOP_N}개 값 · 최대 {_MAX_CAT_TABLE_COLS}열</p>
    {cat_html}
  </section>

  <section class="section">
    <h2>이상치 요약 (IQR 1.5×)</h2>
    <p class="meta">수치 열별 IQR 경계 밖 행 수입니다. Isolation Forest 등은 분석 탭에서 별도 확인하세요.</p>
    {"<p class='meta'>이상치 없음</p>" if not outlier_rows else _html_table(["컬럼", "이상치 행", "비율"], outlier_rows)}
  </section>

  {corr_section}

  <p class="footer">— Gridloom · 표 데이터 EDA 리포트 —</p>
</div>
</body>
</html>"""
