"""
소방시설 설치 의무 판단
근거: 소방시설 설치 및 관리에 관한 법률 (소방시설법) + 시행령 별표4·5
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FireSafetyItem(str, Enum):
    SPRINKLER = "스프링클러설비"
    FIRE_DETECTOR = "자동화재탐지설비"
    EMERGENCY_LIGHTING = "비상조명등"
    EXIT_SIGN = "유도등·유도표지"
    FIRE_EXTINGUISHER = "소화기구(소화기·투척용소화용구)"
    STANDPIPE = "옥내소화전설비"
    OUTDOOR_STANDPIPE = "옥외소화전설비"
    FIRE_ALARM = "비상경보설비"
    EMERGENCY_BROADCAST = "비상방송설비"
    SMOKE_CONTROL = "제연설비"
    FIRE_DOOR_CLOSER = "방화문 자동폐쇄장치"
    WATER_SUPPLY = "소방용수시설 (거리 기준)"


class InstallStatus(str, Enum):
    REQUIRED = "설치 의무"
    RECOMMENDED = "설치 권장"
    NOT_REQUIRED = "설치 불필요"


@dataclass
class FireSafetyCheck:
    item: FireSafetyItem
    status: InstallStatus
    basis: str
    note: str = ""


def check_fire_safety(
    total_floor_area: float,
    floors_above: int,
    building_height_m: float,
    building_use_str: str,
    has_sprinkler: bool = False,
    floors_below: int = 0,
) -> list[FireSafetyCheck]:
    """
    용도·면적·층수 기준 소방시설 설치 의무 자동 판단.
    """
    results: list[FireSafetyCheck] = []

    # ── 소화기구 ────────────────────────────────────────────────────────────
    if total_floor_area >= 33:
        results.append(FireSafetyCheck(
            item=FireSafetyItem.FIRE_EXTINGUISHER,
            status=InstallStatus.REQUIRED,
            basis=f"연면적 {total_floor_area}㎡ >= 33㎡ (소방시설법 시행령 별표4)",
        ))

    # ── 자동화재탐지설비 ─────────────────────────────────────────────────────
    detector_uses = {
        "제1종근린생활시설", "제2종근린생활시설", "업무시설",
        "판매시설", "의료시설", "교육연구시설", "숙박시설",
        "공동주택", "단독주택", "다가구주택",
    }
    is_neighborhood = building_use_str in {"제1종근린생활시설", "제2종근린생활시설"}
    detector_required = (
        total_floor_area >= 1000
        or (building_use_str in detector_uses and total_floor_area >= 400)
        or floors_above >= 6
        or (is_neighborhood and floors_below > 0)  # 근생 지하층 있으면 무조건
    )
    results.append(FireSafetyCheck(
        item=FireSafetyItem.FIRE_DETECTOR,
        status=InstallStatus.REQUIRED if detector_required else InstallStatus.RECOMMENDED,
        basis=(
            f"연면적 {total_floor_area}㎡ / {floors_above}층 / 용도: {building_use_str}"
            if detector_required else
            f"연면적 {total_floor_area}㎡ < 기준 미달 (권장)"
        ),
    ))

    # ── 옥내소화전 ──────────────────────────────────────────────────────────
    standpipe_required = total_floor_area >= 3000 or floors_above >= 4
    results.append(FireSafetyCheck(
        item=FireSafetyItem.STANDPIPE,
        status=InstallStatus.REQUIRED if standpipe_required else InstallStatus.NOT_REQUIRED,
        basis=f"연면적 {total_floor_area}㎡ / {floors_above}층",
        note="지하층 포함 4층 이상 또는 연면적 3,000㎡ 이상",
    ))

    # ── 스프링클러 ──────────────────────────────────────────────────────────
    sprinkler_uses_high = {"숙박시설", "의료시설", "노유자시설"}
    sprinkler_required = (
        total_floor_area >= 5000
        or (building_use_str in sprinkler_uses_high and total_floor_area >= 600)
        or (is_neighborhood and total_floor_area >= 1000)  # 근생 1,000㎡ 이상
        or floors_above >= 11
        or (floors_above >= 6 and total_floor_area >= 2000)
    )
    results.append(FireSafetyCheck(
        item=FireSafetyItem.SPRINKLER,
        status=InstallStatus.REQUIRED if sprinkler_required else InstallStatus.NOT_REQUIRED,
        basis=(
            f"연면적 {total_floor_area}㎡ / {floors_above}층 / 용도: {building_use_str}"
            if sprinkler_required else
            f"연면적 {total_floor_area}㎡ 미만 기준·{floors_above}층 미만"
        ),
    ))

    # ── 비상조명등 ──────────────────────────────────────────────────────────
    # 소방시설법 시행령 별표4: 지하층, 무창층, 11층 이상
    emergency_light_required = floors_below > 0 or floors_above >= 11
    basis_em_parts = [f"{floors_above}층 / 지하 {floors_below}층"]
    if floors_below > 0:
        basis_em_parts.append("지하층 → 의무")
    elif floors_above >= 11:
        basis_em_parts.append("11층 이상 → 의무")
    results.append(FireSafetyCheck(
        item=FireSafetyItem.EMERGENCY_LIGHTING,
        status=InstallStatus.REQUIRED if emergency_light_required else InstallStatus.NOT_REQUIRED,
        basis=" / ".join(basis_em_parts),
        note="지하층·무창층·11층이상 (소방시설법 시행령 별표4); 무창층은 현장 판단",
    ))

    # ── 유도등·유도표지 ─────────────────────────────────────────────────────
    # 근생: 면적·층수 무관 전부 의무 (소방시설법 시행령 별표5)
    exit_required = is_neighborhood or total_floor_area >= 400 or floors_above >= 2
    exit_basis = (
        f"근린생활시설 → 전체 의무 (소방시설법 시행령 별표5)"
        if is_neighborhood
        else f"연면적 {total_floor_area}㎡ / {floors_above}층"
    )
    results.append(FireSafetyCheck(
        item=FireSafetyItem.EXIT_SIGN,
        status=InstallStatus.REQUIRED if exit_required else InstallStatus.NOT_REQUIRED,
        basis=exit_basis,
    ))

    # ── 비상방송설비 ────────────────────────────────────────────────────────
    broadcast_required = total_floor_area >= 3500 or floors_above >= 11
    results.append(FireSafetyCheck(
        item=FireSafetyItem.EMERGENCY_BROADCAST,
        status=InstallStatus.REQUIRED if broadcast_required else InstallStatus.NOT_REQUIRED,
        basis=f"연면적 {total_floor_area}㎡ / {floors_above}층",
    ))

    # ── 제연설비 ────────────────────────────────────────────────────────────
    smoke_required = (
        floors_above >= 6
        or total_floor_area >= 1000
        or building_use_str in {"숙박시설", "의료시설"}
    )
    results.append(FireSafetyCheck(
        item=FireSafetyItem.SMOKE_CONTROL,
        status=InstallStatus.REQUIRED if smoke_required else InstallStatus.NOT_REQUIRED,
        basis=f"연면적 {total_floor_area}㎡ / {floors_above}층 / 용도: {building_use_str}",
        note="특별피난계단 부속실 포함",
    ))

    # ── 소방용수시설 거리 기준 ──────────────────────────────────────────────
    results.append(FireSafetyCheck(
        item=FireSafetyItem.WATER_SUPPLY,
        status=InstallStatus.REQUIRED,
        basis="건축물 신축·용도변경 시 소방용수시설(소화전) 140m 이내 위치 확인 필요",
        note="소방기본법 §10 — 반경 140m 이내 소방용수 없으면 신규 설치 협의",
    ))

    return results
