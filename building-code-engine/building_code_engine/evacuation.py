"""
피난·방화구획 기준 검토
근거: 건축법 시행령 제34조~제46조 / 건축물 피난·방화구조 등의 기준에 관한 규칙
"""

from dataclasses import dataclass, field
from enum import Enum


class StaircaseType(str, Enum):
    DIRECT_STAIRCASE = "직통계단"
    FIRE_STAIRCASE = "피난계단"
    SPECIAL_FIRE_STAIRCASE = "특별피난계단"


@dataclass
class EvacuationResult:
    item: str
    required: bool
    requirement: str
    current_status: str
    pass_: bool
    note: str = ""


def check_direct_staircase(
    floor_room_area: float,       # 피난층 외 거실 바닥면적 합계 (㎡)
    floors_above: int,
) -> EvacuationResult:
    """
    직통계단 설치 기준.
    건축법 시행령 §34: 거실 바닥면적 합계 400㎡(주거 600㎡) 초과 시 2개소 이상
    """
    if floor_room_area > 400:
        req = "직통계단 2개소 이상 (거실 400㎡ 초과)"
        note = "주거용 건축물은 600㎡ 초과 시 2개소"
        ok = False  # 실제 계단수는 입력받지 않으므로 검토 필요 표시
    else:
        req = "직통계단 1개소 이상"
        ok = True
        note = ""

    return EvacuationResult(
        item="직통계단",
        required=True,
        requirement=req,
        current_status=f"거실 바닥면적 합계 {floor_room_area}㎡ / {floors_above}층",
        pass_=ok,
        note=note,
    )


def check_staircase_type(
    floors_above: int,
    building_use_str: str,
    total_floor_area: float,
) -> EvacuationResult:
    """
    피난계단 vs 특별피난계단 판단.
    - 5층 이상 or 지하 2층 이하: 피난계단 or 특별피난계단
    - 11층 이상: 특별피난계단
    - 판매·업무 등 다중이용시설: 5층 이상 특별피난계단
    """
    high_use = {"판매시설", "업무시설", "의료시설", "숙박시설", "문화및집회시설"}

    if floors_above >= 11:
        stair_type = StaircaseType.SPECIAL_FIRE_STAIRCASE
        req = f"{floors_above}층 이상 → 특별피난계단 설치 의무"
        ok = True  # 계획 확인 필요
    elif floors_above >= 5 and building_use_str in high_use:
        stair_type = StaircaseType.SPECIAL_FIRE_STAIRCASE
        req = f"{floors_above}층 / {building_use_str} → 특별피난계단 설치"
        ok = True
    elif floors_above >= 5:
        stair_type = StaircaseType.FIRE_STAIRCASE
        req = f"{floors_above}층 이상 → 피난계단 설치"
        ok = True
    else:
        stair_type = StaircaseType.DIRECT_STAIRCASE
        req = f"{floors_above}층 → 직통계단으로 가능"
        ok = True

    return EvacuationResult(
        item="계단 형식",
        required=True,
        requirement=req,
        current_status=f"{floors_above}층 / {building_use_str}",
        pass_=ok,
        note=stair_type.value,
    )


def check_fire_compartment(
    floor_area_per_floor: float,    # 층당 바닥면적 (㎡)
    has_sprinkler: bool,
    building_use_str: str,
) -> list[EvacuationResult]:
    """
    방화구획 면적 기준 검토 (건축법 시행령 §46).
    - 스프링클러 없음: 1,000㎡ 이내마다 구획
    - 스프링클러 있음: 3,000㎡ 이내마다 구획
    """
    results = []
    limit = 3000 if has_sprinkler else 1000
    sp_label = "스프링클러 설치 시" if has_sprinkler else "스프링클러 미설치 시"
    compartments_needed = max(1, -(-int(floor_area_per_floor) // limit))  # ceiling div

    ok = floor_area_per_floor <= limit
    results.append(EvacuationResult(
        item="방화구획(면적 기준)",
        required=True,
        requirement=f"층당 {limit:,}㎡ 이내마다 방화구획 ({sp_label})",
        current_status=f"층당 바닥면적 {floor_area_per_floor:,.0f}㎡",
        pass_=ok,
        note=f"필요 구획수: {compartments_needed}개" if not ok else "1개 구획으로 가능",
    ))

    # 수직 방화구획 (3층 이상: 층별 구획)
    results.append(EvacuationResult(
        item="방화구획(수직·층간)",
        required=True,
        requirement="층별 바닥: 내화구조 + 방화문 설치 (건축법 시행령 §46①)",
        current_status="설계 시 반영 확인 필요",
        pass_=True,
        note="계단실·엘리베이터 샤프트 관통부 방화처리 포함",
    ))

    return results


def check_corridor_width(
    both_sides_rooms: bool,
    building_use_str: str,
) -> EvacuationResult:
    """
    복도 폭 기준 (건축법 시행령 §48).
    - 양측 거실: 1.8m 이상
    - 기타: 1.2m 이상
    """
    min_width = 1.8 if both_sides_rooms else 1.2
    label = "양측 거실 복도" if both_sides_rooms else "편측 거실 복도"
    return EvacuationResult(
        item="복도 폭",
        required=True,
        requirement=f"{label}: {min_width}m 이상",
        current_status="실측 확인 필요",
        pass_=True,
        note="피난계단 접속 복도는 별도 기준 적용",
    )


def full_evacuation_check(
    floor_room_area: float,
    floors_above: int,
    floor_area_per_floor: float,
    has_sprinkler: bool,
    building_use_str: str,
    both_sides_corridor: bool = True,
) -> list[EvacuationResult]:
    """전체 피난·방화구획 통합 검토."""
    results = []
    results.append(check_direct_staircase(floor_room_area, floors_above))
    results.append(check_staircase_type(floors_above, building_use_str, floor_room_area))
    results.extend(check_fire_compartment(floor_area_per_floor, has_sprinkler, building_use_str))
    results.append(check_corridor_width(both_sides_corridor, building_use_str))
    return results
