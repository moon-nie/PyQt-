"""분석 탭 의존성 검사."""
from __future__ import annotations


def missing_analysis_dependencies() -> list[str]:
    missing: list[str] = []
    for name, mod in (
        ("matplotlib", "matplotlib"),
        ("numpy", "numpy"),
        ("scikit-learn", "sklearn"),
        ("scipy", "scipy"),
    ):
        try:
            __import__(mod)
        except ImportError:
            missing.append(name)
    return missing


def analysis_deps_message() -> str | None:
    missing = missing_analysis_dependencies()
    if not missing:
        return None
    pkgs = ", ".join(missing)
    return f"분석 기능에 필요한 패키지가 없습니다: {pkgs}\n→ pip install -r requirements.txt"


def sklearn_available() -> bool:
    try:
        __import__("sklearn")
        return True
    except ImportError:
        return False


def scipy_available() -> bool:
    try:
        __import__("scipy")
        return True
    except ImportError:
        return False
