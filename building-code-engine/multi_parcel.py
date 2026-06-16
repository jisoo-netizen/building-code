"""
다필지 동시 법규 검토 모듈
합필하지 않은 복수 필지를 각각 독립 유지하면서 통합 법규 검토.
실무: 인접 필지 묶음 개발, 지구단위계획 내 분할 소유 필지 등
"""

from __future__ import annotations

import io
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

from api.lookup import build_site_from_address, LookupResult
from api.vworld import ZoningInfo
from building_code_engine.use_change import BuildingUseCode
from building_code_engine.parking import calc_parking, ParkingInput, BuildingUse, total_required_spaces
from building_code_engine.sewage import calc_sewage, SewageInput, SewerUse
from building_code_engine.zoning import ZoneType, ZONE_TABLE, get_zone_regulation, check_bcr, check_far
from building_code_engine.report import SiteInfoFull, ReportItem


# ══════════════════════════════════════════════════════════════════════════════
#  collect_all_items 래퍼 (report.py 내부 함수 재사용)
# ══════════════════════════════════════════════════════════════════════════════

def _collect(site: SiteInfoFull) -> list[ReportItem]:
    """report.py의 모든 _check_* 를 모아서 반환."""
    from building_code_engine.report import (
        _check_use_change, _check_zoning, _check_parking_section,
        _check_sewage_section, _check_seismic_section, _check_fire_section,
        _check_evacuation_section, _check_setback_section,
        _check_accessibility_section, _check_elevator_section, _check_energy_section,
    )
    items: list[ReportItem] = []
    for fn in (
        _check_use_change, _check_zoning, _check_parking_section,
        _check_sewage_section, _check_seismic_section, _check_fire_section,
        _check_evacuation_section, _check_setback_section,
        _check_accessibility_section, _check_elevator_section, _check_energy_section,
    ):
        try:
            items += fn(site)
        except Exception:
            pass
    return items


# ══════════════════════════════════════════════════════════════════════════════
#  데이터 클래스
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParcelSummary:
    """필지 1개 검토 결과."""
    index: int                        # 1-based 순서
    address_input: str                # 입력 주소
    lookup: Optional[LookupResult]    # API 조회 결과 (None=오류)
    items: list[ReportItem]           # 법규 검토 항목
    api_log: str                      # API 호출 stdout 캡처
    error: str = ""                   # 오류 메시지 (조회 실패 시)

    # 편의 속성
    @property
    def ok(self) -> bool:
        return self.lookup is not None and not self.error

    @property
    def site_area(self) -> float:
        return self.lookup.building.site_area if self.ok else 0.0

    @property
    def total_floor_area(self) -> float:
        return self.lookup.building.total_floor_area if self.ok else 0.0

    @property
    def building_footprint(self) -> float:
        if not self.ok:
            return 0.0
        b = self.lookup.building
        return b.building_coverage or (b.site_area * 0.5)

    @property
    def zone_type(self) -> Optional[ZoneType]:
        return self.lookup.site.zone_type if self.ok else None

    @property
    def zone_name(self) -> str:
        return self.lookup.zoning.zone_name if self.ok else "알 수 없음"

    @property
    def parking_required(self) -> int:
        if not self.ok:
            return 0
        results = calc_parking(self.lookup.site.parking_after)
        return total_required_spaces(results)

    @property
    def parking_provided(self) -> int:
        return self.lookup.site.parking_provided if self.ok else 0

    @property
    def sewage_daily_L(self) -> float:
        if not self.ok:
            return 0.0
        results = calc_sewage(self.lookup.site.sewage_after)
        return sum(r.daily_volume_L for r in results)

    @property
    def critical_count(self) -> int:
        from building_code_engine.report import Severity
        return sum(1 for i in self.items if i.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        from building_code_engine.report import Severity
        return sum(1 for i in self.items if i.severity == Severity.WARNING)


@dataclass
class IntegratedResult:
    """통합 시뮬레이션 결과 (합산 기준)."""
    total_site_area: float
    total_floor_area: float
    total_footprint: float
    total_parking_required: int
    total_parking_provided: int
    total_sewage_daily_L: float

    # 용도지역 분석
    zone_list: list[str]               # 필지별 용도지역
    zone_consistent: bool              # 모두 동일 여부
    strictest_zone: Optional[ZoneType] # 가장 불리한 용도지역 (BCR 기준)

    # 통합 건폐율·용적률 (합산 대지 기준)
    combined_bcr_pct: float
    combined_far_pct: float
    bcr_limit: float
    far_limit: float
    bcr_pass: bool
    far_pass: bool

    # 주차 여부
    parking_deficit: int               # 부족 대수 (양수=부족)

    # 경고 목록
    warnings: list[str]


@dataclass
class MultiParcelReport:
    """다필지 검토 전체 결과."""
    parcels: list[ParcelSummary]
    integrated: IntegratedResult
    to_use_str: str
    to_use_code: BuildingUseCode

    @property
    def parcel_count(self) -> int:
        return len(self.parcels)

    @property
    def success_count(self) -> int:
        return sum(1 for p in self.parcels if p.ok)

    @property
    def fail_count(self) -> int:
        return sum(1 for p in self.parcels if not p.ok)


# ══════════════════════════════════════════════════════════════════════════════
#  내부 헬퍼
# ══════════════════════════════════════════════════════════════════════════════

def _bcr_rank(zone: ZoneType) -> float:
    """건폐율 기준 — 작을수록 불리(엄격)."""
    reg = get_zone_regulation(zone)
    return reg.building_coverage_ratio if reg else 999.0


def _far_rank(zone: ZoneType) -> float:
    reg = get_zone_regulation(zone)
    return reg.floor_area_ratio if reg else 9999.0


def _strictest_zone(zones: list[ZoneType]) -> Optional[ZoneType]:
    """건폐율 기준 가장 불리한(낮은) 용도지역 반환."""
    if not zones:
        return None
    return min(zones, key=_bcr_rank)


def _build_warnings(
    parcels: list[ParcelSummary],
    integrated: IntegratedResult,
) -> list[str]:
    warnings: list[str] = []

    # 용도지역 불일치
    if not integrated.zone_consistent:
        zones_str = " / ".join(sorted(set(integrated.zone_list)))
        warnings.append(
            f"용도지역 불일치: 필지별 용도지역이 다릅니다 ({zones_str}). "
            f"합필 없이 통합 개발 시 각 필지에 해당 용도지역 기준이 개별 적용됩니다."
        )
        warnings.append(
            f"불리한 기준 적용 원칙: 용도지역이 상이한 필지 포함 시 "
            f"통합 건폐율·용적률 검토는 가장 불리한 기준({integrated.strictest_zone.value if integrated.strictest_zone else '-'})을 준용합니다."
        )

    # 건폐율·용적률 초과
    if not integrated.bcr_pass:
        warnings.append(
            f"통합 건폐율 초과: 합산 {integrated.combined_bcr_pct:.1f}% > "
            f"기준 {integrated.bcr_limit:.0f}% (가장 불리한 용도지역 기준)."
        )
    if not integrated.far_pass:
        warnings.append(
            f"통합 용적률 초과: 합산 {integrated.combined_far_pct:.1f}% > "
            f"기준 {integrated.far_limit:.0f}%."
        )

    # 주차 부족
    if integrated.parking_deficit > 0:
        warnings.append(
            f"주차대수 부족: 합산 필요 {integrated.total_parking_required}대 > "
            f"계획 {integrated.total_parking_provided}대 "
            f"(부족 {integrated.parking_deficit}대)."
        )

    # API 실패 필지
    failed = [p for p in parcels if not p.ok]
    if failed:
        addrs = ", ".join(p.address_input for p in failed)
        warnings.append(f"API 조회 실패 필지: {addrs} — 통합 면적에서 제외됨.")

    # 단일 필지 부적합
    for p in parcels:
        if p.ok and p.critical_count > 0:
            warnings.append(
                f"필지 {p.index} ({p.address_input}): "
                f"부적합 항목 {p.critical_count}개 — 개별 검토 필요."
            )

    # 합필 관련 고정 주의사항
    warnings.append("합필 없이 통합 개발 시 각 필지 건폐율은 개별 대지 기준으로 각각 적용됩니다.")
    warnings.append("접도 의무(도로 접면 2m 이상)는 도로에 접한 필지를 기준으로 판단하며, 내부 필지는 통로 확보가 필요합니다.")

    return warnings


def _build_integrated(
    parcels: list[ParcelSummary],
    to_use_code: BuildingUseCode,
    to_use_str: str,
) -> IntegratedResult:
    ok_parcels = [p for p in parcels if p.ok]

    total_site   = sum(p.site_area for p in ok_parcels)
    total_fa     = sum(p.total_floor_area for p in ok_parcels)
    total_fp     = sum(p.building_footprint for p in ok_parcels)
    total_pk_req = sum(p.parking_required for p in ok_parcels)
    total_pk_prov= sum(p.parking_provided for p in ok_parcels)
    total_sew    = sum(p.sewage_daily_L for p in ok_parcels)

    zone_list = [p.zone_name for p in ok_parcels]
    zones_enum = [p.zone_type for p in ok_parcels if p.zone_type]
    zone_consistent = len(set(zone_list)) <= 1
    strictest = _strictest_zone(zones_enum)

    # 통합 건폐율·용적률 (가장 불리한 용도지역 기준)
    if strictest and total_site > 0:
        reg = get_zone_regulation(strictest)
        bcr_limit = reg.building_coverage_ratio if reg else 60.0
        far_limit = reg.floor_area_ratio if reg else 200.0
        combined_bcr = total_fp / total_site * 100
        combined_far = total_fa / total_site * 100
        # FAR 산정 시 지하층 제외 (간이 추정: 지상층 면적만)
        # 단순화: 총 연면적으로 최대 추정
        bcr_pass = combined_bcr <= bcr_limit
        far_pass = combined_far <= far_limit
    else:
        bcr_limit = far_limit = 0.0
        combined_bcr = combined_far = 0.0
        bcr_pass = far_pass = True

    parking_deficit = max(0, total_pk_req - total_pk_prov)

    integrated = IntegratedResult(
        total_site_area=round(total_site, 2),
        total_floor_area=round(total_fa, 2),
        total_footprint=round(total_fp, 2),
        total_parking_required=total_pk_req,
        total_parking_provided=total_pk_prov,
        total_sewage_daily_L=round(total_sew, 1),
        zone_list=zone_list,
        zone_consistent=zone_consistent,
        strictest_zone=strictest,
        combined_bcr_pct=round(combined_bcr, 1),
        combined_far_pct=round(combined_far, 1),
        bcr_limit=bcr_limit,
        far_limit=far_limit,
        bcr_pass=bcr_pass,
        far_pass=far_pass,
        parking_deficit=parking_deficit,
        warnings=[],
    )

    integrated.warnings = _build_warnings(parcels, integrated)
    return integrated


# ══════════════════════════════════════════════════════════════════════════════
#  메인 진입점
# ══════════════════════════════════════════════════════════════════════════════

def run_multi_parcel(
    addresses: list[str],
    to_use_code: BuildingUseCode = BuildingUseCode.FIRST_NEIGHBORHOOD,
    to_use_str: str = "제1종근린생활시설",
    road_width_m: float = 6.0,
    north_setback_m: Optional[float] = None,
    parking_provided: Optional[int] = None,
    progress_callback=None,        # callable(index, total, address) or None
) -> MultiParcelReport:
    """
    복수 주소를 순차 조회 후 다필지 통합 검토 리포트 반환.

    Parameters
    ----------
    addresses         : 조회할 주소 목록
    to_use_code       : 변경 후 용도 코드 (전 필지 동일 적용)
    to_use_str        : 변경 후 용도 표시명
    road_width_m      : 접면 도로 폭 (기본 6m)
    north_setback_m   : 정북 이격거리 실측값 (없으면 None)
    parking_provided  : 필지당 계획 주차대수 (None=자동 추정)
    progress_callback : 진행 상황 콜백 함수
    """
    parcels: list[ParcelSummary] = []

    for idx, addr in enumerate(addresses, start=1):
        addr = addr.strip()
        if not addr:
            continue

        if progress_callback:
            progress_callback(idx, len(addresses), addr)

        # stdout 캡처
        buf = io.StringIO()
        old_out = sys.stdout
        sys.stdout = buf

        try:
            result = build_site_from_address(
                address=addr,
                to_use_code=to_use_code,
                to_use_str=to_use_str,
                north_setback_m=north_setback_m,
                road_width_m=road_width_m,
                parking_provided=parking_provided,
            )
            sys.stdout = old_out
            api_log = buf.getvalue()

            items = _collect(result.site)
            parcel = ParcelSummary(
                index=idx,
                address_input=addr,
                lookup=result,
                items=items,
                api_log=api_log,
            )

        except Exception as e:
            sys.stdout = old_out
            api_log = buf.getvalue()
            parcel = ParcelSummary(
                index=idx,
                address_input=addr,
                lookup=None,
                items=[],
                api_log=api_log,
                error=f"{type(e).__name__}: {e}",
            )

        parcels.append(parcel)

        # API 호출 간격 (rate limit 방지)
        if idx < len(addresses):
            time.sleep(0.5)

    integrated = _build_integrated(parcels, to_use_code, to_use_str)

    return MultiParcelReport(
        parcels=parcels,
        integrated=integrated,
        to_use_str=to_use_str,
        to_use_code=to_use_code,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  텍스트 리포트 출력 (CLI 용)
# ══════════════════════════════════════════════════════════════════════════════

def print_multi_parcel_report(report: MultiParcelReport) -> str:
    lines: list[str] = []
    W = 72

    lines.append("=" * W)
    lines.append(f"  다필지 통합 법규 검토 리포트")
    lines.append(f"  변경 용도: {report.to_use_str} | 총 {report.parcel_count}필지")
    lines.append("=" * W)

    # ── 필지별 요약 ─────────────────────────────────────────────────────────
    lines.append("\n  [필지별 요약]")
    lines.append("  " + "-" * (W - 2))
    lines.append(f"  {'순서':<4}  {'주소':<28}  {'대지':<8}  {'연면적':<8}  "
                 f"{'용도지역':<14}  {'주차':<6}  {'판정'}")
    lines.append("  " + "-" * (W - 2))

    for p in report.parcels:
        if p.ok:
            b = p.lookup.building
            verdict = "적합" if p.critical_count == 0 else f"부적합({p.critical_count})"
            lines.append(
                f"  {p.index:<4}  {p.address_input[:26]:<28}  "
                f"{p.site_area:>6.1f}㎡  {p.total_floor_area:>6.1f}㎡  "
                f"{p.zone_name[:12]:<14}  {p.parking_required:>3}대   {verdict}"
            )
        else:
            lines.append(
                f"  {p.index:<4}  {p.address_input[:26]:<28}  "
                f"{'API 오류':>6}  {'':>6}  {'':14}  {'':6}  {p.error[:30]}"
            )

    lines.append("  " + "-" * (W - 2))

    # ── 통합 검토 결과 ───────────────────────────────────────────────────────
    ig = report.integrated
    lines.append("\n" + "=" * W)
    lines.append("  [통합 검토 결과]  (합산 기준 — 합필 없이 독립 필지 유지 가정)")
    lines.append("=" * W)

    lines.append(f"\n  총 대지면적     : {ig.total_site_area:>10,.2f} ㎡")
    lines.append(f"  총 건축면적(추정): {ig.total_footprint:>10,.2f} ㎡")
    lines.append(f"  총 연면적       : {ig.total_floor_area:>10,.2f} ㎡")
    lines.append(f"  통합 건폐율     : {ig.combined_bcr_pct:>6.1f}%  "
                 f"{'[적합]' if ig.bcr_pass else '[초과!]'} (기준 {ig.bcr_limit:.0f}%)")
    lines.append(f"  통합 용적률     : {ig.combined_far_pct:>6.1f}%  "
                 f"{'[적합]' if ig.far_pass else '[초과!]'} (기준 {ig.far_limit:.0f}%)")
    lines.append(f"\n  통합 필요 주차  : {ig.total_parking_required:>4} 대")
    lines.append(f"  통합 계획 주차  : {ig.total_parking_provided:>4} 대  "
                 f"{'[충족]' if ig.parking_deficit == 0 else f'[부족 {ig.parking_deficit}대]'}")
    lines.append(f"  통합 오수 발생량 : {ig.total_sewage_daily_L:>8,.1f} L/일")

    # 용도지역 분포
    lines.append(f"\n  용도지역 현황:")
    zone_counter: dict[str, int] = {}
    for z in ig.zone_list:
        zone_counter[z] = zone_counter.get(z, 0) + 1
    for z, cnt in sorted(zone_counter.items()):
        mark = " ← 가장 불리한 기준 적용" if (ig.strictest_zone and z == ig.strictest_zone.value) else ""
        lines.append(f"    {z}: {cnt}필지{mark}")
    if not ig.zone_consistent:
        lines.append("    ※ 용도지역 혼재 — 불리한 기준이 통합 산정에 적용됩니다.")

    # ── 종합 판정 ───────────────────────────────────────────────────────────
    all_ok = (
        ig.bcr_pass and ig.far_pass and ig.parking_deficit == 0
        and all(p.critical_count == 0 for p in report.parcels if p.ok)
    )
    lines.append("\n" + "-" * W)
    if all_ok:
        lines.append("  종합 판정: 이상 없음 — 통합 개발 법규 기준 충족")
    else:
        lines.append("  종합 판정: 검토 필요 — 아래 주의사항 확인")
    lines.append("-" * W)

    # ── 주의사항 ────────────────────────────────────────────────────────────
    lines.append("\n  [주의사항 및 권고]")
    for i, w in enumerate(ig.warnings, 1):
        # 긴 텍스트 줄바꿈
        words = w.split()
        line = f"  {i}. "
        for word in words:
            if len(line) + len(word) + 1 > W - 2:
                lines.append(line)
                line = "      " + word + " "
            else:
                line += word + " "
        lines.append(line.rstrip())

    lines.append("\n" + "=" * W)

    text = "\n".join(lines)
    return text


# ══════════════════════════════════════════════════════════════════════════════
#  CLI 직접 실행
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys as _sys

    _sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding="utf-8")

    TEST_ADDRESSES = [
        "서울특별시 동대문구 전농동 530-45",
        "서울특별시 동대문구 전농동 530-46",
        "서울특별시 동대문구 전농동 530-47",
    ]

    print("다필지 동시 검토 시작...")
    print(f"대상 필지 {len(TEST_ADDRESSES)}개:")
    for i, a in enumerate(TEST_ADDRESSES, 1):
        print(f"  {i}. {a}")
    print()

    report = run_multi_parcel(
        addresses=TEST_ADDRESSES,
        to_use_code=BuildingUseCode.FIRST_NEIGHBORHOOD,
        to_use_str="제1종근린생활시설",
        road_width_m=6.0,
    )

    output = print_multi_parcel_report(report)
    print(output)
