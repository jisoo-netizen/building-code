"""
장애인 편의시설 설치 의무 판단
근거: 장애인·노인·임산부 등의 편의증진 보장에 관한 법률 (편의증진법)
     + 동법 시행령 별표2
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AccessibilityItem(str, Enum):
    RAMP = "경사로 (접근로)"
    PARKING = "장애인 전용주차구역"
    ENTRANCE = "출입구 (자동문·폭 기준)"
    RESTROOM = "장애인용 화장실"
    ELEVATOR = "장애인용 승강기"
    TACTILE_BLOCK = "점자블록 (유도·경고)"
    COUNTER = "접수·안내 카운터 (높이 조정)"
    PARKING_PATH = "장애인주차에서 건물까지 접근로"
    SIGNAGE = "점자 안내판·음성 안내"


class InstallObligation(str, Enum):
    MANDATORY = "의무 설치"
    RECOMMENDED = "권장 설치"
    NOT_REQUIRED = "설치 불필요"


@dataclass
class AccessibilityCheck:
    item: AccessibilityItem
    obligation: InstallObligation
    basis: str
    note: str = ""


# 의무 설치 대상 용도 목록 (편의증진법 시행령 별표2)
MANDATORY_USES = {
    "제1종근린생활시설", "제2종근린생활시설",
    "판매시설", "업무시설", "의료시설",
    "교육연구시설", "노유자시설", "수련시설",
    "문화및집회시설", "종교시설", "운동시설",
    "숙박시설", "공동주택",
}


def check_accessibility(
    building_use_str: str,
    total_floor_area: float,
    floors_above: int,
    parking_spaces: int,
    has_elevator: bool,
) -> list[AccessibilityCheck]:
    """
    용도·면적 기준 편의시설 설치 의무 자동 판단.
    """
    results: list[AccessibilityCheck] = []
    is_neighborhood_use = building_use_str in {"제1종근린생활시설", "제2종근린생활시설"}
    # 근린생활시설: 연면적 500㎡ 이상만 의무, 미만은 권고 (편의증진법 시행령 별표2)
    if is_neighborhood_use:
        is_mandatory_use = total_floor_area >= 500
    else:
        is_mandatory_use = building_use_str in MANDATORY_USES
    area_trigger = total_floor_area >= 500  # 연면적 500㎡ 이상

    # ── 경사로 ─────────────────────────────────────────────────────────────
    results.append(AccessibilityCheck(
        item=AccessibilityItem.RAMP,
        obligation=InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str} / 연면적 {total_floor_area}㎡",
        note="경사: 1/12 이하, 유효폭 1.2m 이상, 손잡이 양측 설치",
    ))

    # ── 장애인전용주차구역 ──────────────────────────────────────────────────
    if parking_spaces >= 10:
        disabled_required = max(1, parking_spaces // 50)  # 주차 50대당 1면 이상
        obligation = InstallObligation.MANDATORY
        note = f"총 {parking_spaces}대 중 장애인전용 {disabled_required}면 이상 (3.3m×5m)"
    elif parking_spaces > 0:
        disabled_required = 1
        obligation = InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED
        note = f"주차 {parking_spaces}대 → 장애인전용 1면"
    else:
        disabled_required = 0
        obligation = InstallObligation.NOT_REQUIRED
        note = "주차장 없음"

    results.append(AccessibilityCheck(
        item=AccessibilityItem.PARKING,
        obligation=obligation,
        basis=f"주차대수 {parking_spaces}대 기준",
        note=note,
    ))

    # ── 출입구 ─────────────────────────────────────────────────────────────
    results.append(AccessibilityCheck(
        item=AccessibilityItem.ENTRANCE,
        obligation=InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str}",
        note="출입문 유효폭 0.9m 이상, 자동문 권장, 문턱 없음",
    ))

    # ── 장애인용 화장실 ─────────────────────────────────────────────────────
    toilet_trigger = is_mandatory_use and total_floor_area >= 300
    results.append(AccessibilityCheck(
        item=AccessibilityItem.RESTROOM,
        obligation=InstallObligation.MANDATORY if toilet_trigger else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str} / 연면적 {total_floor_area}㎡",
        note="남녀 각 1개소 이상 (유효면적 1.4×1.8m 이상, 안전손잡이)",
    ))

    # ── 장애인용 승강기 ─────────────────────────────────────────────────────
    elevator_trigger = floors_above >= 2 and total_floor_area >= 500 and is_mandatory_use
    results.append(AccessibilityCheck(
        item=AccessibilityItem.ELEVATOR,
        obligation=InstallObligation.MANDATORY if elevator_trigger else InstallObligation.RECOMMENDED,
        basis=f"{floors_above}층 / 연면적 {total_floor_area}㎡",
        note="카 내부 1.1m×1.4m 이상, 점자버튼·음성안내 필수",
    ))

    # ── 점자블록 ────────────────────────────────────────────────────────────
    results.append(AccessibilityCheck(
        item=AccessibilityItem.TACTILE_BLOCK,
        obligation=InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str}",
        note="주출입구~주차장·도로까지 유도블록 설치",
    ))

    # ── 접수·안내 카운터 ────────────────────────────────────────────────────
    counter_uses = {"업무시설", "판매시설", "의료시설", "교육연구시설"}
    results.append(AccessibilityCheck(
        item=AccessibilityItem.COUNTER,
        obligation=InstallObligation.MANDATORY if building_use_str in counter_uses else InstallObligation.NOT_REQUIRED,
        basis=f"용도: {building_use_str}",
        note="카운터 높이 0.7~0.85m 이하 구간 확보",
    ))

    return results
