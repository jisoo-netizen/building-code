"""
오수발생량 및 정화조 용량 산정
근거: 하수도법 시행규칙 별표 / 환경부 오수처리시설 설치기준
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import math


class SewerUse(str, Enum):
    SINGLE_HOUSE = "단독주택·다가구주택"
    APARTMENT = "공동주택(아파트·연립)"
    OFFICE = "업무시설"
    FIRST_NEIGHBORHOOD = "제1종근린생활시설"
    SECOND_NEIGHBORHOOD = "제2종근린생활시설"
    RETAIL = "판매시설"
    RESTAURANT = "음식점(일반음식점)"
    HOTEL = "숙박시설"
    MEDICAL = "의료시설"
    EDUCATION = "교육연구시설"
    CULTURE_ASSEMBLY = "문화·집회시설"
    FACTORY = "공장"


# 오수발생량 원단위 (하수도법 시행규칙 별표 기준)
# 단위: L/인·일 또는 L/㎡·일
@dataclass
class SewageUnit:
    use: SewerUse
    basis: str               # "person" or "area"
    unit_volume: float       # L/인·일 or L/㎡·일
    persons_per_unit: Optional[float] = None  # 면적 기준일 때 ㎡당 인원 환산
    note: str = ""


# 법정 원단위 환산:
#   주택       : 0.05인/㎡ × 200L/인·일 = 10.0 L/㎡·일 (또는 인원 기준 200L/인·일)
#   1종근생    : 0.07인/㎡ × 200L/인·일 = 14.0 L/㎡·일 (소매·사무소 등)
#   1종근생의원: 0.08인/㎡ × 200L/인·일 = 16.0 L/㎡·일
#   2종근생    : 0.07인/㎡ × 200L/인·일 = 14.0 L/㎡·일 (학원 등 일반)
#   음식점     : 0.12인/㎡ × 200L/인·일 = 24.0 L/㎡·일
# 근거: 하수도법 시행규칙 [별표] 오수발생량 원단위표

SEWAGE_UNITS: dict[SewerUse, SewageUnit] = {
    SewerUse.SINGLE_HOUSE: SewageUnit(
        use=SewerUse.SINGLE_HOUSE,
        basis="person",
        unit_volume=200,
        persons_per_unit=0.05,   # 0.05인/㎡ → 면적모드: 10L/㎡·일
        note="1인당 200L/일 (하수도법 시행규칙 별표, 인원 미정시 0.05인/㎡ 적용)",
    ),
    SewerUse.APARTMENT: SewageUnit(
        use=SewerUse.APARTMENT,
        basis="person",
        unit_volume=200,
        persons_per_unit=0.05,
        note="1인당 200L/일",
    ),
    SewerUse.OFFICE: SewageUnit(
        use=SewerUse.OFFICE,
        basis="area",
        unit_volume=0.06,        # L/㎡·일
        note="업무시설 0.06L/㎡·일",
    ),
    SewerUse.FIRST_NEIGHBORHOOD: SewageUnit(
        use=SewerUse.FIRST_NEIGHBORHOOD,
        basis="area",
        unit_volume=14.0,        # 0.07인/㎡ × 200L/인·일
        note="1종근생(소매·사무소) 14.0L/㎡·일 (0.07인/㎡ × 200L/인·일)",
    ),
    SewerUse.SECOND_NEIGHBORHOOD: SewageUnit(
        use=SewerUse.SECOND_NEIGHBORHOOD,
        basis="area",
        unit_volume=14.0,        # 0.07인/㎡ × 200L/인·일 (학원 등 일반)
        note="2종근생(학원·일반) 14.0L/㎡·일 (0.07인/㎡ × 200L/인·일); 음식점은 RESTAURANT 사용",
    ),
    SewerUse.RETAIL: SewageUnit(
        use=SewerUse.RETAIL,
        basis="area",
        unit_volume=14.0,        # 0.07인/㎡ × 200L/인·일
        note="판매시설 14.0L/㎡·일",
    ),
    SewerUse.RESTAURANT: SewageUnit(
        use=SewerUse.RESTAURANT,
        basis="area",
        unit_volume=24.0,        # 0.12인/㎡ × 200L/인·일
        note="음식점(일반음식점) 24.0L/㎡·일 (0.12인/㎡ × 200L/인·일)",
    ),
    SewerUse.HOTEL: SewageUnit(
        use=SewerUse.HOTEL,
        basis="person",
        unit_volume=250,
        note="숙박시설 250L/인·일",
    ),
    SewerUse.MEDICAL: SewageUnit(
        use=SewerUse.MEDICAL,
        basis="area",
        unit_volume=16.0,        # 0.08인/㎡ × 200L/인·일
        note="의료시설(의원) 16.0L/㎡·일 (0.08인/㎡ × 200L/인·일)",
    ),
    SewerUse.EDUCATION: SewageUnit(
        use=SewerUse.EDUCATION,
        basis="person",
        unit_volume=80,
        note="교육시설 80L/인·일",
    ),
    SewerUse.CULTURE_ASSEMBLY: SewageUnit(
        use=SewerUse.CULTURE_ASSEMBLY,
        basis="person",
        unit_volume=30,
        note="문화·집회 30L/인·일 (단시간 체류)",
    ),
    SewerUse.FACTORY: SewageUnit(
        use=SewerUse.FACTORY,
        basis="person",
        unit_volume=100,
        note="공장 근로자 100L/인·일",
    ),
}


@dataclass
class SewageInput:
    use: SewerUse
    floor_area: float = 0.0   # ㎡ (면적 기준)
    persons: int = 0           # 인원 (인원 기준)


@dataclass
class SewageResult:
    use: SewerUse
    daily_volume_L: float     # 일 오수발생량 (L/일)
    basis_detail: str
    septic_capacity_m3: float  # 필요 정화조 용량 (㎥)
    note: str


def calc_sewage(inputs: list[SewageInput]) -> list[SewageResult]:
    results = []
    for inp in inputs:
        unit = SEWAGE_UNITS[inp.use]
        if unit.basis == "person":
            if inp.persons > 0:
                vol = unit.unit_volume * inp.persons
                detail = f"{inp.persons}인 × {unit.unit_volume}L/인·일 = {vol:.1f}L/일"
            elif inp.floor_area > 0 and unit.persons_per_unit:
                # 인원 미정: 면적 × 인밀도로 환산
                persons_est = inp.floor_area * unit.persons_per_unit
                vol = unit.unit_volume * persons_est
                detail = (
                    f"{inp.floor_area:.0f}㎡ × {unit.persons_per_unit}인/㎡"
                    f" × {unit.unit_volume}L/인·일 = {vol:.1f}L/일"
                )
            else:
                vol = 0.0
                detail = "인원 또는 면적 정보 없음"
        else:
            vol = unit.unit_volume * inp.floor_area
            detail = f"{inp.floor_area:.0f}㎡ × {unit.unit_volume}L/㎡·일 = {vol:.1f}L/일"

        # 정화조 용량: 일 오수량의 1일분 (체류시간 24시간 기준) — 하수도법 시행규칙
        septic = vol / 1000  # L → ㎥
        results.append(SewageResult(
            use=inp.use,
            daily_volume_L=round(vol, 1),
            basis_detail=detail,
            septic_capacity_m3=math.ceil(septic * 10) / 10,  # 소수 1자리 올림
            note=unit.note,
        ))
    return results


def compare_sewage(
    before: list[SewageInput],
    after: list[SewageInput],
) -> dict:
    """용도변경 전후 오수발생량 비교."""
    r_before = calc_sewage(before)
    r_after = calc_sewage(after)
    total_before = sum(r.daily_volume_L for r in r_before)
    total_after = sum(r.daily_volume_L for r in r_after)
    septic_before = sum(r.septic_capacity_m3 for r in r_before)
    septic_after = sum(r.septic_capacity_m3 for r in r_after)

    return {
        "before": r_before,
        "after": r_after,
        "total_before_L": round(total_before, 1),
        "total_after_L": round(total_after, 1),
        "increase_L": round(total_after - total_before, 1),
        "septic_before_m3": septic_before,
        "septic_after_m3": septic_after,
        "septic_upgrade_needed": septic_after > septic_before,
        "public_sewer_connection": True,  # 공공하수도 연결 여부는 지자체 확인 필요
        "note": "공공하수도 처리구역 내 위치 시 정화조 설치 면제 가능 (하수도법 §34)",
    }
