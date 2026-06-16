"""
다중이용업소 추가 규제 검토
근거: 다중이용업소의 안전관리에 관한 특별법 (다중이용업소법) + 시행령·시행규칙
     소방시설법 시행령 별표4
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ── 다중이용업소 업종 판단 ────────────────────────────────────────────────────

DANGEROUS_BUSINESS_KEYWORDS: list[tuple[str, str]] = [
    # (키워드, 표준 업종명)
    ("단란주점",        "단란주점영업"),
    ("유흥주점",        "유흥주점영업"),
    ("고시원",          "고시원업"),
    ("산후조리",        "산후조리업"),
    ("노래연습",        "노래연습장업"),
    ("노래방",          "노래연습장업"),
    ("pc방",           "인터넷컴퓨터게임시설제공업"),
    ("인터넷게임",      "인터넷컴퓨터게임시설제공업"),
    ("게임제공업",      "게임제공업"),
    ("복합유통게임",    "복합유통게임제공업"),
    ("키즈카페",        "키즈카페"),
    ("어린이식당",      "키즈카페"),
    ("안마시술소",      "안마시술소"),
]

# 면적·층수 조건이 있는 업종 (조건 충족 시에만 다중이용업소 해당)
CONDITIONAL_BUSINESS: dict[str, dict] = {
    "학원":            {"min_capacity": 300, "or_min_area": 300.0},
    "안마시술소":      {"or_min_area": 100.0, "basement_min_floor": 2},
    "키즈카페":        {"or_min_area": 66.0},
    "일반음식점":      {"or_min_area": 100.0, "basement_min_floor": 2},
    "휴게음식점":      {"or_min_area": 100.0, "basement_min_floor": 2},
    "제과점":          {"or_min_area": 100.0, "basement_min_floor": 2},
}

# 규모 무관 무조건 해당 업종
UNCONDITIONAL_BUSINESS: set[str] = {
    "단란주점영업", "유흥주점영업", "고시원업", "산후조리업",
    "노래연습장업", "게임제공업", "복합유통게임제공업",
    "인터넷컴퓨터게임시설제공업",
}


class MultiUseRequirement(str, Enum):
    MANDATORY    = "의무"
    CONDITIONAL  = "조건부 의무"
    NOT_REQUIRED = "해당 없음"


@dataclass
class MultiUseCheck:
    item: str
    requirement: MultiUseRequirement
    detail: str
    legal_basis: str
    note: str = ""


@dataclass
class MultiUseResult:
    is_multi_use: bool
    business_type: str
    checks: list[MultiUseCheck]
    summary: str


def detect_business_type(use_detail_str: str) -> Optional[str]:
    """용도 세부 문자열에서 다중이용업소 업종 자동 감지."""
    lowered = use_detail_str.lower().replace(" ", "")
    for kw, biz_type in DANGEROUS_BUSINESS_KEYWORDS:
        if kw in lowered:
            return biz_type
    return None


def check_multi_use_business(
    use_detail_str: str,          # 예: "노래연습장업", "고시원업"
    floor_area: float,            # 해당 영업장 면적 (㎡)
    floors_below: int = 0,        # 지하층 수
    capacity: int = 0,            # 수용 인원 (학원 등)
    is_explicitly_multi_use: bool = False,  # 사용자가 직접 다중이용업소라고 명시
) -> MultiUseResult:
    """
    다중이용업소 해당 여부 판단 및 추가 규제 항목 반환.
    """
    # 업종 자동 감지 (또는 직접 지정)
    biz_type = detect_business_type(use_detail_str) or use_detail_str

    # 해당 여부 판단
    if is_explicitly_multi_use or biz_type in UNCONDITIONAL_BUSINESS:
        is_multi_use = True
    else:
        # 조건부 확인
        cond = next(
            (v for k, v in CONDITIONAL_BUSINESS.items() if k in use_detail_str or k in biz_type),
            None
        )
        if cond is None:
            return MultiUseResult(
                is_multi_use=False,
                business_type=biz_type,
                checks=[],
                summary="다중이용업소 해당 없음",
            )
        # 조건 평가
        area_ok = floor_area >= cond.get("or_min_area", float("inf"))
        cap_ok = capacity >= cond.get("min_capacity", float("inf"))
        bl_ok = floors_below >= cond.get("basement_min_floor", float("inf"))
        is_multi_use = area_ok or cap_ok or bl_ok

    if not is_multi_use:
        return MultiUseResult(
            is_multi_use=False,
            business_type=biz_type,
            checks=[],
            summary="다중이용업소 기준 미달 (면적·층수·인원 조건 미충족)",
        )

    # ── 규제 항목 생성 ─────────────────────────────────────────────────────
    checks: list[MultiUseCheck] = []

    # 1. 비상구 2방향 설치
    two_exit = floor_area >= 150
    checks.append(MultiUseCheck(
        item="비상구 2방향 출구",
        requirement=MultiUseRequirement.MANDATORY if two_exit else MultiUseRequirement.CONDITIONAL,
        detail=(
            f"영업장 면적 {floor_area}㎡ ≥ 150㎡ → 주출입구 외 비상구 1개소 이상 의무"
            if two_exit else
            f"영업장 면적 {floor_area}㎡ < 150㎡ → 주출입구 비상구 겸용 가능 (단, 개구부 확보 필요)"
        ),
        legal_basis="다중이용업소법 §10 + 시행령 §9·별표2",
        note="비상구: 유효폭 0.75m 이상, 높이 1.5m 이상, 외부 개방형",
    ))

    # 2. 간이스프링클러
    simple_sp_required = biz_type in {
        "고시원업", "산후조리업", "노래연습장업", "유흥주점영업", "단란주점영업",
        "인터넷컴퓨터게임시설제공업", "게임제공업", "복합유통게임제공업",
    }
    checks.append(MultiUseCheck(
        item="간이스프링클러",
        requirement=MultiUseRequirement.MANDATORY if simple_sp_required else MultiUseRequirement.CONDITIONAL,
        detail=(
            f"{biz_type} → 규모·층수 무관 간이스프링클러 의무"
            if simple_sp_required else
            "업종에 따라 설치 여부 확인 필요"
        ),
        legal_basis="다중이용업소법 §9 + 소방시설법 시행령 별표4 소화설비 4호",
    ))

    # 3. 영상음향차단장치
    av_block_required = any(
        k in (use_detail_str + biz_type)
        for k in ["노래연습", "노래방", "단란주점", "유흥주점", "게임제공", "복합유통게임"]
    )
    checks.append(MultiUseCheck(
        item="영상음향차단장치",
        requirement=MultiUseRequirement.MANDATORY if av_block_required else MultiUseRequirement.NOT_REQUIRED,
        detail=(
            "화재 신호 수신 시 영상·음향 자동 차단 장치 설치 의무"
            if av_block_required else
            "해당 업종 아님"
        ),
        legal_basis="다중이용업소법 §9 + 시행규칙 §9의2",
    ))

    # 4. 실내장식물 방염처리
    checks.append(MultiUseCheck(
        item="실내장식물 방염처리",
        requirement=MultiUseRequirement.MANDATORY,
        detail="카펫·커튼·벽지 등 방염성능 기준 이상 자재 사용 의무",
        legal_basis="소방시설법 §12 + 시행령 §20",
        note="방염 대상: 카펫·합판·섬유벽지·암막커튼 등; 방염성능검사 합격품 사용",
    ))

    # 5. 화재배상책임보험
    checks.append(MultiUseCheck(
        item="화재배상책임보험 가입",
        requirement=MultiUseRequirement.MANDATORY,
        detail="영업 개시 전 화재배상책임보험 가입 의무 (피해자 1인당 1억 5천만 원 이상)",
        legal_basis="다중이용업소법 §13의2",
        note="보험 미가입 시 영업정지·과태료 처분",
    ))

    # 6. 안전시설 등 완비증명서
    checks.append(MultiUseCheck(
        item="안전시설 완비증명서",
        requirement=MultiUseRequirement.MANDATORY,
        detail="영업 개시 전 소방서 안전시설 완비증명서 발급 필요",
        legal_basis="다중이용업소법 §9③",
        note="완비증명서 없이 영업 시 300만 원 이하 벌금",
    ))

    return MultiUseResult(
        is_multi_use=True,
        business_type=biz_type,
        checks=checks,
        summary=(
            f"다중이용업소 ({biz_type}) 해당 → "
            f"추가 소방·안전 규제 {len(checks)}개 항목 검토 필요"
        ),
    )
