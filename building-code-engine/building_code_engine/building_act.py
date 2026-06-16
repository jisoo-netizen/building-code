"""
건축행위 자동 판단 및 허가/신고 분류
근거: 건축법 제2조 (정의) + 제11조 (허가) + 제14조 (신고)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BuildingAction(str, Enum):
    NEW_BUILD = "신축"
    EXTENSION = "증축"
    RECONSTRUCTION = "개축"
    REBUILD = "재축"
    RELOCATION = "이전"
    MAJOR_REPAIR = "대수선"
    USE_CHANGE = "용도변경"


class ActionCategory(str, Enum):
    PERMIT = "건축허가"
    REPORT = "건축신고"
    EXEMPT = "허가·신고 불필요"


@dataclass
class ActionResult:
    action: BuildingAction
    category: ActionCategory
    reason: str
    major_repair_items: list[str] = field(default_factory=list)
    notes: str = ""


# 대수선 해당 항목 (건축법 §2①9호)
MAJOR_REPAIR_ITEMS = [
    "내력벽 면적 30㎡ 이상 해체·수선",
    "기둥 3개 이상 해체·수선",
    "보 3개 이상 해체·수선",
    "지붕틀 3개 이상 해체·수선",
    "방화벽 해체·수선",
    "계단 해체·수선 (주요구조부)",
    "외벽 마감재 해체·수선 (방화 관련)",
    "주요구조부 절반 이상 해체·수선",
]


def check_major_repair(items_checked: list[str]) -> tuple[bool, list[str]]:
    """대수선 해당 여부 판단 — 해당 항목 목록과 boolean 반환."""
    matched = [i for i in items_checked if i in MAJOR_REPAIR_ITEMS]
    return len(matched) > 0, matched


def determine_action(
    action: BuildingAction,
    total_floor_area: float,
    floors_above: int,
    height_m: float,
    extension_area: Optional[float] = None,   # 증축 면적
    major_repair_items: Optional[list[str]] = None,
) -> ActionResult:
    """
    건축행위 유형별 허가/신고 자동 분류.

    허가 대상 (건축법 §11):
    - 연면적 100㎡ 초과 신축·증축·개축·재축·이전
    - 3층 이상 신축·증축
    - 높이 8m 이상 신축·증축
    - 대수선

    신고 대상 (건축법 §14):
    - 연면적 100㎡ 이하
    - 증축 면적 85㎡ 이하 (지구단위계획구역 외 기존 4층 이하)
    """
    if action == BuildingAction.MAJOR_REPAIR:
        checked = major_repair_items or []
        is_major, matched = check_major_repair(checked)
        if is_major:
            return ActionResult(
                action=action,
                category=ActionCategory.PERMIT,
                reason="대수선 → 건축허가 필요 (건축법 §11)",
                major_repair_items=matched,
                notes="내력벽·기둥·보 등 주요구조부 수선 포함",
            )
        return ActionResult(
            action=action,
            category=ActionCategory.REPORT,
            reason="대수선 해당 없음 → 건축신고 (일반 수선)",
            major_repair_items=[],
        )

    if action == BuildingAction.USE_CHANGE:
        return ActionResult(
            action=action,
            category=ActionCategory.PERMIT,
            reason="용도변경 → use_change 모듈에서 허가/신고/기재변경 별도 판단",
        )

    # 신축·증축·개축·재축·이전 공통 판단
    permit_triggers = []
    if total_floor_area > 100:
        permit_triggers.append(f"연면적 {total_floor_area}㎡ > 100㎡")
    if floors_above >= 3:
        permit_triggers.append(f"{floors_above}층 이상")
    if height_m >= 8:
        permit_triggers.append(f"높이 {height_m}m >= 8m")
    if extension_area and extension_area > 85:
        permit_triggers.append(f"증축 면적 {extension_area}㎡ > 85㎡")

    if permit_triggers:
        return ActionResult(
            action=action,
            category=ActionCategory.PERMIT,
            reason=" / ".join(permit_triggers) + " → 건축허가 필요",
        )

    return ActionResult(
        action=action,
        category=ActionCategory.REPORT,
        reason=f"연면적 {total_floor_area}㎡ 이하·{floors_above}층 미만·높이 {height_m}m 미만 → 건축신고",
    )
