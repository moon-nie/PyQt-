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
    QInputDialog,
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
    crawl_to_dataframe,
    crawl_url_to_dataframe,
    extract_fields,
    load_params_from_file,
    merge_crawl_into_base,
    parse_fields_text,
    parse_param_list,
    render_url_template,
    scan_url_structure,
    series_to_param_list,
)
from df_tool.analysis_deps import webengine_available
from df_tool.qt_async import AsyncPoller
from df_tool.qt_dependency import require
from df_tool.qt_theme import card_frame_style, primary_button
from df_tool.theme import COLORS

_BROWSER_SETTLE_MS = 2500

_BATCH_FIELDS_PLACEHOLDER = (
    "# 열이름|CSS selector|속성(생략 시 text)\n"
    "# text=글자 · href=링크주소 · src=이미지주소\n"
    "종목명|.wrap_company h2 a|text\n"
    "현재가|.no_today .blind|text\n"
    "# 이미지 예: 로고|.thumb img|src"
)

_COOKIE_HELP = """\
【추천】 로그인 브라우저
1. [로그인 브라우저]를 엽니다.
2. 사이트에 직접 로그인합니다.
3. [세션(Cookie) 적용]을 누릅니다. Cookie 칸에 자동으로 채워집니다.
4. 관리자·JS 페이지는 [브라우저 렌더 미리보기] / [브라우저로 일괄]을 사용하세요.
   (일반 [미리보기]는 정적 HTML만 받아 SPA·관리자 화면이 비어 있을 수 있습니다.)

【수동】 Chrome에서 Cookie 복사
1. 브라우저로 로그인 → F12 → Network → 문서 요청 → Cookie 복사 → Cookie 칸에 붙여넣기.

【참고】
• Cookie는 비밀번호처럼 다루세요. 공유·커밋하지 마세요.
• 세션은 ~/.gridloom/webengine/ 에 유지될 수 있습니다.
• PyQt6-WebEngine 패키지가 필요합니다 (requirements.txt).
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
        on_apply_merged: Callable[[pd.DataFrame, str], None] | None = None,
        on_log: Callable[[str, str, str | None], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_import = on_import
        self.on_apply_merged = on_apply_merged
        self.has_data = has_data
        self.get_dataframe = get_dataframe or (lambda: None)
        self.on_log = on_log
        self._preview_df: pd.DataFrame | None = None
        self._candidates: list[StructureCandidate] = []
        self._params_from_column: str | None = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gridloom-crawl")
        self._poller = AsyncPoller(poll_ms=50)
        self._we_profile = None
        self._we_fetcher = None
        self._browser_queue: list[tuple[str, str]] = []
        self._browser_rows: list[dict[str, str]] = []
        self._browser_fields = None
        self._browser_param_key = "code"
        self._browser_gen = 0
        self._build_ui()
        self._gate_webengine_buttons()
        self._refresh_preset_combo()
        self._refresh_merge_left_columns()
        self._on_import_mode_changed()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        title = QLabel("크롤링")
        title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS['text']};")
        root.addWidget(title)

        hint = QLabel(
            "로그인·JS 페이지: [로그인 브라우저] → [브라우저 렌더] / [브라우저로 일괄].\n"
            "공개 정적 HTML은 Cookie 없이 일반 미리보기로도 됩니다. "
            "규칙 프리셋으로 URL·selector를 저장할 수 있습니다."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['text_secondary']};")
        root.addWidget(hint)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("규칙 프리셋"))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(180)
        self.preset_combo.setToolTip("저장해 둔 크롤 규칙(URL·selector·일괄 설정)")
        preset_row.addWidget(self.preset_combo, stretch=1)
        self.preset_load_btn = QPushButton("불러오기")
        self.preset_load_btn.clicked.connect(self._load_selected_preset)
        preset_row.addWidget(self.preset_load_btn)
        self.preset_save_btn = QPushButton("현재 저장…")
        self.preset_save_btn.clicked.connect(self._save_current_preset)
        preset_row.addWidget(self.preset_save_btn)
        self.preset_delete_btn = QPushButton("삭제")
        self.preset_delete_btn.clicked.connect(self._delete_selected_preset)
        preset_row.addWidget(self.preset_delete_btn)
        root.addLayout(preset_row)

        cookie_row = QHBoxLayout()
        cookie_row.addWidget(QLabel("Cookie(선택)"))
        self.cookie_edit = QLineEdit()
        self.cookie_edit.setPlaceholderText("로그인 브라우저로 적용 · 또는 수동 붙여넣기")
        self.cookie_edit.setEchoMode(QLineEdit.EchoMode.Password)
        cookie_row.addWidget(self.cookie_edit, stretch=1)
        self.login_browser_btn = QPushButton("로그인 브라우저")
        self.login_browser_btn.clicked.connect(self._open_login_browser)
        cookie_row.addWidget(self.login_browser_btn)
        cookie_help_btn = QPushButton("Cookie 도움말")
        cookie_help_btn.clicked.connect(self._show_cookie_help)
        cookie_row.addWidget(cookie_help_btn)
        root.addLayout(cookie_row)

        self.webengine_status = QLabel("")
        self.webengine_status.setWordWrap(True)
        self.webengine_status.setStyleSheet(f"color: {COLORS['warning']};")
        root.addWidget(self.webengine_status)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_single_tab(), "단일 페이지")
        self.tabs.addTab(self._build_batch_tab(), "일괄 (URL 패턴)")
        root.addWidget(self.tabs, stretch=1)

        btn_row = QHBoxLayout()
        self.import_mode = QComboBox()
        self.import_mode.addItem("크롤 결과로 교체", "replace")
        self.import_mode.addItem("열린 표에 병합", "merge")
        self.import_mode.setToolTip(
            "교체: 가공 탭 표를 크롤 결과로 바꿉니다.\n"
            "병합: 열린 표의 키 열과 크롤 파라미터 키를 맞춰 열을 붙입니다."
        )
        self.import_mode.currentIndexChanged.connect(self._on_import_mode_changed)
        btn_row.addWidget(self.import_mode)
        self.merge_left_col = QComboBox()
        self.merge_left_col.setMinimumWidth(100)
        self.merge_left_col.setToolTip("병합 시 열린 표의 키 열")
        self.merge_left_col.setEnabled(False)
        btn_row.addWidget(QLabel("키 열"))
        btn_row.addWidget(self.merge_left_col)
        self.import_btn = primary_button("표로 가져오기")
        self.import_btn.clicked.connect(self._run_import)
        self.import_btn.setEnabled(False)
        btn_row.addWidget(self.import_btn)
        self.cancel_btn = QPushButton("작업 취소")
        self.cancel_btn.setToolTip("진행 중인 스캔·미리보기·일괄·브라우저 렌더를 중단합니다.")
        self.cancel_btn.clicked.connect(self.cancel_pending)
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.cancel_btn)
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

        vsplit = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

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
        top_layout.addWidget(form_wrap)

        row = QHBoxLayout()
        self.scan_btn = QPushButton("구조 스캔")
        self.scan_btn.clicked.connect(self._run_scan)
        row.addWidget(self.scan_btn)
        self.preview_btn = QPushButton("미리보기")
        self.preview_btn.clicked.connect(self._run_preview)
        row.addWidget(self.preview_btn)
        self.render_preview_btn = QPushButton("브라우저 렌더 미리보기")
        self.render_preview_btn.clicked.connect(self._run_render_preview)
        row.addWidget(self.render_preview_btn)
        row.addStretch()
        top_layout.addLayout(row)
        vsplit.addWidget(top)

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
        right_layout.addWidget(QLabel("미리보기 (구분선 드래그로 크기 조절)"))
        self.preview_table = QTableWidget(0, 1)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        right_layout.addWidget(self.preview_table, stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        vsplit.addWidget(splitter)
        vsplit.setStretchFactor(0, 0)
        vsplit.setStretchFactor(1, 1)
        vsplit.setSizes([200, 400])
        layout.addWidget(vsplit, stretch=1)
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
        self.batch_max.setRange(1, 50_000)
        self.batch_max.setValue(100)
        form.addRow("최대 건수", self.batch_max)
        layout.addWidget(form_wrap)

        vsplit = QSplitter(Qt.Orientation.Vertical)
        mid_wrap = QWidget()
        mid_layout = QVBoxLayout(mid_wrap)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(8)

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
        self.param_column.currentIndexChanged.connect(self._sync_merge_left_from_param_col)
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
        mid_layout.addWidget(mid, stretch=1)

        row = QHBoxLayout()
        self.batch_run_btn = QPushButton("일괄 미리보기")
        self.batch_run_btn.clicked.connect(self._run_batch)
        row.addWidget(self.batch_run_btn)
        self.batch_browser_btn = QPushButton("브라우저로 일괄")
        self.batch_browser_btn.clicked.connect(self._run_batch_browser)
        row.addWidget(self.batch_browser_btn)
        row.addStretch()
        mid_layout.addLayout(row)
        vsplit.addWidget(mid_wrap)

        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(QLabel("일괄 미리보기 (구분선 드래그로 표 높이 조절)"))
        self.batch_preview = QTableWidget(0, 0)
        self.batch_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.batch_preview.setAlternatingRowColors(True)
        self.batch_preview.horizontalHeader().setStretchLastSection(True)
        bottom_layout.addWidget(self.batch_preview, stretch=1)
        vsplit.addWidget(bottom)
        vsplit.setStretchFactor(0, 1)
        vsplit.setStretchFactor(1, 1)
        vsplit.setSizes([300, 340])
        layout.addWidget(vsplit, stretch=1)
        return page

    def apply_theme(self) -> None:
        pass

    def refresh_data_columns(self) -> None:
        """가공 탭 DF가 바뀔 때 파라미터용·병합 키 열 콤보를 갱신합니다."""
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
        self._refresh_merge_left_columns()
        self._on_param_source_changed()
        self._on_import_mode_changed()

    def _refresh_merge_left_columns(self) -> None:
        current = self.merge_left_col.currentText()
        prefer = self._params_from_column or self.param_column.currentText()
        self.merge_left_col.blockSignals(True)
        self.merge_left_col.clear()
        df = self.get_dataframe()
        if df is not None and not df.empty:
            for col in df.columns:
                self.merge_left_col.addItem(str(col))
        self.merge_left_col.blockSignals(False)
        for candidate in (prefer, current):
            if candidate:
                idx = self.merge_left_col.findText(str(candidate))
                if idx >= 0:
                    self.merge_left_col.setCurrentIndex(idx)
                    break

    def _sync_merge_left_from_param_col(self, *_args) -> None:
        if self.param_source.currentData() == "dataframe":
            text = self.param_column.currentText()
            if text:
                idx = self.merge_left_col.findText(text)
                if idx >= 0:
                    self.merge_left_col.setCurrentIndex(idx)

    def _on_import_mode_changed(self, *_args) -> None:
        merge = self.import_mode.currentData() == "merge"
        self.merge_left_col.setEnabled(merge and self.merge_left_col.count() > 0)

    def cancel_pending(self) -> None:
        """스캔·HTTP 일괄·브라우저 렌더/일괄을 모두 중단하고 busy를 해제합니다."""
        self._browser_gen += 1
        self._browser_queue.clear()
        self._poller.cancel()
        if self._we_fetcher is not None:
            self._we_fetcher.cancel()
        self._set_busy(False, "취소됨")
        if self.on_log:
            self.on_log("info", "크롤링 작업 취소", None)

    def shutdown(self) -> None:
        self.cancel_pending()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _refresh_preset_combo(self) -> None:
        from df_tool.crawl_presets import load_presets

        current = self.preset_combo.currentText() if hasattr(self, "preset_combo") else ""
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("(프리셋 선택)", "")
        for preset in load_presets():
            self.preset_combo.addItem(preset.name, preset.name)
        idx = self.preset_combo.findText(current)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)

    def _collect_preset_from_ui(self, name: str):
        from df_tool.crawl_presets import CrawlPreset

        return CrawlPreset(
            name=name.strip(),
            url=self.url_edit.text().strip(),
            selector=self.selector_edit.text().strip(),
            attr=self.attr_combo.currentText().strip() or "text",
            limit=int(self.limit_spin.value()),
            column=self.column_edit.text().strip() or "value",
            batch_template=self.batch_template.text().strip(),
            batch_param_key=self.batch_param_key.text().strip() or "code",
            batch_fields=self.batch_fields.toPlainText(),
            batch_delay_ms=int(self.batch_delay.value()),
            batch_max=int(self.batch_max.value()),
            batch_params=self.batch_params.toPlainText(),
        )

    def _apply_preset_to_ui(self, preset) -> None:
        self.url_edit.setText(preset.url)
        self.selector_edit.setText(preset.selector)
        idx = self.attr_combo.findText(preset.attr)
        if idx >= 0:
            self.attr_combo.setCurrentIndex(idx)
        self.limit_spin.setValue(max(1, int(preset.limit)))
        self.column_edit.setText(preset.column or "value")
        self.batch_template.setText(preset.batch_template)
        self.batch_param_key.setText(preset.batch_param_key or "code")
        self.batch_fields.setPlainText(preset.batch_fields)
        self.batch_delay.setValue(max(0, int(preset.batch_delay_ms)))
        self.batch_max.setValue(max(1, int(preset.batch_max)))
        if preset.batch_params.strip():
            self.batch_params.setPlainText(preset.batch_params)
            self.param_source.setCurrentIndex(self.param_source.findData("manual"))

    def _save_current_preset(self) -> None:
        from df_tool.crawl_presets import upsert_preset

        name, ok = QInputDialog.getText(self, "규칙 프리셋 저장", "프리셋 이름:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            QMessageBox.warning(self, "규칙 프리셋", "이름을 입력하세요.")
            return
        preset = self._collect_preset_from_ui(name)
        upsert_preset(preset)
        self._refresh_preset_combo()
        idx = self.preset_combo.findData(name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.status_label.setText(f"프리셋 저장: {name}")
        if self.on_log:
            self.on_log("success", "크롤 프리셋 저장", name)

    def _load_selected_preset(self) -> None:
        from df_tool.crawl_presets import load_presets

        name = self.preset_combo.currentData()
        if not name:
            QMessageBox.information(self, "규칙 프리셋", "불러올 프리셋을 선택하세요.")
            return
        match = next((p for p in load_presets() if p.name == name), None)
        if match is None:
            QMessageBox.warning(self, "규칙 프리셋", "선택한 프리셋을 찾지 못했습니다.")
            self._refresh_preset_combo()
            return
        self._apply_preset_to_ui(match)
        self.status_label.setText(f"프리셋 불러옴: {name}")
        if self.on_log:
            self.on_log("info", "크롤 프리셋 불러오기", name)

    def _delete_selected_preset(self) -> None:
        from df_tool.crawl_presets import delete_preset

        name = self.preset_combo.currentData()
        if not name:
            QMessageBox.information(self, "규칙 프리셋", "삭제할 프리셋을 선택하세요.")
            return
        if (
            QMessageBox.question(self, "규칙 프리셋 삭제", f"'{name}' 프리셋을 삭제할까요?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        delete_preset(name)
        self._refresh_preset_combo()
        self.status_label.setText(f"프리셋 삭제: {name}")

    def _show_cookie_help(self) -> None:
        QMessageBox.information(self, "Cookie 사용법", _COOKIE_HELP)

    def _show_attr_help(self) -> None:
        QMessageBox.information(self, "attr(추출 속성) 안내", _ATTR_HELP)

    def _gate_webengine_buttons(self) -> None:
        """WebEngine 없으면 버튼은 켜 두고, 클릭 시 설치 안내를 띄운다.

        비활성만 하면 사용자가 원인을 확인할 수 없어 버튼을 계속 클릭 가능하게 둔다.
        """
        from df_tool.analysis_deps import feature_requirement_message

        ok = webengine_available()
        tip = "" if ok else feature_requirement_message(
            "PyQt6.QtWebEngineWidgets", feature="로그인 브라우저", inline=True
        )
        for btn in (self.login_browser_btn, self.render_preview_btn, self.batch_browser_btn):
            btn.setEnabled(True)
            btn.setToolTip(tip)
        if ok:
            self.webengine_status.setText("")
        else:
            self.webengine_status.setText(
                "로그인 브라우저를 쓰려면 PyQt6-WebEngine이 필요합니다. "
                "버튼을 누르면 설치 안내가 나옵니다. → pip install PyQt6-WebEngine"
            )

    def _ensure_webengine(self) -> bool:
        if not require(
            self,
            webengine_available(),
            "PyQt6.QtWebEngineWidgets",
            feature="로그인 브라우저",
        ):
            return False
        if self._we_profile is None:
            from df_tool.qt_webengine_crawl import (
                RenderedHtmlFetcher,
                crawl_webengine_profile,
                ensure_webengine_imported,
            )

            ensure_webengine_imported()
            self._we_profile = crawl_webengine_profile(self)
            self._we_fetcher = RenderedHtmlFetcher(self._we_profile, self)
        return True

    def _open_login_browser(self) -> None:
        if not self._ensure_webengine():
            return
        from df_tool.qt_webengine_crawl import LoginBrowserDialog

        start = self.url_edit.text().strip()
        if not start:
            tpl = self.batch_template.text().strip()
            start = tpl.split("{")[0] if tpl else "https://"
        dlg = LoginBrowserDialog(start, profile=self._we_profile, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.cookie_header:
            self.cookie_edit.setText(dlg.cookie_header)
            self.status_label.setText("로그인 세션(Cookie) 적용됨")
            if self.on_log:
                self.on_log("info", "크롤링 로그인 세션", "Cookie 적용")

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
            self._params_from_column = str(col)
            self._refresh_merge_left_columns()
            self.import_mode.setCurrentIndex(self.import_mode.findData("merge"))
            self.status_label.setText(f"열린 표 '{col}'에서 {len(values):,}개 채움 · 가져오기=병합 권장")
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
        self._params_from_column = None
        self.status_label.setText(f"파일에서 {len(values):,}개 채움")

    def _cookie(self) -> str | None:
        text = self.cookie_edit.text().strip()
        return text or None

    def _set_busy(self, busy: bool, message: str) -> None:
        # 로그인 브라우저는 busy와 무관하게 유지 (세션 잡기 / 설치 안내)
        for btn in (
            self.scan_btn,
            self.preview_btn,
            self.render_preview_btn,
            self.batch_run_btn,
            self.batch_browser_btn,
            self.preset_load_btn,
            self.preset_save_btn,
            self.preset_delete_btn,
        ):
            btn.setEnabled(not busy)
        if hasattr(self, "cancel_btn"):
            self.cancel_btn.setEnabled(busy)
        if not busy:
            self._gate_webengine_buttons()
        self.login_browser_btn.setEnabled(True)
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

    def _run_render_preview(self) -> None:
        url = self.url_edit.text().strip()
        selector = self.selector_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "입력 오류", "URL을 입력하세요.")
            return
        if not selector:
            QMessageBox.warning(self, "입력 오류", "CSS selector를 입력하세요.")
            return
        if not self._ensure_webengine():
            return
        if self._we_fetcher is None or self._we_fetcher.busy or self._poller.busy:
            QMessageBox.information(self, "크롤링", "이미 요청을 처리 중입니다.")
            return
        attr = self.attr_combo.currentText()
        limit = int(self.limit_spin.value())
        column = self.column_edit.text().strip() or "value"
        self._set_busy(True, "브라우저 렌더 중…")

        def on_html(html: str | None, error: str | None) -> None:
            if error or html is None:
                self._set_busy(False, "렌더 실패")
                QMessageBox.critical(self, "브라우저 렌더 실패", error or "알 수 없는 오류")
                if self.on_log:
                    self.on_log("error", "크롤링 브라우저 렌더 실패", error)
                return
            try:
                df = crawl_to_dataframe(html, selector, attr=attr, limit=limit, column=column)
            except Exception as exc:
                self._set_busy(False, "추출 실패")
                QMessageBox.critical(self, "추출 실패", str(exc))
                return
            self._fill_preview_table(self.preview_table, df)
            self._set_busy(False, f"렌더 미리보기 {len(df):,}행")
            if self.on_log:
                self.on_log("info", "크롤링 브라우저 렌더", f"{len(df):,}행")

        try:
            self._we_fetcher.fetch(url, settle_ms=_BROWSER_SETTLE_MS, callback=on_html)
        except Exception as exc:
            self._set_busy(False, "렌더 실패")
            QMessageBox.critical(self, "브라우저 렌더 실패", str(exc))

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

    def _run_batch_browser(self) -> None:
        template = self.batch_template.text().strip()
        if not template:
            QMessageBox.warning(self, "입력 오류", "URL 템플릿을 입력하세요. 예: ...?idx={code}")
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
        if not self._ensure_webengine():
            return
        if self._we_fetcher is None or self._we_fetcher.busy or self._poller.busy:
            QMessageBox.information(self, "크롤링", "이미 요청을 처리 중입니다.")
            return
        param_key = self.batch_param_key.text().strip() or "code"
        max_items = int(self.batch_max.value())
        values = params[:max_items]
        queue: list[tuple[str, str]] = []
        for value in values:
            try:
                url = render_url_template(template, **{param_key: value})
            except ValueError as exc:
                QMessageBox.warning(self, "입력 오류", str(exc))
                return
            queue.append((value, url))
        self._browser_queue = queue
        self._browser_rows = []
        self._browser_fields = fields
        self._browser_param_key = param_key
        self._browser_gen += 1
        gen = self._browser_gen
        self._set_busy(True, f"브라우저 일괄 0/{len(queue)}…")
        self._advance_browser_batch(gen)

    def _advance_browser_batch(self, gen: int) -> None:
        if gen != self._browser_gen:
            return
        assert self._we_fetcher is not None
        total = len(self._browser_rows) + len(self._browser_queue)
        if not self._browser_queue:
            df = pd.DataFrame(self._browser_rows)
            self._fill_preview_table(self.batch_preview, df)
            err_n = int((df["error"].astype(str).str.len() > 0).sum()) if "error" in df.columns else 0
            self._set_busy(False, f"브라우저 일괄 {len(df):,}건 (오류 {err_n})")
            if self.on_log:
                self.on_log("info", "크롤링 브라우저 일괄", f"{len(df):,}건 · 오류 {err_n}")
            return
        value, url = self._browser_queue.pop(0)
        done = len(self._browser_rows)
        self.status_label.setText(f"브라우저 일괄 {done + 1}/{total}…")
        key = self._browser_param_key
        fields = self._browser_fields or []

        def on_html(html: str | None, error: str | None) -> None:
            if gen != self._browser_gen:
                return
            row: dict[str, str] = {key: value, "url": url}
            if error or html is None:
                for field in fields:
                    row[field.name] = ""
                row["error"] = error or "렌더 실패"
            else:
                try:
                    row.update(extract_fields(html, fields))
                    row["error"] = ""
                except Exception as exc:
                    for field in fields:
                        row.setdefault(field.name, "")
                    row["error"] = str(exc)
            self._browser_rows.append(row)
            self._advance_browser_batch(gen)

        try:
            self._we_fetcher.fetch(url, settle_ms=_BROWSER_SETTLE_MS, callback=on_html)
        except Exception as exc:
            if gen != self._browser_gen:
                return
            row = {key: value, "url": url, "error": str(exc)}
            for field in fields:
                row[field.name] = ""
            self._browser_rows.append(row)
            self._advance_browser_batch(gen)

    def _run_import(self) -> None:
        if self._preview_df is None or self._preview_df.empty:
            QMessageBox.information(self, "표로 가져오기", "먼저 미리보기/일괄 수집을 실행하세요.")
            return

        mode = self.import_mode.currentData()
        crawl_df = self._preview_df.copy()

        if mode == "merge":
            base = self.get_dataframe()
            if base is None or base.empty:
                QMessageBox.warning(
                    self,
                    "열린 표에 병합",
                    "가공 탭에 열린 표가 없습니다.\n"
                    "먼저 표를 열거나, 가져오기 방식을 ‘크롤 결과로 교체’로 바꾸세요.",
                )
                return
            left_on = self.merge_left_col.currentText().strip()
            if not left_on:
                QMessageBox.warning(self, "열린 표에 병합", "열린 표의 키 열을 선택하세요.")
                return
            right_on = self.batch_param_key.text().strip() or "code"
            if right_on not in crawl_df.columns:
                # 단일 페이지 미리보기는 파라미터 키가 없을 수 있음
                QMessageBox.warning(
                    self,
                    "열린 표에 병합",
                    f"크롤 결과에 키 열 '{right_on}'이(가) 없습니다.\n"
                    "일괄(URL 패턴) 미리보기 결과에서 병합하거나, "
                    "파라미터 키와 같은 이름의 열이 있어야 합니다.",
                )
                return
            try:
                merged = merge_crawl_into_base(
                    base, crawl_df, left_on=left_on, right_on=right_on
                )
            except ValueError as exc:
                QMessageBox.warning(self, "병합 실패", str(exc))
                return
            label = f"크롤링 병합 ({left_on}↔{right_on}, +{len(crawl_df.columns) - 1}열)"
            if self.on_apply_merged is not None:
                self.on_apply_merged(merged, label)
            else:
                self.on_import(merged, label)
            if self.on_log:
                self.on_log("success", label, f"{len(merged):,}행")
            return

        # replace
        if self.has_data():
            reply = QMessageBox.question(
                self,
                "표로 가져오기",
                "현재 열린 데이터를 크롤링 결과로 바꿀까요?\n\n"
                "기존 표를 유지하려면 가져오기 방식을 ‘열린 표에 병합’으로 바꾸세요.",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.on_import(crawl_df, f"크롤링 가져오기 ({len(crawl_df):,}행)")
