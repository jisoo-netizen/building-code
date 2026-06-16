"""
정북방향 일조 이격거리 산정
근거: 건축법 제61조 + 건축법 시행령 제86조
"""

from dataclasses import dataclass
from enum import Enum


class HeightZone(str, Enum):
    """건물 높이 구간."""
    UP_TO_9M = "9m 이하"
    ABOVE_9M = "9m 초과"


# 정북일조 이격거리 기준 (건축법 시행령 §86①)
# 전용주거·일반주거지역 적용
# 높이 9m 이하 부분: 인접대지경계선으로부터 1.5m 이상
# 높이 9m 초과 부분: 해당 부분 높이의 1/2 이상
SETBACK_BASE_UNDER_9M = 1.5   # m
SETBACK_RATIO_ABOVE_9M = 0.5  # 높이의 1/2


@dataclass
class FloorProfile:
    """층 단위 높이 프로파일."""
    floor_no: int
    floor_height: float   # 해당 층 바닥~천장 높이 (m)


@dataclass
class SunlightResult:
    total_height: float
    required_setback: float
    calculation_detail: list[dict]
    applicable: bool
    reason: str


def calc_north_setback(total_height: float, zone_type_str: str = "") -> SunlightResult:
    """
    건물 전체 높이를 받아 정북 이격거리 산정.

    Parameters
    ----------
    total_height : float
        건물 최고 높이 (m, 지표면 기준)
    zone_type_str : str
        용도지역 명칭 (적용 여부 판단용)
    """
    # 정북일조 적용 대상: 전용주거 / 일반주거지역 (준주거·상업·공업·녹지는 미적용)
    residential_zones = {
        "제1종전용주거지역", "제2종전용주거지역",
        "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역",
    }

    applicable = (zone_type_str in residential_zones) or (zone_type_str == "")
    if not applicable:
        return SunlightResult(
            total_height=total_height,
            required_setback=0,
            calculation_detail=[],
            applicable=False,
            reason=f"{zone_type_str}은(는) 정북일조 규정 미적용 지역",
        )

    detail = []

    if total_height <= 9.0:
        required = SETBACK_BASE_UNDER_9M
        detail.append({
            "section": f"전체 높이 {total_height}m (9m 이하)",
            "rule": f"인접 대지경계선으로부터 {SETBACK_BASE_UNDER_9M}m 이상",
            "setback": SETBACK_BASE_UNDER_9M,
        })
    else:
        # 건축법 시행령 §86①: 높이 9m 초과 부분에 대해
        # "해당 건축물 각 부분의 높이의 2분의 1 이상"
        # → 각 부분의 지표면 기준 높이(total_height) × 0.5
        required = total_height * SETBACK_RATIO_ABOVE_9M

        detail.append({
            "section": "높이 9m 이하 부분",
            "rule": "1.5m (고정, 하한)",
            "setback": SETBACK_BASE_UNDER_9M,
        })
        detail.append({
            "section": f"높이 9m 초과 부분 (최고높이 {total_height:.2f}m)",
            "rule": f"{total_height:.2f}m × 1/2 = {required:.2f}m (각 부분 높이 기준)",
            "setback": round(required, 3),
        })

    return SunlightResult(
        total_height=total_height,
        required_setback=round(required, 3),
        calculation_detail=detail,
        applicable=True,
        reason="전용·일반주거지역 정북일조 규정 적용 (건축법 시행령 §86①)",
    )


def calc_north_setback_by_floor(floors: list[FloorProfile], zone_type_str: str = "") -> SunlightResult:
    """
    층별 높이 프로파일을 받아 각 층의 이격거리를 산정하고 최대값 반환.
    계단식 후퇴(Stepping) 설계 시 층별 검토에 활용.
    """
    cumulative_height = 0.0
    detail = []
    max_setback = 0.0

    applicable = (zone_type_str in {
        "제1종전용주거지역", "제2종전용주거지역",
        "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역",
    }) or (zone_type_str == "")

    if not applicable:
        return SunlightResult(
            total_height=0,
            required_setback=0,
            calculation_detail=[],
            applicable=False,
            reason=f"{zone_type_str}은(는) 정북일조 규정 미적용 지역",
        )

    for f in floors:
        cumulative_height += f.floor_height
        result = calc_north_setback(cumulative_height)
        max_setback = max(max_setback, result.required_setback)
        detail.append({
            "floor": f.floor_no,
            "cumulative_height": round(cumulative_height, 3),
            "required_setback": result.required_setback,
        })

    total_h = sum(f.floor_height for f in floors)
    return SunlightResult(
        total_height=round(total_h, 3),
        required_setback=round(max_setback, 3),
        calculation_detail=detail,
        applicable=True,
        reason="층별 누적 높이 기준 정북일조 산정",
    )


def check_north_setback(
    total_height: float,
    actual_setback: float,
    zone_type_str: str = "",
) -> dict:
    """실제 이격거리 vs 법정 이격거리 비교."""
    result = calc_north_setback(total_height, zone_type_str)
    if not result.applicable:
        return {
            "applicable": False,
            "pass": True,
            "reason": result.reason,
        }
    return {
        "applicable": True,
        "total_height": total_height,
        "required_setback": result.required_setback,
        "actual_setback": actual_setback,
        "pass": actual_setback >= result.required_setback,
        "margin": round(actual_setback - result.required_setback, 3),
        "detail": result.calculation_detail,
    }
