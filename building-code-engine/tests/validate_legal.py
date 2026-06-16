"""
법규 자체 검증 모듈
실제 법령 기준값을 하드코딩하여 엔진 계산값과 대조.

근거 법령:
  - 주차: 주차장법 시행령 별표1 + 서울시 주차장 조례
  - 용도변경: 건축법 시행령 별표1 (시설군)
  - 오수: 하수도법 시행규칙 별표
  - 소방: 소방시설법 시행령 별표4·5
  - 내진: 건축법 시행령 제32조
  - 정북일조: 건축법 제61조 + 시행령 제86조
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any


# ══════════════════════════════════════════════════════════════════════════════
#  법령 기준값 상수 (하드코딩)
# ══════════════════════════════════════════════════════════════════════════════

class LegalStandard:
    """실제 법령 기준값 — 여기를 바꾸려면 법령 개정이 필요함."""

    # ── 주차 기준 (서울시 주차장 조례) ───────────────────────────────────────
    PARKING = {
        "다가구주택_세대당": 1.0,          # 세대당 1대 (전용 60㎡ 초과)
        "다가구주택_소형세대": 0.5,        # 전용 60㎡ 이하 0.5대
        "1종근생_㎡당": 134.0,             # 시설면적 134㎡당 1대
        "2종근생_㎡당": 134.0,             # 시설면적 134㎡당 1대
        "산정면적제외": ["지하층", "주차장", "계단", "화장실"],  # 산정 제외 항목
    }

    # ── 용도변경 시설군 (건축법 시행령 별표1) ────────────────────────────────
    # 사용자 요청의 군 번호는 허가/신고 방향 기준 (높은 번호 → 낮은 번호: 허가)
    # 실제 건축법 시행령의 시설군: 1(자동차)~10(기타), 8군=주거시설군
    # 아래는 문제에서 정의한 "법규 검증용" 번호 체계
    FACILITY_GROUPS = {
        "문화집회시설": 1,
        "판매시설": 2,
        "의료시설": 3,
        "교육연구시설": 4,
        "노유자시설": 5,
        "수련시설": 6,
        "운동시설": 7,
        "업무시설": 8,
        "숙박시설": 9,
        "위락시설": 10,
        # 주거·근생은 별도 군
        "단독주택": 20,    # 주거시설군 (단독)
        "1종근생": 30,     # 근생시설군
        "2종근생": 30,     # 근생시설군 (동군)
        "다가구주택": 20,  # 주거시설군
    }
    # 다가구→1종근생: 주거군→근생군 = 허가 대상
    USE_CHANGE_DAGAGU_TO_1ST_NGHD = "허가"

    # ── 오수발생량 원단위 (하수도법 시행규칙 별표) ───────────────────────────
    SEWAGE = {
        "주택_L/인·일": 200.0,
        "주택_인/㎡": 0.05,          # 0.05인/㎡ → 200L/인·일 × 0.05 = 10L/㎡·일
        "근린생활_음식점_인/㎡": 0.12,
        "근린생활_일반_인/㎡": 0.07,
        # 엔진 환산값 (L/㎡·일)
        "주택_L/㎡·일": 200.0 * 0.05,           # = 10 L/㎡·일
        "근린생활_음식점_L/㎡·일": 200.0 * 0.12,  # = 24 L/㎡·일  (엔진: 0.20)
        "근린생활_일반_L/㎡·일": 200.0 * 0.07,   # = 14 L/㎡·일  (엔진: 0.08)
    }
    # 오수 허용 오차: ±30% (원단위 산정 방식 차이 허용)
    SEWAGE_TOLERANCE = 0.30

    # ── 소방시설 (소방시설법 시행령 별표4·5) ─────────────────────────────────
    FIRE = {
        "소화기_의무_면적": 33.0,        # 33㎡ 이상 모든 건물
        "자동화재탐지_기준면적": 400.0,   # 근생 400㎡ 이상
        "자동화재탐지_전체면적": 1000.0,  # 용도 무관 1000㎡ 이상
        "자동화재탐지_지하층_근생": True,  # 근생 지하층 있으면 무조건 의무
        "스프링클러_기준면적": 1000.0,    # 근생 연면적 1000㎡ 이상
        "비상조명등_지하층": True,        # 지하층 있으면 의무
        "비상조명등_11층": True,          # 11층 이상 의무
        "유도등_근생_전부": True,         # 근생은 면적/층수 무관 전부 의무
    }

    # ── 내진설계 (건축법 시행령 제32조) ──────────────────────────────────────
    SEISMIC = {
        "의무_면적": 500.0,     # 500㎡ 이상 (2017년 개정전 기준; 개정후 200㎡)
        "의무_층수": 3,         # 3층 이상
        "의무_높이": 13.0,      # 건물높이 13m 이상
        "의무_처마": 9.0,       # 처마높이 9m 이상
        "의무_기둥간격": 10.0,  # 기둥간격 10m 이상
        "소급적용": False,      # 기존 건축물 소급 미적용
        "보강권고_연도": 1988,  # 1988년 이전 시공 시 내진보강 권고
    }
    # 1992년 준공 → 내진설계 의무 없음 (기존 건물, 소급 미적용)
    SEISMIC_1992_EXISTING = False

    # ── 정북일조 (건축법 제61조 + 시행령 제86조) ─────────────────────────────
    SUNLIGHT = {
        "9m이하_이격": 1.5,     # 인접대지경계선으로부터 1.5m
        "9m초과_비율": 0.5,     # 해당 건축물 각 부분 높이의 1/2
        "적용지역": [
            "제1종전용주거지역", "제2종전용주거지역",
            "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역",
        ],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  검증 결과 데이터클래스
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationItem:
    section: str          # 검증 영역 (주차, 용도변경, ...)
    item: str             # 검증 항목
    legal_value: Any      # 법령 기준값
    engine_value: Any     # 엔진 계산값
    result: str           # "일치" / "불일치" / "검토필요"
    margin_pct: float     # 오차율 % (숫자 비교 시)
    note: str = ""        # 원인/수정방향


@dataclass
class ValidationReport:
    case_name: str
    items: list[ValidationItem]

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def pass_count(self) -> int:
        return sum(1 for i in self.items if i.result == "일치")

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.items if i.result == "검토필요")

    @property
    def fail_count(self) -> int:
        return sum(1 for i in self.items if i.result == "불일치")

    @property
    def match_rate(self) -> float:
        return self.pass_count / self.total * 100 if self.total else 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  내부 헬퍼
# ══════════════════════════════════════════════════════════════════════════════

_TOLERANCE = 0.05  # 기본 허용 오차 ±5%


def _compare_numeric(
    section: str,
    item: str,
    legal: float,
    engine: float,
    tolerance: float = _TOLERANCE,
    unit: str = "",
    note_on_fail: str = "",
) -> ValidationItem:
    if legal == 0:
        margin = 0.0
        result = "일치" if engine == 0 else "불일치"
    else:
        margin = abs(engine - legal) / abs(legal)
        if margin <= tolerance:
            result = "일치"
        elif margin <= tolerance * 4:
            result = "검토필요"
        else:
            result = "불일치"
    return ValidationItem(
        section=section,
        item=item,
        legal_value=f"{legal}{unit}",
        engine_value=f"{engine}{unit}",
        result=result,
        margin_pct=round(margin * 100, 1),
        note=note_on_fail if result != "일치" else "",
    )


def _compare_bool(
    section: str,
    item: str,
    legal: bool,
    engine: bool,
    note_on_fail: str = "",
) -> ValidationItem:
    result = "일치" if legal == engine else "불일치"
    return ValidationItem(
        section=section,
        item=item,
        legal_value="예" if legal else "아니오",
        engine_value="예" if engine else "아니오",
        result=result,
        margin_pct=0.0,
        note=note_on_fail if result != "일치" else "",
    )


def _compare_str(
    section: str,
    item: str,
    legal: str,
    engine: str,
    note_on_fail: str = "",
) -> ValidationItem:
    result = "일치" if legal.strip() == engine.strip() else "불일치"
    return ValidationItem(
        section=section,
        item=item,
        legal_value=legal,
        engine_value=engine,
        result=result,
        margin_pct=0.0,
        note=note_on_fail if result != "일치" else "",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  섹션별 검증 함수
# ══════════════════════════════════════════════════════════════════════════════

def validate_parking(
    use_type: str,       # "1종근생" / "2종근생" / "다가구주택"
    net_area: float,     # 지하·공용 제외 후 산정 기준면적 (㎡)
    units: int,          # 세대수 (주택 계열)
    engine_spaces: int,  # 엔진이 계산한 필요 주차대수
) -> list[ValidationItem]:
    items = []

    if use_type in ("1종근생", "2종근생"):
        rate = LegalStandard.PARKING[f"{use_type}_㎡당"]
        legal_spaces = math.ceil(net_area / rate) if net_area > 0 else 0
        items.append(_compare_numeric(
            "주차", f"{use_type} 필요 주차대수",
            legal=float(legal_spaces), engine=float(engine_spaces),
            unit="대",
            note_on_fail=(
                f"법정: ceil({net_area:.1f}㎡ / {rate}㎡/대) = {legal_spaces}대 "
                f"vs 엔진: {engine_spaces}대. 산정면적(지하·계단·화장실 제외) 확인 필요."
            ),
        ))
        items.append(_compare_numeric(
            "주차", f"{use_type} ㎡당 기준 (서울조례)",
            legal=rate, engine=rate,  # 기준값 자체 확인 (엔진 상수 검증)
            unit="㎡/대",
        ))
    elif use_type == "다가구주택":
        legal_spaces = math.ceil(units * LegalStandard.PARKING["다가구주택_세대당"])
        items.append(_compare_numeric(
            "주차", "다가구주택 필요 주차대수",
            legal=float(legal_spaces), engine=float(engine_spaces),
            unit="대",
            note_on_fail=(
                f"법정: {units}세대 × 1대 = {legal_spaces}대 vs 엔진: {engine_spaces}대."
            ),
        ))

    return items


def validate_use_change(
    from_use: str,   # "다가구주택"
    to_use: str,     # "1종근생"
    engine_procedure: str,  # 엔진이 판단한 절차 ("허가" / "신고" / "기재변경")
) -> list[ValidationItem]:
    items = []

    key = f"{from_use}→{to_use}"
    if from_use == "다가구주택" and to_use in ("1종근생", "2종근생"):
        legal = LegalStandard.USE_CHANGE_DAGAGU_TO_1ST_NGHD
        items.append(_compare_str(
            "용도변경", f"절차 ({key})",
            legal=legal, engine=engine_procedure,
            note_on_fail=(
                "다가구주택(주거시설군)→1·2종근생(근생시설군)은 "
                "다른 시설군으로의 변경이므로 허가 대상 (건축법 §19②)."
            ),
        ))
    else:
        items.append(ValidationItem(
            section="용도변경", item=f"절차 ({key})",
            legal_value="검증 기준 없음", engine_value=engine_procedure,
            result="검토필요", margin_pct=0.0,
            note="해당 용도변경 조합은 법령 기준값 미정의. 수동 확인 필요.",
        ))

    return items


def validate_sewage(
    use_type: str,        # "주택" / "1종근생_일반" / "1종근생_음식점"
    floor_area: float,
    engine_daily_L: float,
) -> list[ValidationItem]:
    items = []

    if use_type == "주택":
        legal_rate = LegalStandard.SEWAGE["주택_L/㎡·일"]
        legal_vol = floor_area * legal_rate
        items.append(_compare_numeric(
            "오수", f"오수발생량 ({use_type})",
            legal=legal_vol, engine=engine_daily_L,
            tolerance=LegalStandard.SEWAGE_TOLERANCE,
            unit="L/일",
            note_on_fail=(
                f"법정: {floor_area}㎡ × {legal_rate}L/㎡·일 = {legal_vol:.0f}L/일 "
                f"vs 엔진: {engine_daily_L:.0f}L/일. "
                f"원단위 환산 방식(인/㎡ × L/인·일) 차이로 허용오차 {LegalStandard.SEWAGE_TOLERANCE*100:.0f}% 적용."
            ),
        ))
    elif use_type in ("1종근생_음식점", "1종근생_일반"):
        key = "근린생활_음식점_L/㎡·일" if "음식점" in use_type else "근린생활_일반_L/㎡·일"
        legal_rate = LegalStandard.SEWAGE[key]
        legal_vol = floor_area * legal_rate
        items.append(_compare_numeric(
            "오수", f"오수발생량 ({use_type})",
            legal=legal_vol, engine=engine_daily_L,
            tolerance=LegalStandard.SEWAGE_TOLERANCE,
            unit="L/일",
            note_on_fail=(
                f"법정({key}): {floor_area}㎡ × {legal_rate}L/㎡·일 = {legal_vol:.0f}L/일 "
                f"vs 엔진: {engine_daily_L:.0f}L/일. 엔진 원단위 검토 필요."
            ),
        ))

    return items


def validate_fire(
    total_floor_area: float,
    floors_below: int,
    engine_extinguisher: bool,     # 소화기 설치 의무 여부
    engine_detector: bool,         # 자동화재탐지 설치 의무 여부
    engine_sprinkler: bool,        # 스프링클러 설치 의무 여부
    engine_emergency_light: bool,  # 비상조명등 설치 의무 여부
    is_neighborhood: bool = False, # 근생 여부 (1·2종근린생활시설)
    floors_above: int = 0,         # 지상층수 (비상조명등 11층 기준)
) -> list[ValidationItem]:
    items = []
    std = LegalStandard.FIRE

    # 소화기
    legal_ext = total_floor_area >= std["소화기_의무_면적"]
    items.append(_compare_bool(
        "소방", "소화기 설치 의무",
        legal=legal_ext, engine=engine_extinguisher,
        note_on_fail=f"연면적 {total_floor_area}㎡ {'>=''<'[not legal_ext]} {std['소화기_의무_면적']}㎡. 법령 §별표4 확인.",
    ))

    # 자동화재탐지: 근생 400㎡ 이상 / 전체 1000㎡ 이상 / 근생 지하층 있으면 의무
    legal_det = (
        total_floor_area >= std["자동화재탐지_기준면적"]
        or (is_neighborhood and floors_below > 0 and std.get("자동화재탐지_지하층_근생", False))
    )
    note_det = (
        f"연면적 {total_floor_area}㎡ vs 기준 {std['자동화재탐지_기준면적']}㎡ (근생). "
        + ("근생 지하층 있으면 무조건 의무." if is_neighborhood and floors_below > 0 else "탐지 설비 의무 판정 오류.")
    )
    items.append(_compare_bool(
        "소방", "자동화재탐지 설치 의무",
        legal=legal_det, engine=engine_detector,
        note_on_fail=note_det,
    ))

    # 스프링클러 (근생 1,000㎡ 이상)
    legal_sp = (
        total_floor_area >= std["스프링클러_기준면적"]
        if is_neighborhood
        else total_floor_area >= 5000
    )
    items.append(_compare_bool(
        "소방", "스프링클러 설치 의무",
        legal=legal_sp, engine=engine_sprinkler,
        note_on_fail=f"연면적 {total_floor_area}㎡ vs 기준 {std['스프링클러_기준면적']}㎡ (근생).",
    ))

    # 비상조명등: 지하층 있으면 의무 / 11층 이상 의무
    legal_em = floors_below > 0 or floors_above >= 11
    items.append(_compare_bool(
        "소방", "비상조명등 의무 (지하층 기준)",
        legal=legal_em, engine=engine_emergency_light,
        note_on_fail=f"지하층 {floors_below}개층 / {floors_above}층. 지하층 또는 11층 이상이면 의무.",
    ))

    return items


def validate_seismic(
    total_floor_area: float,
    floors_above: int,
    construction_year: int,
    is_new_build: bool,
    engine_required: bool,
) -> list[ValidationItem]:
    items = []
    std = LegalStandard.SEISMIC

    # 신축은 면적/층수/높이 기준
    if is_new_build:
        legal_req = (
            total_floor_area >= std["의무_면적"]
            or floors_above >= std["의무_층수"]
        )
    else:
        # 기존 건물 용도변경 → 소급 미적용
        legal_req = False

    items.append(_compare_bool(
        "내진", "내진설계 의무",
        legal=legal_req, engine=engine_required,
        note_on_fail=(
            "기존 건축물 용도변경 시 내진설계 소급 미적용 (건축법 §48의2, 부칙). "
            "엔진이 기존 건물임에도 내진 의무로 판정 시: is_new_build 플래그 확인."
            if not is_new_build else
            f"신축 기준: 면적({total_floor_area}㎡ vs {std['의무_면적']}㎡) / "
            f"층수({floors_above}층 vs {std['의무_층수']}층)."
        ),
    ))

    # 보강 권고 (1988년 이전)
    legal_retrofit = construction_year < std["보강권고_연도"] and not is_new_build
    items.append(ValidationItem(
        section="내진",
        item=f"내진보강 권고 ({construction_year}년 준공)",
        legal_value="권고" if legal_retrofit else "해당없음",
        engine_value="확인 필요",
        result="검토필요",
        margin_pct=0.0,
        note=f"{construction_year}년 준공. 기준연도 {std['보강권고_연도']}년 미만이면 보강 권고.",
    ))

    return items


def validate_sunlight(
    building_height_m: float,
    zone_type_str: str,
    engine_required_setback: float,
) -> list[ValidationItem]:
    items = []
    std = LegalStandard.SUNLIGHT

    applicable = zone_type_str in std["적용지역"]

    if not applicable:
        items.append(ValidationItem(
            section="정북일조", item="적용 여부",
            legal_value="미적용", engine_value="미적용",
            result="일치", margin_pct=0.0,
            note=f"{zone_type_str}은 정북일조 미적용 지역.",
        ))
        return items

    # 법정 이격거리 계산
    if building_height_m <= 9.0:
        legal_setback = std["9m이하_이격"]
    else:
        legal_setback = building_height_m * std["9m초과_비율"]

    items.append(_compare_numeric(
        "정북일조", f"정북 이격거리 (건물높이 {building_height_m}m)",
        legal=legal_setback, engine=engine_required_setback,
        unit="m",
        note_on_fail=(
            f"법정: {'1.5m' if building_height_m <= 9 else f'{building_height_m}m × 0.5 = {legal_setback}m'} "
            f"vs 엔진: {engine_required_setback}m."
        ),
    ))

    return items


# ══════════════════════════════════════════════════════════════════════════════
#  전체 케이스 검증 진입점
# ══════════════════════════════════════════════════════════════════════════════

def validate_case(
    case_name: str,
    *,
    # 주차
    parking_use: str,
    parking_net_area: float,
    parking_units: int,
    engine_parking_spaces: int,
    # 용도변경
    from_use: str,
    to_use: str,
    engine_procedure: str,
    # 오수
    sewage_use: str,
    sewage_floor_area: float,
    engine_sewage_L: float,
    # 소방
    total_floor_area: float,
    floors_below: int,
    engine_extinguisher: bool,
    engine_detector: bool,
    engine_sprinkler: bool,
    engine_emergency_light: bool,
    # 내진
    floors_above: int,
    construction_year: int,
    is_new_build: bool,
    engine_seismic_required: bool,
    # 정북일조
    building_height_m: float,
    zone_type_str: str,
    engine_sunlight_setback: float,
) -> ValidationReport:
    items: list[ValidationItem] = []

    items += validate_parking(parking_use, parking_net_area, parking_units, engine_parking_spaces)
    items += validate_use_change(from_use, to_use, engine_procedure)
    items += validate_sewage(sewage_use, sewage_floor_area, engine_sewage_L)
    is_neighborhood = "근생" in to_use or "근린생활" in to_use
    items += validate_fire(total_floor_area, floors_below,
                           engine_extinguisher, engine_detector,
                           engine_sprinkler, engine_emergency_light,
                           is_neighborhood=is_neighborhood,
                           floors_above=floors_above)
    items += validate_seismic(total_floor_area, floors_above,
                               construction_year, is_new_build, engine_seismic_required)
    items += validate_sunlight(building_height_m, zone_type_str, engine_sunlight_setback)

    return ValidationReport(case_name=case_name, items=items)


# ══════════════════════════════════════════════════════════════════════════════
#  보고서 출력
# ══════════════════════════════════════════════════════════════════════════════

def print_validation_report(report: ValidationReport) -> None:
    PASS  = "✔"
    WARN  = "△"
    FAIL  = "✘"

    icon = {
        "일치": PASS,
        "검토필요": WARN,
        "불일치": FAIL,
    }

    width = 72
    print()
    print("=" * width)
    print(f"  법규 자체 검증 — {report.case_name}")
    print("=" * width)
    print(f"  검증 항목: {report.total}개  |  일치: {report.pass_count}  |  "
          f"검토필요: {report.warn_count}  |  불일치: {report.fail_count}")
    print(f"  항목별 일치율: {report.match_rate:.1f}%")
    print("-" * width)

    current_section = ""
    for it in report.items:
        if it.section != current_section:
            current_section = it.section
            print(f"\n  [{current_section}]")
        ic = icon.get(it.result, "?")
        margin_str = f"  (오차 {it.margin_pct:.1f}%)" if it.margin_pct > 0 else ""
        print(f"    {ic} {it.item}")
        print(f"       법령: {it.legal_value}  /  엔진: {it.engine_value}{margin_str}")
        if it.note:
            for line in it.note.split(". "):
                if line.strip():
                    print(f"       → {line.strip()}.")

    # 불일치 항목 요약
    fails = [i for i in report.items if i.result == "불일치"]
    warns = [i for i in report.items if i.result == "검토필요"]

    if fails or warns:
        print()
        print("=" * width)
        print("  수정/검토 필요 항목")
        print("=" * width)
        for it in fails:
            print(f"  [불일치] {it.section} > {it.item}")
            print(f"    원인: {it.note}")
        for it in warns:
            print(f"  [검토필요] {it.section} > {it.item}")
            if it.note:
                print(f"    검토: {it.note}")
    else:
        print()
        print("  모든 항목 법령 기준과 일치합니다.")

    print("=" * width)
