"""
승강기 설치 의무 판단
근거: 건축법 제64조 + 건축법 시행령 §89 ~ §91
"""

from dataclasses import dataclass
from enum import Enum


class ElevatorType(str, Enum):
    PASSENGER = "승객용 승강기"
    DISABLED = "장애인용 승강기"
    EMERGENCY = "비상용 승강기"
    GOODS = "화물용 승강기"


@dataclass
class ElevatorCheck:
    elevator_type: ElevatorType
    required: bool
    min_units: int
    basis: str
    note: str = ""


def check_elevator(
    floors_above: int,
    total_floor_area: float,
    building_height_m: float,
    building_use_str: str,
    has_disabled_elevator: bool = False,
) -> list[ElevatorCheck]:
    """
    승강기 설치 의무 통합 판단.

    승객용: 6층 이상 or 연면적 2,000㎡ 이상 (건축법 §64①)
    비상용: 높이 31m 초과 (건축법 §64②)
    장애인용: 편의증진법 + 6층 이상 연면적 500㎡ 이상 의무시설
    """
    results: list[ElevatorCheck] = []

    # ── 승객용 승강기 ────────────────────────────────────────────────────────
    passenger_required = floors_above >= 6 or total_floor_area >= 2000
    if passenger_required:
        # 최소 대수: 연면적 3,000㎡ 이하 1대, 이후 2,000㎡마다 1대 추가
        if total_floor_area <= 3000:
            min_units = 1
        else:
            min_units = 1 + int((total_floor_area - 3000) / 2000) + 1
    else:
        min_units = 0

    results.append(ElevatorCheck(
        elevator_type=ElevatorType.PASSENGER,
        required=passenger_required,
        min_units=min_units,
        basis=f"{floors_above}층 / 연면적 {total_floor_area:,.0f}㎡",
        note="연면적 3,000㎡ 초과 시 2,000㎡마다 1대 추가 (건축법 시행령 §89)",
    ))

    # ── 비상용 승강기 ───────────────────────────────────────────────────────
    emergency_required = building_height_m > 31
    if emergency_required:
        # 높이 31m 초과: 1대, 10m 추가마다 1대 추가
        extra = max(0, int((building_height_m - 31) / 10))
        emergency_units = 1 + extra
    else:
        emergency_units = 0

    results.append(ElevatorCheck(
        elevator_type=ElevatorType.EMERGENCY,
        required=emergency_required,
        min_units=emergency_units,
        basis=f"건물 높이 {building_height_m}m {'> 31m' if emergency_required else '<= 31m'}",
        note="비상용 승강기는 승객용과 겸용 가능 (구조 기준 충족 시)",
    ))

    # ── 장애인용 승강기 ─────────────────────────────────────────────────────
    disabled_mandatory_uses = {
        "제1종근린생활시설", "제2종근린생활시설", "업무시설",
        "판매시설", "의료시설", "교육연구시설",
        "문화및집회시설", "공동주택",
    }
    disabled_required = (
        floors_above >= 2
        and total_floor_area >= 500
        and building_use_str in disabled_mandatory_uses
    )
    results.append(ElevatorCheck(
        elevator_type=ElevatorType.DISABLED,
        required=disabled_required,
        min_units=1 if disabled_required else 0,
        basis=f"{floors_above}층 / 연면적 {total_floor_area}㎡ / 용도: {building_use_str}",
        note="카 내부 1.1×1.4m 이상, 점자버튼·음성안내 의무 (편의증진법)",
    ))

    return results
