"""
관광진흥법 특례 검토 (호스텔·관광숙박시설)
근거: 관광진흥법 제15조 (사업계획승인)
     건축법 시행령 제13조제1항제3호 (주거지역 숙박시설 특례)
     서울특별시 도시계획 조례 제31조② (거리제한)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


TOURISM_LODGING_KEYWORDS: set[str] = {
    "호스텔", "관광숙박", "관광호텔", "수상관광호텔", "한국전통호텔",
    "가족호텔", "의료관광호텔", "소형호텔", "펜션",
}


class TourismCheckStatus(str, Enum):
    PASS        = "충족"
    FAIL        = "미충족"
    REVIEW      = "확인 필요"
    NOT_APPLIED = "해당 없음"


@dataclass
class TourismCheck:
    item: str
    status: TourismCheckStatus
    detail: str
    legal_basis: str
    note: str = ""


@dataclass
class TourismResult:
    is_tourism_lodging: bool
    checks: list[TourismCheck]
    summary: str


def is_tourism_lodging(use_detail_str: str) -> bool:
    """용도 문자열에서 관광진흥법 적용 숙박시설 여부 감지."""
    lowered = use_detail_str.lower().replace(" ", "")
    return any(k in lowered for k in TOURISM_LODGING_KEYWORDS)


def check_tourism_special(
    use_detail_str: str,
    zone_type_str: str,          # 용도지역 (예: "제2종일반주거지역")
    road_width_m: float,          # 접면 도로 폭 (m)
    building_height_m: float,     # 건물 높이 (m)
    adjacent_setback_m: float,    # 인접대지경계선까지 거리 (m)
    distance_to_residential_m: Optional[float] = None,  # 주거지역 경계까지 거리 (m)
    has_tourism_approval: bool = False,  # 관광진흥법 §15 사업계획승인 여부
) -> TourismResult:
    """
    관광진흥법 특례 적용 숙박시설 입지·건축 조건 종합 검토.
    """
    if not is_tourism_lodging(use_detail_str):
        return TourismResult(
            is_tourism_lodging=False,
            checks=[],
            summary="관광진흥법 적용 숙박시설 아님 (일반숙박시설로 검토)",
        )

    checks: list[TourismCheck] = []
    is_residential_zone = any(k in zone_type_str for k in ["주거지역", "전용주거", "일반주거", "준주거"])

    # ── 1. 주거지역 내 숙박시설 원칙적 불허 안내 ─────────────────────────────
    if is_residential_zone:
        checks.append(TourismCheck(
            item="용도지역 적합성",
            status=TourismCheckStatus.REVIEW,
            detail=(
                f"{zone_type_str}: 주거지역에서 숙박시설은 원칙적 불허 "
                "→ 관광진흥법 §15 사업계획승인 취득 시 특례 적용 가능"
            ),
            legal_basis="국토계획법 시행령 별표4 + 관광진흥법 §15",
            note="사업계획승인 없이 건축허가 신청 시 반려 가능",
        ))
    else:
        checks.append(TourismCheck(
            item="용도지역 적합성",
            status=TourismCheckStatus.PASS,
            detail=f"{zone_type_str}: 숙박시설 허용 용도지역",
            legal_basis="국토계획법 시행령",
        ))

    # ── 2. 관광진흥법 §15 사업계획승인 ──────────────────────────────────────
    checks.append(TourismCheck(
        item="관광진흥법 §15 사업계획승인",
        status=TourismCheckStatus.PASS if has_tourism_approval else TourismCheckStatus.REVIEW,
        detail=(
            "사업계획승인 취득 확인됨 → 주거지역 입지 특례 적용 가능"
            if has_tourism_approval else
            "사업계획승인 취득 여부 확인 필요 (문화체육관광부 또는 지방자치단체장)"
        ),
        legal_basis="관광진흥법 §15·§4",
        note="사업계획승인 대상: 100실 이상 또는 연면적 3,000㎡ 이상 관광숙박업",
    ))

    # ── 3. 건축법 시행령 제13조제1항제3호 — 주거지역 추가 기준 ─────────────
    if is_residential_zone:
        # 조건① 도로 폭 6m 이상
        road_ok = road_width_m >= 6.0
        checks.append(TourismCheck(
            item="접면 도로 폭 (6m 이상)",
            status=TourismCheckStatus.PASS if road_ok else TourismCheckStatus.FAIL,
            detail=f"접면 도로 {road_width_m}m {'≥' if road_ok else '<'} 6m",
            legal_basis="건축법 시행령 §13①3호 가목",
            note="6m 미만 도로는 특례 적용 불가",
        ))

        # 조건② 건물 높이 ≤ 인접대지 수평거리 × 2
        if adjacent_setback_m > 0:
            max_allowed_height = adjacent_setback_m * 2
            height_ok = building_height_m <= max_allowed_height
            checks.append(TourismCheck(
                item="건물 높이 ≤ 인접거리 × 2",
                status=TourismCheckStatus.PASS if height_ok else TourismCheckStatus.FAIL,
                detail=(
                    f"건물높이 {building_height_m}m {'≤' if height_ok else '>'} "
                    f"인접거리 {adjacent_setback_m}m × 2 = {max_allowed_height}m"
                ),
                legal_basis="건축법 시행령 §13①3호 나목",
                note="초과 시 건물 높이 축소 또는 인접 이격 확보 필요",
            ))
        else:
            checks.append(TourismCheck(
                item="건물 높이 ≤ 인접거리 × 2",
                status=TourismCheckStatus.REVIEW,
                detail="인접대지 경계까지 거리 미입력 → 직접 확인 필요",
                legal_basis="건축법 시행령 §13①3호 나목",
            ))

    # ── 4. 서울시 도시계획조례 §31② — 주거지역 경계 50m 이내 거리제한 ──────
    checks.append(TourismCheck(
        item="주거지역 경계 50m 거리제한",
        status=(
            TourismCheckStatus.PASS
            if (distance_to_residential_m is not None and distance_to_residential_m >= 50)
            else TourismCheckStatus.REVIEW
        ),
        detail=(
            f"주거지역 경계까지 {distance_to_residential_m}m "
            f"{'≥ 50m (충족)' if distance_to_residential_m and distance_to_residential_m >= 50 else '→ 확인 필요'}"
            if distance_to_residential_m is not None else
            "주거지역 경계까지 거리 미입력 → 토지이음 또는 현장 확인 필요"
        ),
        legal_basis="서울특별시 도시계획 조례 §31② (일반숙박·생활숙박·위락시설)",
        note=(
            "주거지역 '내부'의 관광진흥법 특례 숙박시설은 거리 제한 적용 제외 가능 "
            "(법제처 유권해석 확인 필요); 주거지역 외부 숙박시설은 50m 준수 필요"
        ),
    ))

    # ── 5. 관광숙박업 등록 절차 안내 ────────────────────────────────────────
    checks.append(TourismCheck(
        item="관광숙박업 등록 절차",
        status=TourismCheckStatus.REVIEW,
        detail="건축허가 → 준공 → 관광숙박업 등록 (지자체 문화·관광 담당 부서)",
        legal_basis="관광진흥법 §4·§6",
        note="호스텔업 등록 기준: 욕실·샤워시설 구비, 외국어 안내서비스 등",
    ))

    all_pass = all(c.status in (TourismCheckStatus.PASS, TourismCheckStatus.REVIEW) for c in checks)
    fail_count = sum(1 for c in checks if c.status == TourismCheckStatus.FAIL)

    return TourismResult(
        is_tourism_lodging=True,
        checks=checks,
        summary=(
            f"관광진흥법 특례 숙박시설 ({use_detail_str}) — "
            + (f"조건 {fail_count}개 미충족, 즉시 검토 필요" if fail_count else "전체 조건 검토 완료")
        ),
    )


# Optional 타입 import (함수 시그니처용)
from typing import Optional
