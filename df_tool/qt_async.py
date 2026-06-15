"""백그라운드 Future 폴링 공통 래퍼(UI 계층).

`ThreadPoolExecutor`의 Future를 `QTimer`로 주기 폴링하다, 완료되면 결과를
콜백(`on_done(future)`)에 넘긴다. 로딩 표시·토스트·로그·stale 토큰 검사 등
흐름별로 다른 처리는 콜백 안에서 하므로, 이 클래스는 폴링 보일러플레이트만 담는다.
"""
from __future__ import annotations

from concurrent.futures import Future
from typing import Callable

from PyQt6.QtCore import QTimer


class AsyncPoller:
    """단일 Future를 폴링해 완료 시 콜백을 호출한다(동시 1개)."""

    def __init__(self, poll_ms: int = 60) -> None:
        self._poll_ms = poll_ms
        self._future: Future | None = None
        self._on_done: Callable[[Future], None] | None = None

    @property
    def busy(self) -> bool:
        return self._future is not None and not self._future.done()

    def start(self, future: Future, on_done: Callable[[Future], None]) -> None:
        """Future 폴링을 시작한다. 완료되면 ``on_done(future)``가 1회 호출된다."""
        self._future = future
        self._on_done = on_done
        QTimer.singleShot(self._poll_ms, self._poll)

    def _poll(self) -> None:
        future = self._future
        if future is None:
            return
        if not future.done():
            QTimer.singleShot(self._poll_ms, self._poll)
            return
        on_done = self._on_done
        self._future = None
        self._on_done = None
        if on_done is not None:
            on_done(future)

    def cancel(self) -> None:
        """진행 중 작업이 있으면 취소하고 상태를 비운다(창 종료 등)."""
        if self._future is not None and not self._future.done():
            self._future.cancel()
        self._future = None
        self._on_done = None
