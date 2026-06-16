"""
법령 원문 기준 데이터 — 단일 진실 공급원 (Single Source of Truth)

모든 수치는 아래 법령을 1차 근거로 함:
- 건축법·시행령·시행규칙
- 국토의 계획 및 이용에 관한 법률·시행령
- 서울특별시 도시계획 조례 (건폐율·용적률)
- 서울특별시 주차장 조례 제17조·별표2 (주차)
- 서울특별시 건축 조례 제24~42조 (조경·공개공지·이격·일조)
- 주택건설기준 등에 관한 규정 제27조 (공동주택 주차)
- 주차장법 시행령 별표1
- 건축법 제57조·서울시조례 제40조 (대지분할)
- 건축법 제43조·서울시조례 제26조 (공개공지)
"""

from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# 1. 용도지역별 건폐율·용적률
#    근거: 서울특별시 도시계획 조례 제44조(건폐율), 제55조(용적률)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ZoneLimit:
    bcr: int            # 건폐율 상한 (%)
    far: int            # 용적률 상한 (%)
    far_historic: Optional[int] = None  # 역사도심 특별관리구역 상한
    notes: str = ""


ZONING_TABLE: dict[str, ZoneLimit] = {
    # 주거지역
    "제1종전용주거지역": ZoneLimit(bcr=50, far=100,
        notes="단독주택 중심, 공동주택(아파트) 불허 (조례 §44①1, §55①1)"),
    "제2종전용주거지역": ZoneLimit(bcr=40, far=120,
        notes="공동주택 4층 이하 허용 (조례 §44①2, §55①2)"),
    "제1종일반주거지역": ZoneLimit(bcr=60, far=150,
        notes="4층 이하 주택 중심 (조례 §44①3, §55①3)"),
    "제2종일반주거지역": ZoneLimit(bcr=60, far=200,
        notes="중층 공동주택 허용 (조례 §44①4, §55①4)"),
    "제3종일반주거지역": ZoneLimit(bcr=50, far=250,
        notes="고층 주거 허용 (조례 §44①5, §55①5)"),
    "준주거지역":        ZoneLimit(bcr=60, far=400,
        notes="주거+상업 혼합, 주거기능 보호 (조례 §44①6, §55①6)"),

    # 상업지역
    "중심상업지역": ZoneLimit(bcr=60, far=1000, far_historic=800,
        notes="도심·부도심 핵심상업 (조례 §44②1, §55②1); 역사도심 800%"),
    "일반상업지역": ZoneLimit(bcr=60, far=800,  far_historic=600,
        notes="일반 상업·업무 (조례 §44②2, §55②2); 역사도심 600%"),
    "근린상업지역": ZoneLimit(bcr=60, far=600,  far_historic=500,
        notes="근린 생활권 상업 (조례 §44②3, §55②3); 역사도심 500%"),
    "유통상업지역": ZoneLimit(bcr=60, far=600,  far_historic=500,
        notes="유통·물류 특화 (조례 §44②4, §55②4); 역사도심 500%"),

    # 공업지역
    "전용공업지역": ZoneLimit(bcr=60, far=200,
        notes="중화학·환경오염 업종 (조례 §44③1, §55③1)"),
    "일반공업지역": ZoneLimit(bcr=60, far=200,
        notes="일반 제조업 (조례 §44③2, §55③2)"),
    "준공업지역":   ZoneLimit(bcr=60, far=400,
        notes="도시형 공업·지식산업 (조례 §44③3, §55③3)"),

    # 녹지지역
    "보전녹지지역": ZoneLimit(bcr=20, far=50,
        notes="자연환경·산림 보전 (조례 §44④1, §55④1)"),
    "생산녹지지역": ZoneLimit(bcr=20, far=50,
        notes="농업·임업 생산 (조례 §44④2, §55④2)"),
    "자연녹지지역": ZoneLimit(bcr=20, far=50,
        notes="도시 녹지축 유지 (조례 §44④3, §55④3)"),

    # 관리지역 (도시 외곽, 참고)
    "보전관리지역": ZoneLimit(bcr=20, far=50),
    "생산관리지역": ZoneLimit(bcr=20, far=50),
    "계획관리지역": ZoneLimit(bcr=40, far=100),
}

# 별칭 매핑 (VWorld API 응답 → ZONING_TABLE 키)
ZONE_ALIAS: dict[str, str] = {
    "1종전용주거": "제1종전용주거지역",
    "2종전용주거": "제2종전용주거지역",
    "1종일반주거": "제1종일반주거지역",
    "2종일반주거": "제2종일반주거지역",
    "3종일반주거": "제3종일반주거지역",
    "준주거":      "준주거지역",
    "중심상업":    "중심상업지역",
    "일반상업":    "일반상업지역",
    "근린상업":    "근린상업지역",
    "유통상업":    "유통상업지역",
    "전용공업":    "전용공업지역",
    "일반공업":    "일반공업지역",
    "준공업":      "준공업지역",
    "보전녹지":    "보전녹지지역",
    "생산녹지":    "생산녹지지역",
    "자연녹지":    "자연녹지지역",
    # 상위 분류 fallback
    "주거지역":    "제2종일반주거지역",
    "상업지역":    "일반상업지역",
    "공업지역":    "준공업지역",
    "녹지지역":    "자연녹지지역",
}


def get_zone_limit(zone_name: str) -> Optional[ZoneLimit]:
    """용도지역명(전체 또는 약칭) → ZoneLimit. 없으면 None."""
    key = ZONE_ALIAS.get(zone_name, zone_name)
    return ZONING_TABLE.get(key)


# ══════════════════════════════════════════════════════════════════════════════
# 2. 주차 기준 — 시설면적당 대수
#    근거: 서울특별시 주차장 조례 제17조, 별표2
#    단위: ㎡/대 (해당 면적당 1대)
# ══════════════════════════════════════════════════════════════════════════════

# 시설 종류별 기준 면적 (㎡당 1대)
PARKING_TABLE: dict[str, int] = {
    "위락시설":             100,
    "문화및집회시설":        100,
    "종교시설":             100,
    "판매시설":             100,
    "운수시설":             100,
    "의료시설":             100,
    "운동시설":             100,
    "업무시설":             100,
    "방송통신시설_방송국":   100,
    "장례식장":             100,
    # ↓ 핵심 수정: 134㎡ → 200㎡ (서울시 주차장 조례 별표2)
    "제1종근린생활시설":     200,
    "제2종근린생활시설":     200,
    "숙박시설":             200,
    "수련시설":             350,
    "공장":                350,
    "발전시설":             350,
    "방송통신시설_기타":     350,
    "교정시설":             350,
    "관광휴게시설":         350,
    "창고시설":             400,
    "학생용기숙사":         400,
    "그밖의건축물":         300,
}

# 교육연구시설: 법정 200㎡, 서울 150㎡
PARKING_EDUCATION = {"법정": 200, "서울": 150}

# 문화·집회시설: 법정 100㎡, 서울 75㎡
PARKING_CULTURE = {"법정": 100, "서울": 75}


# ══════════════════════════════════════════════════════════════════════════════
# 3. 단독주택 주차 기준
#    근거: 서울시 주차장 조례 별표2 (다가구주택 제외 단독주택)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SingleHouseParkingRule:
    """단독주택(다가구 제외) 주차 산정 규칙."""
    floor_area_min: float       # 적용 최소 연면적 (㎡)
    base_spaces: int            # 기본 대수
    excess_area: float          # 초과분 계산 기준 면적 (㎡)
    excess_base: float          # 초과분 기준 연면적 시작점
    notes: str


SINGLE_HOUSE_PARKING = SingleHouseParkingRule(
    floor_area_min=50,
    base_spaces=1,
    excess_area=100,        # 150㎡ 초과분 100㎡당 1대 추가
    excess_base=150,
    notes=(
        "50㎡ 이하: 주차 의무 없음. "
        "50㎡~150㎡: 1대. "
        "150㎡ 초과: 1대 + (초과면적 / 100㎡) 반올림 추가. "
        "(서울시 주차장 조례 별표2)"
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 4. 다가구주택·공동주택 주차 기준
#    근거: 주택건설기준 등에 관한 규정 제27조 / 서울시 주차장 조례 별표2
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MultiHouseParkingTier:
    area_max: float         # 전용면적 상한 (㎡), None=초과 없음
    spaces_per_unit: float  # 세대당 주차대수
    notes: str


MULTI_HOUSE_PARKING: list[MultiHouseParkingTier] = [
    MultiHouseParkingTier(
        area_max=30,
        spaces_per_unit=0.5,
        notes="전용 30㎡ 이하 → 0.5대/세대",
    ),
    MultiHouseParkingTier(
        area_max=60,
        spaces_per_unit=0.8,
        notes="전용 30㎡ 초과~60㎡ 이하 → 0.8대/세대",
    ),
    MultiHouseParkingTier(
        area_max=85,
        spaces_per_unit=1.0,
        notes="전용 60㎡ 초과~85㎡ 이하 → 1.0대/세대",
    ),
    MultiHouseParkingTier(
        area_max=float("inf"),
        spaces_per_unit=1.0,
        notes="전용 85㎡ 초과 → 1.0대/세대 (지자체 조례 가산 가능)",
    ),
]


def get_multi_house_parking_rate(exclusive_area_m2: float) -> float:
    """전용면적(㎡) → 세대당 주차대수."""
    for tier in MULTI_HOUSE_PARKING:
        if exclusive_area_m2 <= tier.area_max:
            return tier.spaces_per_unit
    return 1.0


# ══════════════════════════════════════════════════════════════════════════════
# 5. 정북일조 이격거리
#    근거: 서울시 건축조례 제42조 (건축법 시행령 §86①보다 강화)
#    ※ 서울시: 기준높이 9m (건축법 자체는 10m)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SunlightRegulation:
    applicable_zones: list[str]
    base_height_m: float        # 이격거리 구간 전환 높이 (서울시 9m)
    setback_below_base: float   # 기준높이 이하 고정 이격거리 (m)
    setback_ratio_above: float  # 기준높이 초과 시 높이 대비 배수
    basis: str


SUNLIGHT_REGULATION = SunlightRegulation(
    applicable_zones=[
        "제1종전용주거지역",
        "제2종전용주거지역",
        "제1종일반주거지역",
        "제2종일반주거지역",
        "제3종일반주거지역",
    ],
    base_height_m=9.0,
    setback_below_base=1.5,
    setback_ratio_above=0.5,
    basis=(
        "서울시 건축조례 제42조. "
        "9m 이하: 정북방향 1.5m 이상 이격. "
        "9m 초과: 해당 높이의 1/2 이상 이격."
    ),
)


# ══════════════════════════════════════════════════════════════════════════════
# 6. 대지안의 공지 (이격거리)
#    근거: 서울시 건축조례 제25조
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class SetbackRequirement:
    adjacent_boundary_m: float  # 인접대지경계선 이격 (m)
    road_boundary_m: float      # 도로경계선 이격 (m)
    notes: str = ""


SETBACK_TABLE: dict[str, SetbackRequirement] = {
    "다중이용건축물": SetbackRequirement(
        adjacent_boundary_m=6.0,
        road_boundary_m=3.0,
        notes="문화집회·판매·의료·운수 등 다중이용, 6m 이내 조례 적용",
    ),
    "공동주택_전용주거지역": SetbackRequirement(
        adjacent_boundary_m=1.5,
        road_boundary_m=1.0,
        notes="전용주거지역 내 공동주택",
    ),
    "공동주택_일반준주거지역": SetbackRequirement(
        adjacent_boundary_m=1.0,
        road_boundary_m=1.0,
        notes="일반주거·준주거지역 내 공동주택",
    ),
    "일반건축물_1000이상": SetbackRequirement(
        adjacent_boundary_m=1.0,
        road_boundary_m=1.0,
        notes="연면적 1,000㎡ 이상 일반 건축물",
    ),
    "단독주택": SetbackRequirement(
        adjacent_boundary_m=0.5,
        road_boundary_m=0.5,
        notes="단독주택, 다가구주택",
    ),
    "그외": SetbackRequirement(
        adjacent_boundary_m=0.5,
        road_boundary_m=0.5,
        notes="그 밖의 건축물",
    ),
}


# ══════════════════════════════════════════════════════════════════════════════
# 7. 대지분할 최소면적
#    근거: 건축법 제57조, 서울시 건축조례 제40조
# ══════════════════════════════════════════════════════════════════════════════

LAND_DIVISION_MIN: dict[str, int] = {
    "주거지역": 60,
    "상업지역": 150,
    "공업지역": 150,
    "녹지지역": 200,
    "그외":    60,
}


def get_land_division_min(zone_name: str) -> int:
    """용도지역명 → 대지분할 최소면적(㎡)."""
    if "주거" in zone_name:
        return LAND_DIVISION_MIN["주거지역"]
    if "상업" in zone_name:
        return LAND_DIVISION_MIN["상업지역"]
    if "공업" in zone_name:
        return LAND_DIVISION_MIN["공업지역"]
    if "녹지" in zone_name:
        return LAND_DIVISION_MIN["녹지지역"]
    return LAND_DIVISION_MIN["그외"]


# ══════════════════════════════════════════════════════════════════════════════
# 8. 조경 의무
#    근거: 서울시 건축조례 제24조
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LandscapeRequirement:
    site_area_min: float    # 의무 대상 최소 대지면적 (㎡)
    tiers: list[tuple]      # (대지면적 상한, 조경 비율%) — 상한 None = 초과 없음


LANDSCAPE_TABLE = LandscapeRequirement(
    site_area_min=200,
    tiers=[
        (1000,  5),     # 200~1,000㎡ 미만: 5%
        (2000, 10),     # 1,000~2,000㎡ 미만: 10%
        (None, 15),     # 2,000㎡ 이상: 15%
    ],
)


def get_landscape_ratio(site_area_m2: float) -> Optional[int]:
    """대지면적(㎡) → 조경 의무 비율(%). 의무 없으면 None."""
    if site_area_m2 < LANDSCAPE_TABLE.site_area_min:
        return None
    for area_limit, ratio in LANDSCAPE_TABLE.tiers:
        if area_limit is None or site_area_m2 < area_limit:
            return ratio
    return 15


# ══════════════════════════════════════════════════════════════════════════════
# 9. 공개공지
#    근거: 건축법 제43조, 서울시 건축조례 제26조
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PublicSpaceRule:
    applicable_zones: list[str]
    min_floor_area_m2: int      # 의무 대상 최소 연면적
    ratio_min: float            # 공개공지 면적 비율 최소 (%)
    ratio_max: float            # 공개공지 면적 비율 최대 (%)
    far_incentive: float        # 용적률 인센티브 배수
    height_incentive: float     # 높이 인센티브 배수
    basis: str


PUBLIC_SPACE_TABLE = PublicSpaceRule(
    applicable_zones=["일반주거지역", "준주거지역", "상업지역", "준공업지역"],
    min_floor_area_m2=5000,
    ratio_min=5.0,
    ratio_max=10.0,
    far_incentive=1.2,
    height_incentive=1.2,
    basis="건축법 §43, 서울시 건축조례 §26. 연면적 5,000㎡ 이상 해당 지역 건축물 의무.",
)
