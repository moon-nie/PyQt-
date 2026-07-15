"""분석/차트 기능의 선택적 의존성 검사 및 안내 메시지(SSOT).

이 모듈은 두 가지 책임만 가진다.
1. 선택적 패키지(matplotlib·numpy·scikit-learn·scipy)의 설치 여부 확인.
2. 누락 시 사용자에게 보여줄 **일관된 안내 문구** 생성.

UI 코드(`qt_analysis_panel.py`, `qt_data_dialogs.py` 등)는 안내 문구를
직접 만들지 말고 반드시 이 모듈의 함수를 사용한다. (문구 중복 방지)
"""
from __future__ import annotations

# 모든 안내 문구가 공유하는 단일 설치 명령 (문구 표준화의 핵심).
INSTALL_HINT = "pip install -r requirements.txt"

# 모듈명 → 사용자에게 보여줄 패키지 이름.
_PACKAGE_LABEL = {
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "sklearn": "scikit-learn",
    "scipy": "scipy",
    "PyQt6.QtWebEngineWidgets": "PyQt6-WebEngine",
}


def _package_available(module_name: str) -> bool:
    try:
        import importlib.util

        if importlib.util.find_spec(module_name) is None:
            return False
        # find_spec만으로 부족한 확장 모듈이 있어 실제 import도 확인
        __import__(module_name)
        return True
    except ImportError:
        return False


def package_label(module_name: str) -> str:
    """모듈명을 사용자용 패키지 이름으로 변환 (예: ``sklearn`` → ``scikit-learn``)."""
    return _PACKAGE_LABEL.get(module_name, module_name)


def feature_requirement_message(
    module_name: str,
    *,
    feature: str | None = None,
    inline: bool = False,
) -> str:
    """선택적 패키지가 필요할 때 보여줄 표준 안내 문구.

    Args:
        module_name: 필요한 모듈명 (예: ``"sklearn"``, ``"scipy"``).
        feature: 기능 이름. 주면 "{기능}에는 {패키지}이(가) 필요합니다." 형태.
                 없으면 "{패키지} 설치 후 사용할 수 있습니다." 형태.
        inline: True면 한 줄(`... 안내. 명령`), False면 두 줄(줄바꿈 분리).
    """
    label = package_label(module_name)
    if feature:
        head = f"{feature}에는 {label}이(가) 필요합니다."
    else:
        head = f"{label} 설치 후 사용할 수 있습니다."
    # WebEngine은 별도 패키지라 직접 설치 명령을 함께 안내
    if module_name == "PyQt6.QtWebEngineWidgets":
        hint = "pip install PyQt6-WebEngine\n(또는 pip install -r requirements.txt)\n앱을 쓰는 것과 같은 Python으로 설치한 뒤 앱을 다시 실행하세요."
    else:
        hint = INSTALL_HINT
    separator = " " if inline else "\n"
    if inline and module_name == "PyQt6.QtWebEngineWidgets":
        return f"{head} pip install PyQt6-WebEngine 후 앱 재실행"
    return f"{head}{separator}{hint}"


def missing_analysis_dependencies() -> list[str]:
    """분석 전체 기능에 필요한 패키지 중 빠진 것의 사용자용 이름 목록."""
    return [
        package_label(mod)
        for mod in ("matplotlib", "numpy", "sklearn", "scipy")
        if not _package_available(mod)
    ]


def analysis_deps_message() -> str | None:
    """분석 의존성이 하나라도 빠지면 배너용 안내 문구, 모두 있으면 None."""
    missing = missing_analysis_dependencies()
    if not missing:
        return None
    return f"분석 기능에 필요한 패키지가 없습니다: {', '.join(missing)}\n→ {INSTALL_HINT}"


def matplotlib_available() -> bool:
    return _package_available("matplotlib")


def numpy_available() -> bool:
    return _package_available("numpy")


def charts_available() -> bool:
    """기본 차트 렌더링에 필요한 최소 의존성(matplotlib + numpy)."""
    return matplotlib_available() and numpy_available()


def charts_deps_message() -> str | None:
    """차트 렌더링 의존성이 빠지면 안내 문구, 모두 있으면 None."""
    missing = [
        package_label(mod)
        for mod in ("matplotlib", "numpy")
        if not _package_available(mod)
    ]
    if not missing:
        return None
    return f"차트 기능에 필요한 패키지가 없습니다: {', '.join(missing)}\n→ {INSTALL_HINT}"


def sklearn_available() -> bool:
    return _package_available("sklearn")


def scipy_available() -> bool:
    return _package_available("scipy")


def webengine_available() -> bool:
    """인앱 로그인 브라우저·JS 렌더 추출용 Qt WebEngine.

    패키지 존재만 확인합니다. 실제 import는 ``gridloom.pyw``에서
    QApplication 생성 **전**에 해야 하므로, 여기서는 find_spec만 사용합니다.
    """
    try:
        import importlib.util

        return importlib.util.find_spec("PyQt6.QtWebEngineWidgets") is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False
