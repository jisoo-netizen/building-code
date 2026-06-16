"""단위 테스트 — 전체 모듈 커버."""

import pytest
from building_code_engine.zoning import ZoneType, check_bcr, check_far
from building_code_engine.parking import BuildingUse, ParkingInput, calc_parking, compare_parking
from building_code_engine.sunlight import calc_north_setback, check_north_setback
from building_code_engine.use_change import (
    BuildingUseCode, ChangeCategory, determine_use_change,
    NeighborhoodBusinessType, classify_neighborhood,
)
from building_code_engine.sewage import SewerUse, SewageInput, calc_sewage, compare_sewage
from building_code_engine.seismic import check_seismic
from building_code_engine.building_act import BuildingAction, determine_action
from building_code_engine.fire_safety import check_fire_safety, InstallStatus
from building_code_engine.evacuation import check_direct_staircase, check_fire_compartment
from building_code_engine.setback import check_building_line_setback, check_adjacent_boundary_setback
from building_code_engine.accessibility import check_accessibility, InstallObligation
from building_code_engine.elevator import check_elevator
from building_code_engine.energy import check_energy, CertObligation


# ── 용도지역 ──────────────────────────────────────────────────────────────

def test_bcr_pass():
    r = check_bcr(ZoneType.SECOND_GENERAL_RESIDENTIAL, 1000, 550)
    assert r["pass"] is True

def test_bcr_fail():
    r = check_bcr(ZoneType.SECOND_GENERAL_RESIDENTIAL, 1000, 650)
    assert r["pass"] is False

def test_far_pass():
    r = check_far(ZoneType.SECOND_GENERAL_RESIDENTIAL, 1000, 2000)
    assert r["pass"] is True

def test_far_fail():
    r = check_far(ZoneType.SECOND_GENERAL_RESIDENTIAL, 1000, 2600)
    assert r["pass"] is False


# ── 주차 ─────────────────────────────────────────────────────────────────

def test_parking_office_seoul():
    r = calc_parking([ParkingInput(use=BuildingUse.OFFICE, floor_area=1000, apply_seoul=True)])
    # 업무시설 서울 100㎡/대: ceil(1000/100) = 10
    assert r[0].required_spaces == 10

def test_parking_apartment():
    r = calc_parking([ParkingInput(use=BuildingUse.APARTMENT, units=20)])
    assert r[0].required_spaces == 20

def test_parking_1st_neighborhood_basic():
    # 1종 근생: 134㎡/대 (서울 동일 기준)
    r = calc_parking([ParkingInput(use=BuildingUse.FIRST_NEIGHBORHOOD,
                                   floor_area=134, apply_seoul=True)])
    assert r[0].required_spaces == 1

def test_parking_1st_neighborhood_excluded():
    # 전농동 케이스: 총면적 185.31, 지하 61.77 제외 → 순면적 123.54㎡
    # 123.54 / 134 = 0.922 → ceil → 1대
    r = calc_parking([ParkingInput(
        use=BuildingUse.FIRST_NEIGHBORHOOD,
        floor_area=185.31,
        excluded_area=61.77,
        apply_seoul=True,
    )])
    assert r[0].required_spaces == 1

def test_parking_excluded_area_zero_floor():
    # excluded_area >= floor_area → net 0 → 0대
    r = calc_parking([ParkingInput(
        use=BuildingUse.FIRST_NEIGHBORHOOD,
        floor_area=50.0,
        excluded_area=60.0,
        apply_seoul=True,
    )])
    assert r[0].required_spaces == 0

def test_parking_compare_deficit():
    before = [ParkingInput(use=BuildingUse.MULTI_FAMILY, units=6)]
    # 1종 근생 134㎡/대: 402㎡ → ceil(402/134) = 3대
    after = [ParkingInput(use=BuildingUse.FIRST_NEIGHBORHOOD, floor_area=402, apply_seoul=True)]
    cmp = compare_parking(before, after, 6, 3)
    assert cmp.deficit == 0  # 필요 3대, 계획 3대


# ── 정북일조 ──────────────────────────────────────────────────────────────

def test_sunlight_under_9m():
    r = calc_north_setback(8.0, "제2종일반주거지역")
    assert r.required_setback == 1.5

def test_sunlight_above_9m():
    # 법령: 21.0m × 0.5 = 10.5m (건축법 시행령 §86① — 각 부분 높이의 1/2)
    r = calc_north_setback(21.0, "제1종일반주거지역")
    assert r.required_setback == 10.5

def test_sunlight_not_applicable():
    r = calc_north_setback(30.0, "일반상업지역")
    assert r.applicable is False

def test_sunlight_check_pass():
    # 16.5m × 0.5 = 8.25m 필요 / 실제 8.5m → 통과
    r = check_north_setback(16.5, 8.5, "제2종일반주거지역")
    assert r["pass"] is True


# ── 용도변경 ──────────────────────────────────────────────────────────────

def test_use_change_permit():
    # 다가구(8군) → 1종근생(7군): 상위→하위 = 허가
    r = determine_use_change(BuildingUseCode.MULTI_FAMILY, BuildingUseCode.FIRST_NEIGHBORHOOD)
    assert r.category == ChangeCategory.PERMIT

def test_use_change_report():
    # 근생(7군) → 업무(8군, 주거업무시설군): 하위→상위 = 신고
    r = determine_use_change(BuildingUseCode.FIRST_NEIGHBORHOOD, BuildingUseCode.OFFICE)
    assert r.category == ChangeCategory.REPORT

def test_use_change_record():
    # 동일군(7군) 내 변경 = 기재변경
    r = determine_use_change(BuildingUseCode.FIRST_NEIGHBORHOOD, BuildingUseCode.SECOND_NEIGHBORHOOD)
    assert r.category == ChangeCategory.RECORD

def test_neighborhood_classify_1st():
    r = classify_neighborhood(NeighborhoodBusinessType.MEDICAL_CLINIC, 200)
    assert r.classification == "제1종"
    assert r.applicable is True

def test_neighborhood_classify_area_exceeded():
    # 슈퍼마켓 1000㎡ 초과
    r = classify_neighborhood(NeighborhoodBusinessType.SMALL_MARKET, 1200)
    assert r.applicable is False


# ── 오수 ─────────────────────────────────────────────────────────────────

def test_sewage_area_basis():
    r = calc_sewage([SewageInput(use=SewerUse.OFFICE, floor_area=1000)])
    # 0.06L/㎡·일 × 1000 = 60L/일
    assert r[0].daily_volume_L == pytest.approx(60.0)

def test_sewage_compare_increase():
    before = [SewageInput(use=SewerUse.SINGLE_HOUSE, persons=10)]
    after = [SewageInput(use=SewerUse.RESTAURANT, floor_area=200)]
    cmp = compare_sewage(before, after)
    # 음식점 200㎡: 24.0×200=4800L > 주거 10인×200=2000L → 증가
    assert cmp["increase_L"] > 0


# ── 내진 ─────────────────────────────────────────────────────────────────

def test_seismic_required():
    r = check_seismic(600, 4, "제1종근린생활시설")
    assert r.required is True

def test_seismic_not_required():
    r = check_seismic(100, 2, "단독주택")
    assert r.required is False

def test_seismic_retrofit():
    r = check_seismic(500, 3, "업무시설", construction_year=1980)
    assert r.retrofit_recommended is True


# ── 건축행위 ──────────────────────────────────────────────────────────────

def test_building_act_permit():
    r = determine_action(BuildingAction.NEW_BUILD, 500, 4, 15.0)
    from building_code_engine.building_act import ActionCategory
    assert r.category == ActionCategory.PERMIT

def test_building_act_report():
    r = determine_action(BuildingAction.NEW_BUILD, 80, 2, 6.0)
    from building_code_engine.building_act import ActionCategory
    assert r.category == ActionCategory.REPORT


# ── 소방 ─────────────────────────────────────────────────────────────────

def test_fire_extinguisher_required():
    checks = check_fire_safety(100, 2, 7.0, "제1종근린생활시설")
    ext = next(c for c in checks if "소화기" in c.item.value)
    assert ext.status == InstallStatus.REQUIRED

def test_sprinkler_not_required_small():
    checks = check_fire_safety(400, 3, 10.0, "제1종근린생활시설")
    sp = next(c for c in checks if c.item.value == "스프링클러설비")
    assert sp.status == InstallStatus.NOT_REQUIRED


# ── 피난 ─────────────────────────────────────────────────────────────────

def test_direct_staircase_single():
    r = check_direct_staircase(300, 3)
    assert r.pass_ is True

def test_fire_compartment_ok():
    results = check_fire_compartment(800, False, "업무시설")
    area_check = results[0]
    assert area_check.pass_ is True

def test_fire_compartment_fail():
    results = check_fire_compartment(1500, False, "업무시설")
    assert results[0].pass_ is False


# ── 이격거리 ─────────────────────────────────────────────────────────────

def test_building_line_setback_wide_road():
    r = check_building_line_setback(6.0, 0.0)
    assert r.required_m == 0.0
    assert r.pass_ is True

def test_building_line_setback_narrow_road():
    r = check_building_line_setback(3.0, 0.3)
    # 3m 도로: 중심선 2m → 양쪽 각 2m이나 도로측만 0.5m 후퇴 필요
    assert r.required_m > 0

def test_adjacent_setback():
    r = check_adjacent_boundary_setback(10.0, 0.5)
    assert r.pass_ is True  # 완화기준 0.5m


# ── 장애인편의 ────────────────────────────────────────────────────────────

def test_accessibility_mandatory_use():
    checks = check_accessibility("제1종근린생활시설", 600, 3, 8, False)
    ramp = next(c for c in checks if "경사로" in c.item.value)
    assert ramp.obligation == InstallObligation.MANDATORY

def test_accessibility_parking_disabled():
    checks = check_accessibility("업무시설", 1000, 5, 50, True)
    pk = next(c for c in checks if "주차구역" in c.item.value)
    assert pk.obligation == InstallObligation.MANDATORY


# ── 승강기 ────────────────────────────────────────────────────────────────

def test_elevator_not_required():
    checks = check_elevator(4, 500, 13.0, "제1종근린생활시설")
    passenger = next(c for c in checks if c.elevator_type.value == "승객용 승강기")
    assert not passenger.required

def test_elevator_required():
    checks = check_elevator(7, 3000, 25.0, "업무시설")
    passenger = next(c for c in checks if c.elevator_type.value == "승객용 승강기")
    assert passenger.required

def test_emergency_elevator_required():
    checks = check_elevator(12, 5000, 40.0, "업무시설")
    em = next(c for c in checks if c.elevator_type.value == "비상용 승강기")
    assert em.required


# ── 에너지 ────────────────────────────────────────────────────────────────

def test_energy_plan_required():
    checks = check_energy(600, "업무시설", is_new_build=True, is_extension=False)
    plan = next(c for c in checks if "에너지절약계획서" in c.cert_type.value)
    assert plan.obligation == CertObligation.MANDATORY

def test_energy_plan_not_required_small():
    checks = check_energy(300, "업무시설", is_new_build=True, is_extension=False)
    plan = next(c for c in checks if "에너지절약계획서" in c.cert_type.value)
    assert plan.obligation == CertObligation.NOT_REQUIRED
