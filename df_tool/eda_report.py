"""EDA HTML 리포트 생성 (PyQt import 금지)."""
from __future__ import annotations

import base64
from io import BytesIO
from datetime import datetime
from html import escape

import pandas as pd

from df_tool.analysis import (
    PLOT_MAX_ROWS,
    eda_overview,
    format_stat_number,
    missing_summary,
    numeric_columns,
)
from df_tool.operations import resolve_column_key
from df_tool.ui_fonts import html_body_font_css_stack


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
    return f'<figure><img src="{src}" alt="{escape(alt)}"/><figcaption>{escape(alt)}</figcaption></figure>'


def _render_charts(df: pd.DataFrame, missing: list[tuple[str, int, float]], nums: list[str]) -> str:
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
            ax.barh([m[0] for m in top], [m[2] for m in top], color="#818cf8")
            ax.set_xlabel("결측 비율 (%)")
            ax.set_title("결측 비율 상위 열")
            ax.invert_yaxis()
            figures.append(_chart_img(_fig_to_data_uri(fig), "결측 비율 상위 열"))

        if nums:
            key = resolve_column_key(df, nums[0])
            if key is not None:
                plot_df, sampled = sample_for_plot(df[[key]], max_rows=PLOT_MAX_ROWS)
                vals = pd.to_numeric(plot_df[key], errors="coerce").dropna()
                if len(vals):
                    fig = Figure(figsize=(8, 4), dpi=130)
                    ax = fig.add_subplot(111)
                    ax.hist(vals, bins=min(40, max(10, len(vals) // 20)), color="#22d3ee", edgecolor="#64748b")
                    ax.set_title(f"{key} 분포")
                    ax.set_xlabel(str(key))
                    ax.set_ylabel("빈도")
                    sample_note = f" (표본 n={len(plot_df):,})" if sampled else f" (전체 n={len(plot_df):,})"
                    figures.append(_chart_img(_fig_to_data_uri(fig), f"{key} 분포{sample_note}"))

        if len(nums) >= 2:
            keys = [resolve_column_key(df, c) for c in nums[:10]]
            keys = [k for k in keys if k is not None]
            if len(keys) >= 2:
                corr = df[keys].apply(pd.to_numeric, errors="coerce").corr()
                if not corr.empty:
                    fig = Figure(figsize=(7, 5), dpi=130)
                    ax = fig.add_subplot(111)
                    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdBu_r", aspect="auto")
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
    return "\n".join(figures)


def build_eda_html(df: pd.DataFrame, *, title: str = "Gridloom EDA 리포트") -> str:
    """데이터프레임 EDA 요약 HTML 문자열."""
    overview = eda_overview(df)
    missing = missing_summary(df)
    nums = numeric_columns(df)
    chart_section = _render_charts(df, missing, nums)

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

    missing_rows = [[name, f"{cnt:,}", f"{pct:.1f}%"] for name, cnt, pct in missing[:30]]

    corr_section = ""
    if len(nums) >= 2:
        keys = [resolve_column_key(df, c) for c in nums[:12]]
        keys = [k for k in keys if k is not None]
        if len(keys) >= 2:
            corr = df[keys].apply(pd.to_numeric, errors="coerce").corr()
            corr_rows = []
            for i, row_name in enumerate(corr.index):
                for j, col_name in enumerate(corr.columns):
                    if j <= i:
                        continue
                    val = corr.iloc[i, j]
                    if pd.notna(val):
                        corr_rows.append([str(row_name), str(col_name), f"{val:.4f}"])
            if corr_rows:
                corr_section = f"""
<h2>수치 열 상관 (상위 12열, |r| 큰 순)</h2>
{_html_table(["열 A", "열 B", "피어슨 r"], sorted(corr_rows, key=lambda r: -abs(float(r[2])))[:25])}
"""

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<title>{escape(title)}</title>
<style>
body {{ font-family: {html_body_font_css_stack()}; margin: 24px; color: #1e293b; background: #f8fafc; }}
h1 {{ color: #312e81; border-bottom: 2px solid #818cf8; padding-bottom: 8px; }}
h2 {{ color: #4338ca; margin-top: 28px; }}
.meta {{ color: #64748b; margin-bottom: 20px; }}
.warn {{ color: #b45309; background: #fef3c7; border: 1px solid #f59e0b; padding: 10px; border-radius: 6px; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; background: #fff; }}
th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; font-size: 13px; }}
th {{ background: #e0e7ff; }}
tr:nth-child(even) {{ background: #f1f5f9; }}
.summary {{ background: #fff; padding: 16px; border-radius: 8px; border: 1px solid #e2e8f0; }}
figure {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin: 16px 0 24px; }}
figcaption {{ color: #64748b; font-size: 12px; margin-top: 8px; }}
img {{ max-width: 100%; height: auto; display: block; }}
</style>
</head>
<body>
<h1>{escape(title)}</h1>
<p class="meta">생성: {generated} · Gridloom EDA</p>
<div class="summary">
<p><strong>행 × 열:</strong> {overview.row_count:,} × {overview.col_count:,}</p>
<p><strong>숫자 열:</strong> {len(nums)}개 · <strong>결측 있는 열:</strong> {len(missing)}개</p>
</div>

<h2>핵심 차트</h2>
<p class="meta">분포 차트는 데이터가 많을 경우 최대 {PLOT_MAX_ROWS:,}행 무작위 표본으로 표시됩니다. 표와 결측 요약은 현재 열린 전체 데이터 기준입니다.</p>
{chart_section}

<h2>열 개요</h2>
{_html_table(["컬럼", "종류", "타입", "결측", "결측%", "고유값", "평균", "표준편차"], overview_rows)}

<h2>결측 현황 (상위 30열)</h2>
{"<p>결측치 없음</p>" if not missing_rows else _html_table(["컬럼", "결측 수", "결측%"], missing_rows)}

{corr_section}

<p class="meta">— Gridloom · 표 데이터 EDA</p>
</body>
</html>"""
