"""
용도지역별 건폐율 / 용적률 테이블
근거: 국토의 계획 및 이용에 관한 법률 시행령 별표
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ZoneType(str, Enum):
    # 주거지역
    FIRST_EXCLUSIVE_RESIDENTIAL = "제1종전용주거지역"
    SECOND_EXCLUSIVE_RESIDENTIAL = "제2종전용주거지역"
    FIRST_GENERAL_RESIDENTIAL = "제1종일반주거지역"
    SECOND_GENERAL_RESIDENTIAL = "제2종일반주거지역"
    THIRD_GENERAL_RESIDENTIAL = "제3종일반주거지역"
    QUASI_RESIDENTIAL = "준주거지역"

    # 상업지역
    CENTRAL_COMMERCIAL = "중심상업지역"
    GENERAL_COMMERCIAL = "일반상업지역"
    NEIGHBORHOOD_COMMERCIAL = "근린상업지역"
    DISTRIBUTION_COMMERCIAL = "유통상업지역"

    # 공업지역
    EXCLUSIVE_INDUSTRIAL = "전용공업지역"
    GENERAL_INDUSTRIAL = "일반공업지역"
    QUASI_INDUSTRIAL = "준공업지역"

    # 녹지지역
    CONSERVATION_GREEN = "보전녹지지역"
    PRODUCTION_GREEN = "생산녹지지역"
    NATURAL_GREEN = "자연녹지지역"


@dataclass
class ZoneRegulation:
    zone: ZoneType
    building_coverage_ratio: float   # 건폐율 (%, 최대)
    floor_area_ratio: float           # 용적률 (%, 최대)
    # 지자체 조례로 낮출 수 있는 하한
    bcr_min: Optional[float] = None
    far_min: Optional[float] = None
    notes: str = ""


ZONE_TABLE: dict[ZoneType, ZoneRegulation] = {
    # ── 주거지역 ──────────────────────────────────────────────────────────────
    ZoneType.FIRST_EXCLUSIVE_RESIDENTIAL: ZoneRegulation(
        zone=ZoneType.FIRST_EXCLUSIVE_RESIDENTIAL,
        building_coverage_ratio=50,
        floor_area_ratio=100,
        far_min=50,
        notes="단독주택 중심, 공동주택(아파트) 불허",
    ),
    ZoneType.SECOND_EXCLUSIVE_RESIDENTIAL: ZoneRegulation(
        zone=ZoneType.SECOND_EXCLUSIVE_RESIDENTIAL,
        building_coverage_ratio=50,
        floor_area_ratio=150,
        far_min=50,
        notes="공동주택(4층 이하) 허용",
    ),
    ZoneType.FIRST_GENERAL_RESIDENTIAL: ZoneRegulation(
        zone=ZoneType.FIRST_GENERAL_RESIDENTIAL,
        building_coverage_ratio=60,
        floor_area_ratio=200,
        far_min=100,
        notes="4층 이하 주택 중심",
    ),
    ZoneType.SECOND_GENERAL_RESIDENTIAL: ZoneRegulation(
        zone=ZoneType.SECOND_GENERAL_RESIDENTIAL,
        building_coverage_ratio=60,
        floor_area_ratio=250,
        far_min=100,
        notes="중층 아파트 허용",
    ),
    ZoneType.THIRD_GENERAL_RESIDENTIAL: ZoneRegulation(
        zone=ZoneType.THIRD_GENERAL_RESIDENTIAL,
        building_coverage_ratio=50,
        floor_area_ratio=300,
        far_min=100,
        notes="고층 주거 허용",
    ),
    ZoneType.QUASI_RESIDENTIAL: ZoneRegulation(
        zone=ZoneType.QUASI_RESIDENTIAL,
        building_coverage_ratio=70,
        floor_area_ratio=500,
        far_min=200,
        notes="주거+상업 혼합, 주거기능 보호",
    ),

    # ── 상업지역 ──────────────────────────────────────────────────────────────
    ZoneType.CENTRAL_COMMERCIAL: ZoneRegulation(
        zone=ZoneType.CENTRAL_COMMERCIAL,
        building_coverage_ratio=90,
        floor_area_ratio=1500,
        far_min=400,
        notes="도심·부도심 업무·상업 핵심",
    ),
    ZoneType.GENERAL_COMMERCIAL: ZoneRegulation(
        zone=ZoneType.GENERAL_COMMERCIAL,
        building_coverage_ratio=80,
        floor_area_ratio=1300,
        far_min=300,
        notes="일반 상업·업무 기능",
    ),
    ZoneType.NEIGHBORHOOD_COMMERCIAL: ZoneRegulation(
        zone=ZoneType.NEIGHBORHOOD_COMMERCIAL,
        building_coverage_ratio=70,
        floor_area_ratio=900,
        far_min=200,
        notes="근린 생활권 상업",
    ),
    ZoneType.DISTRIBUTION_COMMERCIAL: ZoneRegulation(
        zone=ZoneType.DISTRIBUTION_COMMERCIAL,
        building_coverage_ratio=80,
        floor_area_ratio=1100,
        far_min=200,
        notes="유통·물류 특화",
    ),

    # ── 공업지역 ──────────────────────────────────────────────────────────────
    ZoneType.EXCLUSIVE_INDUSTRIAL: ZoneRegulation(
        zone=ZoneType.EXCLUSIVE_INDUSTRIAL,
        building_coverage_ratio=70,
        floor_area_ratio=300,
        far_min=150,
        notes="중화학·환경오염 업종 집중",
    ),
    ZoneType.GENERAL_INDUSTRIAL: ZoneRegulation(
        zone=ZoneType.GENERAL_INDUSTRIAL,
        building_coverage_ratio=70,
        floor_area_ratio=350,
        far_min=150,
        notes="일반 제조업",
    ),
    ZoneType.QUASI_INDUSTRIAL: ZoneRegulation(
        zone=ZoneType.QUASI_INDUSTRIAL,
        building_coverage_ratio=70,
        floor_area_ratio=400,
        far_min=150,
        notes="도시형 공업·지식산업",
    ),

    # ── 녹지지역 ──────────────────────────────────────────────────────────────
    ZoneType.CONSERVATION_GREEN: ZoneRegulation(
        zone=ZoneType.CONSERVATION_GREEN,
        building_coverage_ratio=20,
        floor_area_ratio=80,
        far_min=50,
        notes="자연환경·산림 보전",
    ),
    ZoneType.PRODUCTION_GREEN: ZoneRegulation(
        zone=ZoneType.PRODUCTION_GREEN,
        building_coverage_ratio=20,
        floor_area_ratio=100,
        far_min=50,
        notes="농업·임업 생산",
    ),
    ZoneType.NATURAL_GREEN: ZoneRegulation(
        zone=ZoneType.NATURAL_GREEN,
        building_coverage_ratio=20,
        floor_area_ratio=100,
        far_min=50,
        notes="도시 녹지축 유지",
    ),
}


def get_zone_regulation(zone: ZoneType) -> ZoneRegulation:
    return ZONE_TABLE[zone]


def check_bcr(zone: ZoneType, site_area: float, building_footprint: float) -> dict:
    """건폐율 검토."""
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
    """용적률 검토 (지하층·주차장 면적 제외는 별도 적용 필요)."""
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
