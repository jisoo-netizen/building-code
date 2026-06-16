"""
주소 한 줄 → 법규 검토 입력 데이터 자동 조립
VWorld + 건축물대장 API 순차 호출 후 SiteInfoFull 반환
"""

import time
from dataclasses import dataclass
from typing import Optional

from .vworld import lookup_address, ZoningInfo, ParcelInfo
from .building_registry import get_building_info, get_floor_info, BuildingBasicInfo

# engine imports
from building_code_engine.zoning import ZoneType
from building_code_engine.use_change import BuildingUseCode
from building_code_engine.parking import BuildingUse, ParkingInput
from building_code_engine.sewage import SewerUse, SewageInput
from building_code_engine.report import SiteInfoFull


# ── 용도지역 문자열 → ZoneType 변환 ────────────────────────────────────────

ZONE_STR_TO_ENUM: dict[str, ZoneType] = {z.value: z for z in ZoneType}

def _zone_str_to_type(zone_str: str) -> ZoneType:
    """용도지역 문자열 → ZoneType enum. 매핑 실패 시 제2종일반주거지역 fallback."""
    if zone_str in ZONE_STR_TO_ENUM:
        return ZONE_STR_TO_ENUM[zone_str]
    # 부분 매칭 시도
    for key, val in ZONE_STR_TO_ENUM.items():
        if zone_str in key or key in zone_str:
            return val
    print(f"  [WARNING] 용도지역 매핑 실패: '{zone_str}' → 제2종일반주거지역으로 대체")
    return ZoneType.SECOND_GENERAL_RESIDENTIAL


# ── 기존 용도 문자열 → BuildingUseCode 변환 ────────────────────────────────

_USE_KEYWORD_MAP: list[tuple[str, BuildingUseCode]] = [
    ("다가구",         BuildingUseCode.MULTI_FAMILY),
    ("단독주택",        BuildingUseCode.SINGLE_HOUSE),
    ("다세대",         BuildingUseCode.MULTI_FAMILY),
    ("아파트",         BuildingUseCode.APARTMENT),
    ("공동주택",        BuildingUseCode.APARTMENT),
    ("연립",          BuildingUseCode.APARTMENT),
    ("제1종근린생활",    BuildingUseCode.FIRST_NEIGHBORHOOD),
    ("1종근린",        BuildingUseCode.FIRST_NEIGHBORHOOD),
    ("제2종근린생활",    BuildingUseCode.SECOND_NEIGHBORHOOD),
    ("2종근린",        BuildingUseCode.SECOND_NEIGHBORHOOD),
    ("근린생활",        BuildingUseCode.FIRST_NEIGHBORHOOD),  # 미세분 → 1종 기본
    ("업무",          BuildingUseCode.OFFICE),
    ("판매",          BuildingUseCode.RETAIL),
    ("숙박",          BuildingUseCode.ACCOMMODATION),
    ("의료",          BuildingUseCode.MEDICAL),
    ("교육",          BuildingUseCode.EDUCATION),
    ("문화",          BuildingUseCode.CULTURE_ASSEMBLY),
    ("공장",          BuildingUseCode.FACTORY),
    ("창고",          BuildingUseCode.WAREHOUSE),
]

def _infer_use_code(use_str: str) -> BuildingUseCode:
    for keyword, code in _USE_KEYWORD_MAP:
        if keyword in use_str:
            return code
    return BuildingUseCode.MULTI_FAMILY  # 기본 fallback


# ── 기존 용도 → 주차·오수 입력 자동 생성 ────────────────────────────────────

def _auto_parking_before(use_code: BuildingUseCode, bld: BuildingBasicInfo) -> list[ParkingInput]:
    """기존 용도 기준 주차 입력 추정."""
    if use_code in (BuildingUseCode.MULTI_FAMILY, BuildingUseCode.SINGLE_HOUSE):
        # 세대수 추정: 지상층수 × 1세대 (보수적)
        units = max(bld.floors_above, 1)
        return [ParkingInput(use=BuildingUse.MULTI_FAMILY, units=units, apply_seoul=True)]
    if use_code == BuildingUseCode.APARTMENT:
        units = max(bld.floors_above * 2, 1)
        return [ParkingInput(use=BuildingUse.APARTMENT, units=units, apply_seoul=True)]
    # 기타: 면적 기준
    return [ParkingInput(use=BuildingUse.FIRST_NEIGHBORHOOD,
                         floor_area=bld.total_floor_area, apply_seoul=True)]


def _auto_sewage_before(use_code: BuildingUseCode, bld: BuildingBasicInfo) -> list[SewageInput]:
    """기존 용도 기준 오수 입력 추정."""
    if use_code in (BuildingUseCode.MULTI_FAMILY, BuildingUseCode.SINGLE_HOUSE):
        persons = max(bld.floors_above * 2, 2)
        return [SewageInput(use=SewerUse.SINGLE_HOUSE, persons=persons)]
    return [SewageInput(use=SewerUse.FIRST_NEIGHBORHOOD, floor_area=bld.total_floor_area)]


def _estimate_basement_area(bld: BuildingBasicInfo) -> float:
    """
    지하층 면적 추정.
    건축물대장 totArea는 전층 합계이므로, 층당 평균 면적 × 지하층수로 추정.
    """
    total_floors = bld.floors_above + bld.floors_below
    if total_floors == 0:
        return 0.0
    area_per_floor = bld.total_floor_area / total_floors
    return round(area_per_floor * bld.floors_below, 2)


def _auto_parking_after(
    to_use_code: BuildingUseCode,
    bld: BuildingBasicInfo,
    from_use_code: BuildingUseCode,
) -> list[ParkingInput]:
    """
    변경 후 용도 주차 입력.
    근생 면적 기준: 지상층 전체 면적에서 지하층 추정 면적 제외.
    건물 전체가 근생으로 바뀌는 경우 지상 연면적 = total - basement.
    일부(하위층) 변경인 경우 변경 층 면적만 사용.
    """
    basement_area = _estimate_basement_area(bld)
    aboveground_area = max(0.0, bld.total_floor_area - basement_area)

    inputs = []

    if to_use_code in (BuildingUseCode.FIRST_NEIGHBORHOOD,
                       BuildingUseCode.SECOND_NEIGHBORHOOD):
        park_use = (BuildingUse.FIRST_NEIGHBORHOOD
                    if to_use_code == BuildingUseCode.FIRST_NEIGHBORHOOD
                    else BuildingUse.SECOND_NEIGHBORHOOD)

        if from_use_code in (BuildingUseCode.MULTI_FAMILY, BuildingUseCode.SINGLE_HOUSE):
            # 상위 절반 층은 주거 유지, 하위 절반 층은 근생으로 변경
            remaining_units = max(bld.floors_above // 2, 1)
            # 근생 변경 층 면적: 층당 평균 × 변경 층수 (전체의 절반)
            changed_floors = bld.floors_above - remaining_units
            area_per_ground_floor = (aboveground_area / bld.floors_above
                                     if bld.floors_above > 0 else aboveground_area)
            changed_area = area_per_ground_floor * max(changed_floors, 1)

            inputs.append(ParkingInput(
                use=BuildingUse.MULTI_FAMILY,
                units=remaining_units,
                apply_seoul=True,
            ))
        else:
            # 전체 용도변경: 지상 전체 면적 기준
            changed_area = aboveground_area

        # 근생 주차: 지상 시설면적 기준, 지하층 이미 제외된 상태
        inputs.append(ParkingInput(
            use=park_use,
            floor_area=changed_area,
            excluded_area=0.0,   # 이미 지상층 면적만 계산됨
            apply_seoul=True,
        ))

    elif to_use_code == BuildingUseCode.OFFICE:
        inputs.append(ParkingInput(
            use=BuildingUse.OFFICE,
            floor_area=aboveground_area,
            excluded_area=0.0,
            apply_seoul=True,
        ))
    else:
        inputs.append(ParkingInput(
            use=BuildingUse.FIRST_NEIGHBORHOOD,
            floor_area=aboveground_area,
            excluded_area=0.0,
            apply_seoul=True,
        ))

    return inputs


def _auto_sewage_after(
    to_use_code: BuildingUseCode,
    bld: BuildingBasicInfo,
    from_use_code: BuildingUseCode,
) -> list[SewageInput]:
    remaining_persons = max(bld.floors_above, 2)
    changed_area = bld.total_floor_area / 2
    inputs = []
    if from_use_code in (BuildingUseCode.MULTI_FAMILY, BuildingUseCode.SINGLE_HOUSE):
        inputs.append(SewageInput(use=SewerUse.SINGLE_HOUSE, persons=remaining_persons))
    if to_use_code == BuildingUseCode.FIRST_NEIGHBORHOOD:
        inputs.append(SewageInput(use=SewerUse.FIRST_NEIGHBORHOOD, floor_area=changed_area))
    elif to_use_code == BuildingUseCode.SECOND_NEIGHBORHOOD:
        inputs.append(SewageInput(use=SewerUse.SECOND_NEIGHBORHOOD, floor_area=changed_area))
    else:
        inputs.append(SewageInput(use=SewerUse.OFFICE, floor_area=changed_area))
    return inputs


# ── 메인 통합 조회 함수 ──────────────────────────────────────────────────────

@dataclass
class LookupResult:
    parcel: ParcelInfo
    zoning: ZoningInfo
    building: BuildingBasicInfo
    site: SiteInfoFull


def build_site_from_address(
    address: str,
    to_use_code: BuildingUseCode = BuildingUseCode.FIRST_NEIGHBORHOOD,
    to_use_str: str = "제1종근린생활시설",
    north_setback_m: Optional[float] = None,
    road_width_m: float = 6.0,
    adjacent_setback_m: float = 1.0,
    parking_provided: Optional[int] = None,
    designer: str = "",
    note: str = "",
) -> LookupResult:
    """
    주소 한 줄 입력 → API 자동 조회 → SiteInfoFull 조립.

    Parameters
    ----------
    address        : 조회할 주소 (지번 or 도로명)
    to_use_code    : 변경 후 용도 코드
    to_use_str     : 변경 후 용도 표시명
    north_setback_m: 정북 이격거리 실측값 (없으면 None → 검토 생략)
    road_width_m   : 접면 도로 폭 (현장 확인 필요, 기본 6m)
    parking_provided: 계획 주차대수 (None이면 자동 추정)
    """
    print("\n" + "="*60)
    print(f"  API 자동 조회 시작: {address}")
    print("="*60)

    # 1. VWorld: 주소 → 위경도 + PNU + 용도지역
    parcel, zoning = lookup_address(address)
    time.sleep(0.3)

    # 2. 건축물대장: PNU → 건물 정보
    print(f"\n[건축물대장] 조회 시작: PNU={parcel.pnu}")
    building = get_building_info(parcel.pnu, address)
    print(f"  → 대지면적: {building.site_area}㎡ / 연면적: {building.total_floor_area}㎡")
    print(f"  → {building.floors_above}층 / 높이: {building.height_m}m")
    print(f"  → 기존 용도: {building.main_use} / 사용승인: {building.construction_year}년")

    # 3. 용도 코드 추론
    from_use_code = _infer_use_code(building.main_use)
    from_use_str  = building.main_use or "다가구주택"
    zone_type     = _zone_str_to_type(zoning.zone_name_mapped)

    # 4. 주차·오수 자동 생성
    p_before = _auto_parking_before(from_use_code, building)
    p_after  = _auto_parking_after(to_use_code, building, from_use_code)
    s_before = _auto_sewage_before(from_use_code, building)
    s_after  = _auto_sewage_after(to_use_code, building, from_use_code)

    # 계획 주차대수 자동 추정 (지하 1층 전체를 주차로 가정)
    if parking_provided is None:
        floor_area_b1 = building.total_floor_area / (building.floors_above + building.floors_below) \
            if (building.floors_above + building.floors_below) > 0 \
            else building.total_floor_area / 4
        parking_provided = max(1, int(floor_area_b1 / 25))  # 25㎡/대 자주식 기준

    # 층당 바닥면적 = 연면적 / 지상층수
    floor_area_per_floor = (
        building.total_floor_area / building.floors_above
        if building.floors_above > 0
        else building.total_floor_area
    )

    # 건축면적 fallback (대지면적 × 0.5)
    footprint = building.building_coverage or (building.site_area * 0.5)

    site = SiteInfoFull(
        address=f"{building.address or address}",
        zone_type=zone_type,
        site_area=building.site_area or 0.0,
        road_width_m=road_width_m,
        building_footprint=footprint,
        total_floor_area=building.total_floor_area or 0.0,
        floor_area_per_floor=floor_area_per_floor,
        building_height_m=building.height_m,
        floors_above=building.floors_above,
        floors_below=building.floors_below,
        construction_year=building.construction_year,
        north_setback_m=north_setback_m,
        road_setback_m=0.0,
        adjacent_setback_m=adjacent_setback_m,
        from_use_code=from_use_code,
        to_use_code=to_use_code,
        from_use_str=from_use_str,
        to_use_str=to_use_str,
        parking_before=p_before,
        parking_after=p_after,
        parking_provided=parking_provided,
        sewage_before=s_before,
        sewage_after=s_after,
        has_sprinkler=False,
        both_sides_corridor=True,
        is_new_build=False,
        is_public=False,
        designer=designer,
        note=note or f"API 자동 조회 | VWorld 용도지역: {zoning.zone_name} | PNU: {parcel.pnu}",
    )

    return LookupResult(parcel=parcel, zoning=zoning, building=building, site=site)
