"""
장애인 편의시설 설치 의무 판단
근거: 장애인·노인·임산부 등의 편의증진 보장에 관한 법률 (편의증진법)
     + 동법 시행령 별표2 (2023년 개정)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AccessibilityItem(str, Enum):
    RAMP          = "경사로 (접근로)"
    PARKING       = "장애인 전용주차구역"
    ENTRANCE      = "출입구 (자동문·폭 기준)"
    RESTROOM      = "장애인용 화장실"
    ELEVATOR      = "장애인용 승강기"
    TACTILE_BLOCK = "점자블록 (유도·경고)"
    COUNTER       = "접수·안내 카운터 (높이 조정)"
    PARKING_PATH  = "장애인주차에서 건물까지 접근로"
    SIGNAGE       = "점자 안내판·음성 안내"


class InstallObligation(str, Enum):
    MANDATORY    = "의무 설치"
    RECOMMENDED  = "권장 설치"
    NOT_REQUIRED = "설치 불필요"


@dataclass
class AccessibilityCheck:
    item: AccessibilityItem
    obligation: InstallObligation
    basis: str
    note: str = ""


# ── 의무 설치 대상 용도 + 면적 기준 (편의증진법 시행령 별표2) ──────────────────
# 형식: 용도 → 최소 바닥면적 (㎡); None = 면적 무관 의무
MANDATORY_AREA_TABLE: dict[str, Optional[float]] = {
    # 근린생활시설: 300㎡ 이상 의무 (시행령 별표2 제5호)
    "제1종근린생활시설":  300.0,
    "제2종근린생활시설":  300.0,
    # 판매·업무·의료·교육: 500㎡ 이상
    "판매시설":           500.0,
    "업무시설":           500.0,
    "의료시설":           500.0,
    "교육연구시설":       500.0,
    # 수련·노유자·운동: 500㎡ 이상
    "노유자시설":         500.0,
    "수련시설":           500.0,
    "운동시설":           500.0,
    # 문화·집회·종교: 500㎡ 이상
    "문화및집회시설":     500.0,
    "종교시설":           500.0,
    # 숙박·공동주택: 면적 무관 의무
    "숙박시설":           None,
    "공동주택":           None,
}


def _is_mandatory(building_use_str: str, total_floor_area: float) -> bool:
    """편의증진법 시행령 별표2 기준 의무 여부 판단."""
    for key, min_area in MANDATORY_AREA_TABLE.items():
        if key in building_use_str or building_use_str == key:
            if min_area is None:
                return True
            return total_floor_area >= min_area
    return False


def check_accessibility(
    building_use_str: str,
    total_floor_area: float,
    floors_above: int,
    parking_spaces: int,
    has_elevator: bool,
) -> list[AccessibilityCheck]:
    """
    용도·면적 기준 편의시설 설치 의무 자동 판단.

    근린생활시설: 바닥면적 300㎡ 이상 → 의무 (편의증진법 시행령 별표2 제5호).
    미만인 경우는 "권장 설치"로 표시.
    """
    results: list[AccessibilityCheck] = []
    is_mandatory_use = _is_mandatory(building_use_str, total_floor_area)

    # 근린생활시설 면적 기준 (300㎡)
    nb_area_threshold = 300.0
    is_neighborhood = "근린생활시설" in building_use_str
    nb_area_met = total_floor_area >= nb_area_threshold if is_neighborhood else True
    basis_suffix = (
        f"(바닥면적 {total_floor_area}㎡ {'≥' if nb_area_met else '<'} {nb_area_threshold}㎡)"
        if is_neighborhood else
        f"(바닥면적 {total_floor_area}㎡)"
    )

    # ── 접근로 (경사로) ────────────────────────────────────────────────────
    results.append(AccessibilityCheck(
        item=AccessibilityItem.RAMP,
        obligation=InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str} {basis_suffix} (편의증진법 시행령 별표2)",
        note="접근로 유효폭 1.2m 이상, 종단경사 1/18 이하, 횡단경사 1/50 이하",
    ))

    # ── 장애인전용주차구역 ──────────────────────────────────────────────────
    # 주차 2~4% (시설별), 최소 1면; 규격 3.3m × 5.0m
    if parking_spaces >= 50:
        disabled_pct = 4 if "의료시설" in building_use_str else 2
        disabled_req = max(1, round(parking_spaces * disabled_pct / 100))
        obligation = InstallObligation.MANDATORY
        note = f"총 {parking_spaces}대 × {disabled_pct}% = {disabled_req}면 이상 (3.3m×5.0m)"
    elif parking_spaces >= 10:
        disabled_req = 1
        obligation = InstallObligation.MANDATORY
        note = f"10~49대 → 장애인전용 1면 (3.3m×5.0m)"
    elif parking_spaces > 0:
        disabled_req = 1
        obligation = InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED
        note = f"주차 {parking_spaces}대 → 장애인전용 1면 (3.3m×5.0m)"
    else:
        disabled_req = 0
        obligation = InstallObligation.NOT_REQUIRED
        note = "주차장 없음"

    results.append(AccessibilityCheck(
        item=AccessibilityItem.PARKING,
        obligation=obligation,
        basis=f"주차대수 {parking_spaces}대 기준 (편의증진법 §17)",
        note=note,
    ))

    # ── 출입구 ─────────────────────────────────────────────────────────────
    results.append(AccessibilityCheck(
        item=AccessibilityItem.ENTRANCE,
        obligation=InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str} {basis_suffix}",
        note="출입문 유효폭 0.9m 이상, 자동문 권장, 문턱 없음, 레버형 손잡이",
    ))

    # ── 장애인용 화장실 ─────────────────────────────────────────────────────
    # 각 층 남녀 각 1개소, 최소 1.6m×2.0m (편의증진법 시행규칙 별표1)
    toilet_trigger = is_mandatory_use
    results.append(AccessibilityCheck(
        item=AccessibilityItem.RESTROOM,
        obligation=InstallObligation.MANDATORY if toilet_trigger else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str} {basis_suffix}",
        note="각 층 남녀 각 1개소 이상; 유효면적 1.6m×2.0m 이상, 안전손잡이, 세면대 0.85m 이하",
    ))

    # ── 장애인용 승강기 ─────────────────────────────────────────────────────
    # 3층 이상 + 의무 설치 대상 시설 (편의증진법 시행령 별표2)
    elevator_trigger = floors_above >= 3 and is_mandatory_use
    results.append(AccessibilityCheck(
        item=AccessibilityItem.ELEVATOR,
        obligation=InstallObligation.MANDATORY if elevator_trigger else InstallObligation.RECOMMENDED,
        basis=f"{floors_above}층 / {basis_suffix}",
        note="카 내부 1.1m×1.4m 이상, 점자버튼·음성안내·점자표지 필수",
    ))

    # ── 점자블록 ────────────────────────────────────────────────────────────
    results.append(AccessibilityCheck(
        item=AccessibilityItem.TACTILE_BLOCK,
        obligation=InstallObligation.MANDATORY if is_mandatory_use else InstallObligation.RECOMMENDED,
        basis=f"용도: {building_use_str} {basis_suffix}",
        note="주출입구~주차장·도로까지 유도블록(황색) 설치; 경고블록 단차·장애물 전방 설치",
    ))

    # ── 접수·안내 카운터 ────────────────────────────────────────────────────
    counter_uses = {"업무시설", "판매시설", "의료시설", "교육연구시설"}
    results.append(AccessibilityCheck(
        item=AccessibilityItem.COUNTER,
        obligation=(
            InstallObligation.MANDATORY
            if any(u in building_use_str for u in counter_uses) and is_mandatory_use
            else InstallObligation.NOT_REQUIRED
        ),
        basis=f"용도: {building_use_str}",
        note="카운터 높이 0.7~0.85m 이하 구간 확보 (유효폭 0.9m 이상)",
    ))

    return results
