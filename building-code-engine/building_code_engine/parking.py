"""
주차대수 산정 (용도변경 전·후 비교 포함)
근거: 주차장법 시행령 별표 1 + 서울시 주차장 조례
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import math


class BuildingUse(str, Enum):
    APARTMENT = "공동주택(아파트·연립·다세대)"
    SINGLE_HOUSE = "단독주택"
    MULTI_FAMILY = "다가구주택"
    FIRST_NEIGHBORHOOD = "제1종근린생활시설"
    SECOND_NEIGHBORHOOD = "제2종근린생활시설"
    OFFICE = "업무시설"
    RETAIL = "판매시설"
    HOTEL = "숙박시설"
    MEDICAL = "의료시설"
    EDUCATION = "교육연구시설"
    CULTURE_ASSEMBLY = "문화·집회시설"
    FACTORY = "공장"
    WAREHOUSE = "창고시설"
    RESTAURANT = "음식점(일반음식점)"


@dataclass
class ParkingStandard:
    use: BuildingUse
    area_per_space: float           # 법정 기준 ㎡/대
    area_per_space_seoul: Optional[float] = None  # 서울 조례
    unit_based: bool = False        # 세대·객실 단위 기준 여부
    units_per_space: Optional[float] = None
    notes: str = ""


PARKING_STANDARDS: dict[BuildingUse, ParkingStandard] = {
    BuildingUse.APARTMENT: ParkingStandard(
        use=BuildingUse.APARTMENT,
        area_per_space=0,
        unit_based=True,
        units_per_space=1,
        notes="전용 60㎡ 이하 0.5대, 60~85㎡ 0.8대, 85㎡ 초과 1대/세대 (서울조례)",
    ),
    BuildingUse.SINGLE_HOUSE: ParkingStandard(
        use=BuildingUse.SINGLE_HOUSE,
        area_per_space=0,
        unit_based=True,
        units_per_space=1,
        notes="1세대당 1대",
    ),
    BuildingUse.MULTI_FAMILY: ParkingStandard(
        use=BuildingUse.MULTI_FAMILY,
        area_per_space=0,
        unit_based=True,
        units_per_space=1,
        notes="다가구(서울조례): 전용30㎡이하→0.5대/세대, 30~60㎡→0.8대/세대, 60㎡초과→1.0대/세대",
        area_per_space_seoul=None,
    ),
    BuildingUse.FIRST_NEIGHBORHOOD: ParkingStandard(
        use=BuildingUse.FIRST_NEIGHBORHOOD,
        area_per_space=134,
        area_per_space_seoul=134,   # 서울시 조례 동일 (근생은 강화기준 없음)
        notes="1종근생: 지상 시설면적 134㎡당 1대 (지하층·주차·계단·화장실 제외)",
    ),
    BuildingUse.SECOND_NEIGHBORHOOD: ParkingStandard(
        use=BuildingUse.SECOND_NEIGHBORHOOD,
        area_per_space=134,
        area_per_space_seoul=134,
        notes="2종근생: 지상 시설면적 134㎡당 1대 (지하층·주차·계단·화장실 제외)",
    ),
    BuildingUse.OFFICE: ParkingStandard(
        use=BuildingUse.OFFICE,
        area_per_space=150,
        area_per_space_seoul=100,
        notes="업무: 150㎡당 1대 / 서울 100㎡",
    ),
    BuildingUse.RETAIL: ParkingStandard(
        use=BuildingUse.RETAIL,
        area_per_space=134,
        area_per_space_seoul=67,
        notes="판매: 134㎡당 1대 / 서울 67㎡",
    ),
    BuildingUse.HOTEL: ParkingStandard(
        use=BuildingUse.HOTEL,
        area_per_space=0,
        unit_based=True,
        units_per_space=1,
        notes="숙박: 객실 1실당 1대",
    ),
    BuildingUse.MEDICAL: ParkingStandard(
        use=BuildingUse.MEDICAL,
        area_per_space=100,
        area_per_space_seoul=75,
        notes="의료: 100㎡당 1대 / 서울 75㎡",
    ),
    BuildingUse.EDUCATION: ParkingStandard(
        use=BuildingUse.EDUCATION,
        area_per_space=200,
        area_per_space_seoul=150,
        notes="교육: 200㎡당 1대 / 서울 150㎡",
    ),
    BuildingUse.CULTURE_ASSEMBLY: ParkingStandard(
        use=BuildingUse.CULTURE_ASSEMBLY,
        area_per_space=100,
        area_per_space_seoul=75,
        notes="문화·집회: 100㎡당 1대 / 서울 75㎡",
    ),
    BuildingUse.FACTORY: ParkingStandard(
        use=BuildingUse.FACTORY,
        area_per_space=350,
        notes="공장: 350㎡당 1대",
    ),
    BuildingUse.WAREHOUSE: ParkingStandard(
        use=BuildingUse.WAREHOUSE,
        area_per_space=400,
        notes="창고: 400㎡당 1대",
    ),
    BuildingUse.RESTAURANT: ParkingStandard(
        use=BuildingUse.RESTAURANT,
        area_per_space=134,
        area_per_space_seoul=67,
        notes="음식점: 134㎡당 1대 / 서울 67㎡ (2종근생에 포함)",
    ),
}


@dataclass
class ParkingInput:
    use: BuildingUse
    floor_area: float = 0.0          # 해당 용도 전체 바닥면적 (㎡)
    excluded_area: float = 0.0       # 산정 제외 면적 (지하층·주차장·계단·화장실 등)
    units: int = 0
    unit_area: float = 60.0          # 다가구 세대 전용면적 (㎡) — 구간별 산정용
    seats: int = 0                   # 음식점 좌석수 (8석당 1대, 면적 기준과 병행)
    apply_seoul: bool = True

    @property
    def net_area(self) -> float:
        """주차 산정 기준 면적 (제외 면적 차감 후)."""
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
    deficit: int                   # 부족 대수 (after - before, 양수면 추가 필요)
    disabled_before: DisabledParkingResult
    disabled_after: DisabledParkingResult
    mechanical_note: str = "기계식 주차 적용 시 일반 주차의 40% 이상 자주식 유지 필요"
    pass_: bool = False


def _multi_family_spaces(inp: ParkingInput) -> tuple[int, str]:
    """다가구주택 세대별 전용면적 구간 적용 (서울시 주차장 조례)."""
    if inp.unit_area <= 30:
        rate = 0.5
        label = "전용30㎡이하→0.5대/세대"
    elif inp.unit_area <= 60:
        rate = 0.8
        label = "전용30~60㎡→0.8대/세대"
    else:
        rate = 1.0
        label = "전용60㎡초과→1.0대/세대"
    spaces = math.ceil(inp.units * rate)
    return spaces, f"{inp.units}세대 × {rate}대/세대 ({label}) = {spaces}대"


def calc_parking(inputs: list[ParkingInput]) -> list[ParkingResult]:
    results = []
    for inp in inputs:
        std = PARKING_STANDARDS[inp.use]

        # 다가구주택: 전용면적 구간별 차등 (서울시 주차장 조례)
        if inp.use == BuildingUse.MULTI_FAMILY and inp.apply_seoul:
            spaces, basis = _multi_family_spaces(inp)

        elif std.unit_based:
            spaces = math.ceil(inp.units * (std.units_per_space or 1))
            basis = f"{inp.units}단위 × {std.units_per_space}대/단위"

        else:
            rate = (
                std.area_per_space_seoul
                if (inp.apply_seoul and std.area_per_space_seoul)
                else std.area_per_space
            )
            net = inp.net_area
            area_spaces = math.ceil(net / rate) if net > 0 else 0
            label = "서울조례" if (inp.apply_seoul and std.area_per_space_seoul) else "법정"
            if inp.excluded_area > 0:
                area_basis = (
                    f"({inp.floor_area:,.1f} - {inp.excluded_area:,.1f})㎡"
                    f" = 순면적 {net:,.1f}㎡ / {rate}㎡/대 [{label}]"
                )
            else:
                area_basis = f"{net:,.1f}㎡ / {rate}㎡/대 [{label}]"

            # 음식점: 면적 기준과 좌석 기준(8석당 1대) 중 큰 값 적용
            if inp.use == BuildingUse.RESTAURANT and inp.seats > 0:
                seat_spaces = math.ceil(inp.seats / 8)
                if seat_spaces > area_spaces:
                    spaces = seat_spaces
                    basis = f"좌석 {inp.seats}석 / 8석/대 = {seat_spaces}대 (면적기준 {area_spaces}대보다 큼)"
                else:
                    spaces = area_spaces
                    basis = area_basis + f" (좌석기준 {seat_spaces}대보다 큼)"
            else:
                spaces = area_spaces
                basis = area_basis

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
    """장애인전용주차 필요 대수 산정 (주차장법 §17의2)."""
    if total_spaces >= 50:
        required = math.ceil(total_spaces * 0.02)  # 2% 이상
        basis = f"{total_spaces}대 × 2% = {required}면"
    elif total_spaces >= 10:
        required = 1
        basis = f"10~49대: 최소 1면"
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
    provided_before: int,
    provided_after: int,
) -> ParkingCompareResult:
    """용도변경 전·후 주차대수 비교."""
    r_before = calc_parking(before)
    r_after = calc_parking(after)
    total_before = total_required_spaces(r_before)
    total_after = total_required_spaces(r_after)
    deficit = total_after - provided_after

    return ParkingCompareResult(
        before_results=r_before,
        after_results=r_after,
        before_total=total_before,
        after_total=total_after,
        deficit=deficit,
        disabled_before=calc_disabled_parking(provided_before),
        disabled_after=calc_disabled_parking(provided_after),
        pass_=provided_after >= total_after,
    )
