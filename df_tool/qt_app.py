"""Gridloom PyQt 메인 창."""
from __future__ import annotations

import gc
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from df_tool import __version__
from df_tool.branding import APP_NAME, APP_TAGLINE
from df_tool.window_state import load_window_state, save_window_state
from df_tool.qt_data_dialogs import (
    qt_concat_dialog,
    qt_fill_na_dialog,
    qt_fill_na_pick_column_dialog,
    qt_group_summary_dialog,
    qt_merge_dialog,
    qt_vlookup_dialog,
)
from df_tool.qt_design_settings import show_design_settings_dialog
from df_tool.help_content import HELP_TEXT
from df_tool.loader import EXCEL_SUFFIXES, FILE_DIALOG_TYPES, LoadedData, load_file, resolve_file_suffix, save_file
from df_tool.performance import (
    LARGE_FILE_PREVIEW_ROWS,
    LARGE_FILE_WARN_ROWS,
    adaptive_undo_depth,
    format_file_size,
    is_heavy_dataframe,
    is_wide_dataframe,
    should_defer_analysis_charts,
    should_prompt_large_file,
)
from df_tool.operations import (
    FILL_NA_METHOD_LABELS,
    concat_dataframes,
    convert_column_dtype,
    delete_column,
    drop_duplicates,
    drop_na_rows,
    fill_na,
    fill_na_knn,
    fill_na_mice,
    find_replace as op_find_replace,
    group_summary,
    insert_column_at_end,
    merge_dataframes,
    vlookup,
)
from df_tool.qt_dialogs import (
    QtHelpDialog,
    QtSaveAsDialog,
    qt_add_column_dialog,
    qt_find_replace_dialog,
    qt_select_column_dialog,
)
from df_tool.qt_analysis_panel import AnalysisPanel
from df_tool.qt_async import AsyncPoller
from df_tool.qt_crawl_panel import CrawlPanel
from df_tool.qt_panels import ActivityLogPanel, CodePanel, InfoPanel
from df_tool.qt_theme import (
    app_stylesheet,
    configure_sheet_combo,
    muted_label,
    nav_button,
    primary_button,
    resize_sheet_combo,
    separator,
    style_nav_button,
    tagline_label,
    title_label,
    toolbar_frame_style,
)
from df_tool.qt_viewer import DataFrameViewer
from df_tool.theme import COLORS, load_theme_config


class MainWindow(QMainWindow):
    MAX_UNDO = 20
    STATUS_REVERT_MS = 3000

    def __init__(self) -> None:
        super().__init__()
        load_theme_config()
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.setMinimumSize(1100, 720)

        self._loaded: LoadedData | None = None
        self._undo_stack: list[pd.DataFrame] = []
        self._before_summary_df: pd.DataFrame | None = None
        self._current_page = "main"
        self._updating_sheet_combo = False
        self._data_token = 0
        self._partial_load_limit: int | None = None
        self._pending_load_limit: int | None = None
        self._load_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gridloom-load")
        self._load_poller = AsyncPoller(poll_ms=40)
        self._work_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gridloom-work")
        self._fill_poller = AsyncPoller(poll_ms=80)
        self._loading = False
        self._info_refresh_timer = QTimer(self)
        self._info_refresh_timer.setSingleShot(True)
        self._info_refresh_timer.timeout.connect(self._run_deferred_info_refresh)
        self._status_revert_timer = QTimer(self)
        self._status_revert_timer.setSingleShot(True)
        self._status_revert_timer.timeout.connect(self._revert_status)

        self._build_ui()
        self._bind_shortcuts()
        self._restore_window_geometry()

    def _restore_window_geometry(self) -> None:
        state = load_window_state()
        if state is None:
            return
        self.resize(state["width"], state["height"])
        self.move(state["x"], state["y"])
        if state["maximized"]:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def _persist_window_geometry(self) -> None:
        # 최대화 중이면 normalGeometry로 복원 시 쓸 크기를 저장
        geo = self.normalGeometry() if self.isMaximized() else self.geometry()
        save_window_state(
            x=geo.x(),
            y=geo.y(),
            width=geo.width(),
            height=geo.height(),
            maximized=self.isMaximized(),
        )

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        self._toolbar = QFrame()
        self._toolbar.setObjectName("ToolbarFrame")
        self._toolbar.setStyleSheet(toolbar_frame_style())
        toolbar_layout = QVBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(12, 8, 12, 8)
        toolbar_layout.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(10)
        row1.addWidget(title_label(APP_NAME))
        row1.addWidget(tagline_label(APP_TAGLINE))
        row1.addWidget(separator())

        open_btn = QPushButton("열기")
        open_btn.clicked.connect(self.open_file)
        row1.addWidget(open_btn)
        save_btn = primary_button("저장")
        save_btn.clicked.connect(self.save_file)
        row1.addWidget(save_btn)
        row1.addWidget(separator())

        row1.addWidget(muted_label("시트"))
        self.sheet_combo = QComboBox()
        configure_sheet_combo(self.sheet_combo)
        self.sheet_combo.setEnabled(False)
        self.sheet_combo.currentTextChanged.connect(self._on_sheet_changed)
        row1.addWidget(self.sheet_combo)
        self.sheet_delete_btn = QPushButton("시트 삭제")
        self.sheet_delete_btn.setEnabled(False)
        self.sheet_delete_btn.clicked.connect(self.delete_current_sheet)
        row1.addWidget(self.sheet_delete_btn)
        row1.addStretch(1)

        help_btn = QPushButton("도움말 ▾")
        help_menu = QMenu(help_btn)
        help_btn.setMenu(help_menu)
        help_menu.addAction("사용법", self.show_help)
        help_menu.addAction("설치 · 실행 가이드", self.show_setup_guide)
        help_menu.addAction("코드 공부 가이드", self.show_learning_guide)
        help_menu.addAction("프로젝트 파일 지도", self.show_project_map)
        help_menu.addAction("기능 추가 가이드 (개발)", self.show_developer_guide)
        help_menu.addAction("코드 작성 규칙", self.show_coding_standards)
        help_menu.addAction("PyQt 엔진 마이그레이션 기록", self.show_migration_doc)
        help_menu.addAction("디자인 설정…", self.show_design_settings)
        help_menu.addAction("정보", self._show_about)
        row1.addWidget(help_btn)
        toolbar_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(muted_label("파일"))
        self.path_label = QLabel("열린 파일 없음")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_label.setSizePolicy(
            self.path_label.sizePolicy().horizontalPolicy(),
            self.path_label.sizePolicy().verticalPolicy(),
        )
        self.path_label.setMinimumWidth(120)
        row2.addWidget(self.path_label, stretch=1)
        self._mode_badges: list[QLabel] = []
        for _ in range(4):
            badge = QLabel("")
            badge.hide()
            row2.addWidget(badge)
            self._mode_badges.append(badge)
        toolbar_layout.addLayout(row2)
        root.addWidget(self._toolbar)

        nav = QHBoxLayout()
        nav.setSpacing(6)
        self._nav_main_btn = nav_button("가공", active=True)
        self._nav_main_btn.clicked.connect(lambda: self._show_page("main"))
        self._nav_analysis_btn = nav_button("분석", active=False)
        self._nav_analysis_btn.clicked.connect(lambda: self._show_page("analysis"))
        self._nav_crawl_btn = nav_button("크롤링", active=False)
        self._nav_crawl_btn.clicked.connect(lambda: self._show_page("crawl"))
        self._nav_log_btn = nav_button("작업 로그", active=False)
        self._nav_log_btn.clicked.connect(lambda: self._show_page("log"))
        nav.addWidget(self._nav_main_btn)
        nav.addWidget(self._nav_analysis_btn)
        nav.addWidget(self._nav_crawl_btn)
        nav.addWidget(self._nav_log_btn)
        nav.addStretch()
        root.addLayout(nav)

        self._stack = QStackedWidget()
        root.addWidget(self._stack, stretch=1)

        main_page = QWidget()
        main_layout = QVBoxLayout(main_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        self.viewer = DataFrameViewer(
            on_change=self._on_viewer_change,
            on_info_refresh=self._refresh_info_preview,
            on_action=self._toast_action,
            on_action_error=self._toast_error,
            on_drop_duplicates=self.drop_duplicates,
            on_drop_na_rows=self.drop_na_rows,
            on_fill_na=self.fill_missing_values,
            on_fill_na_column=self.fill_missing_in_column,
            on_vlookup=self.run_vlookup,
            on_merge=self.run_merge,
            on_concat=self.run_concat,
            on_group_summary=self.run_group_summary,
            on_add_column=self.add_column,
            on_delete_column=self.delete_column,
        )
        splitter.addWidget(self.viewer)

        sidebar = QSplitter(Qt.Orientation.Vertical)
        sidebar.setMinimumWidth(300)
        self.info_panel = InfoPanel(
            on_dtype_change=self.change_column_dtype,
            on_fill_na=self.fill_missing_in_column,
        )
        self.code_panel = CodePanel(
            on_run=self._apply_code_result,
            get_dataframe=lambda: self._loaded.dataframe if self._loaded else None,
            on_undo=self.undo,
            on_notify=self._code_notify,
        )
        sidebar.addWidget(self.info_panel)
        sidebar.addWidget(self.code_panel)
        sidebar.setSizes([300, 400])
        splitter.addWidget(sidebar)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([860, 300])

        self._stack.addWidget(main_page)

        self.analysis_panel = AnalysisPanel(
            get_dataframe=lambda: self._loaded.dataframe if self._loaded else None,
            on_apply=self._apply_analysis_result,
            on_log=self._log_action,
        )
        self._stack.addWidget(self.analysis_panel)

        self.crawl_panel = CrawlPanel(
            on_import=self._apply_crawled_dataframe,
            has_data=lambda: self._loaded is not None,
            get_dataframe=lambda: self._loaded.dataframe if self._loaded else None,
            on_log=self._log_action,
        )
        self._stack.addWidget(self.crawl_panel)

        self._activity_log = ActivityLogPanel()
        self._stack.addWidget(self._activity_log)
        self._show_page("main")

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("준비")
        self._apply_styles()

    def _apply_styles(self) -> None:
        self.setStyleSheet(app_stylesheet())
        self._toolbar.setStyleSheet(toolbar_frame_style())
        self.path_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self._sync_mode_badges()
        style_nav_button(self._nav_main_btn, active=self._current_page == "main")
        style_nav_button(self._nav_analysis_btn, active=self._current_page == "analysis")
        style_nav_button(self._nav_crawl_btn, active=self._current_page == "crawl")
        style_nav_button(self._nav_log_btn, active=self._current_page == "log")
        self.viewer.apply_theme()
        self.info_panel.apply_theme()
        self.code_panel.apply_theme()
        self.analysis_panel.apply_theme()
        self.crawl_panel.apply_theme()
        self._activity_log.apply_theme()

    def _bind_shortcuts(self) -> None:
        self.addAction(QAction("열기", self, shortcut=QKeySequence("Ctrl+O"), triggered=self.open_file))
        self.addAction(QAction("저장", self, shortcut=QKeySequence("Ctrl+S"), triggered=self.save_file))
        self.addAction(QAction("실행 취소", self, shortcut=QKeySequence("Ctrl+Z"), triggered=self.undo))
        find_act = QAction("찾기", self, shortcut=QKeySequence("Ctrl+F"), triggered=self.find_replace)
        find_act.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.addAction(find_act)

        table_shortcuts = (
            ("Ctrl+Shift+Up", self.insert_row_above),
            ("Ctrl+Shift+Down", self.insert_row_below),
            ("Ctrl+Shift+Left", self.insert_column_left),
            ("Ctrl+Shift+Right", self.insert_column_right),
            ("Ctrl+Shift+N", self.add_column),
        )
        for seq, handler in table_shortcuts:
            act = QAction(self, shortcut=QKeySequence(seq), triggered=lambda _c=False, fn=handler: self._run_table_shortcut(fn))
            act.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
            self.addAction(act)

    def _badge_style(self, *, warning: bool = False) -> str:
        bg = COLORS["primary_soft"] if warning else COLORS["surface_alt"]
        fg = COLORS["warning"] if warning else COLORS["text_secondary"]
        return (
            f"background: {bg}; color: {fg}; border: 1px solid {COLORS['border']}; "
            "border-radius: 10px; padding: 2px 8px; font-size: 9pt;"
        )

    def _sync_mode_badges(self) -> None:
        badges: list[tuple[str, bool, str]] = []
        if self._loaded is not None:
            df = self._loaded.dataframe
            rows, cols = len(df), len(df.columns)
            if self._partial_load_limit is not None:
                badges.append(
                    (
                        f"부분 로드 {self._partial_load_limit:,}행",
                        True,
                        "원본 파일의 앞부분만 표시 중입니다. 저장 시 현재 보이는 데이터만 저장됩니다.",
                    )
                )
            if is_heavy_dataframe(rows, cols):
                badges.append(("대용량", True, "스크롤·검색·분석에 시간이 걸릴 수 있습니다."))
            if is_wide_dataframe(cols):
                badges.append(("넓은 표", False, "열이 많아 가로 스크롤 중심으로 탐색합니다."))
            if should_defer_analysis_charts(rows, cols):
                badges.append(("분석 수동", False, "분석 차트는 [지금 그리기] 또는 각 탭 버튼으로 그립니다."))
        for idx, badge in enumerate(self._mode_badges):
            if idx < len(badges):
                text, warning, tip = badges[idx]
                badge.setText(text)
                badge.setToolTip(tip)
                badge.setStyleSheet(self._badge_style(warning=warning))
                badge.show()
            else:
                badge.hide()

    def _run_table_shortcut(self, handler) -> None:
        focus = self.focusWidget()
        if focus in (self.viewer.search_entry, self.viewer.preview_text):
            return
        if not self._require_data():
            return
        handler()

    def insert_row_above(self) -> None:
        if self._require_data():
            self.viewer.insert_row_above_selection()

    def insert_row_below(self) -> None:
        if self._require_data():
            self.viewer.insert_row_below_selection()

    def insert_column_left(self) -> None:
        if self._require_data():
            self.viewer.insert_column_left_selection()

    def insert_column_right(self) -> None:
        if self._require_data():
            self.viewer.insert_column_right_selection()

    def delete_rows(self) -> None:
        if self._require_data():
            self.viewer.delete_selected_rows()

    def delete_column(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        columns = [str(c) for c in self._loaded.dataframe.columns]
        if not columns:
            return
        result = qt_select_column_dialog(
            self,
            "열 삭제",
            "삭제할 열:",
            columns,
            confirm_text="삭제",
        )
        if not result:
            return
        df = delete_column(self._loaded.dataframe, result)
        self._apply_dataframe(df, message=f"열 삭제: {result}")

    def _show_page(self, page: str) -> None:
        self._current_page = page
        index = {"main": 0, "analysis": 1, "crawl": 2, "log": 3}.get(page, 0)
        self._stack.setCurrentIndex(index)
        style_nav_button(self._nav_main_btn, active=page == "main")
        style_nav_button(self._nav_analysis_btn, active=page == "analysis")
        style_nav_button(self._nav_crawl_btn, active=page == "crawl")
        style_nav_button(self._nav_log_btn, active=page == "log")
        if page == "analysis":
            self.analysis_panel.refresh()
        elif page == "crawl":
            self.crawl_panel.refresh_data_columns()

    def _apply_analysis_result(self, df: pd.DataFrame, message: str) -> None:
        self._apply_dataframe(df, message=message)

    def _apply_crawled_dataframe(self, df: pd.DataFrame, message: str) -> None:
        """크롤링 결과를 새 세션으로 가공 탭에 로드합니다."""
        if df is None or df.empty:
            self._toast_warning("가져올 크롤링 결과가 없습니다.")
            return
        loaded = LoadedData(path=Path("crawled.csv"), dataframe=df.copy())
        self._pending_prev_path = None
        self._pending_sheet_name = None
        self._pending_load_limit = None
        self._apply_loaded_data(loaded, new_file=True)
        self.path_label.setText("크롤링 결과")
        self.setWindowTitle(f"{APP_NAME} — 크롤링 결과")
        self._show_page("main")
        self._set_status(f"{message} — {len(df):,}행 × {len(df.columns):,}열")
        self._log_action("success", message, f"{len(df):,}행 × {len(df.columns):,}열")

    @staticmethod
    def _format_action_message(message: str) -> str:
        if any(message.endswith(s) for s in ("완료", "됨", "제거", "변경", "복원", "추가", "등록", "적용", "삭제", "초기화", "지우기")):
            return message
        return f"{message} 완료"

    def _log_action(self, kind: str, message: str, detail: str | None = None) -> None:
        self._activity_log.add(kind, message, detail)

    def _toast_action(self, message: str) -> None:
        self._log_action("success", self._format_action_message(message))

    def _toast_error(self, title: str, detail: str) -> None:
        self._set_status(f"{title} — {detail}")
        QMessageBox.critical(self, title, detail)
        self._log_action("error", title, detail)

    def _toast_warning(self, message: str, *, detail: str | None = None) -> None:
        self._set_status(message)
        if detail:
            QMessageBox.warning(self, message, detail)
        self._log_action("warning", message, detail)

    def _set_status(self, message: str, *, revert_after_ms: int | None = STATUS_REVERT_MS) -> None:
        self._status_revert_timer.stop()
        self._status.showMessage(message)
        if revert_after_ms is not None:
            self._status_revert_timer.start(revert_after_ms)

    def _set_status_persistent(self, message: str | None = None) -> None:
        self._status_revert_timer.stop()
        self._status.showMessage(message if message is not None else self._default_status_text())

    def _revert_status(self) -> None:
        self._status.showMessage(self._default_status_text())

    def _default_status_text(self) -> str:
        if self._loaded is None:
            return "준비"
        df = self._loaded.dataframe
        suffix = "  |  부분 로드" if self._partial_load_limit is not None else ""
        return f"{self._loaded.path.name}  |  {len(df):,}행 × {len(df.columns):,}열{suffix}"

    def _require_data(self) -> bool:
        if self._loaded is None:
            self._toast_warning("먼저 파일을 여세요.")
            return False
        return True

    def _push_undo(self) -> None:
        if self._loaded is None:
            return
        df = self._loaded.dataframe
        limit = adaptive_undo_depth(len(df), len(df.columns), default=self.MAX_UNDO)
        self._undo_stack.append(df.copy())
        while len(self._undo_stack) > limit:
            self._undo_stack.pop(0)

    def _on_viewer_change(self, df: pd.DataFrame) -> None:
        if self._loaded is None:
            return
        self._push_undo()
        self._data_token += 1
        self._loaded.dataframe = df
        if self._loaded.active_sheet:
            self._loaded.sheet_frames[self._loaded.active_sheet] = df
        self.analysis_panel.invalidate_pending_work()
        self._schedule_info_refresh()
        self._sync_mode_badges()
        self._set_status(f"데이터 수정됨 — {len(df):,}행 × {len(df.columns):,}열")

    def _schedule_info_refresh(self) -> None:
        self._info_refresh_timer.start(350)

    def _run_deferred_info_refresh(self) -> None:
        self._refresh_info()

    def _apply_dataframe(self, df: pd.DataFrame, *, message: str | None = None) -> None:
        if self._loaded is None:
            return
        self._push_undo()
        self._data_token += 1
        self._loaded.dataframe = df
        if self._loaded.active_sheet:
            self._loaded.sheet_frames[self._loaded.active_sheet] = df
        self.analysis_panel.invalidate_pending_work()
        self.viewer.set_dataframe(df, reset_sort=False, copy=False, new_session=False)
        self._refresh_info()
        self._sync_mode_badges()
        if self._current_page == "analysis":
            self.analysis_panel.refresh()
        if message:
            self._set_status(f"{message} — {len(df):,}행 × {len(df.columns):,}열")
            self._log_action("success", self._format_action_message(message), f"{len(df):,}행 × {len(df.columns):,}열")
        else:
            self._set_status(f"적용 완료 — {len(df):,}행 × {len(df.columns):,}열")
            self._log_action("success", "적용 완료", f"{len(df):,}행 × {len(df.columns):,}열")

    def _apply_code_result(self, df: pd.DataFrame) -> None:
        self._apply_dataframe(df, message="Python 코드 실행")

    def _code_notify(self, success: bool, message: str, *, detail: str | None = None) -> None:
        if not success:
            self._toast_error(message, detail or message)

    def open_file(self) -> None:
        if self._loading:
            self._toast_warning("파일을 불러오는 중입니다. 잠시 기다려 주세요.")
            return
        filters = ";;".join(f"{label} ({pat})" for label, pat in FILE_DIALOG_TYPES)
        path, _ = QFileDialog.getOpenFileName(self, "데이터 파일 열기", "", filters)
        if path:
            self.load_path(Path(path))

    def _choose_load_limit(self, path: Path, file_size: int) -> int | None | bool:
        suffix = resolve_file_suffix(path)
        is_excel = suffix in EXCEL_SUFFIXES
        if not should_prompt_large_file(file_size, is_excel=is_excel):
            return None
        excel_note = "\n\n※ Excel은 전체를 읽은 뒤 앞부분만 표시할 수 있습니다." if is_excel else ""
        prompt = (
            f"'{path.name}' ({format_file_size(file_size)})\n\n"
            f"예 — 처음 {LARGE_FILE_PREVIEW_ROWS:,}행만 열기 (권장)\n"
            f"아니오 — 전체 열기\n"
            f"취소 — 열기 중단"
            f"{excel_note}"
        )
        reply = QMessageBox.question(
            self,
            "대용량 파일",
            prompt,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        if reply == QMessageBox.StandardButton.Yes:
            return LARGE_FILE_PREVIEW_ROWS
        return None

    def _release_current_file(self) -> None:
        self.viewer.prepare_for_new_dataset()
        self._undo_stack.clear()
        self._before_summary_df = None
        self.viewer.set_restore_available(False)
        self._loaded = None
        self._partial_load_limit = None
        self._sync_mode_badges()
        gc.collect()

    def _set_loading(self, active: bool, message: str = "") -> None:
        self._loading = active
        if active:
            self._set_status(message, revert_after_ms=None)
        elif self._loaded is not None:
            self._set_status_persistent()
        else:
            self._status.showMessage("준비")

    def load_path(self, path: Path, sheet_name: str | None = None) -> None:
        if self._loading:
            self._toast_warning("파일을 불러오는 중입니다.")
            return
        path = Path(path)
        try:
            file_size = path.stat().st_size
        except OSError as exc:
            self._toast_error("파일 열기 실패", str(exc))
            return
        limit = self._choose_load_limit(path, file_size)
        if limit is False:
            return
        nrows = limit if isinstance(limit, int) else None
        self._pending_load_limit = nrows
        self._pending_prev_path = self._loaded.path if self._loaded else None
        self._pending_sheet_name = sheet_name
        self._release_current_file()
        self._set_loading(True, f"불러오는 중: {path.name}…")

        def work() -> LoadedData:
            return load_file(path, sheet_name=sheet_name, nrows=nrows)

        self._load_poller.start(self._load_executor.submit(work), self._on_file_loaded)

    def _on_file_loaded(self, future: Future) -> None:
        try:
            loaded = future.result()
        except Exception as exc:
            self._set_loading(False)
            self._toast_error("파일 열기 실패", str(exc))
            return
        row_count = len(loaded.dataframe)
        col_count = len(loaded.dataframe.columns)
        if row_count > LARGE_FILE_WARN_ROWS:
            self._log_action("info", "대용량 데이터", f"{row_count:,}행 — 스크롤·검색에 시간이 걸릴 수 있습니다.")
        elif col_count >= 50:
            self._log_action("info", "넓은 표", f"{col_count:,}열 — 가로 스크롤로 열 구간을 이동합니다.")
        self._apply_loaded_data(loaded, new_file=True)
        self._set_loading(False)

    def _apply_loaded_data(self, loaded: LoadedData, *, new_file: bool) -> None:
        prev_path = getattr(self, "_pending_prev_path", None)
        prev_sheet = getattr(self, "_pending_sheet_name", None)
        self._loaded = loaded
        self._partial_load_limit = self._pending_load_limit
        self._pending_load_limit = None
        self._data_token += 1
        self._undo_stack.clear()
        self._before_summary_df = None
        self.viewer.set_restore_available(False)
        self._refresh_ui()
        detail = f"{len(loaded.dataframe):,}행 × {len(loaded.dataframe.columns):,}열"
        if new_file and prev_path != loaded.path:
            self._activity_log.clear()
            self._log_action("info", f"파일 열기: {loaded.path.name}", detail)
        elif prev_sheet and prev_sheet != loaded.active_sheet:
            self._log_action("info", f"시트 전환: {loaded.active_sheet}", detail)

    def _refresh_ui(self) -> None:
        if self._loaded is None:
            return
        loaded = self._loaded
        self.path_label.setText(loaded.path.name)
        self.viewer.set_dataframe(loaded.dataframe, copy=False, new_session=True)
        self.info_panel.apply_default_stats_visibility(len(loaded.dataframe), len(loaded.dataframe.columns))
        self._refresh_info()
        self._sync_mode_badges()
        if self._current_page == "analysis":
            self.analysis_panel.refresh()
        else:
            self.analysis_panel.refresh_light()
        self._sync_sheet_selector()
        self._set_status_persistent()
        self.setWindowTitle(f"{APP_NAME} — {loaded.path.name}")

    def _sync_sheet_selector(self) -> None:
        loaded = self._loaded
        self._updating_sheet_combo = True
        self.sheet_combo.blockSignals(True)
        try:
            if loaded is None:
                self.sheet_combo.clear()
                self.sheet_combo.setEnabled(False)
                self.sheet_delete_btn.setEnabled(False)
                return
            if not loaded.sheet_names:
                self.sheet_combo.clear()
                self.sheet_combo.addItem("해당 없음")
                self.sheet_combo.setEnabled(False)
                self.sheet_delete_btn.setEnabled(False)
                return
            active = loaded.active_sheet or loaded.sheet_names[0]
            self.sheet_combo.clear()
            self.sheet_combo.addItems(loaded.sheet_names)
            idx = self.sheet_combo.findText(active)
            if idx >= 0:
                self.sheet_combo.setCurrentIndex(idx)
            self.sheet_combo.setEnabled(len(loaded.sheet_names) > 1)
            self.sheet_delete_btn.setEnabled(len(loaded.sheet_names) > 1)
        finally:
            self.sheet_combo.blockSignals(False)
            self._updating_sheet_combo = False
        resize_sheet_combo(self.sheet_combo)

    def _on_sheet_changed(self, sheet: str) -> None:
        if self._updating_sheet_combo or self._loaded is None or not self._loaded.sheet_names:
            return
        sheet = sheet.strip()
        if not sheet or sheet == self._loaded.active_sheet or sheet not in self._loaded.sheet_names:
            return
        self.switch_sheet(sheet)

    def switch_sheet(self, sheet_name: str) -> None:
        if self._loading or self._loaded is None:
            return
        self._loaded.remember_current_sheet()
        try:
            df = self._loaded.load_sheet(sheet_name)
        except Exception as exc:
            self._toast_error("시트 전환 실패", str(exc))
            self._sync_sheet_selector()
            return
        self.viewer.prepare_for_new_dataset()
        self._loaded.active_sheet = sheet_name
        self._loaded.dataframe = df
        self._partial_load_limit = None
        self._undo_stack.clear()
        self._before_summary_df = None
        self.viewer.set_restore_available(False)
        self._refresh_ui()
        self._log_action("info", f"시트 전환: {sheet_name}", f"{len(df):,}행 × {len(df.columns):,}열")

    def delete_current_sheet(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        if not self._loaded.sheet_names:
            self._toast_warning("시트가 있는 파일이 아닙니다.")
            return
        sheet = self._loaded.active_sheet
        if not sheet or len(self._loaded.sheet_names) <= 1:
            self._toast_warning("마지막 시트는 삭제할 수 없습니다.")
            return
        reply = QMessageBox.question(
            self,
            "시트 삭제",
            f"시트 '{sheet}'을(를) 삭제할까요?\n\n저장 시 이 시트는 파일에서 제외됩니다.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._loaded.remember_current_sheet()
        try:
            self._loaded.delete_sheet(sheet)
        except ValueError as exc:
            self._toast_error("시트 삭제 실패", str(exc))
            return
        self._undo_stack.clear()
        self._before_summary_df = None
        self.viewer.set_restore_available(False)
        self._refresh_ui()
        self._set_status(f"시트 '{sheet}' 삭제")
        self._log_action("success", f"시트 '{sheet}' 삭제")

    def save_file(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        dialog = QtSaveAsDialog(self, self._loaded.path, self._loaded.save_format)
        result = dialog.get_result()
        if not result:
            return
        path, save_format = result
        if self._partial_load_limit is not None and path.resolve() == self._loaded.path.resolve():
            reply = QMessageBox.question(
                self,
                "부분 로드 저장 확인",
                (
                    f"현재 파일은 처음 {self._partial_load_limit:,}행만 열린 상태입니다.\n\n"
                    "원본 경로에 저장하면 화면에 보이지 않는 나머지 행은 저장 파일에서 제외됩니다.\n"
                    "그래도 원본 파일에 덮어쓸까요?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                self._set_status("부분 로드 데이터의 원본 덮어쓰기를 취소했습니다.")
                self._log_action("warning", "부분 로드 저장 취소", "현재 보이는 일부 데이터만 저장될 수 있어 취소했습니다.")
                return
        if self._loaded.active_sheet:
            self._loaded.remember_current_sheet()
        try:
            saved = save_file(
                path,
                self._loaded.dataframe,
                save_format=save_format,
                sheet_name=self._loaded.active_sheet or "Sheet1",
                sheet_names=self._loaded.sheet_names,
                sheet_frames=self._loaded.sheet_frames,
                source_path=self._loaded.path,
            )
        except Exception as exc:
            self._toast_error("저장 실패", str(exc))
            return
        if saved.resolve() == self._loaded.path.resolve():
            self._loaded.path = saved
            self._loaded.save_format = save_format
            self.path_label.setText(saved.name)
            self.setWindowTitle(f"{APP_NAME} — {saved.name}")
            self._set_status(f"저장 완료: {saved.name}")
            self._log_action("success", f"저장 완료: {saved.name}")
        else:
            self._set_status(f"다른 이름으로 저장: {saved.name}")
            self._log_action("success", f"다른 이름으로 저장: {saved.name}", f"현재 작업 파일: {self._loaded.path.name}")

    def undo(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        if not self._undo_stack:
            self._toast_warning("되돌릴 작업이 없습니다.")
            return
        df = self._undo_stack.pop()
        self._data_token += 1
        self._loaded.dataframe = df
        self.analysis_panel.invalidate_pending_work()
        self.viewer.set_dataframe(df, reset_sort=False, copy=False, new_session=False)
        self._refresh_info()
        if self._current_page == "analysis":
            self.analysis_panel.refresh()
        else:
            self.analysis_panel.refresh_light()
        self._set_status(f"실행 취소 — {len(df):,}행 × {len(df.columns):,}열")
        self._log_action("success", "실행 취소", f"{len(df):,}행 × {len(df.columns):,}열")

    def find_replace(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        selection = self.viewer.get_selection()
        result = qt_find_replace_dialog(
            self,
            [str(c) for c in self._loaded.dataframe.columns],
            selection_hint=selection.describe(),
            has_selection=selection.mode != "none",
        )
        if not result:
            return
        find, replace, column, match_case = result
        row_indices = columns = None
        single_column = column
        if column == "__selection__":
            single_column = None
            row_indices = selection.row_indices()
            columns = selection.column_names()
            if not row_indices and not columns:
                self._toast_warning("선택된 영역이 없습니다.")
                return
        try:
            df = op_find_replace(
                self._loaded.dataframe,
                find,
                replace,
                single_column,
                match_case,
                row_indices=row_indices,
                columns=columns,
            )
        except Exception as exc:
            self._toast_error("찾기/바꾸기 실패", str(exc))
            return
        scope = "선택 영역" if column == "__selection__" else "전체"
        self._apply_dataframe(df, message=f"찾기/바꾸기 완료 ({scope})")

    def add_column(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        result = qt_add_column_dialog(self, position_hint="표 맨 끝에 새 열을 추가합니다.")
        if not result:
            return
        name, default = result
        try:
            df = insert_column_at_end(self._loaded.dataframe, name, default or pd.NA)
        except Exception as exc:
            self._toast_error("열 추가 실패", str(exc))
            return
        self._apply_dataframe(df, message=f"열 추가: {name}")

    def drop_duplicates(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        before = len(self._loaded.dataframe)
        df = drop_duplicates(self._loaded.dataframe)
        removed = before - len(df)
        if removed == 0:
            self._set_status("중복 행 없음 — 데이터 변경 없음")
            self._log_action("info", "중복 행 없음", "변경된 데이터가 없습니다.")
            return
        self._apply_dataframe(df, message=f"중복 {removed:,}행 제거")

    def fill_missing_values(self) -> None:
        """결측이 있는 열을 고른 뒤 채우기."""
        if not self._require_data() or self._loaded is None:
            return
        column = qt_fill_na_pick_column_dialog(self, self._loaded.dataframe)
        if column:
            self.fill_missing_in_column(column)

    def fill_missing_in_column(self, column: str) -> None:
        if not self._require_data() or self._loaded is None:
            return
        df = self._loaded.dataframe
        result = qt_fill_na_dialog(self, df, column)
        if not result:
            return
        method, constant, n_neighbors = result
        label = FILL_NA_METHOD_LABELS.get(method, method)
        detail = f"k={n_neighbors}" if method == "knn" and n_neighbors else None
        msg = f"'{column}' 결측치 채우기 ({label})"
        if detail:
            msg = f"{msg}, {detail}"
        if method in {"knn", "mice"}:
            self._fill_missing_in_column_async(
                df.copy(deep=True),
                column,
                method,
                n_neighbors=n_neighbors,
                message=msg,
            )
            return
        try:
            new_df = fill_na(df, column, method, constant_value=constant)
        except Exception as exc:
            self._toast_error("결측치 채우기 실패", str(exc))
            return
        self._apply_dataframe(new_df, message=msg)

    def _fill_missing_in_column_async(
        self,
        df: pd.DataFrame,
        column: str,
        method: str,
        *,
        n_neighbors: int | None,
        message: str,
    ) -> None:
        if self._fill_poller.busy:
            self._toast_warning("결측치 채우기 작업이 진행 중입니다.", detail="끝난 뒤 다시 시도하세요.")
            return
        token = self._data_token

        def work() -> pd.DataFrame:
            if method == "knn":
                return fill_na_knn(df, [column], n_neighbors=n_neighbors or 5)
            return fill_na_mice(df, [column])

        def on_done(future: Future) -> None:
            try:
                new_df = future.result()
            except Exception as exc:
                self._toast_error("결측치 채우기 실패", str(exc) or type(exc).__name__)
                return
            if token != self._data_token:
                self._set_status("데이터가 변경되어 결측치 채우기 결과를 적용하지 않았습니다.")
                self._log_action("warning", "결측치 채우기 결과 폐기", "작업 중 데이터가 변경되었습니다.")
                return
            self._apply_dataframe(new_df, message=message)

        self._fill_poller.start(self._work_executor.submit(work), on_done)
        self._set_status(f"{message} — 백그라운드 적용 중…", revert_after_ms=None)
        self._log_action("info", "결측치 채우기 시작", message)

    def drop_na_rows(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        before = len(self._loaded.dataframe)
        df = drop_na_rows(self._loaded.dataframe)
        removed = before - len(df)
        if removed == 0:
            self._set_status("결측 행 없음 — 데이터 변경 없음")
            self._log_action("info", "결측 행 없음", "변경된 데이터가 없습니다.")
            return
        self._apply_dataframe(df, message=f"결측 행 {removed:,}개 제거")

    def run_vlookup(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        result = qt_vlookup_dialog(
            self,
            [str(c) for c in self._loaded.dataframe.columns],
            self._loaded.dataframe,
        )
        if not result:
            return
        ref_df, left_key, right_key, return_col, new_name = result
        try:
            df = vlookup(self._loaded.dataframe, ref_df, left_key, right_key, return_col, new_name)
        except Exception as exc:
            self._toast_error("VLOOKUP 실패", str(exc))
            return
        self._apply_dataframe(df, message=f"VLOOKUP → '{new_name}' 열 추가")

    def run_merge(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        result = qt_merge_dialog(
            self,
            [str(c) for c in self._loaded.dataframe.columns],
            self._loaded.dataframe,
        )
        if not result:
            return
        ref_df, left_on, right_on, how = result
        try:
            df = merge_dataframes(self._loaded.dataframe, ref_df, left_on, right_on, how=how)
        except Exception as exc:
            self._toast_error("조인 실패", str(exc))
            return
        self._apply_dataframe(df, message=f"조인 완료 ({how})")

    def run_concat(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        result = qt_concat_dialog(self, self._loaded.dataframe)
        if not result:
            return
        try:
            df = concat_dataframes(result)
        except Exception as exc:
            self._toast_error("병합 실패", str(exc))
            return
        self._apply_dataframe(df, message=f"세로 병합 → {len(df):,}행")

    def run_group_summary(self) -> None:
        if not self._require_data() or self._loaded is None:
            return
        result = qt_group_summary_dialog(self, [str(c) for c in self._loaded.dataframe.columns])
        if not result:
            return
        group_col, value_col, agg = result
        try:
            self._before_summary_df = self._loaded.dataframe.copy()
            df = group_summary(self._loaded.dataframe, [group_col], value_col, agg)
        except Exception as exc:
            self._toast_error("그룹 요약 실패", str(exc))
            self._before_summary_df = None
            return
        self._apply_dataframe(df, message=f"그룹 요약 ({agg})")
        self.viewer.set_restore_available(True, self.restore_from_summary)

    def restore_from_summary(self) -> None:
        if self._before_summary_df is None or self._loaded is None:
            return
        self._apply_dataframe(self._before_summary_df.copy(), message="그룹 요약 전 원본으로 복원")
        self._before_summary_df = None
        self.viewer.set_restore_available(False)

    def change_column_dtype(self, column: str, dtype_name: str) -> None:
        if not self._require_data() or self._loaded is None:
            return
        try:
            df = convert_column_dtype(self._loaded.dataframe, column, dtype_name)
        except Exception as exc:
            self._toast_error("타입 변경 실패", str(exc))
            return
        from df_tool.operations import column_dtype_display

        label = column_dtype_display(df[column])
        self._apply_dataframe(df, message=f"'{column}' → {label} 타입으로 변경")

    def _refresh_info(self) -> None:
        if self._loaded is None:
            return
        loaded = self._loaded
        self.info_panel.show(loaded.dataframe, str(loaded.path), loaded.active_sheet)

    def _refresh_info_preview(self, df: pd.DataFrame) -> None:
        if self._loaded is None:
            return
        self.info_panel.show(df, str(self._loaded.path), self._loaded.active_sheet)

    def show_design_settings(self) -> None:
        show_design_settings_dialog(self, self.refresh_theme)

    def refresh_theme(self) -> None:
        self._apply_styles()
        self._set_status("디자인 설정 적용")
        self._log_action("success", "디자인 설정 적용")

    def show_help(self) -> None:
        QtHelpDialog(self, HELP_TEXT, title="사용법").exec()

    def show_guide_doc(self, filename: str, title: str) -> None:
        guide_path = Path(__file__).resolve().parent.parent / filename
        try:
            content = guide_path.read_text(encoding="utf-8")
        except OSError:
            self._toast_error("가이드 파일 없음", str(guide_path))
            return
        QtHelpDialog(self, content, title=title).exec()

    def show_setup_guide(self) -> None:
        self.show_guide_doc("SETUP_GUIDE.md", "설치 · 실행 가이드 (Windows / Mac)")

    def show_project_map(self) -> None:
        self.show_guide_doc("PROJECT_MAP.md", "프로젝트 파일 지도")

    def show_migration_doc(self) -> None:
        self.show_guide_doc("MIGRATION_QT.md", "PyQt 표 엔진 마이그레이션")

    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            APP_NAME,
            f"{APP_TAGLINE}\n\n버전 {__version__}\nPyQt6 표 엔진\n\n[도움말 > 사용법] 참고",
        )

    def show_developer_guide(self) -> None:
        self.show_guide_doc("DEVELOPER_GUIDE.md", "기능 추가 가이드 (개발)")

    def show_learning_guide(self) -> None:
        self.show_guide_doc("LEARNING_GUIDE.md", "코드 공부 가이드")

    def show_coding_standards(self) -> None:
        self.show_guide_doc("CODING_STANDARDS.md", "코드 작성 규칙")

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_window_geometry()
        self._load_poller.cancel()
        self._fill_poller.cancel()
        self.crawl_panel.shutdown()
        self._load_executor.shutdown(wait=False, cancel_futures=True)
        self._work_executor.shutdown(wait=False, cancel_futures=True)
        event.accept()

    def run(self) -> None:
        """창 표시 및 이벤트 루프 (QApplication이 이미 있어야 함)."""
        app = QApplication.instance()
        if app is None:
            raise RuntimeError(
                "QApplication이 없습니다. gridloom.pyw 또는 launch()로 실행하세요."
            )
        self.show()
        app.exec()


def launch() -> int:
    """권장 엔트리 — QApplication 생성 후 MainWindow 실행."""
    qt_app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return qt_app.exec()


def main() -> None:
    sys.exit(launch())


if __name__ == "__main__":
    main()
