"""
용도변경 절차 자동 판단
근거: 건축법 제19조 + 건축법 시행령 별표1 / 별표2
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── 건축물 용도 28가지 (건축법 시행령 별표1) ──────────────────────────────

class BuildingUseCode(str, Enum):
    # 1군: 자동차 관련 시설군
    CAR_FACILITY = "1-자동차관련시설"

    # 2군: 산업 등 시설군
    FACTORY = "2-공장"
    WAREHOUSE = "2-창고시설"
    HAZARDOUS = "2-위험물저장처리시설"
    BROADCASTING = "2-방송통신시설"
    WASTE = "2-묘지관련시설"

    # 3군: 전기통신 시설군 (건축법 별표1 3번)
    POWER_TELECOM = "3-발전시설"

    # 4군: 문화 및 집회 시설군
    CULTURE_ASSEMBLY = "4-문화및집회시설"
    RELIGION = "4-종교시설"
    SPORTS = "4-운동시설"

    # 5군: 영업 시설군
    RETAIL = "5-판매시설"
    TRANSPORTATION = "5-운수시설"
    ACCOMMODATION = "5-숙박시설"
    ENTERTAINMENT = "5-위락시설"

    # 6군: 교육 및 복지 시설군
    EDUCATION = "6-교육연구시설"
    WELFARE = "6-노유자시설"
    MEDICAL = "6-의료시설"
    TRAINING = "6-수련시설"
    CEMETERY = "6-묘지관련시설"

    # 7군: 근린생활 시설군
    FIRST_NEIGHBORHOOD = "7-제1종근린생활시설"
    SECOND_NEIGHBORHOOD = "7-제2종근린생활시설"

    # 8군: 주거업무 시설군 (단독주택·공동주택·업무시설·교정및군사시설)
    SINGLE_HOUSE = "8-단독주택"
    MULTI_HOUSE = "8-다중주택"
    MULTI_FAMILY = "8-다가구주택"
    APARTMENT = "8-공동주택"
    QUASI_RESIDENTIAL = "8-준주거복합"
    OFFICE = "8-업무시설"       # 업무시설은 주거업무시설군(8군) — 건축법 시행령 별표1의2

    # 9군: 그 밖의 시설군
    MISC_FACILITY = "9-기타시설"


# 시설군 번호 매핑 (1~10, 숫자가 클수록 상위군)
FACILITY_GROUP: dict[BuildingUseCode, int] = {
    BuildingUseCode.CAR_FACILITY: 1,

    BuildingUseCode.FACTORY: 2,
    BuildingUseCode.WAREHOUSE: 2,
    BuildingUseCode.HAZARDOUS: 2,
    BuildingUseCode.BROADCASTING: 2,
    BuildingUseCode.WASTE: 2,

    BuildingUseCode.POWER_TELECOM: 3,

    BuildingUseCode.CULTURE_ASSEMBLY: 4,
    BuildingUseCode.RELIGION: 4,
    BuildingUseCode.SPORTS: 4,

    BuildingUseCode.RETAIL: 5,
    BuildingUseCode.TRANSPORTATION: 5,
    BuildingUseCode.ACCOMMODATION: 5,
    BuildingUseCode.ENTERTAINMENT: 5,

    BuildingUseCode.EDUCATION: 6,
    BuildingUseCode.WELFARE: 6,
    BuildingUseCode.MEDICAL: 6,
    BuildingUseCode.TRAINING: 6,
    BuildingUseCode.CEMETERY: 6,

    BuildingUseCode.FIRST_NEIGHBORHOOD: 7,
    BuildingUseCode.SECOND_NEIGHBORHOOD: 7,

    BuildingUseCode.SINGLE_HOUSE: 8,
    BuildingUseCode.MULTI_HOUSE: 8,
    BuildingUseCode.MULTI_FAMILY: 8,
    BuildingUseCode.APARTMENT: 8,
    BuildingUseCode.QUASI_RESIDENTIAL: 8,
    BuildingUseCode.OFFICE: 8,          # 주거업무시설군 — 건축법 시행령 별표1의2 §8

    BuildingUseCode.MISC_FACILITY: 9,   # 그 밖의 시설군
}


class ChangeCategory(str, Enum):
    PERMIT = "허가"               # 건축허가
    REPORT = "신고"               # 용도변경 신고
    RECORD = "기재변경"            # 건축물대장 기재사항 변경
    NOT_APPLICABLE = "해당없음"


@dataclass
class UseChangeProcedure:
    from_use: BuildingUseCode
    to_use: BuildingUseCode
    category: ChangeCategory
    reason: str
    notes: str = ""


def determine_use_change(
    from_use: BuildingUseCode,
    to_use: BuildingUseCode,
) -> UseChangeProcedure:
    """
    용도변경 절차 자동 판단.

    건축법 제19조:
    - 상위군 → 하위군: 허가 (군 번호 큰 쪽이 상위)
    - 하위군 → 상위군: 신고
    - 동일군 내: 기재변경 (일부 예외 있음)
    - 동일 용도: 해당없음

    ※ 시설군 번호가 클수록 상위군(주거 8, 업무 9 등)
       → 상위(큰 번호) → 하위(작은 번호) 변경 = 허가
       → 하위 → 상위 변경 = 신고
    """
    if from_use == to_use:
        return UseChangeProcedure(
            from_use=from_use,
            to_use=to_use,
            category=ChangeCategory.NOT_APPLICABLE,
            reason="동일 용도로 용도변경 불필요",
        )

    g_from = FACILITY_GROUP[from_use]
    g_to = FACILITY_GROUP[to_use]

    if g_from == g_to:
        return UseChangeProcedure(
            from_use=from_use,
            to_use=to_use,
            category=ChangeCategory.RECORD,
            reason=f"동일 시설군({g_from}군) 내 변경 → 건축물대장 기재사항 변경",
            notes="동일군 내라도 일부 용도(위락·숙박 등)는 허가 필요 여부 별도 확인",
        )
    elif g_from > g_to:
        # 상위군 → 하위군 (예: 주거8 → 근린생활7)
        return UseChangeProcedure(
            from_use=from_use,
            to_use=to_use,
            category=ChangeCategory.PERMIT,
            reason=f"상위군({g_from}군) → 하위군({g_to}군) 변경 → 건축허가 필요",
            notes="구조·설비·피난 기준 재검토 필수",
        )
    else:
        # 하위군 → 상위군 (예: 근린생활7 → 업무9)
        return UseChangeProcedure(
            from_use=from_use,
            to_use=to_use,
            category=ChangeCategory.REPORT,
            reason=f"하위군({g_from}군) → 상위군({g_to}군) 변경 → 신고",
            notes="신고 후 건축물대장 정리 필요",
        )


# ── 제1종/2종 근린생활시설 업종 세분류 ───────────────────────────────────

class NeighborhoodBusinessType(str, Enum):
    # 제1종 근린생활시설
    SMALL_MARKET = "슈퍼마켓·일용품점 (1종, 1,000㎡ 미만)"
    BAKERY_LAUNDRY = "세탁소·이용원·미용원·목욕장 (1종)"
    MEDICAL_CLINIC = "의원·치과·한의원·조산원 (1종)"
    COMMUNITY_HALL = "마을회관·공중화장실·대피소 (1종)"
    RELIGIOUS_SMALL = "종교집회장 (1종, 500㎡ 미만)"
    CHILDCARE = "어린이집·공부방·독서실 (1종)"
    POSTAL = "우체국·금융업소 (1종)"
    NEIGHBORHOOD_OFFICE = "동사무소·경찰지구대·소방서 (1종)"

    # 제2종 근린생활시설
    PC_ROOM = "PC방·게임제공업소 (2종)"
    KARAOKE = "노래연습장 (2종)"
    GENERAL_RESTAURANT = "일반음식점 (2종)"
    FAST_FOOD = "휴게음식점·제과점 (1종, 300㎡ 미만)"
    ACADEMY = "학원 (2종, 500㎡ 미만)"
    SPORTS_FACILITY = "체력단련장·당구장 (2종)"
    REPAIR_SHOP = "수리점·세탁소 500㎡ 이상 (2종)"
    PHOTO_STUDIO = "사진관·표구점 (2종)"
    SHOWROOM = "제조업소·수리점 (2종, 500㎡ 미만)"
    BANK_LARGE = "금융업소·사무소 (2종, 500㎡ 이상)"
    FUNERAL = "장례식장 (2종)"
    PRINTING = "인쇄소 (2종)"


@dataclass
class NeighborhoodClassResult:
    business_type: NeighborhoodBusinessType
    classification: str           # "제1종" or "제2종"
    area_limit: Optional[float]   # 면적 상한 (㎡), None이면 제한 없음
    applicable: bool              # 해당 면적에서 분류 적합 여부
    note: str = ""


# 업종별 제1종/2종 기준 + 면적 임계값
NEIGHBORHOOD_RULES: dict[NeighborhoodBusinessType, dict] = {
    NeighborhoodBusinessType.SMALL_MARKET:     {"class": "제1종", "area_limit": 1000},
    NeighborhoodBusinessType.BAKERY_LAUNDRY:   {"class": "제1종", "area_limit": None},
    NeighborhoodBusinessType.MEDICAL_CLINIC:   {"class": "제1종", "area_limit": None},
    NeighborhoodBusinessType.COMMUNITY_HALL:   {"class": "제1종", "area_limit": None},
    NeighborhoodBusinessType.RELIGIOUS_SMALL:  {"class": "제1종", "area_limit": 500},
    NeighborhoodBusinessType.CHILDCARE:        {"class": "제1종", "area_limit": None},
    NeighborhoodBusinessType.POSTAL:           {"class": "제1종", "area_limit": None},
    NeighborhoodBusinessType.NEIGHBORHOOD_OFFICE: {"class": "제1종", "area_limit": None},

    NeighborhoodBusinessType.PC_ROOM:          {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.KARAOKE:          {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.GENERAL_RESTAURANT: {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.FAST_FOOD:        {"class": "제1종", "area_limit": 300},
    NeighborhoodBusinessType.ACADEMY:          {"class": "제2종", "area_limit": 500},
    NeighborhoodBusinessType.SPORTS_FACILITY:  {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.REPAIR_SHOP:      {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.PHOTO_STUDIO:     {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.SHOWROOM:         {"class": "제2종", "area_limit": 500},
    NeighborhoodBusinessType.BANK_LARGE:       {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.FUNERAL:          {"class": "제2종", "area_limit": None},
    NeighborhoodBusinessType.PRINTING:         {"class": "제2종", "area_limit": None},
}


def classify_neighborhood(
    biz_type: NeighborhoodBusinessType,
    floor_area: float,
) -> NeighborhoodClassResult:
    """업종·면적 기준으로 1종/2종 근생 분류."""
    rule = NEIGHBORHOOD_RULES[biz_type]
    cls = rule["class"]
    limit = rule["area_limit"]

    if limit and floor_area > limit:
        # 면적 초과 → 상위 종으로 전환 또는 별도 용도
        return NeighborhoodClassResult(
            business_type=biz_type,
            classification=cls,
            area_limit=limit,
            applicable=False,
            note=f"바닥면적 {floor_area}㎡ > 기준면적 {limit}㎡ → {cls} 초과, 상위 용도 또는 2종 재분류 필요",
        )

    return NeighborhoodClassResult(
        business_type=biz_type,
        classification=cls,
        area_limit=limit,
        applicable=True,
        note=f"{cls}근린생활시설 해당" + (f" (면적 {floor_area}㎡ / 기준 {limit}㎡ 이하)" if limit else ""),
    )
