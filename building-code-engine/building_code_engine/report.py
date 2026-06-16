"""
전면 통합 건축법규 검토 리포트
용도변경 전·후 비교 + 항목별 Critical / Warning / Info 자동 분류
섹션 순서: BUILDING INFO → SUMMARY → USE CHANGE → ZONE → PARKING → SEWAGE
           → SETBACK → FIRE SAFETY → EVACUATION → SEISMIC → ACCESSIBILITY
           → ELEVATOR → ENERGY → MULTI USE BUSINESS → TOURISM SPECIAL
           → REDEVELOPMENT → ACTION
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .zoning import ZoneType, get_zone_regulation, check_bcr, check_far
from .parking import (
    BuildingUse as ParkingUse,
    ParkingInput,
    compare_parking,
    calc_parking,
    total_required_spaces,
    calc_disabled_parking,
)
from .sunlight import check_north_setback
from .use_change import (
    BuildingUseCode,
    determine_use_change,
    classify_neighborhood,
    NeighborhoodBusinessType,
)
from .sewage import SewerUse, SewageInput, compare_sewage, calc_sewage
from .seismic import check_seismic
from .building_act import BuildingAction, determine_action
from .fire_safety import (
    check_fire_safety,
    has_sprinkler_installed,
    InstallStatus as FireStatus,
    FireSafetyItem,
)
from .evacuation import full_evacuation_check
from .setback import full_setback_check
from .accessibility import check_accessibility, InstallObligation
from .elevator import check_elevator
from .energy import check_energy, CertObligation
from .multi_use_business import check_multi_use_business, MultiUseRequirement
from .tourism_special import check_tourism_special, TourismCheckStatus
from .redevelopment_check import check_redevelopment, RedevelStatus


# ── 심각도 ─────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "CRITICAL"    # 부적합 → 공사 불가
    WARNING  = "WARNING"     # 검토 필요 / 조건부 적합
    INFO     = "INFO"        # 참고 / 적합


SEV_LABEL = {
    Severity.CRITICAL: "[부적합]",
    Severity.WARNING:  "[검토필요]",
    Severity.INFO:     "[적합]",
}


# ── 리포트 항목 ────────────────────────────────────────────────────────────

@dataclass
class ReportItem:
    section: str
    item: str
    severity: Severity
    status: str          # "적합" / "부적합" / "검토필요" / "해당없음"
    detail: str
    action: str = ""


# ── 필지 정보 ──────────────────────────────────────────────────────────────

@dataclass
class SiteInfoFull:
    """통합 필지 정보."""
    # 기본
    address: str
    zone_type: ZoneType
    site_area: float
    road_width_m: float

    # 건물 (용도변경이므로 구조 동일)
    building_footprint: float
    total_floor_area: float
    floor_area_per_floor: float
    building_height_m: float
    floors_above: int
    floors_below: int = 0
    construction_year: int = 2000
    basement_area: float = 0.0          # 지하층 면적 (㎡)
    is_windowless_floor: bool = False   # 무창층 여부

    # 이격거리
    north_setback_m: Optional[float] = None
    road_setback_m: float = 0.0
    adjacent_setback_m: float = 1.0

    # 용도변경
    from_use_code: BuildingUseCode = BuildingUseCode.MULTI_FAMILY
    to_use_code: BuildingUseCode = BuildingUseCode.FIRST_NEIGHBORHOOD
    from_use_str: str = "다가구주택"
    to_use_str: str = "제1종근린생활시설"
    to_use_detail_str: str = ""         # 세부 업종 (다중이용업소·관광숙박 판단용)

    # 주차
    parking_before: list[ParkingInput] = field(default_factory=list)
    parking_after: list[ParkingInput] = field(default_factory=list)
    parking_provided: int = 0

    # 오수
    sewage_before: list[SewageInput] = field(default_factory=list)
    sewage_after: list[SewageInput] = field(default_factory=list)

    # 소방
    has_sprinkler: bool = False
    both_sides_corridor: bool = True

    # 에너지
    is_new_build: bool = False
    is_public: bool = False

    # 근생 업종
    neighborhood_biz_type: Optional[NeighborhoodBusinessType] = None
    neighborhood_biz_area: float = 0.0

    # 다중이용업소
    is_multi_use_business: bool = False

    # 관광진흥법 숙박
    has_tourism_approval: bool = False
    distance_to_residential_m: Optional[float] = None

    # 정비구역
    is_in_redevel_zone: Optional[bool] = None   # None = 미확인
    redevel_zone_type: str = ""

    # 메타
    designer: str = ""
    note: str = ""


# ── 공통 헬퍼 ──────────────────────────────────────────────────────────────

def _item(
    section: str,
    item: str,
    ok: Optional[bool],
    detail: str,
    action: str = "",
    warn_only: bool = False,
) -> ReportItem:
    if ok is True:
        sev, status = Severity.INFO, "적합"
    elif ok is False:
        sev = Severity.WARNING if warn_only else Severity.CRITICAL
        status = "검토필요" if warn_only else "부적합"
    else:
        sev, status = Severity.WARNING, "검토필요"
    return ReportItem(section=section, item=item, severity=sev,
                      status=status, detail=detail, action=action)


# ── 섹션별 검토 함수 ────────────────────────────────────────────────────────

def _check_use_change(site: SiteInfoFull) -> list[ReportItem]:
    proc = determine_use_change(site.from_use_code, site.to_use_code)
    items = [_item(
        "용도변경", "절차 구분", None,
        f"{site.from_use_str} → {site.to_use_str} : {proc.category.value}",
        action=proc.reason, warn_only=True,
    )]
    if site.neighborhood_biz_type:
        cls = classify_neighborhood(site.neighborhood_biz_type, site.neighborhood_biz_area)
        items.append(_item(
            "용도변경", "근생 업종 분류",
            cls.applicable, cls.note,
            action="" if cls.applicable else "업종·면적 재검토 또는 2종 근생 허가 신청",
        ))
    return items


def _check_zoning(site: SiteInfoFull) -> list[ReportItem]:
    bcr = check_bcr(site.zone_type, site.site_area, site.building_footprint)
    far = check_far(site.zone_type, site.site_area, site.total_floor_area)
    return [
        _item("용도지역", "건폐율",
              bcr["pass"],
              f"계획 {bcr['actual_bcr']}% / 상한 {bcr['limit_bcr']}% (여유 {bcr['margin']:+.2f}%p)",
              action="건축면적 축소 필요" if not bcr["pass"] else ""),
        _item("용도지역", "용적률",
              far["pass"],
              f"계획 {far['actual_far']}% / 상한 {far['limit_far']}% (여유 {far['margin']:+.2f}%p)",
              action="연면적 축소 필요" if not far["pass"] else ""),
    ]


def _check_parking_section(site: SiteInfoFull) -> list[ReportItem]:
    items: list[ReportItem] = []
    if not site.parking_after:
        return [_item("주차", "주차대수", None, "주차 계획 미입력", warn_only=True)]

    cmp = compare_parking(
        site.parking_before, site.parking_after,
        provided_before=0,
        provided_after=site.parking_provided,
    )

    before_bases = "; ".join(r.calculation_basis for r in cmp.before_results) or "해당 없음"
    items.append(_item("주차", "①변경 전 필요대수", True,
                       f"{cmp.before_total}대 ({before_bases})"))

    after_bases = "; ".join(r.calculation_basis for r in cmp.after_results) or "해당 없음"
    items.append(_item("주차", "②변경 후 필요대수", True,
                       f"{cmp.after_total}대 ({after_bases})"))

    items.append(_item(
        "주차", "③추가 설치 의무(비고5)", cmp.pass_,
        (f"추가 의무 {cmp.additional_required}대 = "
         f"변경후 {cmp.after_total}대 − 변경전 {cmp.before_total}대 "
         f"/ 계획 {site.parking_provided}대"),
        action=f"주차 {cmp.deficit}대 부족 → 인근 부설주차장 확보 또는 주차장법 §19의2 협의"
               if not cmp.pass_ else "",
    ))

    d_after = cmp.disabled_after
    items.append(_item(
        "주차", "장애인전용주차",
        d_after.required_disabled == 0 or site.parking_provided >= d_after.required_disabled,
        f"계획 {site.parking_provided}대 기준 → 장애인전용 {d_after.required_disabled}면 필요 ({d_after.basis})",
        action="장애인전용 주차구역 미확보 시 편의증진법 위반" if d_after.required_disabled > 0 else "",
        warn_only=True,
    ))
    return items


def _check_sewage_section(site: SiteInfoFull) -> list[ReportItem]:
    if not site.sewage_after:
        return []
    cmp = compare_sewage(site.sewage_before, site.sewage_after)
    increase_pct = (
        (cmp["increase_L"] / cmp["total_before_L"] * 100)
        if cmp["total_before_L"] > 0 else 0
    )
    return [
        _item("오수·정화조", "일 오수발생량",
              cmp["increase_L"] <= 0,
              f"변경 전 {cmp['total_before_L']:.0f}L/일 → 변경 후 {cmp['total_after_L']:.0f}L/일 ({increase_pct:+.1f}%)",
              action="오수 증가 시 하수도 연결 용량 확인 및 정화조 증설 검토",
              warn_only=True),
        _item("오수·정화조", "정화조 용량",
              not cmp["septic_upgrade_needed"],
              f"변경 전 {cmp['septic_before_m3']:.1f}㎥ → 변경 후 {cmp['septic_after_m3']:.1f}㎥",
              action="정화조 용량 증설 필요" if cmp["septic_upgrade_needed"] else "",
              warn_only=True),
    ]


def _check_setback_section(site: SiteInfoFull) -> list[ReportItem]:
    checks = full_setback_check(
        road_width_m=site.road_width_m,
        building_line_setback_actual=site.road_setback_m,
        building_height_m=site.building_height_m,
        north_setback_actual=site.north_setback_m,
        adjacent_setback_actual=site.adjacent_setback_m,
        zone_type_str=site.zone_type.value,
    )
    return [
        _item(
            "이격거리", r.item, r.pass_,
            f"필요 {r.required_m}m / 계획 {r.actual_m}m" if r.required_m is not None else r.basis,
            action=r.note if not r.pass_ else "",
        )
        for r in checks
    ]


def _check_fire_section(site: SiteInfoFull) -> list[ReportItem]:
    checks = check_fire_safety(
        total_floor_area=site.total_floor_area,
        floors_above=site.floors_above,
        building_height_m=site.building_height_m,
        building_use_str=site.to_use_str,
        has_sprinkler=site.has_sprinkler,
        floors_below=site.floors_below,
        basement_area=site.basement_area,
        is_windowless_floor=site.is_windowless_floor,
    )
    # 스프링클러 설치 의무 여부 → evacuation.py 방화구획 완화 연계
    site._sprinkler_required = has_sprinkler_installed(checks)  # type: ignore[attr-defined]

    items: list[ReportItem] = []
    for c in checks:
        is_req = (c.status == FireStatus.REQUIRED)
        is_rec = (c.status == FireStatus.RECOMMENDED)
        items.append(_item(
            "소방시설", c.item.value,
            True if c.status == FireStatus.NOT_REQUIRED else None if is_rec else True,
            f"{c.status.value} - {c.basis}",
            action=f"{c.item.value} 설계 반영 필요" if is_req else "",
            warn_only=is_rec,
        ))
    return items


def _check_evacuation_section(site: SiteInfoFull) -> list[ReportItem]:
    # 스프링클러 설치 의무가 있으면 방화구획 3배 완화 적용
    sp_required = getattr(site, "_sprinkler_required", site.has_sprinkler)
    checks = full_evacuation_check(
        floor_room_area=site.floor_area_per_floor,
        floors_above=site.floors_above,
        floor_area_per_floor=site.floor_area_per_floor,
        has_sprinkler=site.has_sprinkler or sp_required,
        building_use_str=site.to_use_str,
        both_sides_corridor=site.both_sides_corridor,
    )
    return [
        _item(
            "피난·방화구획", r.item, r.pass_,
            f"{r.requirement} / 현황: {r.current_status}",
            action=r.note if not r.pass_ else "",
            warn_only=not r.pass_,
        )
        for r in checks
    ]


def _check_seismic_section(site: SiteInfoFull) -> list[ReportItem]:
    r = check_seismic(
        site.total_floor_area, site.floors_above,
        site.to_use_str, site.construction_year,
        is_new_build=site.is_new_build,
        building_height_m=site.building_height_m,
    )
    items = [_item(
        "내진설계", "내진설계 의무",
        not r.required or True,
        f"{r.grade.value} / {r.reason}",
        action="용도변경 시 구조 변경 없으면 기존 내진성능 검토서 제출 권고",
        warn_only=True,
    )]
    if r.retrofit_recommended:
        items.append(_item(
            "내진설계", "내진보강 권고", False, r.retrofit_note,
            action="내진성능 평가 용역 후 보강 설계 시행", warn_only=True,
        ))
    return items


def _check_accessibility_section(site: SiteInfoFull) -> list[ReportItem]:
    checks = check_accessibility(
        site.to_use_str, site.total_floor_area,
        site.floors_above, site.parking_provided,
        has_elevator=(site.floors_above >= 6),
    )
    items: list[ReportItem] = []
    for c in checks:
        items.append(_item(
            "장애인편의", c.item.value,
            True if c.obligation == InstallObligation.NOT_REQUIRED else
            True if c.obligation == InstallObligation.MANDATORY else None,
            f"{c.obligation.value} - {c.basis}",
            action=c.note if c.obligation == InstallObligation.MANDATORY else "",
            warn_only=(c.obligation == InstallObligation.RECOMMENDED),
        ))
    return items


def _check_elevator_section(site: SiteInfoFull) -> list[ReportItem]:
    checks = check_elevator(
        site.floors_above, site.total_floor_area,
        site.building_height_m, site.to_use_str,
    )
    return [
        _item(
            "승강기", c.elevator_type.value,
            not c.required or c.min_units == 0 or True,
            f"{'의무' if c.required else '불필요'} - 최소 {c.min_units}대 / {c.basis}",
            action=f"{c.elevator_type.value} {c.min_units}대 이상 설치 필요" if c.required and c.min_units > 0 else "",
            warn_only=c.required,
        )
        for c in checks
    ]


def _check_energy_section(site: SiteInfoFull) -> list[ReportItem]:
    checks = check_energy(
        site.total_floor_area, site.to_use_str,
        site.is_new_build, False, 0, site.is_public,
    )
    return [
        _item(
            "에너지", c.cert_type.value,
            c.obligation != CertObligation.MANDATORY,
            f"{c.obligation.value} - {c.basis}",
            action=c.note if c.obligation == CertObligation.MANDATORY else "",
            warn_only=True,
        )
        for c in checks
    ]


def _check_multi_use_section(site: SiteInfoFull) -> list[ReportItem]:
    detail_str = site.to_use_detail_str or site.to_use_str
    result = check_multi_use_business(
        use_detail_str=detail_str,
        floor_area=site.total_floor_area,
        floors_below=site.floors_below,
        is_explicitly_multi_use=site.is_multi_use_business,
    )
    if not result.is_multi_use:
        return []
    items: list[ReportItem] = []
    for c in result.checks:
        is_mand = (c.requirement == MultiUseRequirement.MANDATORY)
        items.append(_item(
            "다중이용업소", c.item,
            True if c.requirement == MultiUseRequirement.NOT_REQUIRED else
            None if not is_mand else True,
            f"{c.requirement.value} - {c.detail}",
            action=f"{c.item} 설계 반영 / 신청 필요" if is_mand else "",
            warn_only=not is_mand,
        ))
    return items


def _check_tourism_section(site: SiteInfoFull) -> list[ReportItem]:
    detail_str = site.to_use_detail_str or site.to_use_str
    result = check_tourism_special(
        use_detail_str=detail_str,
        zone_type_str=site.zone_type.value,
        road_width_m=site.road_width_m,
        building_height_m=site.building_height_m,
        adjacent_setback_m=site.adjacent_setback_m,
        distance_to_residential_m=site.distance_to_residential_m,
        has_tourism_approval=site.has_tourism_approval,
    )
    if not result.is_tourism_lodging:
        return []
    items: list[ReportItem] = []
    for c in result.checks:
        ok = (c.status == TourismCheckStatus.PASS)
        fail = (c.status == TourismCheckStatus.FAIL)
        items.append(_item(
            "관광진흥법특례", c.item,
            ok if (ok or fail) else None,
            c.detail,
            action=c.note if fail else "",
            warn_only=not fail,
        ))
    return items


def _check_redevelopment_section(site: SiteInfoFull) -> list[ReportItem]:
    result = check_redevelopment(
        is_in_zone=site.is_in_redevel_zone,
        zone_type=site.redevel_zone_type,
        address=site.address,
    )
    if result.status == RedevelStatus.NOT_IN_ZONE:
        return []
    sev_ok = (result.status == RedevelStatus.UNKNOWN)
    return [_item(
        "정비구역", "정비구역 여부",
        False if result.status == RedevelStatus.IN_ZONE else None,
        result.detail,
        action=result.note,
        warn_only=True,
    )]


# ── 메인 리포트 생성 ────────────────────────────────────────────────────────

SECTION_ORDER: list[str] = [
    "용도변경", "용도지역", "주차", "오수·정화조", "이격거리",
    "소방시설", "피난·방화구획", "내진설계",
    "장애인편의", "승강기", "에너지",
    "다중이용업소", "관광진흥법특례", "정비구역",
]


def generate_report(site: SiteInfoFull) -> str:
    """전체 법규 검토 리포트 생성."""

    # ── 섹션 수집 (선언 순서 = 출력 순서) ────────────────────────────────
    all_items: list[ReportItem] = []
    all_items += _check_use_change(site)
    all_items += _check_zoning(site)
    all_items += _check_parking_section(site)
    all_items += _check_sewage_section(site)
    all_items += _check_setback_section(site)
    all_items += _check_fire_section(site)
    all_items += _check_evacuation_section(site)
    all_items += _check_seismic_section(site)
    all_items += _check_accessibility_section(site)
    all_items += _check_elevator_section(site)
    all_items += _check_energy_section(site)
    all_items += _check_multi_use_section(site)
    all_items += _check_tourism_section(site)
    all_items += _check_redevelopment_section(site)

    # ── 심각도 정렬 ────────────────────────────────────────────────────────
    order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    sorted_by_sev = sorted(all_items, key=lambda x: order[x.severity])

    counts = {s: 0 for s in Severity}
    for i in all_items:
        counts[i.severity] += 1

    lines: list[str] = []

    def div(char="=", width=68):
        lines.append(char * width)

    def h1(txt: str):
        div()
        lines.append(f"  {txt}")
        div()

    def h2(txt: str):
        lines.append(f"\n{'─'*64}")
        lines.append(f"  {txt}")
        lines.append("─" * 64)

    # ── BUILDING INFO ──────────────────────────────────────────────────────
    h1("건축법규 전체 검토 리포트 (용도변경)")
    lines.append(f"  대지 위치  : {site.address}")
    lines.append(f"  용도지역   : {site.zone_type.value}")
    lines.append(f"  대지면적   : {site.site_area:,.2f} ㎡")
    lines.append(f"  용도변경   : {site.from_use_str}  →  {site.to_use_str}")
    if site.to_use_detail_str:
        lines.append(f"  세부 용도  : {site.to_use_detail_str}")
    lines.append(f"  연면적     : {site.total_floor_area:,.2f} ㎡  /  {site.floors_above}층")
    if site.designer:
        lines.append(f"  설계자     : {site.designer}")
    if site.note:
        lines.append(f"  비고       : {site.note}")

    # ── SUMMARY ────────────────────────────────────────────────────────────
    h2("종합 통계")
    lines.append(
        f"  부적합(CRITICAL) {counts[Severity.CRITICAL]}건 / "
        f"검토필요(WARNING) {counts[Severity.WARNING]}건 / "
        f"적합(INFO) {counts[Severity.INFO]}건"
    )
    overall = "전 항목 이상 없음" if counts[Severity.CRITICAL] == 0 else "즉시 조치 필요 항목 있음"
    lines.append(f"  최종 판정 : {overall}")

    # ── 전체 항목 표 (심각도 정렬) ────────────────────────────────────────
    h2("항목별 검토 결과 (우선순위 순)")
    col_w = [14, 18, 20, 8]
    header = f"  {'섹션':<{col_w[0]}} {'항목':<{col_w[1]}} {'핵심 내용':<{col_w[2]}} {'판정':>{col_w[3]}}"
    lines.append(header)
    lines.append("  " + "-" * (sum(col_w) + 3))
    for it in sorted_by_sev:
        detail_short = it.detail[:38] + ".." if len(it.detail) > 38 else it.detail
        label = SEV_LABEL[it.severity]
        lines.append(
            f"  {it.section:<{col_w[0]}} {it.item:<{col_w[1]}} "
            f"{detail_short:<{col_w[2]}} {label:>{col_w[3]}}"
        )

    # ── 섹션별 상세 (선언 순서) ────────────────────────────────────────────
    def _section_order(it: ReportItem) -> int:
        try:
            return SECTION_ORDER.index(it.section)
        except ValueError:
            return 99

    current_section = ""
    for it in sorted(all_items, key=_section_order):
        if it.section != current_section:
            h2(f"[{it.section}] 상세")
            current_section = it.section
        lines.append(f"\n  [{SEV_LABEL[it.severity]}] {it.item}")
        lines.append(f"    내용  : {it.detail}")
        if it.action:
            lines.append(f"    조치  : {it.action}")

    # ── ACTION — 우선 조치 항목 ────────────────────────────────────────────
    action_items = [i for i in sorted_by_sev if i.action and i.severity != Severity.INFO]
    if action_items:
        h2("우선 조치 항목 요약")
        for idx, it in enumerate(action_items, 1):
            lines.append(f"  {idx:2}. [{SEV_LABEL[it.severity]}] {it.section} > {it.item}")
            lines.append(f"      → {it.action}")

    lines.append("")
    div()
    lines.append("  본 리포트는 입력된 설계 정보 기반 자동 검토 결과입니다.")
    lines.append("  최종 판단은 반드시 허가권자 및 담당 건축사 확인 후 진행하세요.")
    div()
    lines.append("")

    return "\n".join(lines)
