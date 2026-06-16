"""
내진설계 의무 여부 판단
근거: 건축법 제48조의2 + 건축법 시행령 제32조의2
"""

from dataclasses import dataclass
from enum import Enum


class SeismicGrade(str, Enum):
    GRADE_I = "내진등급 I (중요도 높음)"       # 병원·학교·소방서 등
    GRADE_II = "내진등급 II (일반 건축물)"
    GRADE_III = "내진등급 III (소규모)"
    NOT_REQUIRED = "내진설계 불필요"


# 내진등급 I 해당 용도
SEISMIC_GRADE_I_USES = {
    "의료시설", "교육연구시설", "노유자시설", "수련시설",
    "문화및집회시설", "종교시설", "운동시설",
    "방송통신시설", "발전시설",
}


@dataclass
class SeismicResult:
    required: bool
    grade: SeismicGrade
    reason: str
    retrofit_recommended: bool  # 기존 건축물 내진보강 권고 여부
    retrofit_note: str = ""


def check_seismic(
    total_floor_area: float,
    floors_above: int,
    building_use_str: str,
    construction_year: int = 2000,
    is_new_build: bool = True,
    building_height_m: float = 0.0,   # 건축물 높이 (m)
    eave_height_m: float = 0.0,       # 처마높이 (m)
    max_span_m: float = 0.0,          # 최대 기둥간격 (m)
) -> SeismicResult:
    """
    내진설계 의무 여부 판단.

    의무 대상 (건축법 시행령 §32의2):
    - 연면적 500㎡ 이상 (목조건축물 제외)  [주: 2017년 개정 후 200㎡ 이상으로 강화]
    - 3층 이상
    - 건축물 높이 13m 이상
    - 처마높이 9m 이상
    - 기둥과 기둥 사이 10m 이상
    → 하나라도 해당하면 내진설계 의무 (신축 기준)
    → 기존 건물 용도변경은 소급 미적용 (건축법 §48의2 부칙)
    """
    # 기존 건물 용도변경: 내진설계 소급 미적용
    if not is_new_build:
        retrofit = construction_year < 1988
        return SeismicResult(
            required=False,
            grade=SeismicGrade.NOT_REQUIRED,
            reason=(
                f"기존 건축물 용도변경 → 내진설계 소급 미적용 "
                f"(건축법 §48의2 부칙, {construction_year}년 준공)"
            ),
            retrofit_recommended=retrofit,
            retrofit_note=(
                f"1988년 이전 시공 건축물 → 내진보강 성능평가 권고"
                if retrofit else ""
            ),
        )

    # 신축 의무 여부 판단 (건축법 시행령 §32의2)
    area_trigger = total_floor_area >= 500      # 2017 개정전 기준 (개정후 200㎡)
    floor_trigger = floors_above >= 3
    height_trigger = building_height_m >= 13.0
    eave_trigger = eave_height_m >= 9.0
    span_trigger = max_span_m >= 10.0
    required = area_trigger or floor_trigger or height_trigger or eave_trigger or span_trigger

    triggers = []
    if area_trigger: triggers.append(f"연면적 {total_floor_area}㎡")
    if floor_trigger: triggers.append(f"{floors_above}층")
    if height_trigger: triggers.append(f"높이 {building_height_m}m")
    if eave_trigger: triggers.append(f"처마높이 {eave_height_m}m")
    if span_trigger: triggers.append(f"기둥간격 {max_span_m}m")

    if not required:
        return SeismicResult(
            required=False,
            grade=SeismicGrade.NOT_REQUIRED,
            reason=(
                f"연면적 {total_floor_area}㎡ / {floors_above}층 — "
                f"내진설계 의무 기준 미달 (500㎡ 또는 3층 이상)"
            ),
            retrofit_recommended=False,
        )

    trigger_str = " / ".join(triggers) if triggers else "층수·면적 기준"

    # 등급 판정
    if building_use_str in SEISMIC_GRADE_I_USES:
        grade = SeismicGrade.GRADE_I
        reason = f"{building_use_str} 용도 → 내진등급 I (중요도 특)"
    elif total_floor_area >= 1000 or floors_above >= 6:
        grade = SeismicGrade.GRADE_II
        reason = f"{trigger_str} → 내진등급 II"
    else:
        grade = SeismicGrade.GRADE_III
        reason = f"{trigger_str} → 내진등급 III"

    # 기존 건축물 내진보강 권고 (1988년 이전 설계기준)
    retrofit = construction_year < 1988
    retrofit_note = (
        "1988년 이전 시공 건축물 → 내진보강 성능평가 권고 (지진·화산재해대책법 §14)"
        if retrofit else ""
    )

    return SeismicResult(
        required=True,
        grade=grade,
        reason=reason,
        retrofit_recommended=retrofit,
        retrofit_note=retrofit_note,
    )
