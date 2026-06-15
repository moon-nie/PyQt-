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
}


def _package_available(module_name: str) -> bool:
    try:
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
    separator = " " if inline else "\n"
    return f"{head}{separator}{INSTALL_HINT}"


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
