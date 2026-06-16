"""
용도지역별 건폐율·용적률 검토
근거: legal_reference.ZONING_TABLE (서울시 도시계획조례 §44·§55)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .legal_reference import ZONING_TABLE, ZoneLimit, get_zone_limit


# ZoneType enum — 기존 코드 호환용 (report.py 등에서 참조)
class ZoneType(str, Enum):
    FIRST_EXCLUSIVE_RESIDENTIAL  = "제1종전용주거지역"
    SECOND_EXCLUSIVE_RESIDENTIAL = "제2종전용주거지역"
    FIRST_GENERAL_RESIDENTIAL    = "제1종일반주거지역"
    SECOND_GENERAL_RESIDENTIAL   = "제2종일반주거지역"
    THIRD_GENERAL_RESIDENTIAL    = "제3종일반주거지역"
    QUASI_RESIDENTIAL            = "준주거지역"
    CENTRAL_COMMERCIAL           = "중심상업지역"
    GENERAL_COMMERCIAL           = "일반상업지역"
    NEIGHBORHOOD_COMMERCIAL      = "근린상업지역"
    DISTRIBUTION_COMMERCIAL      = "유통상업지역"
    EXCLUSIVE_INDUSTRIAL         = "전용공업지역"
    GENERAL_INDUSTRIAL           = "일반공업지역"
    QUASI_INDUSTRIAL             = "준공업지역"
    CONSERVATION_GREEN           = "보전녹지지역"
    PRODUCTION_GREEN             = "생산녹지지역"
    NATURAL_GREEN                = "자연녹지지역"


@dataclass
class ZoneRegulation:
    """기존 코드 호환용 래퍼 — 내부 값은 legal_reference에서 가져온다."""
    zone: ZoneType
    building_coverage_ratio: float
    floor_area_ratio: float
    bcr_min: Optional[float] = None
    far_min: Optional[float] = None
    notes: str = ""


def _make_regulation(zone: ZoneType) -> ZoneRegulation:
    ref = ZONING_TABLE.get(zone.value)
    if ref is None:
        raise KeyError(f"ZONING_TABLE에 '{zone.value}' 없음")
    return ZoneRegulation(
        zone=zone,
        building_coverage_ratio=float(ref.bcr),
        floor_area_ratio=float(ref.far),
        notes=ref.notes,
    )


# 기존 코드에서 ZONE_TABLE[ZoneType.*] 로 접근하는 패턴 지원
ZONE_TABLE: dict[ZoneType, ZoneRegulation] = {
    z: _make_regulation(z) for z in ZoneType
}


def get_zone_regulation(zone: ZoneType) -> ZoneRegulation:
    return ZONE_TABLE[zone]


def check_bcr(zone: ZoneType, site_area: float, building_footprint: float) -> dict:
    """건폐율 검토 (서울시 도시계획조례 §44 기준)."""
    reg = get_zone_regulation(zone)
    actual_bcr = (building_footprint / site_area) * 100
    limit = reg.building_coverage_ratio
    return {
        "site_area": site_area,
        "building_footprint": building_footprint,
        "actual_bcr": round(actual_bcr, 2),
        "limit_bcr": limit,
        "pass": actual_bcr <= limit,
        "margin": round(limit - actual_bcr, 2),
    }


def check_far(zone: ZoneType, site_area: float, total_floor_area: float) -> dict:
    """용적률 검토 (서울시 도시계획조례 §55 기준, 지하층·주차면적 제외는 호출 측에서 적용)."""
    reg = get_zone_regulation(zone)
    actual_far = (total_floor_area / site_area) * 100
    limit = reg.floor_area_ratio
    return {
        "site_area": site_area,
        "total_floor_area": total_floor_area,
        "actual_far": round(actual_far, 2),
        "limit_far": limit,
        "pass": actual_far <= limit,
        "margin": round(limit - actual_far, 2),
    }
