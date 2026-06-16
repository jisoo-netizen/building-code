"""
소방시설 설치 의무 판단
근거: 소방시설 설치 및 관리에 관한 법률 시행령 별표4·5 (소방시설법 시행령)
      소방시설법 제6조 (건축허가 등의 동의)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ── 열거형 ──────────────────────────────────────────────────────────────────

class FireSafetyItem(str, Enum):
    FIRE_EXTINGUISHER    = "소화기구(소화기·투척용소화용구)"
    STANDPIPE            = "옥내소화전설비"
    OUTDOOR_STANDPIPE    = "옥외소화전설비"
    SPRINKLER            = "스프링클러설비"
    SIMPLE_SPRINKLER     = "간이스프링클러설비"
    FIRE_DETECTOR        = "자동화재탐지설비"
    FIRE_ALARM           = "비상경보설비"
    EMERGENCY_BROADCAST  = "비상방송설비"
    EMERGENCY_LIGHTING   = "비상조명등"
    EXIT_SIGN            = "유도등·유도표지"
    SMOKE_CONTROL        = "제연설비"
    EMERGENCY_OUTLET     = "비상콘센트설비"
    STANDPIPE_CONNECTION = "연결송수관설비"
    WATER_SUPPLY         = "소방용수시설 (거리 기준)"
    FIRE_CONSENT         = "소방서 사전 동의 (건축허가)"


class InstallStatus(str, Enum):
    REQUIRED     = "설치 의무"
    RECOMMENDED  = "설치 권장"
    NOT_REQUIRED = "설치 불필요"


# ── 데이터클래스 ──────────────────────────────────────────────────────────────

@dataclass
class FireSafetyCheck:
    item: FireSafetyItem
    status: InstallStatus
    basis: str
    note: str = ""


# ── 용도 분류 헬퍼 ──────────────────────────────────────────────────────────

def _is_neighborhood(use: str) -> bool:
    return use in {"제1종근린생활시설", "제2종근린생활시설"}

def _is_culture_assembly(use: str) -> bool:
    return "문화" in use or "집회" in use or "공연장" in use or "영화관" in use

def _is_sales_transport(use: str) -> bool:
    return use in {"판매시설", "운수시설"}

def _is_lodging(use: str) -> bool:
    return "숙박" in use

def _is_entertainment(use: str) -> bool:
    return "위락" in use

def _is_medical(use: str) -> bool:
    return "의료시설" in use

def _is_welfare(use: str) -> bool:
    return "노유자시설" in use

def _is_training(use: str) -> bool:
    return "수련시설" in use

def _is_edu_sport(use: str) -> bool:
    return "교육연구시설" in use or "운동시설" in use

def _is_factory_warehouse(use: str) -> bool:
    return use in {"공장", "창고시설"}

def _is_apartment(use: str) -> bool:
    return "공동주택" in use or "아파트" in use or "연립" in use or "다세대" in use

def _is_office(use: str) -> bool:
    return "업무시설" in use

def _is_dormitory(use: str) -> bool:
    return "기숙사" in use


# ── 메인 판단 함수 ───────────────────────────────────────────────────────────

def check_fire_safety(
    total_floor_area: float,
    floors_above: int,
    building_height_m: float,
    building_use_str: str,
    has_sprinkler: bool = False,
    floors_below: int = 0,
    basement_area: float = 0.0,          # 지하층 면적 (㎡)
    is_windowless_floor: bool = False,   # 무창층 여부 (개구부 바닥면적의 1/30 이하)
) -> list[FireSafetyCheck]:
    """
    용도·면적·층수 기준 소방시설 설치 의무 자동 판단.
    (소방시설법 시행령 별표4·5, 2024년 기준)
    """
    results: list[FireSafetyCheck] = []
    fa = total_floor_area
    nb = _is_neighborhood(building_use_str)
    has_basement = floors_below > 0

    # ── 1. 소화기구 (별표4 소화설비) ─────────────────────────────────────────
    # 연면적 33㎡ 이상 또는 위험물 취급 장소
    if fa >= 33:
        results.append(FireSafetyCheck(
            item=FireSafetyItem.FIRE_EXTINGUISHER,
            status=InstallStatus.REQUIRED,
            basis=f"연면적 {fa}㎡ ≥ 33㎡ (시행령 별표4 소화설비 1호)",
        ))

    # ── 2. 옥내소화전 (별표4 소화설비 2호) ───────────────────────────────────
    # 연면적 3,000㎡ 이상 / 지하·무창층 600㎡ 이상 / 지상 4층 이상
    standpipe_req = (
        fa >= 3000
        or floors_above >= 4
        or (has_basement and basement_area >= 600)
        or (is_windowless_floor and fa >= 600)
    )
    basis_parts = []
    if fa >= 3000: basis_parts.append(f"연면적 {fa:,.0f}㎡≥3000㎡")
    if floors_above >= 4: basis_parts.append(f"지상{floors_above}층≥4층")
    if has_basement and basement_area >= 600: basis_parts.append(f"지하600㎡이상")
    results.append(FireSafetyCheck(
        item=FireSafetyItem.STANDPIPE,
        status=InstallStatus.REQUIRED if standpipe_req else InstallStatus.NOT_REQUIRED,
        basis=(
            " / ".join(basis_parts) + " (시행령 별표4 소화설비 2호)"
            if standpipe_req else
            f"연면적 {fa}㎡ / {floors_above}층 (기준 미달)"
        ),
        note="지하층·무창층 600㎡ 이상 또는 4층 이상 건축물",
    ))

    # ── 3. 스프링클러 (별표4 소화설비 3호) ──────────────────────────────────
    sp_req = False
    sp_reason = ""

    if floors_above >= 6:
        sp_req, sp_reason = True, f"6층 이상({floors_above}층): 전 층 의무"
    elif floors_above >= 11 or building_height_m >= 31:
        sp_req, sp_reason = True, f"{floors_above}층·높이{building_height_m}m≥11층·31m"
    elif (
        _is_culture_assembly(building_use_str)
        or _is_sales_transport(building_use_str)
        or _is_lodging(building_use_str)
        or _is_entertainment(building_use_str)
    ) and fa >= 1000:
        sp_req, sp_reason = True, f"{building_use_str} 연면적 {fa}㎡≥1000㎡"
    elif (_is_medical(building_use_str) or _is_welfare(building_use_str)) and fa >= 600:
        sp_req, sp_reason = True, f"{building_use_str} 연면적 {fa}㎡≥600㎡"
    elif _is_training(building_use_str) and fa >= 600:
        sp_req, sp_reason = True, f"수련시설(숙박 포함) 연면적 {fa}㎡≥600㎡"
    elif (_is_edu_sport(building_use_str) or _is_training(building_use_str)) and fa >= 5000:
        sp_req, sp_reason = True, f"{building_use_str} 연면적 {fa}㎡≥5000㎡"
    elif _is_factory_warehouse(building_use_str) and fa >= 5000:
        sp_req, sp_reason = True, f"{building_use_str} 연면적 {fa}㎡≥5000㎡"
    elif _is_apartment(building_use_str) and floors_above >= 16:
        sp_req, sp_reason = True, f"공동주택 {floors_above}층≥16층"
    elif nb and fa >= 1000:
        sp_req, sp_reason = True, f"근린생활시설 연면적 {fa}㎡≥1000㎡"

    results.append(FireSafetyCheck(
        item=FireSafetyItem.SPRINKLER,
        status=InstallStatus.REQUIRED if sp_req else InstallStatus.NOT_REQUIRED,
        basis=sp_reason + " (시행령 별표4 소화설비 3호)" if sp_req else f"연면적 {fa}㎡ / {floors_above}층 (기준 미달)",
        note="스프링클러 설치 시 방화구획 면적 기준 3배 완화 (시행령 §46①단서)" if sp_req else "",
    ))

    # ── 4. 간이스프링클러 (별표4 소화설비 4호) ──────────────────────────────
    simple_sp_req = False
    simple_sp_reason = ""
    if _is_welfare(building_use_str) or (_is_medical(building_use_str) and "정신" in building_use_str):
        if fa >= 300:
            simple_sp_req, simple_sp_reason = True, f"노유자·정신요양 {fa}㎡≥300㎡"
    # 다중이용업소 간이스프링클러는 multi_use_business.py에서 처리
    if simple_sp_req:
        results.append(FireSafetyCheck(
            item=FireSafetyItem.SIMPLE_SPRINKLER,
            status=InstallStatus.REQUIRED,
            basis=simple_sp_reason + " (시행령 별표4 소화설비 4호)",
        ))

    # ── 5. 자동화재탐지설비 (별표4 경보설비 1호) ─────────────────────────────
    det_req = False
    det_reason = ""

    if fa >= 1000:
        det_req, det_reason = True, f"연면적 {fa}㎡≥1000㎡"
    elif (
        nb
        or _is_entertainment(building_use_str)
        or _is_lodging(building_use_str)
        or _is_medical(building_use_str)
        or _is_sales_transport(building_use_str)
    ) and fa >= 400:
        det_req, det_reason = True, f"{building_use_str} 연면적 {fa}㎡≥400㎡"
    elif (
        _is_dormitory(building_use_str)
        or _is_apartment(building_use_str)
        or _is_office(building_use_str)
        or _is_factory_warehouse(building_use_str)
    ) and fa >= 600:
        det_req, det_reason = True, f"{building_use_str} 연면적 {fa}㎡≥600㎡"
    elif nb and has_basement:
        det_req, det_reason = True, f"근생 지하층 → 규모 무관 의무"
    elif floors_above >= 6:
        det_req, det_reason = True, f"{floors_above}층≥6층"
    elif basement_area >= 200:
        det_req, det_reason = True, f"지하주차장 200㎡ 이상"

    results.append(FireSafetyCheck(
        item=FireSafetyItem.FIRE_DETECTOR,
        status=InstallStatus.REQUIRED if det_req else InstallStatus.NOT_REQUIRED,
        basis=(
            det_reason + " (시행령 별표4 경보설비 1호)"
            if det_req else
            f"연면적 {fa}㎡ / {floors_above}층 (기준 미달)"
        ),
    ))

    # ── 6. 비상방송설비 (별표4 경보설비 3호) ────────────────────────────────
    broadcast_req = fa >= 3500 or floors_above >= 11
    results.append(FireSafetyCheck(
        item=FireSafetyItem.EMERGENCY_BROADCAST,
        status=InstallStatus.REQUIRED if broadcast_req else InstallStatus.NOT_REQUIRED,
        basis=f"연면적 {fa}㎡ / {floors_above}층 (기준: 3500㎡ 또는 11층 이상)",
    ))

    # ── 7. 비상조명등 (별표4 피난구조설비 3호) ──────────────────────────────
    em_light_req = has_basement or floors_above >= 11 or is_windowless_floor
    basis_em = []
    if has_basement: basis_em.append(f"지하 {floors_below}층")
    if floors_above >= 11: basis_em.append(f"{floors_above}층≥11층")
    if is_windowless_floor: basis_em.append("무창층")
    results.append(FireSafetyCheck(
        item=FireSafetyItem.EMERGENCY_LIGHTING,
        status=InstallStatus.REQUIRED if em_light_req else InstallStatus.NOT_REQUIRED,
        basis=(
            " / ".join(basis_em) + " → 의무 (별표4 피난구조설비 3호)"
            if em_light_req else
            f"{floors_above}층 / 지하 {floors_below}층 (기준 미달)"
        ),
        note="무창층 여부는 개구부 합계가 바닥면적 1/30 이하인 층 (시행규칙 §2)",
    ))

    # ── 8. 유도등·유도표지 (별표4 피난구조설비 1호) ─────────────────────────
    # 근생·판매·업무·숙박·의료·노유자·수련·문화집회·공장·창고·위락: 면적·층수 무관 의무
    exit_always_uses = {
        "제1종근린생활시설", "제2종근린생활시설", "판매시설", "업무시설",
        "숙박시설", "의료시설", "노유자시설", "수련시설",
        "문화및집회시설", "공장", "창고시설", "위락시설", "운수시설",
    }
    exit_req = (
        building_use_str in exit_always_uses
        or fa >= 400
        or floors_above >= 2
    )
    results.append(FireSafetyCheck(
        item=FireSafetyItem.EXIT_SIGN,
        status=InstallStatus.REQUIRED if exit_req else InstallStatus.NOT_REQUIRED,
        basis=(
            f"{building_use_str} → 전체 의무 (별표4 피난구조설비 1호)"
            if building_use_str in exit_always_uses else
            f"연면적 {fa}㎡ / {floors_above}층"
        ),
    ))

    # ── 9. 제연설비 (별표4 소화활동설비 1호) ─────────────────────────────────
    smoke_req = False
    smoke_reason = ""
    if floors_above >= 6:
        smoke_req, smoke_reason = True, f"{floors_above}층≥6층"
    elif has_basement and (_is_culture_assembly(building_use_str) or "공연장" in building_use_str) and fa >= 600:
        smoke_req, smoke_reason = True, f"지하 영화관·공연장 {fa}㎡≥600㎡"
    elif building_height_m >= 31:
        smoke_req, smoke_reason = True, f"건물높이 {building_height_m}m≥31m"
    results.append(FireSafetyCheck(
        item=FireSafetyItem.SMOKE_CONTROL,
        status=InstallStatus.REQUIRED if smoke_req else InstallStatus.NOT_REQUIRED,
        basis=(
            smoke_reason + " (별표4 소화활동설비 1호)"
            if smoke_req else
            f"연면적 {fa}㎡ / {floors_above}층 / {building_use_str} (기준 미달)"
        ),
        note="특별피난계단 부속실 포함",
    ))

    # ── 10. 비상콘센트 (별표4 소화활동설비 3호) ──────────────────────────────
    outlet_req = floors_above >= 11 or (has_basement and floors_below >= 3 and fa >= 1000)
    results.append(FireSafetyCheck(
        item=FireSafetyItem.EMERGENCY_OUTLET,
        status=InstallStatus.REQUIRED if outlet_req else InstallStatus.NOT_REQUIRED,
        basis=(
            f"{floors_above}층≥11층 또는 지하3층이하+1000㎡이상 (별표4 소화활동설비 3호)"
            if outlet_req else
            f"{floors_above}층 / 지하{floors_below}층 (기준 미달)"
        ),
    ))

    # ── 11. 연결송수관 (별표4 소화활동설비 2호) ──────────────────────────────
    pipe_req = (
        floors_above >= 7
        or (floors_above >= 5 and fa >= 6000)
        or (has_basement and floors_below >= 3 and basement_area >= 500)
    )
    results.append(FireSafetyCheck(
        item=FireSafetyItem.STANDPIPE_CONNECTION,
        status=InstallStatus.REQUIRED if pipe_req else InstallStatus.NOT_REQUIRED,
        basis=(
            f"{floors_above}층≥7층 또는 5층이상+6000㎡이상 또는 지하3층이하500㎡이상 (별표4 소화활동설비 2호)"
            if pipe_req else
            f"{floors_above}층 / 연면적 {fa}㎡ (기준 미달)"
        ),
    ))

    # ── 12. 소방용수시설 거리 기준 ──────────────────────────────────────────
    results.append(FireSafetyCheck(
        item=FireSafetyItem.WATER_SUPPLY,
        status=InstallStatus.REQUIRED,
        basis="건축물 신축·용도변경 시 소방용수시설(소화전) 140m 이내 위치 확인 필요",
        note="소방기본법 §10 — 반경 140m 이내 소방용수 없으면 신규 설치 협의",
    ))

    # ── 13. 소방서 사전 동의 (법 제6조) ─────────────────────────────────────
    # 의료·수련·노유자는 200㎡ 이상, 그 외는 400㎡ 이상
    special_consent_uses = {"의료시설", "노유자시설", "수련시설"}
    consent_threshold = 200 if building_use_str in special_consent_uses else 400
    consent_req = fa >= consent_threshold
    results.append(FireSafetyCheck(
        item=FireSafetyItem.FIRE_CONSENT,
        status=InstallStatus.REQUIRED if consent_req else InstallStatus.NOT_REQUIRED,
        basis=(
            f"연면적 {fa}㎡ ≥ {consent_threshold}㎡ ({building_use_str}) "
            "→ 건축허가 시 소방서 사전 동의 필요 (소방시설법 §6①)"
            if consent_req else
            f"연면적 {fa}㎡ < {consent_threshold}㎡ (사전 동의 불필요)"
        ),
        note="건축허가 신청 전 소방서 건축허가 동의 접수 → 통상 7일 이내 회신" if consent_req else "",
    ))

    return results


def has_sprinkler_installed(checks: list[FireSafetyCheck]) -> bool:
    """스프링클러 설치 의무 여부 — evacuation.py 방화구획 완화 연계용."""
    for c in checks:
        if c.item == FireSafetyItem.SPRINKLER and c.status == InstallStatus.REQUIRED:
            return True
    return False
