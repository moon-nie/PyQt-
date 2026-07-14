"""크롤링 탭 UI — 단일 페이지 / URL 패턴 일괄 수집."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from df_tool.crawl import (
    ALLOWED_ATTRS,
    StructureCandidate,
    crawl_batch,
    crawl_url_to_dataframe,
    load_params_from_file,
    parse_fields_text,
    parse_param_list,
    scan_url_structure,
    series_to_param_list,
)
from df_tool.qt_async import AsyncPoller
from df_tool.qt_theme import card_frame_style, primary_button
from df_tool.theme import COLORS

_BATCH_FIELDS_PLACEHOLDER = (
    "# 열이름|CSS selector|속성(생략 시 text)\n"
    "# text=글자 · href=링크주소 · src=이미지주소\n"
    "종목명|.wrap_company h2 a|text\n"
    "현재가|.no_today .blind|text\n"
    "# 이미지 예: 로고|.thumb img|src"
)

_COOKIE_HELP = """\
Cookie는 ‘브라우저에 이미 로그인한 상태’를 요청에 실어 보내는 방법입니다.

【Chrome에서 복사하는 방법】
1. 해당 사이트에 브라우저로 로그인합니다.
2. F12 → Network(네트워크) 탭을 엽니다.
3. 페이지를 새로고침한 뒤 목록에서 문서(document) 요청을 클릭합니다.
4. Headers → Request Headers → Cookie 값을 전부 복사합니다.
5. 여기 Cookie 칸에 붙여넣습니다.

【참고】
• Cookie는 비밀번호처럼 다루세요. 공유·커밋하지 마세요.
• 만료되면 다시 로그인 후 복사해야 합니다.
• 앱 안에서 로그인 창을 띄우는 방식(브라우저 자동화)은 다음 단계에서
  지원할 수 있습니다. 지금은 수동 Cookie가 가장 단순·안전합니다.
"""

_ATTR_HELP = """\
열 매핑의 세 번째 값(attr)은 ‘요소에서 무엇을 가져올지’입니다.

• text (기본, 생략 가능) — 화면에 보이는 글자 (종목명, 가격 텍스트 등)
• href — <a> 링크의 주소 (상세 페이지 URL 등)
• src — <img> 등의 리소스 주소 (썸네일 이미지 URL 등)

형식: 열이름|CSS selector|attr
예:
  종목명|.wrap_company h2 a|text
  링크|.wrap_company h2 a|href
  썸네일|.thumb img|src

같은 selector라도 attr만 바꾸면 다른 열로 넣을 수 있습니다.
"""



class CrawlPanel(QWidget):
    """가공·분석 옆 크롤링 페이지."""

    def __init__(
        self,
        *,
        on_import: Callable[[pd.DataFrame, str], None],
        has_data: Callable[[], bool],
        get_dataframe: Callable[[], pd.DataFrame | None] | None = None,
        on_log: Callable[[str, str, str | None], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_import = on_import
        self.has_data = has_data
        self.get_dataframe = get_dataframe or (lambda: None)
        self.on_log = on_log
        self._preview_df: pd.DataFrame | None = None
        self._candidates: list[StructureCandidate] = []
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gridloom-crawl")
        self._poller = AsyncPoller(poll_ms=50)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        title = QLabel("크롤링")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS['text']};")
        root.addWidget(title)

        hint = QLabel(
            "단일 페이지 수집 · URL 패턴 일괄({code} 자리표시자) · 선택적 Cookie(로그인 세션).\n"
            "정적 HTML만 지원합니다. 사이트 약관·robots·이용 제한을 지켜 주세요."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        root.addWidget(hint)

        cookie_row = QHBoxLayout()
        cookie_row.addWidget(QLabel("Cookie(선택)"))
        self.cookie_edit = QLineEdit()
        self.cookie_edit.setPlaceholderText("브라우저에서 복사한 Cookie — 로그인 필요 시")
        self.cookie_edit.setEchoMode(QLineEdit.EchoMode.Password)
        cookie_row.addWidget(self.cookie_edit, stretch=1)
        cookie_help_btn = QPushButton("Cookie 도움말")
        cookie_help_btn.clicked.connect(self._show_cookie_help)
        cookie_row.addWidget(cookie_help_btn)
        root.addLayout(cookie_row)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_single_tab(), "단일 페이지")
        self.tabs.addTab(self._build_batch_tab(), "일괄 (URL 패턴)")
        root.addWidget(self.tabs, stretch=1)

        btn_row = QHBoxLayout()
        self.import_btn = primary_button("표로 가져오기")
        self.import_btn.clicked.connect(self._run_import)
        self.import_btn.setEnabled(False)
        btn_row.addWidget(self.import_btn)
        btn_row.addStretch()
        self.status_label = QLabel("준비")
        self.status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        btn_row.addWidget(self.status_label)
        root.addLayout(btn_row)

    def _build_single_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        form_wrap = QWidget()
        form_wrap.setStyleSheet(card_frame_style())
        form = QFormLayout(form_wrap)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(8)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/…")
        form.addRow("URL", self.url_edit)

        self.selector_edit = QLineEdit()
        self.selector_edit.setPlaceholderText("예: ul.items > li")
        form.addRow("CSS selector", self.selector_edit)

        self.attr_combo = QComboBox()
        self.attr_combo.addItems(list(ALLOWED_ATTRS))
        form.addRow("추출 속성", self.attr_combo)

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 50_000)
        self.limit_spin.setValue(100)
        form.addRow("최대 행", self.limit_spin)

        self.column_edit = QLineEdit("value")
        form.addRow("열 이름", self.column_edit)
        layout.addWidget(form_wrap)

        row = QHBoxLayout()
        self.scan_btn = QPushButton("구조 스캔")
        self.scan_btn.clicked.connect(self._run_scan)
        row.addWidget(self.scan_btn)
        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.clicked.connect(self._run_preview)
        row.addWidget(self.preview_btn)
        row.addStretch()
        layout.addLayout(row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("구조 후보"))
        self.candidate_list = QListWidget()
        self.candidate_list.itemClicked.connect(self._on_candidate_clicked)
        left_layout.addWidget(self.candidate_list, stretch=1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("미리보기"))
        self.preview_table = QTableWidget(0, 1)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.preview_table, stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter, stretch=1)
        return page

    def _build_batch_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        form_wrap = QWidget()
        form_wrap.setStyleSheet(card_frame_style())
        form = QFormLayout(form_wrap)
        form.setContentsMargins(12, 12, 12, 12)
        form.setSpacing(8)

        self.batch_template = QLineEdit()
        self.batch_template.setPlaceholderText(
            "https://finance.naver.com/item/main.naver?code={code}"
        )
        form.addRow("URL 템플릿", self.batch_template)

        self.batch_param_key = QLineEdit("code")
        self.batch_param_key.setPlaceholderText("자리표시자 이름 (기본 code)")
        form.addRow("파라미터 키", self.batch_param_key)

        self.batch_delay = QSpinBox()
        self.batch_delay.setRange(0, 10_000)
        self.batch_delay.setValue(350)
        self.batch_delay.setSuffix(" ms")
        form.addRow("요청 간격", self.batch_delay)

        self.batch_max = QSpinBox()
        self.batch_max.setRange(1, 5_000)
        self.batch_max.setValue(20)
        form.addRow("최대 건수", self.batch_max)
        layout.addWidget(form_wrap)

        mid = QSplitter(Qt.Orientation.Horizontal)
        params_box = QWidget()
        params_layout = QVBoxLayout(params_box)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.addWidget(QLabel("파라미터 목록 (한 줄에 하나, # 주석)"))

        src_row = QHBoxLayout()
        src_row.addWidget(QLabel("가져오기"))
        self.param_source = QComboBox()
        self.param_source.addItem("직접 입력", "manual")
        self.param_source.addItem("열린 표의 열", "dataframe")
        self.param_source.addItem("파일에서…", "file")
        self.param_source.currentIndexChanged.connect(self._on_param_source_changed)
        src_row.addWidget(self.param_source)
        self.param_column = QComboBox()
        self.param_column.setMinimumWidth(120)
        self.param_column.setEnabled(False)
        src_row.addWidget(self.param_column)
        fill_btn = QPushButton("목록에 채우기")
        fill_btn.clicked.connect(self._fill_params_from_source)
        src_row.addWidget(fill_btn)
        src_row.addStretch()
        params_layout.addLayout(src_row)

        self.batch_params = QPlainTextEdit()
        self.batch_params.setPlaceholderText("005930\n000660\n005380")
        params_layout.addWidget(self.batch_params)
        mid.addWidget(params_box)

        fields_box = QWidget()
        fields_layout = QVBoxLayout(fields_box)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_hdr = QHBoxLayout()
        fields_hdr.addWidget(QLabel("열 매핑 (열이름|selector|attr)"))
        attr_help_btn = QPushButton("attr 도움말")
        attr_help_btn.clicked.connect(self._show_attr_help)
        fields_hdr.addWidget(attr_help_btn)
        fields_hdr.addStretch()
        fields_layout.addLayout(fields_hdr)
        self.batch_fields = QPlainTextEdit()
        self.batch_fields.setPlaceholderText(_BATCH_FIELDS_PLACEHOLDER)
        fields_layout.addWidget(self.batch_fields)
        mid.addWidget(fields_box)
        mid.setStretchFactor(0, 1)
        mid.setStretchFactor(1, 2)
        layout.addWidget(mid, stretch=1)

        row = QHBoxLayout()
        self.batch_run_btn = QPushButton("일괄 미리보기")
        self.batch_run_btn.clicked.connect(self._run_batch)
        row.addWidget(self.batch_run_btn)
        row.addStretch()
        layout.addLayout(row)

        self.batch_preview = QTableWidget(0, 0)
        self.batch_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.batch_preview.setAlternatingRowColors(True)
        self.batch_preview.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.batch_preview, stretch=1)
        return page

    def apply_theme(self) -> None:
        pass

    def refresh_data_columns(self) -> None:
        """가공 탭 DF가 바뀔 때 파라미터용 열 콤보를 갱신합니다."""
        current = self.param_column.currentText()
        self.param_column.blockSignals(True)
        self.param_column.clear()
        df = self.get_dataframe()
        if df is not None and not df.empty:
            for col in df.columns:
                self.param_column.addItem(str(col))
        self.param_column.blockSignals(False)
        if current:
            idx = self.param_column.findText(current)
            if idx >= 0:
                self.param_column.setCurrentIndex(idx)
        self._on_param_source_changed()

    def cancel_pending(self) -> None:
        self._poller.cancel()

    def shutdown(self) -> None:
        self.cancel_pending()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _show_cookie_help(self) -> None:
        QMessageBox.information(self, "Cookie 사용법", _COOKIE_HELP)

    def _show_attr_help(self) -> None:
        QMessageBox.information(self, "attr(추출 속성) 안내", _ATTR_HELP)

    def _on_param_source_changed(self, *_args) -> None:
        source = self.param_source.currentData()
        self.param_column.setEnabled(source == "dataframe" and self.param_column.count() > 0)

    def _fill_params_from_source(self) -> None:
        source = self.param_source.currentData()
        if source == "manual":
            QMessageBox.information(
                self,
                "파라미터",
                "직접 입력 모드입니다. 왼쪽 칸에 한 줄씩 값을 적거나,\n"
                "소스를 ‘열린 표의 열’ / ‘파일에서…’로 바꾼 뒤 [목록에 채우기]를 누르세요.",
            )
            return
        if source == "dataframe":
            df = self.get_dataframe()
            if df is None or df.empty:
                QMessageBox.warning(self, "파라미터", "먼저 가공 탭에서 파일을 여세요.")
                return
            col = self.param_column.currentText().strip()
            if not col or col not in [str(c) for c in df.columns]:
                # resolve by string match
                match = next((c for c in df.columns if str(c) == col), None)
                if match is None:
                    QMessageBox.warning(self, "파라미터", "열을 선택하세요.")
                    return
                col = match
            else:
                col = next(c for c in df.columns if str(c) == col)
            values = series_to_param_list(df[col])
            if not values:
                QMessageBox.warning(self, "파라미터", "선택한 열에 쓸 값이 없습니다.")
                return
            self.batch_params.setPlainText("\n".join(values))
            self.status_label.setText(f"열린 표 '{col}'에서 {len(values):,}개 채움")
            return

        # file
        path, _ = QFileDialog.getOpenFileName(
            self,
            "파라미터 파일 열기",
            "",
            "데이터 (*.csv *.tsv *.txt *.xlsx *.xls);;모든 파일 (*.*)",
        )
        if not path:
            return
        try:
            values = load_params_from_file(path, column=None)
        except Exception as exc:
            QMessageBox.critical(self, "파일 읽기 실패", str(exc))
            return
        if not values:
            QMessageBox.warning(self, "파라미터", "파일에서 값을 찾지 못했습니다.")
            return
        self.batch_params.setPlainText("\n".join(values))
        self.param_source.setCurrentIndex(self.param_source.findData("manual"))
        self.status_label.setText(f"파일에서 {len(values):,}개 채움")

    def _cookie(self) -> str | None:
        text = self.cookie_edit.text().strip()
        return text or None

    def _set_busy(self, busy: bool, message: str) -> None:
        self.scan_btn.setEnabled(not busy)
        self.preview_btn.setEnabled(not busy)
        self.batch_run_btn.setEnabled(not busy)
        self.import_btn.setEnabled(
            not busy and self._preview_df is not None and not self._preview_df.empty
        )
        self.status_label.setText(message)

    def _fill_preview_table(self, table: QTableWidget, df: pd.DataFrame) -> None:
        self._preview_df = df.copy()
        table.clear()
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        table.setRowCount(len(df))
        for r in range(len(df)):
            for c, col in enumerate(df.columns):
                value = df.iloc[r, c]
                table.setItem(r, c, QTableWidgetItem("" if value is None else str(value)))
        self.import_btn.setEnabled(len(df) > 0)

    def _fill_candidates(self, candidates: list[StructureCandidate]) -> None:
        self._candidates = list(candidates)
        self.candidate_list.clear()
        for cand in candidates:
            item = QListWidgetItem(cand.label)
            tip = [f"selector: {cand.selector}", f"속성 추천: {cand.suggested_attr}"]
            if cand.sample_texts:
                tip.append("샘플: " + " | ".join(cand.sample_texts))
            item.setToolTip("\n".join(tip))
            item.setData(Qt.ItemDataRole.UserRole, cand.selector)
            self.candidate_list.addItem(item)

    def _on_candidate_clicked(self, item: QListWidgetItem) -> None:
        selector = item.data(Qt.ItemDataRole.UserRole)
        if not selector:
            return
        self.selector_edit.setText(str(selector))
        for cand in self._candidates:
            if cand.selector == selector:
                idx = self.attr_combo.findText(cand.suggested_attr)
                if idx >= 0:
                    self.attr_combo.setCurrentIndex(idx)
                break
        self._run_preview()

    def _run_scan(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "URL을 입력하세요.")
            return
        if self._poller.busy:
            QMessageBox.information(self, "크롤링", "이미 요청을 처리 중입니다.")
            return
        cookie = self._cookie()
        self._set_busy(True, "구조 스캔 중…")

        def work() -> list[StructureCandidate]:
            return scan_url_structure(url, cookie=cookie)

        self._poller.start(self._executor.submit(work), self._on_scan_done)

    def _on_scan_done(self, future: Future) -> None:
        try:
            candidates = future.result()
        except Exception as exc:
            self._fill_candidates([])
            self._set_busy(False, "스캔 실패")
            QMessageBox.critical(self, "구조 스캔 실패", str(exc))
            if self.on_log:
                self.on_log("error", "크롤링 구조 스캔 실패", str(exc))
            return
        self._fill_candidates(candidates)
        self._set_busy(False, f"후보 {len(candidates)}개")
        if self.on_log:
            self.on_log("info", "크롤링 구조 스캔", f"후보 {len(candidates)}개")
        if not candidates:
            QMessageBox.information(
                self,
                "구조 스캔",
                "반복 목록 후보를 찾지 못했습니다. selector를 직접 입력해 보세요.",
            )

    def _run_preview(self) -> None:
        url = self.url_edit.text().strip()
        selector = self.selector_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "URL을 입력하세요.")
            return
        if not selector:
            QMessageBox.warning(self, "입력 오류", "CSS selector를 입력하세요.")
            return
        if self._poller.busy:
            QMessageBox.information(self, "크롤링", "이미 요청을 처리 중입니다.")
            return
        attr = self.attr_combo.currentText().strip()
        limit = int(self.limit_spin.value())
        column = self.column_edit.text().strip() or "value"
        cookie = self._cookie()
        self._set_busy(True, "불러오는 중…")

        def work() -> pd.DataFrame:
            return crawl_url_to_dataframe(
                url, selector, attr=attr, limit=limit, column=column, cookie=cookie
            )

        self._poller.start(self._executor.submit(work), self._on_preview_done)

    def _on_preview_done(self, future: Future) -> None:
        try:
            df = future.result()
        except Exception as exc:
            self._preview_df = None
            self.preview_table.setRowCount(0)
            self._set_busy(False, "실패")
            self.import_btn.setEnabled(False)
            QMessageBox.critical(self, "미리보기 실패", str(exc))
            if self.on_log:
                self.on_log("error", "크롤링 미리보기 실패", str(exc))
            return
        self._fill_preview_table(self.preview_table, df)
        self._set_busy(False, f"미리보기 {len(df):,}행")
        if self.on_log:
            self.on_log("info", "크롤링 미리보기", f"{len(df):,}행")

    def _run_batch(self) -> None:
        template = self.batch_template.text().strip()
        if not template:
            QMessageBox.warning(self, "입력 오류", "URL 템플릿을 입력하세요. 예: ...?code={code}")
            return
        try:
            params = parse_param_list(self.batch_params.toPlainText())
            fields = parse_fields_text(self.batch_fields.toPlainText())
        except ValueError as exc:
            QMessageBox.warning(self, "입력 오류", str(exc))
            return
        if not params:
            QMessageBox.warning(self, "입력 오류", "파라미터 목록이 비어 있습니다.")
            return
        if self._poller.busy:
            QMessageBox.information(self, "크롤링", "이미 요청을 처리 중입니다.")
            return
        param_key = self.batch_param_key.text().strip() or "code"
        delay_ms = int(self.batch_delay.value())
        max_items = int(self.batch_max.value())
        cookie = self._cookie()
        self._set_busy(True, f"일괄 수집 중 (최대 {max_items}건)…")

        def work() -> pd.DataFrame:
            return crawl_batch(
                template,
                params,
                fields,
                param_key=param_key,
                delay_sec=delay_ms / 1000.0,
                cookie=cookie,
                max_items=max_items,
            )

        self._poller.start(self._executor.submit(work), self._on_batch_done)

    def _on_batch_done(self, future: Future) -> None:
        try:
            df = future.result()
        except Exception as exc:
            self._preview_df = None
            self.batch_preview.setRowCount(0)
            self._set_busy(False, "일괄 실패")
            self.import_btn.setEnabled(False)
            QMessageBox.critical(self, "일괄 수집 실패", str(exc))
            if self.on_log:
                self.on_log("error", "크롤링 일괄 실패", str(exc))
            return
        self._fill_preview_table(self.batch_preview, df)
        err_n = int((df["error"].astype(str).str.len() > 0).sum()) if "error" in df.columns else 0
        self._set_busy(False, f"일괄 {len(df):,}건 (오류 {err_n})")
        if self.on_log:
            self.on_log("info", "크롤링 일괄 미리보기", f"{len(df):,}건 · 오류 {err_n}")

    def _run_import(self) -> None:
        if self._preview_df is None or self._preview_df.empty:
            QMessageBox.information(self, "표로 가져오기", "먼저 미리보기/일괄 수집을 실행하세요.")
            return
        if self.has_data():
            reply = QMessageBox.question(
                self,
                "표로 가져오기",
                "현재 열린 데이터를 크롤링 결과로 바꿀까요?\n\n저장하지 않은 변경은 사라질 수 있습니다.",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        df = self._preview_df.copy()
        self.on_import(df, f"크롤링 가져오기 ({len(df):,}행)")
