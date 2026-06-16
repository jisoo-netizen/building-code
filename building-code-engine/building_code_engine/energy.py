"""
에너지절약계획서 제출 의무 및 녹색건축 인증 대상 판단
근거: 녹색건축물 조성 지원법 + 건축물 에너지절약설계기준 (국토부 고시)
"""

from dataclasses import dataclass
from enum import Enum


class EnergyCertType(str, Enum):
    ENERGY_PLAN = "에너지절약계획서"
    EFFICIENCY_RATING = "건축물 에너지효율등급 인증"
    GREEN_BUILDING = "녹색건축 인증 (G-SEED)"
    ZERO_ENERGY = "제로에너지건축물 인증"


class CertObligation(str, Enum):
    MANDATORY = "의무 제출/인증"
    RECOMMENDED = "권장"
    NOT_REQUIRED = "해당 없음"


@dataclass
class EnergyCheck:
    cert_type: EnergyCertType
    obligation: CertObligation
    basis: str
    note: str = ""


# 에너지절약계획서 의무 대상 용도
ENERGY_PLAN_USES = {
    "업무시설", "판매시설", "숙박시설", "의료시설",
    "교육연구시설", "문화및집회시설", "운동시설",
    "제1종근린생활시설", "제2종근린생활시설",
    "공동주택", "단독주택",
}

# 에너지효율등급·제로에너지 의무 대상 (공공건축물 기준)
PUBLIC_USES = {"공공업무시설", "공공교육시설", "공공의료시설"}


def check_energy(
    total_floor_area: float,
    building_use_str: str,
    is_new_build: bool,
    is_extension: bool,
    extension_area: float = 0,
    is_public: bool = False,
) -> list[EnergyCheck]:
    """
    에너지절약계획서 제출 의무 + 인증 대상 판단.

    에너지절약계획서 제출 의무 (녹색건축물법 §14):
    - 연면적 500㎡ 이상 건축물 신축·증축(증축 부분 500㎡ 이상)
    - 대상 용도에 한함

    에너지효율등급 의무 (녹색건축물법 §17):
    - 공공기관 연면적 3,000㎡ 이상 신축
    - 아파트 30세대 이상 신축
    """
    results: list[EnergyCheck] = []
    area = extension_area if is_extension else total_floor_area

    # ── 에너지절약계획서 ─────────────────────────────────────────────────────
    plan_required = (
        (is_new_build or (is_extension and extension_area >= 500))
        and area >= 500
        and building_use_str in ENERGY_PLAN_USES
    )
    results.append(EnergyCheck(
        cert_type=EnergyCertType.ENERGY_PLAN,
        obligation=CertObligation.MANDATORY if plan_required else CertObligation.NOT_REQUIRED,
        basis=f"연면적 {area:,.0f}㎡ / 용도: {building_use_str} / {'신축' if is_new_build else '증축'}",
        note="허가 신청 시 에너지절약계획서 첨부 (녹색건축물법 §14)",
    ))

    # ── 에너지효율등급 인증 ─────────────────────────────────────────────────
    efficiency_mandatory = (
        is_public
        and is_new_build
        and total_floor_area >= 3000
    ) or (
        building_use_str == "공동주택"
        and is_new_build
        and total_floor_area >= 3000
    )
    efficiency_recommended = (
        (not efficiency_mandatory)
        and total_floor_area >= 1000
        and building_use_str in ENERGY_PLAN_USES
    )
    results.append(EnergyCheck(
        cert_type=EnergyCertType.EFFICIENCY_RATING,
        obligation=(
            CertObligation.MANDATORY if efficiency_mandatory
            else CertObligation.RECOMMENDED if efficiency_recommended
            else CertObligation.NOT_REQUIRED
        ),
        basis=f"연면적 {total_floor_area:,.0f}㎡ / 공공: {is_public}",
        note="최소 에너지효율등급 5등급 이상 달성 권장",
    ))

    # ── 녹색건축 인증 (G-SEED) ────────────────────────────────────────────
    gseed_mandatory = is_public and is_new_build and total_floor_area >= 3000
    results.append(EnergyCheck(
        cert_type=EnergyCertType.GREEN_BUILDING,
        obligation=CertObligation.MANDATORY if gseed_mandatory else CertObligation.RECOMMENDED,
        basis=f"공공건축물 연면적 {total_floor_area:,.0f}㎡ / 신축 여부: {is_new_build}",
        note="민간: 권장 (세제혜택·용적률 인센티브 적용 가능)",
    ))

    # ── 제로에너지건축물 인증 ────────────────────────────────────────────────
    zeb_mandatory = is_public and is_new_build and total_floor_area >= 1000
    results.append(EnergyCheck(
        cert_type=EnergyCertType.ZERO_ENERGY,
        obligation=CertObligation.MANDATORY if zeb_mandatory else CertObligation.NOT_REQUIRED,
        basis=f"공공건축물 1,000㎡ 이상 신축 → 2023년부터 의무",
        note="민간 아파트 30세대 이상: 2025년부터 의무화 예정",
    ))

    return results
