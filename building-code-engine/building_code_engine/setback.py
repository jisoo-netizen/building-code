"""
이격거리·건축선 후퇴·도로사선제한 종합
근거: 건축법 제46조 (건축선) / 제61조 (일조 등) / 건축법 시행령 §86
※ sunlight.py의 정북일조 함수를 재사용·통합
"""

from dataclasses import dataclass
from typing import Optional
from .sunlight import calc_north_setback, check_north_setback


@dataclass
class SetbackResult:
    item: str
    required_m: Optional[float]
    actual_m: Optional[float]
    pass_: bool
    basis: str
    note: str = ""


def check_building_line_setback(
    road_width_m: float,
    actual_setback_m: float,
) -> SetbackResult:
    """
    건축선 후퇴 여부 (건축법 §46).
    - 도로 폭 4m 미만: 도로 중심선에서 2m 후퇴선이 건축선
    - 도로 폭 4m 이상: 도로 경계선이 건축선
    """
    if road_width_m < 4.0:
        required = max(0.0, 2.0 - road_width_m / 2)
        basis = f"도로폭 {road_width_m}m < 4m → 중심선에서 2m 후퇴 건축선"
        note = "도로 중심선 기준 양쪽 각 2m 확보 시 건축선 성립"
    else:
        required = 0.0
        basis = f"도로폭 {road_width_m}m >= 4m → 도로 경계선이 건축선"
        note = ""

    return SetbackResult(
        item="건축선 후퇴",
        required_m=round(required, 2),
        actual_m=actual_setback_m,
        pass_=actual_setback_m >= required,
        basis=basis,
        note=note,
    )


def check_road_oblique(
    road_width_m: float,
    floor_height_m: float,        # 해당 층 바닥~천장 높이
    distance_from_road_m: float,  # 도로경계선에서 건물까지 거리
    apply_zone: str = "주거지역",
) -> list[SetbackResult]:
    """
    도로사선제한 (건축법 시행령 §86②).
    - 주거지역: 도로 반대측 경계선에서 건물 각 부분까지 높이 ≤ 1.5H (H: 수평거리)
    - 기타지역: 2H
    ※ 2015년 이후 도로사선 폐지, 일조사선만 남음 — 지구단위계획 내 존치 가능
    """
    results = []
    ratio = 1.5 if "주거" in apply_zone else 2.0
    max_height_allowed = distance_from_road_m * ratio + road_width_m * ratio
    results.append(SetbackResult(
        item="도로사선제한",
        required_m=None,
        actual_m=None,
        pass_=True,
        basis=(
            "2015년 건축법 개정으로 일반 도로사선제한 폐지. "
            "지구단위계획 등 별도 지정구역은 해당 지침 적용"
        ),
        note="지구단위계획구역·특별건축구역 여부 확인 필요",
    ))
    return results


def check_adjacent_boundary_setback(
    building_height_m: float,
    actual_setback_m: float,
    building_use_str: str = "",
) -> SetbackResult:
    """
    인접대지경계선 이격 (건축법 시행령 §86③).
    전용·일반주거지역 정북일조와 별개로,
    인접대지경계선에서 건물 외벽까지 최소 이격 기준.
    일반적으로 해당 층 높이의 0.5 이상 (단, 채광창이 없는 경우 0.5m 완화 가능)
    """
    # 인접대지 이격: 채광창 있는 외벽 기준 → 창 높이의 0.5배 이상 (최소 0.5m)
    # 채광창 없는 경우 0.5m로 완화 가능
    required = 0.5   # 채광창 없는 외벽 완화 기준 적용 (실무 기본값)
    return SetbackResult(
        item="인접대지경계선 이격",
        required_m=round(required, 2),
        actual_m=actual_setback_m,
        pass_=actual_setback_m >= required,
        basis=f"채광창 없는 외벽: 0.5m 이상 (건축법 시행령 §86③)",
        note="채광창 있는 외벽은 창 높이의 0.5배 이상 별도 적용 필요",
    )


def full_setback_check(
    road_width_m: float,
    building_line_setback_actual: float,
    building_height_m: float,
    north_setback_actual: Optional[float],
    adjacent_setback_actual: float,
    zone_type_str: str,
) -> list[SetbackResult]:
    """이격거리 전체 통합 검토."""
    results: list[SetbackResult] = []

    # 건축선 후퇴
    results.append(check_building_line_setback(road_width_m, building_line_setback_actual))

    # 정북일조
    if north_setback_actual is not None:
        sun = check_north_setback(building_height_m, north_setback_actual, zone_type_str)
        if sun.get("applicable"):
            results.append(SetbackResult(
                item="정북일조 이격거리",
                required_m=sun["required_setback"],
                actual_m=north_setback_actual,
                pass_=sun["pass"],
                basis=f"건물높이 {building_height_m}m 기준 (건축법 시행령 §86①)",
                note=f"여유: {sun['margin']:+.3f}m",
            ))
        else:
            results.append(SetbackResult(
                item="정북일조 이격거리",
                required_m=0,
                actual_m=north_setback_actual,
                pass_=True,
                basis=sun.get("reason", "미적용 지역"),
            ))

    # 인접대지경계선
    results.append(check_adjacent_boundary_setback(building_height_m, adjacent_setback_actual))

    # 도로사선
    results.extend(check_road_oblique(road_width_m, building_height_m, building_line_setback_actual, zone_type_str))

    return results
