"""
정비구역 여부 확인
근거: 도시 및 주거환경정비법 (도시정비법) §2·§4·§5
     토지이음(eum.go.kr) 또는 서울시 도시계획 포털에서 정비구역 확인 필요
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RedevelStatus(str, Enum):
    IN_ZONE     = "정비구역 해당"
    NOT_IN_ZONE = "정비구역 아님"
    UNKNOWN     = "확인 필요"


@dataclass
class RedevelopmentResult:
    status: RedevelStatus
    zone_type: str       # 정비구역 종류 (재개발·재건축·도시환경·주거환경관리 등)
    detail: str
    action_required: bool
    note: str = ""


# 정비구역 종류 목록
REDEVEL_ZONE_TYPES: list[str] = [
    "주거환경개선구역",
    "재개발구역",
    "재건축구역",
    "도시환경정비구역",
    "주거환경관리구역",
    "가로주택정비구역",
    "소규모재건축구역",
    "빈집정비구역",
]


def check_redevelopment(
    is_in_zone: Optional[bool] = None,   # None = 미확인, True = 구역 내, False = 구역 외
    zone_type: str = "",                  # 정비구역 종류 (알고 있는 경우)
    address: str = "",                    # 주소 (안내용)
) -> RedevelopmentResult:
    """
    정비구역 해당 여부 판단 및 영향 안내.

    VWorld API로 정비구역 레이어 조회가 어려운 경우 수동 체크박스로 대체.
    """
    if is_in_zone is None:
        # 확인 불가 → 사용자 직접 확인 요청
        return RedevelopmentResult(
            status=RedevelStatus.UNKNOWN,
            zone_type="미확인",
            detail=(
                "정비구역 여부를 자동 조회할 수 없습니다. "
                "토지이음(eum.go.kr) → 해당 필지 검색 → '도시계획 정보'에서 직접 확인해 주세요."
            ),
            action_required=True,
            note=(
                "정비구역·정비예정구역 해당 시: "
                "① 정비계획이 본 검토 결과보다 우선 적용됩니다. "
                "② 조합설립·사업시행인가 이후 개별 건축허가 제한될 수 있습니다. "
                "③ 구청 도시재생·정비과에 사전 협의를 권장합니다."
            ),
        )

    if not is_in_zone:
        return RedevelopmentResult(
            status=RedevelStatus.NOT_IN_ZONE,
            zone_type="해당 없음",
            detail="정비구역·정비예정구역 외 필지 → 일반 건축허가 절차 적용",
            action_required=False,
        )

    # 정비구역 내
    zone_label = zone_type or "정비구역(종류 미확인)"
    impacts: list[str] = []

    if "재개발" in zone_label or "재건축" in zone_label:
        impacts += [
            "건축허가: 조합설립인가 이후 관리처분계획인가 전까지 원칙적 건축행위 제한 (§81)",
            "용도변경: 정비계획 용도로 제한 → 소규모 용도변경도 구청 사전 협의 필요",
            "건축물 가치 산정: 감정평가사 기준 분담금에 영향 → 리모델링 투자 주의",
        ]
    elif "주거환경관리" in zone_label or "가로주택" in zone_label:
        impacts += [
            "가로주택정비: 소규모 정비사업 → 공공지원을 받아 개별 건축 가능한 경우 있음",
            "구청 정비과 또는 SH공사에 사업시행 방향 확인 후 개별 건축허가 신청",
        ]
    else:
        impacts.append("구청 도시정비과에 사전 협의하여 건축행위 가능 여부 확인 필요")

    return RedevelopmentResult(
        status=RedevelStatus.IN_ZONE,
        zone_type=zone_label,
        detail=f"{zone_label} 해당 필지 — 개별 건축행위 전 정비계획 우선 확인 필요",
        action_required=True,
        note="\n".join(impacts),
    )
