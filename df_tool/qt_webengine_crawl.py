"""인앱 로그인 브라우저 · JS 렌더 HTML 추출 (Qt WebEngine).

관리자 페이지처럼 로그인·클라이언트 렌더가 필요한 경우:
1. LoginBrowserDialog에서 사용자가 로그인
2. 같은 QWebEngineProfile로 대상 URL을 열어 렌더된 HTML을 받음
3. HTML은 crawl.extract_* 로직에 넘겨 표로 만듦

PyQt6-WebEngine이 없으면 import 시 ImportError — UI에서 webengine_available()로 게이트.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from df_tool.crawl import format_cookie_header

_PROFILE_NAME = "gridloom-crawl"
_STORAGE_DIR = Path.home() / ".gridloom" / "webengine"


def ensure_webengine_imported() -> None:
    """WebEngine 모듈을 로드합니다.

    ``QApplication`` 인스턴스 생성 **전**에 한 번 호출하는 것이 안전합니다
    (``gridloom.pyw`` 참고).
    """
    from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401


def crawl_webengine_profile(parent: QObject | None = None) -> Any:
    """쿠키·스토리지가 유지되는 공유 프로필."""
    from PyQt6.QtWebEngineCore import QWebEngineProfile

    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    profile = QWebEngineProfile(_PROFILE_NAME, parent)
    profile.setPersistentStoragePath(str(_STORAGE_DIR / "storage"))
    profile.setCachePath(str(_STORAGE_DIR / "cache"))
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
    )
    return profile


class RenderedHtmlFetcher(QObject):
    """숨은 WebEngine 페이지로 URL을 열어 렌더된 HTML을 콜백으로 넘깁니다."""

    finished = pyqtSignal(str, object, object)  # url, html|None, error|None

    def __init__(self, profile: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        from PyQt6.QtWebEngineCore import QWebEnginePage
        from PyQt6.QtWebEngineWidgets import QWebEngineView

        self._profile = profile
        self._view = QWebEngineView()
        self._view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        self._view.resize(1280, 900)
        page = QWebEnginePage(profile, self._view)
        self._view.setPage(page)
        self._busy = False
        self._url = ""
        self._settle_ms = 2000
        self._timeout_ms = 60_000
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._capture_html)
        self._hard_timer = QTimer(self)
        self._hard_timer.setSingleShot(True)
        self._hard_timer.timeout.connect(self._on_hard_timeout)
        self._view.loadFinished.connect(self._on_load_finished)
        self._callback: Callable[[str | None, str | None], None] | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def cancel(self) -> None:
        """진행 중 fetch를 중단합니다. 콜백은 호출하지 않습니다."""
        if not self._busy:
            return
        self._busy = False
        self._timer.stop()
        self._hard_timer.stop()
        self._callback = None
        try:
            from PyQt6.QtWebEngineCore import QWebEnginePage

            self._view.page().triggerAction(QWebEnginePage.WebAction.Stop)
        except Exception:
            pass

    def fetch(
        self,
        url: str,
        *,
        settle_ms: int = 2000,
        timeout_ms: int = 60_000,
        callback: Callable[[str | None, str | None], None] | None = None,
    ) -> None:
        if self._busy:
            raise RuntimeError("이미 페이지를 불러오는 중입니다.")
        target = (url or "").strip()
        if not target:
            raise ValueError("URL이 비어 있습니다.")
        self._busy = True
        self._url = target
        self._settle_ms = max(0, int(settle_ms))
        self._timeout_ms = max(5_000, int(timeout_ms))
        self._callback = callback
        self._hard_timer.start(self._timeout_ms)
        self._view.load(QUrl(target))

    def _on_load_finished(self, ok: bool) -> None:
        if not self._busy:
            return
        if not ok:
            self._done(None, "페이지 로드에 실패했습니다.")
            return
        if self._settle_ms <= 0:
            self._capture_html()
        else:
            self._timer.start(self._settle_ms)

    def _on_hard_timeout(self) -> None:
        if not self._busy:
            return
        try:
            from PyQt6.QtWebEngineCore import QWebEnginePage

            self._view.page().triggerAction(QWebEnginePage.WebAction.Stop)
        except Exception:
            pass
        sec = self._timeout_ms / 1000.0
        self._done(None, f"시간 초과 ({sec:.0f}초). 네트워크·로그인·페이지 응답을 확인하세요.")

    def _capture_html(self) -> None:
        if not self._busy:
            return
        self._view.page().toHtml(self._on_html)

    def _on_html(self, html: str) -> None:
        self._done(html or "", None)

    def _done(self, html: str | None, error: str | None) -> None:
        if not self._busy:
            return
        self._busy = False
        self._timer.stop()
        self._hard_timer.stop()
        cb = self._callback
        self._callback = None
        self.finished.emit(self._url, html, error)
        if cb is not None:
            cb(html, error)

    def collect_cookies(self, on_done: Callable[[str], None]) -> None:
        """프로필 Cookie 스토어를 Cookie 헤더 문자열로 모읍니다."""
        store = self._profile.cookieStore()
        jar: dict[str, str] = {}

        def on_added(cookie) -> None:
            try:
                name = bytes(cookie.name()).decode("utf-8", errors="replace")
                value = bytes(cookie.value()).decode("utf-8", errors="replace")
            except Exception:
                return
            if name:
                jar[name] = value

        store.cookieAdded.connect(on_added)
        store.loadAllCookies()

        def finish() -> None:
            try:
                store.cookieAdded.disconnect(on_added)
            except TypeError:
                pass
            on_done(format_cookie_header(jar))

        QTimer.singleShot(150, finish)


class LoginBrowserDialog(QDialog):
    """사용자가 직접 로그인하는 인앱 브라우저 창."""

    def __init__(
        self,
        start_url: str,
        *,
        profile: Any | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        from PyQt6.QtWebEngineCore import QWebEnginePage
        from PyQt6.QtWebEngineWidgets import QWebEngineView

        self.setWindowTitle("로그인 브라우저 — Gridloom 크롤링")
        self.resize(1100, 780)
        self._profile = profile or crawl_webengine_profile(self)
        self.cookie_header = ""
        self.last_url = (start_url or "").strip()

        root = QVBoxLayout(self)
        tip = QLabel(
            "사이트에 로그인한 뒤 [세션(Cookie) 적용]을 누르세요.\n"
            "같은 세션으로 [브라우저 렌더 미리보기]·일괄 수집이 가능합니다."
        )
        tip.setWordWrap(True)
        root.addWidget(tip)

        nav = QHBoxLayout()
        self.url_edit = QLineEdit(self.last_url)
        self.url_edit.returnPressed.connect(self._navigate)
        nav.addWidget(self.url_edit, stretch=1)
        go = QPushButton("이동")
        go.clicked.connect(self._navigate)
        nav.addWidget(go)
        root.addLayout(nav)

        self.view = QWebEngineView(self)
        page = QWebEnginePage(self._profile, self.view)
        self.view.setPage(page)
        self.view.urlChanged.connect(self._on_url_changed)
        root.addWidget(self.view, stretch=1)

        self.status = QLabel("준비")
        root.addWidget(self.status)

        buttons = QDialogButtonBox()
        self.apply_btn = buttons.addButton("세션(Cookie) 적용", QDialogButtonBox.ButtonRole.AcceptRole)
        self.apply_btn.clicked.connect(self._apply_cookies)
        close_btn = buttons.addButton("닫기", QDialogButtonBox.ButtonRole.RejectRole)
        close_btn.clicked.connect(self.reject)
        root.addWidget(buttons)

        if self.last_url:
            self.view.load(QUrl(self.last_url))

    def profile(self) -> Any:
        return self._profile

    def _navigate(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            return
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
            self.url_edit.setText(url)
        self.view.load(QUrl(url))

    def _on_url_changed(self, qurl: QUrl) -> None:
        text = qurl.toString()
        self.last_url = text
        if text:
            self.url_edit.setText(text)

    def _apply_cookies(self) -> None:
        self.status.setText("Cookie 수집 중…")
        self.apply_btn.setEnabled(False)
        store = self._profile.cookieStore()
        jar: dict[str, str] = {}

        def on_added(cookie) -> None:
            try:
                name = bytes(cookie.name()).decode("utf-8", errors="replace")
                value = bytes(cookie.value()).decode("utf-8", errors="replace")
            except Exception:
                return
            if name:
                jar[name] = value

        store.cookieAdded.connect(on_added)
        store.loadAllCookies()

        def finish() -> None:
            try:
                store.cookieAdded.disconnect(on_added)
            except TypeError:
                pass
            self.cookie_header = format_cookie_header(jar)
            self.apply_btn.setEnabled(True)
            if not self.cookie_header:
                self.status.setText("Cookie가 비어 있습니다. 로그인했는지 확인하세요.")
                QMessageBox.warning(
                    self,
                    "Cookie",
                    "수집된 Cookie가 없습니다.\n로그인 후 다시 [세션(Cookie) 적용]을 눌러 주세요.",
                )
                return
            self.status.setText(f"Cookie {len(jar)}개 적용 준비됨")
            self.accept()

        QTimer.singleShot(200, finish)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        super().closeEvent(event)
