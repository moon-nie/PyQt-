"""의존성 기반 UI 게이트 — 위젯 활성/비활성 + 실행 가드(UI 계층).

선택적 패키지(scikit-learn·scipy 등)가 없을 때 버튼/콤보 항목을 비활성화하고
일관된 안내 툴팁·경고를 띄우는 로직을 한곳에 모은다.

문구 자체는 `analysis_deps.feature_requirement_message`(로직 계층, PyQt 무관)에서
가져오며, 이 모듈만 PyQt 위젯을 다룬다(계층 분리 유지).
"""
from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QMessageBox, QWidget

from df_tool.analysis_deps import feature_requirement_message


def gate_widget(widget: QWidget, available: bool, module: str, *, feature: str | None = None) -> None:
    """패키지 유무에 따라 위젯을 활성/비활성하고 누락 시 안내 툴팁을 단다."""
    widget.setEnabled(available)
    widget.setToolTip("" if available else feature_requirement_message(module, feature=feature, inline=True))


def gate_combo_item(
    combo: QComboBox,
    data_value: object,
    available: bool,
    module: str,
    *,
    fallback_index: int = 0,
) -> None:
    """콤보의 특정 항목(data로 식별)을 활성/비활성한다.

    비활성인데 현재 그 항목이 선택돼 있으면 ``fallback_index``로 되돌린다.
    """
    idx = combo.findData(data_value)
    if idx < 0:
        return
    model = combo.model()
    item = model.item(idx) if hasattr(model, "item") else None
    if item is not None:
        item.setEnabled(available)
        item.setToolTip("" if available else feature_requirement_message(module, inline=True))
    if not available and combo.currentData() == data_value:
        combo.setCurrentIndex(fallback_index)


def require(parent: QWidget | None, available: bool, module: str, *, feature: str, title: str | None = None) -> bool:
    """실행 전 가드: 패키지가 없으면 경고를 띄우고 ``False`` 반환."""
    if available:
        return True
    QMessageBox.warning(parent, title or feature, feature_requirement_message(module, feature=feature))
    return False
