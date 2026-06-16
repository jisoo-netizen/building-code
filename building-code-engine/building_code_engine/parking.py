"""
주차대수 산정 (용도변경 전·후 비교 포함)
근거: 서울특별시 주차장 설치 및 관리 조례 제17조·별표2 (2025.9.29 개정)
      주택건설기준 등에 관한 규정 제27조 (다가구·공동주택 세대별)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .legal_reference import (
    PARKING_TABLE,
    SINGLE_HOUSE_PARKING,
    MULTI_HOUSE_PARKING,
    get_multi_house_parking_rate,
)


# ---------------------------------------------------------------------------
# 소수점 처리 (별표2 비고 6·7)
# 0.5 이상 → 올림(천장), 0.5 미만 → 버림(바닥)
# ---------------------------------------------------------------------------
def _round_half_up(x: float) -> int:
    """비고6: 소수점 ≥ 0.5 → 올림, < 0.5 → 버림."""
    return math.floor(x + 0.5)


# ---------------------------------------------------------------------------
# 건물 용도 열거형
# ---------------------------------------------------------------------------
class BuildingUse(str, Enum):
    APARTMENT          = "공동주택(아파트·연립·다세대)"
    SINGLE_HOUSE       = "단독주택"
    MULTI_FAMILY       = "다가구주택"
    FIRST_NEIGHBORHOOD = "제1종근린생활시설"
    SECOND_NEIGHBORHOOD= "제2종근린생활시설"
    OFFICE             = "업무시설"
    OFFICE_PUBLIC      = "업무시설(공공)"
    RETAIL             = "판매시설"
    HOTEL              = "숙박시설"
    MEDICAL            = "의료시설"
    EDUCATION          = "교육연구시설"
    CULTURE_ASSEMBLY   = "문화·집회시설"
    FACTORY            = "공장"
    WAREHOUSE          = "창고시설"
    ENTERTAINMENT      = "위락시설"
    RELIGION           = "종교시설"
    TRANSPORT          = "운수시설"
    SPORTS             = "운동시설"
    BROADCAST_STATION  = "방송통신시설(방송국)"
    DATA_CENTER        = "방송통신시설(데이터센터)"
    FUNERAL            = "장례식장"
    TRAINING           = "수련시설"
    POWER_PLANT        = "발전시설"


# ---------------------------------------------------------------------------
# 면제 대상 (별표2 비고 1)
# 해당 용도는 주차대수 산정 불필요
# ---------------------------------------------------------------------------
EXEMPT_USES: set[str] = {
    "변전소",
    "양수장",
    "정수장",
    "대피소",
    "공중화장실",
    "수도원",
    "수녀원",
    "제실",
    "사당",
    "정신병원",
    "요양병원",
    "격리병원",
}


# ---------------------------------------------------------------------------
# 표준 기준 (별표2)
# ---------------------------------------------------------------------------
@dataclass
class ParkingStandard:
    use: BuildingUse
    area_per_space: float           # 기준 면적 ㎡/대 (0이면 단위 기준)
    area_per_space_seoul: Optional[float] = None  # 서울 조례 완화 기준
    unit_based: bool = False        # True: 세대·객실 등 단위 기준
    units_per_space: Optional[float] = None
    notes: str = ""


PARKING_STANDARDS: dict[BuildingUse, ParkingStandard] = {
    # 별표2 제1호 — 위락시설: 67㎡당 1대
    BuildingUse.ENTERTAINMENT: ParkingStandard(
        use=BuildingUse.ENTERTAINMENT,
        area_per_space=PARKING_TABLE["위락시설"],
        notes=f"위락시설: {PARKING_TABLE['위락시설']}㎡당 1대 (별표2 제1호)",
    ),

    # 별표2 제2호 — 100㎡당 1대
    BuildingUse.CULTURE_ASSEMBLY: ParkingStandard(
        use=BuildingUse.CULTURE_ASSEMBLY,
        area_per_space=PARKING_TABLE["문화및집회시설"],
        notes=f"문화·집회: {PARKING_TABLE['문화및집회시설']}㎡당 1대 (관람장 제외·별표2 제2호)",
    ),
    BuildingUse.RELIGION: ParkingStandard(
        use=BuildingUse.RELIGION,
        area_per_space=PARKING_TABLE["종교시설"],
        notes=f"종교: {PARKING_TABLE['종교시설']}㎡당 1대 (수도원·수녀원·제실·사당 면제·별표2 제2호)",
    ),
    BuildingUse.RETAIL: ParkingStandard(
        use=BuildingUse.RETAIL,
        area_per_space=PARKING_TABLE["판매시설"],
        notes=f"판매: {PARKING_TABLE['판매시설']}㎡당 1대 (별표2 제2호)",
    ),
    BuildingUse.TRANSPORT: ParkingStandard(
        use=BuildingUse.TRANSPORT,
        area_per_space=PARKING_TABLE["운수시설"],
        notes=f"운수: {PARKING_TABLE['운수시설']}㎡당 1대 (별표2 제2호)",
    ),
    BuildingUse.MEDICAL: ParkingStandard(
        use=BuildingUse.MEDICAL,
        area_per_space=PARKING_TABLE["의료시설"],
        notes=f"의료: {PARKING_TABLE['의료시설']}㎡당 1대 (정신·요양·격리병원 제외·별표2 제2호)",
    ),
    BuildingUse.SPORTS: ParkingStandard(
        use=BuildingUse.SPORTS,
        area_per_space=PARKING_TABLE["운동시설"],
        notes=f"운동: {PARKING_TABLE['운동시설']}㎡당 1대 (골프장·골프연습장·옥외수영장 제외·별표2 제2호)",
    ),
    BuildingUse.OFFICE: ParkingStandard(
        use=BuildingUse.OFFICE,
        area_per_space=PARKING_TABLE["업무시설_일반"],
        notes=f"업무(일반): {PARKING_TABLE['업무시설_일반']}㎡당 1대 (별표2 제2호)",
    ),
    BuildingUse.BROADCAST_STATION: ParkingStandard(
        use=BuildingUse.BROADCAST_STATION,
        area_per_space=PARKING_TABLE["방송통신시설_방송국"],
        notes=f"방송국: {PARKING_TABLE['방송통신시설_방송국']}㎡당 1대 (별표2 제2호)",
    ),
    BuildingUse.FUNERAL: ParkingStandard(
        use=BuildingUse.FUNERAL,
        area_per_space=PARKING_TABLE["장례식장"],
        notes=f"장례식장: {PARKING_TABLE['장례식장']}㎡당 1대 (별표2 제2호)",
    ),

    # 별표2 제2호의2 — 공공업무: 200㎡당 1대
    BuildingUse.OFFICE_PUBLIC: ParkingStandard(
        use=BuildingUse.OFFICE_PUBLIC,
        area_per_space=PARKING_TABLE["업무시설_공공"],
        notes=f"업무(공공): {PARKING_TABLE['업무시설_공공']}㎡당 1대 (별표2 제2호의2)",
    ),

    # 별표2 제3호 — 134㎡당 1대
    BuildingUse.FIRST_NEIGHBORHOOD: ParkingStandard(
        use=BuildingUse.FIRST_NEIGHBORHOOD,
        area_per_space=PARKING_TABLE["제1종근린생활시설"],
        notes=(
            f"1종근생: {PARKING_TABLE['제1종근린생활시설']}㎡당 1대 "
            "(바목 변전소·사목 공중화장실 제외·별표2 제3호)"
        ),
    ),
    BuildingUse.SECOND_NEIGHBORHOOD: ParkingStandard(
        use=BuildingUse.SECOND_NEIGHBORHOOD,
        area_per_space=PARKING_TABLE["제2종근린생활시설"],
        notes=f"2종근생: {PARKING_TABLE['제2종근린생활시설']}㎡당 1대 (별표2 제3호)",
    ),
    BuildingUse.HOTEL: ParkingStandard(
        use=BuildingUse.HOTEL,
        area_per_space=PARKING_TABLE["숙박시설"],
        notes=f"숙박: {PARKING_TABLE['숙박시설']}㎡당 1대 (별표2 제3호)",
    ),

    # 별표2 제7호 — 233㎡당 1대
    BuildingUse.TRAINING: ParkingStandard(
        use=BuildingUse.TRAINING,
        area_per_space=PARKING_TABLE["수련시설"],
        notes=f"수련: {PARKING_TABLE['수련시설']}㎡당 1대 (별표2 제7호)",
    ),
    BuildingUse.FACTORY: ParkingStandard(
        use=BuildingUse.FACTORY,
        area_per_space=PARKING_TABLE["공장"],
        notes=f"공장: {PARKING_TABLE['공장']}㎡당 1대 (아파트형 제외·별표2 제7호)",
    ),
    BuildingUse.POWER_PLANT: ParkingStandard(
        use=BuildingUse.POWER_PLANT,
        area_per_space=PARKING_TABLE["발전시설"],
        notes=f"발전: {PARKING_TABLE['발전시설']}㎡당 1대 (별표2 제7호)",
    ),

    # 별표2 제8호 — 267㎡당 1대
    BuildingUse.WAREHOUSE: ParkingStandard(
        use=BuildingUse.WAREHOUSE,
        area_per_space=PARKING_TABLE["창고시설"],
        notes=f"창고: {PARKING_TABLE['창고시설']}㎡당 1대 (별표2 제8호)",
    ),

    # 별표2 제9호 — 데이터센터: 400㎡당 1대
    BuildingUse.DATA_CENTER: ParkingStandard(
        use=BuildingUse.DATA_CENTER,
        area_per_space=PARKING_TABLE["방송통신시설_데이터센터"],
        notes=f"데이터센터: {PARKING_TABLE['방송통신시설_데이터센터']}㎡당 1대 (별표2 제9호)",
    ),

    # 교육연구시설 — 학교 250㎡, 기타 200㎡
    BuildingUse.EDUCATION: ParkingStandard(
        use=BuildingUse.EDUCATION,
        area_per_space=PARKING_TABLE["학교시설"],
        notes=f"학교: {PARKING_TABLE['학교시설']}㎡당 1대 (별표2 제10호)",
    ),

    # 주택 — 세대 단위 기준
    BuildingUse.APARTMENT: ParkingStandard(
        use=BuildingUse.APARTMENT,
        area_per_space=0,
        unit_based=True,
        units_per_space=1,
        notes="공동주택: 세대별 전용면적 구간 적용 (주택건설기준 §27·서울조례)",
    ),
    BuildingUse.SINGLE_HOUSE: ParkingStandard(
        use=BuildingUse.SINGLE_HOUSE,
        area_per_space=0,
        unit_based=True,
        units_per_space=1,
        notes="단독주택: 1세대당 1대 (비고4: 50㎡ 이하 시 면적/100)",
    ),
    BuildingUse.MULTI_FAMILY: ParkingStandard(
        use=BuildingUse.MULTI_FAMILY,
        area_per_space=0,
        unit_based=True,
        units_per_space=1,
        notes="다가구: 전용 ≤30㎡→0.5대, ≤60㎡→0.8대, >60㎡→1.0대/세대 (서울조례)",
    ),
}


# ---------------------------------------------------------------------------
# 입력·출력 데이터클래스
# ---------------------------------------------------------------------------
@dataclass
class ParkingInput:
    use: BuildingUse
    floor_area: float = 0.0        # 해당 용도 연면적 (㎡)
    excluded_area: float = 0.0     # 산정 제외 (지하층·주차장·계단·화장실 등)
    units: int = 0                 # 세대·객실 수
    unit_area: float = 60.0        # 다가구 세대 전용면적 (㎡)
    apply_seoul: bool = True

    @property
    def net_area(self) -> float:
        return max(0.0, self.floor_area - self.excluded_area)


@dataclass
class ParkingResult:
    use: BuildingUse
    required_spaces: int
    calculation_basis: str
    notes: str


@dataclass
class DisabledParkingResult:
    total_spaces: int
    required_disabled: int
    basis: str


@dataclass
class ParkingCompareResult:
    before_results: list[ParkingResult]
    after_results: list[ParkingResult]
    before_total: int
    after_total: int
    additional_required: int       # 비고5: max(0, after − before)
    deficit: int                   # additional_required − provided_after (양수 = 부족)
    disabled_before: DisabledParkingResult
    disabled_after: DisabledParkingResult
    provided_after: int = 0
    pass_: bool = False
    mechanical_note: str = "기계식 주차 적용 시 자주식 40% 이상 유지 필요"


# ---------------------------------------------------------------------------
# 내부 계산 함수
# ---------------------------------------------------------------------------
def _multi_family_spaces(inp: ParkingInput) -> tuple[int, str]:
    """다가구주택 — 세대별 전용면적 구간 적용."""
    rate = get_multi_house_parking_rate(inp.unit_area)
    raw = inp.units * rate
    spaces = _round_half_up(raw)
    basis = (
        f"{inp.units}세대 × {rate}대/세대 (전용{inp.unit_area}㎡) = {raw:.2f} → {spaces}대"
    )
    return spaces, basis


def _single_house_spaces(inp: ParkingInput) -> tuple[int, str]:
    """단독주택 — 비고4: 바닥면적 50㎡ 이하 시 면적/100 대수."""
    if inp.floor_area <= 50.0 and inp.floor_area > 0:
        raw = inp.floor_area / 100.0
        spaces = _round_half_up(raw)
        basis = f"단독주택 50㎡ 이하 특례: {inp.floor_area}㎡ / 100 = {raw:.2f} → {spaces}대 (비고4)"
    else:
        spaces = inp.units or 1
        basis = f"단독주택 1세대당 1대 = {spaces}대"
    return spaces, basis


def _area_based_spaces(inp: ParkingInput, std: ParkingStandard) -> tuple[int, str]:
    """면적 기준 주차대수 산정."""
    rate = std.area_per_space
    net = inp.net_area
    if net <= 0:
        return 0, "산정 면적 없음"
    raw = net / rate
    spaces = _round_half_up(raw)
    if inp.excluded_area > 0:
        basis = (
            f"({inp.floor_area:,.1f} - {inp.excluded_area:,.1f})㎡ = 순{net:,.1f}㎡"
            f" ÷ {rate}㎡/대 = {raw:.3f} → {spaces}대"
        )
    else:
        basis = f"{net:,.1f}㎡ ÷ {rate}㎡/대 = {raw:.3f} → {spaces}대"
    return spaces, basis


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------
def calc_parking(inputs: list[ParkingInput]) -> list[ParkingResult]:
    """주차대수 산정 — 입력 목록별 ParkingResult 반환."""
    results: list[ParkingResult] = []
    for inp in inputs:
        std = PARKING_STANDARDS[inp.use]

        if inp.use == BuildingUse.MULTI_FAMILY:
            spaces, basis = _multi_family_spaces(inp)

        elif inp.use == BuildingUse.SINGLE_HOUSE:
            spaces, basis = _single_house_spaces(inp)

        elif std.unit_based:
            # 공동주택 등 세대 단위
            spaces = inp.units
            basis = f"{inp.units}세대(객실) × 1대/세대 = {spaces}대"

        else:
            spaces, basis = _area_based_spaces(inp, std)

        results.append(ParkingResult(
            use=inp.use,
            required_spaces=spaces,
            calculation_basis=basis,
            notes=std.notes,
        ))
    return results


def total_required_spaces(results: list[ParkingResult]) -> int:
    return sum(r.required_spaces for r in results)


def calc_disabled_parking(total_spaces: int) -> DisabledParkingResult:
    """장애인전용주차 필요 대수 (주차장법 §17의2)."""
    if total_spaces >= 50:
        required = math.ceil(total_spaces * 0.02)
        basis = f"{total_spaces}대 × 2% = {required}면"
    elif total_spaces >= 10:
        required = 1
        basis = "10~49대: 최소 1면"
    else:
        required = 0
        basis = "10대 미만: 의무 없음"
    return DisabledParkingResult(
        total_spaces=total_spaces,
        required_disabled=required,
        basis=basis,
    )


def compare_parking(
    before: list[ParkingInput],
    after: list[ParkingInput],
    provided_before: int = 0,
    provided_after: int = 0,
) -> ParkingCompareResult:
    """
    용도변경 전·후 주차대수 비교.

    비고5 (서울시 주차장 조례 별표2): 추가 설치 의무 = 변경후 − 변경전 (음수→0).
    provided_after: 계획(신설) 주차대수. 이 값이 additional_required 이상이면 적합.
    """
    r_before = calc_parking(before)
    r_after  = calc_parking(after)
    total_before = total_required_spaces(r_before)
    total_after  = total_required_spaces(r_after)

    # 비고5: 추가 의무 대수
    additional_required = max(0, total_after - total_before)

    # 실제 부족 대수
    deficit = max(0, additional_required - provided_after)

    return ParkingCompareResult(
        before_results=r_before,
        after_results=r_after,
        before_total=total_before,
        after_total=total_after,
        additional_required=additional_required,
        deficit=deficit,
        disabled_before=calc_disabled_parking(provided_before),
        disabled_after=calc_disabled_parking(provided_after),
        provided_after=provided_after,
        pass_=(deficit == 0),
    )
