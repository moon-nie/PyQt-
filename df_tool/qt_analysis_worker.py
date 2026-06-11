"""분석 탭 백그라운드 작업."""
from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, Qt, QRunnable, QThreadPool, pyqtSignal


class _WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)


class _AnalysisRunnable(QRunnable):
    def __init__(self, fn: Callable[..., Any], signals: _WorkerSignals, *args, **kwargs) -> None:
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs
        self.signals = signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            self.signals.finished.emit(self._fn(*self._args, **self._kwargs))
        except Exception as exc:
            self.signals.error.emit(str(exc))


def run_analysis_task(
    parent: QObject,
    fn: Callable[..., Any],
    on_success: Callable[[object], None],
    on_error: Callable[[str], None],
    *args,
    **kwargs,
) -> QRunnable:
    """백그라운드에서 fn 실행 후 on_success/on_error를 메인 스레드에서 호출."""
    signals = _WorkerSignals(parent)
    signals.finished.connect(on_success, Qt.ConnectionType.QueuedConnection)
    signals.error.connect(on_error, Qt.ConnectionType.QueuedConnection)
    runnable = _AnalysisRunnable(fn, signals, *args, **kwargs)
    QThreadPool.globalInstance().start(runnable)
    return runnable
