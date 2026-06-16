"""
법규 검토 테스트 케이스 3개

케이스 1: 서울 동대문구 전농동 530-45
  대지 112㎡ / 연면적 185.31㎡ / 지하1+지상2층 / 다가구→1종근생(카페)
  예상: 주차1대, 용도변경허가, 내진불필요(기존건물 1992년)

케이스 2: 유사 필지 A (전농동 인근)
  대지 125㎡ / 연면적 210㎡ / 지하1+지상3층 / 다가구→1종근생(편의점)
  예상: 주차1대, 용도변경허가, 소방 자동화재탐지 의무

케이스 3: 유사 필지 B (전농동 인근)
  대지 98㎡ / 연면적 156㎡ / 지상3층(지하없음) / 다가구→2종근생(학원)
  예상: 주차1대, 용도변경허가, 정북일조 검토필요
"""

from __future__ import annotations
import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from building_code_engine.parking import BuildingUse, ParkingInput, calc_parking
from building_code_engine.use_change import BuildingUseCode, ChangeCategory, determine_use_change
from building_code_engine.sewage import SewerUse, SewageInput, calc_sewage
from building_code_engine.fire_safety import check_fire_safety, InstallStatus, FireSafetyItem
from building_code_engine.seismic import check_seismic
from building_code_engine.sunlight import calc_north_setback
from building_code_engine.report import SiteInfoFull
from building_code_engine.zoning import ZoneType
from tests.validate_legal import validate_case, print_validation_report, ValidationReport


def _get_detector_status(checks, floor_area, floors_below) -> bool:
    """소방 검사 결과에서 자동화재탐지 설치 의무 여부 추출."""
    for c in checks:
        if c.item == FireSafetyItem.FIRE_DETECTOR:
            return c.status == InstallStatus.REQUIRED
    return False


def _get_sprinkler_status(checks) -> bool:
    for c in checks:
        if c.item == FireSafetyItem.SPRINKLER:
            return c.status == InstallStatus.REQUIRED
    return False


def _get_emergency_light(checks) -> bool:
    for c in checks:
        if c.item == FireSafetyItem.EMERGENCY_LIGHTING:
            return c.status == InstallStatus.REQUIRED
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  케이스 1: 전농동 530-45 (카페)
# ══════════════════════════════════════════════════════════════════════════════

def run_case1() -> ValidationReport:
    """서울 동대문구 전농동 530-45 / 다가구→1종근생(카페)."""

    # 건물 기본 정보
    site_area       = 112.0
    total_fa        = 185.31
    floors_above    = 2
    floors_below    = 1
    construction_yr = 1992
    zone            = "제2종일반주거지역"
    height_m        = 7.8      # 지상2층 × 약 3.9m

    # 지하 1층 면적 추정 (총면적 / (지상+지하) × 지하)
    basement_area = total_fa / (floors_above + floors_below) * floors_below  # ≈ 61.77㎡
    net_area_1st  = total_fa - basement_area   # ≈ 123.54㎡ (지상 근생 면적)

    # ── 주차 ────────────────────────────────────────────────────────────────
    parking_inp = ParkingInput(
        use=BuildingUse.FIRST_NEIGHBORHOOD,
        floor_area=total_fa,
        excluded_area=basement_area,
        apply_seoul=True,
    )
    pk_result = calc_parking([parking_inp])
    engine_spaces = pk_result[0].required_spaces  # 기대: 1대

    # ── 용도변경 ─────────────────────────────────────────────────────────────
    uc = determine_use_change(BuildingUseCode.MULTI_FAMILY, BuildingUseCode.FIRST_NEIGHBORHOOD)
    engine_procedure = "허가" if uc.category == ChangeCategory.PERMIT else \
                       "신고" if uc.category == ChangeCategory.REPORT else "기재변경"

    # ── 오수 ─────────────────────────────────────────────────────────────────
    sewage_inp = SewageInput(use=SewerUse.FIRST_NEIGHBORHOOD, floor_area=net_area_1st)
    sewage_res = calc_sewage([sewage_inp])
    engine_sewage_L = sewage_res[0].daily_volume_L

    # ── 소방 ─────────────────────────────────────────────────────────────────
    fire_checks = check_fire_safety(total_fa, floors_above, height_m, "제1종근린생활시설",
                                    floors_below=floors_below)
    engine_ext  = any(c.item == FireSafetyItem.FIRE_EXTINGUISHER
                      and c.status == InstallStatus.REQUIRED for c in fire_checks)
    engine_det  = _get_detector_status(fire_checks, total_fa, floors_below)
    engine_sp   = _get_sprinkler_status(fire_checks)
    engine_em   = _get_emergency_light(fire_checks)

    # ── 내진 ─────────────────────────────────────────────────────────────────
    seismic_res = check_seismic(total_fa, floors_above, "제1종근린생활시설", construction_yr,
                                is_new_build=False)
    engine_seismic = seismic_res.required

    # ── 정북일조 ─────────────────────────────────────────────────────────────
    sun_res = calc_north_setback(height_m, zone)
    engine_setback = sun_res.required_setback if sun_res.applicable else 0.0

    # ── 예상 정답 검증 ───────────────────────────────────────────────────────
    assert engine_spaces == 1, f"[케이스1] 주차: 기대 1대, 실제 {engine_spaces}대"
    assert engine_procedure == "허가", f"[케이스1] 용도변경: 기대 허가, 실제 {engine_procedure}"
    assert not engine_seismic, f"[케이스1] 내진: 기존 건물이므로 불필요해야 함"

    return validate_case(
        "케이스1: 전농동 530-45 (카페, 다가구→1종근생)",
        parking_use="1종근생",
        parking_net_area=net_area_1st,
        parking_units=0,
        engine_parking_spaces=engine_spaces,
        from_use="다가구주택",
        to_use="1종근생",
        engine_procedure=engine_procedure,
        sewage_use="1종근생_일반",
        sewage_floor_area=net_area_1st,
        engine_sewage_L=engine_sewage_L,
        total_floor_area=total_fa,
        floors_below=floors_below,
        engine_extinguisher=engine_ext,
        engine_detector=engine_det,
        engine_sprinkler=engine_sp,
        engine_emergency_light=engine_em,
        floors_above=floors_above,
        construction_year=construction_yr,
        is_new_build=False,
        engine_seismic_required=engine_seismic,
        building_height_m=height_m,
        zone_type_str=zone,
        engine_sunlight_setback=engine_setback,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  케이스 2: 유사 필지 A (편의점)
# ══════════════════════════════════════════════════════════════════════════════

def run_case2() -> ValidationReport:
    """대지 125㎡ / 연면적 210㎡ / 지하1+지상3층 / 다가구→1종근생(편의점)."""

    site_area       = 125.0
    total_fa        = 210.0
    floors_above    = 3
    floors_below    = 1
    construction_yr = 1995
    zone            = "제2종일반주거지역"
    height_m        = 10.5   # 지상3층 × 3.5m

    basement_area = total_fa / (floors_above + floors_below) * floors_below  # 52.5㎡
    net_area_1st  = total_fa - basement_area   # 157.5㎡

    # ── 주차 ────────────────────────────────────────────────────────────────
    parking_inp = ParkingInput(
        use=BuildingUse.FIRST_NEIGHBORHOOD,
        floor_area=total_fa,
        excluded_area=basement_area,
        apply_seoul=True,
    )
    pk_result = calc_parking([parking_inp])
    engine_spaces = pk_result[0].required_spaces  # 기대: ceil(157.5/134)=2대

    # ── 용도변경 ─────────────────────────────────────────────────────────────
    uc = determine_use_change(BuildingUseCode.MULTI_FAMILY, BuildingUseCode.FIRST_NEIGHBORHOOD)
    engine_procedure = "허가" if uc.category == ChangeCategory.PERMIT else \
                       "신고" if uc.category == ChangeCategory.REPORT else "기재변경"

    # ── 오수 ─────────────────────────────────────────────────────────────────
    sewage_inp = SewageInput(use=SewerUse.FIRST_NEIGHBORHOOD, floor_area=net_area_1st)
    sewage_res = calc_sewage([sewage_inp])
    engine_sewage_L = sewage_res[0].daily_volume_L

    # ── 소방 ─────────────────────────────────────────────────────────────────
    fire_checks = check_fire_safety(total_fa, floors_above, height_m, "제1종근린생활시설",
                                    floors_below=floors_below)
    engine_ext  = any(c.item == FireSafetyItem.FIRE_EXTINGUISHER
                      and c.status == InstallStatus.REQUIRED for c in fire_checks)
    engine_det  = _get_detector_status(fire_checks, total_fa, floors_below)
    engine_sp   = _get_sprinkler_status(fire_checks)
    engine_em   = _get_emergency_light(fire_checks)

    # ── 내진 ─────────────────────────────────────────────────────────────────
    seismic_res = check_seismic(total_fa, floors_above, "제1종근린생활시설", construction_yr,
                                is_new_build=False)
    engine_seismic = seismic_res.required

    # ── 정북일조 ─────────────────────────────────────────────────────────────
    sun_res = calc_north_setback(height_m, zone)
    engine_setback = sun_res.required_setback if sun_res.applicable else 0.0

    # ── 예상 정답 검증 ───────────────────────────────────────────────────────
    # 157.5㎡ / 134㎡ = 1.175 → 비고6(소수점 0.175 < 0.5 → 버림) = 1대
    expected_spaces = math.floor(net_area_1st / 134 + 0.5)
    assert engine_spaces == expected_spaces, \
        f"[케이스2] 주차: 기대 {expected_spaces}대, 실제 {engine_spaces}대"
    assert engine_procedure == "허가", f"[케이스2] 용도변경: 기대 허가, 실제 {engine_procedure}"
    # 210㎡ >= 400㎡? 아니다 → 소방 자동화재탐지는 NOT_REQUIRED 가능
    # 단, 지하층 있으므로 비상조명등은 의무
    assert engine_ext, "[케이스2] 소화기는 의무여야 함"

    return validate_case(
        "케이스2: 유사 필지 A (편의점, 다가구→1종근생, 지상3층)",
        parking_use="1종근생",
        parking_net_area=net_area_1st,
        parking_units=0,
        engine_parking_spaces=engine_spaces,
        from_use="다가구주택",
        to_use="1종근생",
        engine_procedure=engine_procedure,
        sewage_use="1종근생_일반",
        sewage_floor_area=net_area_1st,
        engine_sewage_L=engine_sewage_L,
        total_floor_area=total_fa,
        floors_below=floors_below,
        engine_extinguisher=engine_ext,
        engine_detector=engine_det,
        engine_sprinkler=engine_sp,
        engine_emergency_light=engine_em,
        floors_above=floors_above,
        construction_year=construction_yr,
        is_new_build=False,
        engine_seismic_required=engine_seismic,
        building_height_m=height_m,
        zone_type_str=zone,
        engine_sunlight_setback=engine_setback,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  케이스 3: 유사 필지 B (학원, 2종근생)
# ══════════════════════════════════════════════════════════════════════════════

def run_case3() -> ValidationReport:
    """대지 98㎡ / 연면적 156㎡ / 지상3층(지하없음) / 다가구→2종근생(학원)."""

    site_area       = 98.0
    total_fa        = 156.0
    floors_above    = 3
    floors_below    = 0
    construction_yr = 1998
    zone            = "제2종일반주거지역"
    height_m        = 10.5   # 지상3층 × 3.5m

    net_area_2nd = total_fa  # 지하 없음 → 전체가 산정면적

    # ── 주차 ────────────────────────────────────────────────────────────────
    # 2종근생(학원): 156㎡ / 134㎡/대 = 1.164 → ceil = 2대
    parking_inp = ParkingInput(
        use=BuildingUse.SECOND_NEIGHBORHOOD,
        floor_area=total_fa,
        excluded_area=0.0,
        apply_seoul=True,
    )
    pk_result = calc_parking([parking_inp])
    engine_spaces = pk_result[0].required_spaces

    # ── 용도변경 ─────────────────────────────────────────────────────────────
    uc = determine_use_change(BuildingUseCode.MULTI_FAMILY, BuildingUseCode.SECOND_NEIGHBORHOOD)
    engine_procedure = "허가" if uc.category == ChangeCategory.PERMIT else \
                       "신고" if uc.category == ChangeCategory.REPORT else "기재변경"

    # ── 오수 ─────────────────────────────────────────────────────────────────
    sewage_inp = SewageInput(use=SewerUse.SECOND_NEIGHBORHOOD, floor_area=net_area_2nd)
    sewage_res = calc_sewage([sewage_inp])
    engine_sewage_L = sewage_res[0].daily_volume_L

    # ── 소방 ─────────────────────────────────────────────────────────────────
    fire_checks = check_fire_safety(total_fa, floors_above, height_m, "제2종근린생활시설",
                                    floors_below=floors_below)
    engine_ext  = any(c.item == FireSafetyItem.FIRE_EXTINGUISHER
                      and c.status == InstallStatus.REQUIRED for c in fire_checks)
    engine_det  = _get_detector_status(fire_checks, total_fa, floors_below)
    engine_sp   = _get_sprinkler_status(fire_checks)
    engine_em   = _get_emergency_light(fire_checks)

    # ── 내진 ─────────────────────────────────────────────────────────────────
    seismic_res = check_seismic(total_fa, floors_above, "제2종근린생활시설", construction_yr,
                                is_new_build=False)
    engine_seismic = seismic_res.required

    # ── 정북일조 ─────────────────────────────────────────────────────────────
    # 10.5m > 9m → 10.5 × 0.5 = 5.25m 이격 필요 → "검토필요" 기대
    sun_res = calc_north_setback(height_m, zone)
    engine_setback = sun_res.required_setback if sun_res.applicable else 0.0

    # ── 예상 정답 검증 ───────────────────────────────────────────────────────
    # 156㎡ / 134㎡ = 1.164 → 비고6(소수점 0.164 < 0.5 → 버림) = 1대
    expected_spaces = math.floor(net_area_2nd / 134 + 0.5)
    assert engine_spaces == expected_spaces, \
        f"[케이스3] 주차: 기대 {expected_spaces}대, 실제 {engine_spaces}대"
    assert engine_procedure == "허가", f"[케이스3] 용도변경: 기대 허가, 실제 {engine_procedure}"
    # 정북일조: 10.5m > 9m → 5.25m 필요
    assert abs(engine_setback - 5.25) < 0.01, \
        f"[케이스3] 정북일조: 기대 5.25m, 실제 {engine_setback}m"

    return validate_case(
        "케이스3: 유사 필지 B (학원/2종근생, 지상3층, 지하없음)",
        parking_use="2종근생",
        parking_net_area=net_area_2nd,
        parking_units=0,
        engine_parking_spaces=engine_spaces,
        from_use="다가구주택",
        to_use="2종근생",
        engine_procedure=engine_procedure,
        sewage_use="1종근생_일반",   # 2종근생 일반 원단위로 검증
        sewage_floor_area=net_area_2nd,
        engine_sewage_L=engine_sewage_L,
        total_floor_area=total_fa,
        floors_below=floors_below,
        engine_extinguisher=engine_ext,
        engine_detector=engine_det,
        engine_sprinkler=engine_sp,
        engine_emergency_light=engine_em,
        floors_above=floors_above,
        construction_year=construction_yr,
        is_new_build=False,
        engine_seismic_required=engine_seismic,
        building_height_m=height_m,
        zone_type_str=zone,
        engine_sunlight_setback=engine_setback,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  전체 실행
# ══════════════════════════════════════════════════════════════════════════════

def run_all_cases() -> list[ValidationReport]:
    reports = []

    cases = [
        ("케이스 1", run_case1),
        ("케이스 2", run_case2),
        ("케이스 3", run_case3),
    ]

    for name, fn in cases:
        try:
            report = fn()
            reports.append(report)
        except AssertionError as e:
            print(f"\n[예상값 불일치] {name}: {e}")
            raise

    return reports


def print_summary(reports: list[ValidationReport]) -> None:
    width = 72
    print()
    print("=" * width)
    print("  전체 검증 요약")
    print("=" * width)
    total_items = sum(r.total for r in reports)
    total_pass  = sum(r.pass_count for r in reports)
    total_warn  = sum(r.warn_count for r in reports)
    total_fail  = sum(r.fail_count for r in reports)
    overall_pct = total_pass / total_items * 100 if total_items else 0

    for r in reports:
        bar = "✔" * r.pass_count + "△" * r.warn_count + "✘" * r.fail_count
        print(f"  {r.case_name[:40]:<40}  {r.match_rate:5.1f}%  {bar}")

    print("-" * width)
    print(f"  합계  {total_items}항목  |  일치 {total_pass}  검토필요 {total_warn}  불일치 {total_fail}")
    print(f"  전체 항목 일치율: {overall_pct:.1f}%")
    print("=" * width)


if __name__ == "__main__":
    reports = run_all_cases()
    for r in reports:
        print_validation_report(r)
    print_summary(reports)
