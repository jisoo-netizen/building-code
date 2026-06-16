"""
COD-ESTATE — 건축법규 자동 검토 웹앱
streamlit run app.py
"""

import streamlit as st
import traceback

# ── 페이지 설정 (반드시 첫 번째) ────────────────────────────────────────────
st.set_page_config(
    page_title="COD-ESTATE | 건축법규 검토",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 전역 CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

/* ── 기본 리셋 ── */
html, body, [class*="css"] {
    font-family: 'Pretendard', 'Inter', 'Noto Sans KR', sans-serif;
    background: #ffffff;
    color: #0f0f0f;
}
.stApp { background: #ffffff; }

/* ── 전체 폭 840px 중앙 정렬 ── */
.block-container {
    max-width: 840px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* ══════════════════════════════════════════
   타이포그래피 3단계 계층
   Tier 1 — 32px bold  (페이지 타이틀)
   Tier 2 — 18px 600   (섹션·카테고리·라벨)
   Tier 3 — 14px 400   (본문·데이터·안내)
   워드마크 — 52px 700  (별도)
══════════════════════════════════════════ */

/* Tier 1 */
.tier1-title {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: 0.02em;
    color: #0f0f0f;
    line-height: 1.2;
}

/* Tier 2 */
.tier2-heading {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: #0f0f0f;
    line-height: 1.4;
}

/* Tier 3 */
.tier3-body {
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0.01em;
    color: #444;
    line-height: 1.6;
}

/* ── 헤더 ── */
.ce-header {
    padding: 2.8rem 0 1.8rem;
    border-bottom: 1px solid #0f0f0f;
    margin-bottom: 2.4rem;
}
.ce-wordmark {
    font-family: 'Inter', sans-serif;
    font-size: 52px;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #0f0f0f;
    text-transform: uppercase;
    line-height: 1;
}
.ce-title {
    font-size: 14px;
    font-weight: 300;
    letter-spacing: 0.08em;
    color: #888;
    margin-top: 0.6rem;
}

/* ── 섹션 헤더 ── */
.section-hd {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.22em;
    color: #888;
    text-transform: uppercase;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 0.35rem;
    margin: 1.8rem 0 0.9rem;
}

/* ── 입력 레이블 (■ ▲ 마커) ── */
.input-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #0f0f0f;
    margin-bottom: 0.35rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.input-label .marker {
    font-size: 9px;
    color: #0f0f0f;
    line-height: 1;
}

/* ── 자동 조회 안내 라벨 (Tier 3) ── */
.auto-label {
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0.01em;
    color: #aaa;
    margin-top: 0.2rem;
}

/* ── 입력창 높이 통일 ── */
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] > div > div {
    height: 42px !important;
    min-height: 42px !important;
    font-size: 14px !important;
}

/* ── 정보 카드 ── */
.info-card {
    background: #fafafa;
    border: 1px solid #e8e8e8;
    border-left: 2px solid #0f0f0f;
    padding: 0.85rem 1rem;
    margin-bottom: 0.5rem;
}
.info-label {
    font-size: 11px;
    font-weight: 700;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.14em;
}
.info-value {
    font-family: 'Inter', monospace;
    font-size: 14px;
    font-weight: 500;
    color: #0f0f0f;
    margin-top: 0.2rem;
}

/* ── 판정 뱃지 — Tier 3 기준, 텍스트+보더만 ── */
.badge-ok   { color:#2d6a4f; border:1px solid #2d6a4f; padding:2px 10px;
              font-size:14px; font-weight:600; letter-spacing:0.04em; text-transform:uppercase; }
.badge-warn { color:#8a6800; border:1px solid #8a6800; padding:2px 10px;
              font-size:14px; font-weight:600; letter-spacing:0.04em; text-transform:uppercase; }
.badge-fail { color:#9b2335; border:1px solid #9b2335; padding:2px 10px;
              font-size:14px; font-weight:600; letter-spacing:0.04em; text-transform:uppercase; }
.badge-na   { color:#999; border:1px solid #ccc; padding:2px 10px;
              font-size:14px; font-weight:600; letter-spacing:0.04em; text-transform:uppercase; }

/* ── 조치항목 (Tier 3) ── */
.action-item {
    border-left: 2px solid #8a6800;
    padding: 0.55rem 1rem;
    margin: 0.35rem 0;
    font-size: 14px;
    font-weight: 400;
    color: #444;
    background: #fefdf5;
}
.action-crit {
    border-left: 2px solid #9b2335;
    background: #fdf8f8;
    color: #444;
}

/* ── 구분선 ── */
.divider { border: none; border-top: 1px solid #ebebeb; margin: 0.9rem 0; }

/* ── 푸터 (Tier 3 이하) ── */
.ce-footer {
    margin-top: 3.5rem;
    padding-top: 1rem;
    border-top: 1px solid #e0e0e0;
    font-size: 11px;
    letter-spacing: 0.16em;
    color: #ccc;
    text-align: center;
    text-transform: uppercase;
}

/* ── 버튼 (Tier 3) ── */
.stButton > button {
    background: #0f0f0f !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 0 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    letter-spacing: 0.12em !important;
    font-size: 14px !important;
    height: 42px !important;
}
.stButton > button:hover { background: #2d6a4f !important; }

/* ── 다운로드 버튼 (Tier 3) ── */
.stDownloadButton > button {
    background: transparent !important;
    color: #0f0f0f !important;
    border: 1px solid #0f0f0f !important;
    border-radius: 0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    letter-spacing: 0.08em !important;
}

/* ── Streamlit 내부 텍스트 Tier 3 기준 통일 ── */
div[data-testid="stExpander"] summary p,
div[data-testid="stCaption"] p,
.stMarkdown p {
    font-size: 14px !important;
}
div[data-testid="metric-container"] label {
    font-size: 11px !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #888;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 18px !important;
    font-weight: 600 !important;
}
</style>
""", unsafe_allow_html=True)


# ── 헬퍼: 판정 뱃지 ──────────────────────────────────────────────────────────

def badge(status: str) -> str:
    if status == "적합":
        return '<span class="badge-ok">OK</span>'
    if status == "검토필요":
        return '<span class="badge-warn">REVIEW</span>'
    if status == "부적합":
        return '<span class="badge-fail">FAIL</span>'
    return '<span class="badge-na">N/A</span>'


# ── 엔진 임포트 ──────────────────────────────────────────────────────────────

from api.lookup import build_site_from_address, LookupResult
from building_code_engine.use_change import BuildingUseCode
from building_code_engine.report import (
    SiteInfoFull, generate_report,
    _check_use_change, _check_zoning, _check_parking_section,
    _check_sewage_section, _check_seismic_section, _check_fire_section,
    _check_evacuation_section, _check_setback_section,
    _check_accessibility_section, _check_elevator_section, _check_energy_section,
    Severity, ReportItem,
)
from multi_parcel import run_multi_parcel, print_multi_parcel_report, MultiParcelReport, ParcelSummary


# ── 용도 선택지 (세분화) ──────────────────────────────────────────────────────

USE_OPTIONS: dict[str, tuple[BuildingUseCode, str]] = {
    # 1종 근린생활시설
    "1종근생 — 슈퍼마켓·일용품점 (1000㎡ 미만)":        (BuildingUseCode.FIRST_NEIGHBORHOOD, "제1종근린생활시설"),
    "1종근생 — 휴게음식점·제과점 (300㎡ 미만)":          (BuildingUseCode.FIRST_NEIGHBORHOOD, "제1종근린생활시설"),
    "1종근생 — 의원·치과·한의원·조산원":                  (BuildingUseCode.FIRST_NEIGHBORHOOD, "제1종근린생활시설"),
    "1종근생 — 탁구장·체육도장 (500㎡ 미만)":            (BuildingUseCode.FIRST_NEIGHBORHOOD, "제1종근린생활시설"),
    "1종근생 — 동사무소·파출소·소방서 등 공공업무":        (BuildingUseCode.FIRST_NEIGHBORHOOD, "제1종근린생활시설"),
    "1종근생 — 마을회관·공중화장실":                      (BuildingUseCode.FIRST_NEIGHBORHOOD, "제1종근린생활시설"),
    "1종근생 — 마을공동작업소":                           (BuildingUseCode.FIRST_NEIGHBORHOOD, "제1종근린생활시설"),
    # 2종 근린생활시설
    "2종근생 — 일반음식점":                               (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 휴게음식점·제과점 (300㎡ 이상)":           (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 학원·직업훈련소 (500㎡ 미만)":             (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 독서실·고시텔":                            (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 일반업무시설·사무소 (500㎡ 미만)":         (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 다중생활시설 (고시원)":                    (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 제조업소·수리점 (500㎡ 미만)":             (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 게임제공업소·노래연습장":                   (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    "2종근생 — 골프연습장·볼링장 등 운동시설":             (BuildingUseCode.SECOND_NEIGHBORHOOD, "제2종근린생활시설"),
    # 기타 용도
    "업무시설 — 사무소·오피스":                           (BuildingUseCode.OFFICE,              "업무시설"),
    "숙박시설 — 호텔·게스트하우스":                       (BuildingUseCode.ACCOMMODATION,       "숙박시설"),
    "판매시설 — 쇼핑·마트":                               (BuildingUseCode.RETAIL,              "판매시설"),
    "의료시설 — 병원·요양원":                             (BuildingUseCode.MEDICAL,             "의료시설"),
    "교육연구시설 — 학교·연구소":                         (BuildingUseCode.EDUCATION,           "교육연구시설"),
}

SECTION_LABELS: dict[str, str] = {
    "용도변경":     "USE CHANGE — 용도변경",
    "용도지역":     "ZONE — 용도지역",
    "주차":        "PARKING — 주차",
    "오수·정화조":  "SEWAGE — 오수·정화조",
    "내진설계":     "SEISMIC — 내진설계",
    "소방시설":     "FIRE SAFETY — 소방시설",
    "피난·방화구획": "EVACUATION — 피난·방화구획",
    "이격거리":     "SETBACK — 이격거리",
    "장애인편의":   "ACCESSIBILITY — 장애인편의",
    "승강기":       "ELEVATOR — 승강기",
    "에너지":       "ENERGY — 에너지",
}


# ── 결과 렌더링 ───────────────────────────────────────────────────────────────

def render_building_info(result: LookupResult):
    b = result.building
    z = result.zoning

    st.markdown('<p class="section-hd">BUILDING INFO — 건축물 기본 정보</p>', unsafe_allow_html=True)

    cols = st.columns(4)
    info = [
        ("대지면적",  f"{b.site_area:,.1f} ㎡"),
        ("연면적",    f"{b.total_floor_area:,.1f} ㎡"),
        ("층수",      f"지하{b.floors_below} / 지상{b.floors_above}"),
        ("건물높이",  f"{b.height_m:.1f} m"),
        ("용도지역",  z.zone_name or "—"),
        ("기존 용도", b.sub_use or b.main_use or "—"),
        ("구조",      b.structure or "—"),
        ("사용승인",  f"{b.construction_year}년" if b.construction_year else "—"),
    ]
    for i, (label, value) in enumerate(info):
        with cols[i % 4]:
            st.markdown(
                f'<div class="info-card">'
                f'<div class="info-label">{label}</div>'
                f'<div class="info-value">{value}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        f'<div style="font-size:0.73rem;color:#888;margin-top:0.15rem;">'
        f'■ {b.address}  |  도로명: {b.address_road or "—"}  |  PNU: {result.parcel.pnu}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_results_table(items: list[ReportItem]):
    sorted_items = sorted(items, key=lambda x: (
        {"CRITICAL": 0, "WARNING": 1, "INFO": 2}[x.severity.value], x.section
    ))

    counts = {s: 0 for s in Severity}
    for it in sorted_items:
        counts[it.severity] += 1

    st.markdown('<p class="section-hd">SUMMARY — 종합 통계</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("부적합", counts[Severity.CRITICAL])
    c2.metric("검토필요", counts[Severity.WARNING])
    c3.metric("적합", counts[Severity.INFO])

    overall_ok = counts[Severity.CRITICAL] == 0
    if overall_ok:
        st.success("**최종 판정: 전 항목 이상 없음** — 부적합 항목이 없습니다.")
    else:
        st.error("**최종 판정: 즉시 조치 필요** — 부적합 항목을 확인하세요.")

    st.markdown('<p class="section-hd">RESULT — 항목별 검토 결과</p>', unsafe_allow_html=True)

    by_section = {}
    for it in sorted_items:
        by_section.setdefault(it.section, []).append(it)

    for section, sec_items in by_section.items():
        worst = min(sec_items, key=lambda x: {"CRITICAL":0,"WARNING":1,"INFO":2}[x.severity.value])
        icon = "▪" if worst.severity == Severity.CRITICAL else ("▫" if worst.severity == Severity.WARNING else "·")
        label = SECTION_LABELS.get(section, section)

        with st.expander(f"{icon} {label}  [{len(sec_items)}]", expanded=(worst.severity != Severity.INFO)):
            for it in sec_items:
                cols = st.columns([3, 4, 2])
                with cols[0]:
                    st.markdown(f"**{it.item}**")
                with cols[1]:
                    st.caption(it.detail[:80] + ("…" if len(it.detail) > 80 else ""))
                with cols[2]:
                    st.markdown(badge(it.status), unsafe_allow_html=True)
                if it.action:
                    st.markdown(
                        f'<div class="action-item">→ {it.action}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown('<hr class="divider"/>', unsafe_allow_html=True)


def render_action_summary(items: list[ReportItem]):
    action_items = [
        it for it in items
        if it.action and it.severity in (Severity.CRITICAL, Severity.WARNING)
    ]
    if not action_items:
        return

    action_items.sort(key=lambda x: {"CRITICAL":0,"WARNING":1,"INFO":2}[x.severity.value])
    st.markdown('<p class="section-hd">ACTION — 우선 조치사항</p>', unsafe_allow_html=True)

    for i, it in enumerate(action_items, 1):
        cls = "action-crit" if it.severity == Severity.CRITICAL else "action-item"
        icon = "▪" if it.severity == Severity.CRITICAL else "▫"
        st.markdown(
            f'<div class="{cls}">'
            f'<strong>{i}. {icon} {it.section} › {it.item}</strong><br/>'
            f'<span style="color:#555;">{it.action}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def collect_all_items(site: SiteInfoFull) -> list[ReportItem]:
    items: list[ReportItem] = []
    items += _check_use_change(site)
    items += _check_zoning(site)
    items += _check_parking_section(site)
    items += _check_sewage_section(site)
    items += _check_seismic_section(site)
    items += _check_fire_section(site)
    items += _check_evacuation_section(site)
    items += _check_setback_section(site)
    items += _check_accessibility_section(site)
    items += _check_elevator_section(site)
    items += _check_energy_section(site)
    return items


# ── 다필지 탭 렌더링 ──────────────────────────────────────────────────────────

def render_parcel_card(p: ParcelSummary):
    if not p.ok:
        st.error(f"**필지 {p.index}** `{p.address_input}` — API 조회 실패: {p.error}")
        return

    b = p.lookup.building
    z = p.lookup.zoning

    verdict_color = "badge-ok" if p.critical_count == 0 else "badge-fail"
    verdict_text  = "OK" if p.critical_count == 0 else f"FAIL {p.critical_count}건"

    st.markdown(
        f'<div class="info-card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span class="info-label">PARCEL {p.index}</span>'
        f'<span class="{verdict_color}">{verdict_text}</span>'
        f'</div>'
        f'<div class="info-value" style="font-size:0.9rem;margin-top:4px;">{p.address_input}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(6)
    metrics = [
        ("대지면적",  f"{b.site_area:,.1f} ㎡"),
        ("연면적",    f"{b.total_floor_area:,.1f} ㎡"),
        ("층수",      f"B{b.floors_below}/F{b.floors_above}"),
        ("용도지역",  z.zone_name[:8] if z.zone_name else "—"),
        ("필요 주차", f"{p.parking_required}대"),
        ("오수",      f"{p.sewage_daily_L:,.0f} L/일"),
    ]
    for i, (lbl, val) in enumerate(metrics):
        with cols[i]:
            st.metric(lbl, val)

    with st.expander(f"필지 {p.index} 상세 법규 검토", expanded=False):
        render_results_table(p.items)
        render_action_summary(p.items)
        with st.expander("API LOG", expanded=False):
            st.code(p.api_log, language=None)


def render_integrated_result(report: MultiParcelReport):
    ig = report.integrated

    st.markdown('<p class="section-hd">AREA — 통합 면적 현황</p>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 대지면적", f"{ig.total_site_area:,.1f} ㎡")
    c2.metric("총 연면적",   f"{ig.total_floor_area:,.1f} ㎡")
    c3.metric("통합 건폐율", f"{ig.combined_bcr_pct:.1f}%",
              delta=f"한도 {ig.bcr_limit:.0f}%", delta_color="off")
    c4.metric("통합 용적률", f"{ig.combined_far_pct:.1f}%",
              delta=f"한도 {ig.far_limit:.0f}%", delta_color="off")

    bcr_badge = badge("적합") if ig.bcr_pass else badge("부적합")
    far_badge = badge("적합") if ig.far_pass else badge("부적합")
    st.markdown(
        f"건폐율 판정 {bcr_badge} &nbsp;&nbsp; 용적률 판정 {far_badge}",
        unsafe_allow_html=True,
    )

    st.markdown('<p class="section-hd">PARKING · SEWAGE — 통합 주차·오수</p>', unsafe_allow_html=True)
    cp1, cp2, cp3 = st.columns(3)
    cp1.metric("합산 필요 주차", f"{ig.total_parking_required}대")
    cp2.metric("합산 계획 주차", f"{ig.total_parking_provided}대",
               delta=f"{'충족' if ig.parking_deficit == 0 else f'부족 {ig.parking_deficit}대'}",
               delta_color="normal" if ig.parking_deficit == 0 else "inverse")
    cp3.metric("통합 오수 발생량", f"{ig.total_sewage_daily_L:,.0f} L/일")

    st.markdown('<p class="section-hd">ZONE — 용도지역 분포</p>', unsafe_allow_html=True)
    zone_counter: dict[str, int] = {}
    for z in ig.zone_list:
        zone_counter[z] = zone_counter.get(z, 0) + 1

    zone_rows = []
    for z, cnt in sorted(zone_counter.items()):
        is_strict = ig.strictest_zone and z == ig.strictest_zone.value
        mark = " ★ 가장 불리한 기준" if is_strict else ""
        zone_rows.append(f"- **{z}**: {cnt}필지{mark}")
    st.markdown("\n".join(zone_rows))

    if not ig.zone_consistent:
        st.warning("용도지역이 혼재되어 있습니다. 통합 건폐율·용적률은 가장 불리한 기준을 적용합니다.")

    all_ok = (
        ig.bcr_pass and ig.far_pass and ig.parking_deficit == 0
        and all(p.critical_count == 0 for p in report.parcels if p.ok)
    )
    st.markdown('<p class="section-hd">VERDICT — 종합 판정</p>', unsafe_allow_html=True)
    if all_ok:
        st.success("**통합 판정: 이상 없음** — 합산 기준 법규 충족")
    else:
        st.error("**통합 판정: 검토 필요** — 아래 주의사항을 확인하세요.")

    if ig.warnings:
        st.markdown('<p class="section-hd">WARNINGS — 주의사항</p>', unsafe_allow_html=True)
        for w in ig.warnings:
            st.markdown(
                f'<div class="action-item">→ {w}</div>',
                unsafe_allow_html=True,
            )


# ── 단일 필지 탭 ──────────────────────────────────────────────────────────────

def tab_single():
    import io as _io, sys as _sys

    # ① 주소 입력
    st.markdown(
        '<div class="input-label"><span class="marker">■</span> 대지 주소</div>',
        unsafe_allow_html=True,
    )
    address = st.text_input(
        label="address_single",
        label_visibility="collapsed",
        placeholder="주소를 입력하세요  (예: 서울특별시 동대문구 전농동 530-45)",
        value="",
    )

    # ② 변경 용도
    st.markdown(
        '<div class="input-label" style="margin-top:0.8rem;"><span class="marker">▲</span> 변경 용도</div>',
        unsafe_allow_html=True,
    )
    use_label = st.selectbox(
        label="use_single",
        label_visibility="collapsed",
        options=list(USE_OPTIONS.keys()),
        index=0,
    )

    # ③ 자동 산정 항목 안내 (수동 입력 숨김)
    st.markdown("""
    <div style="margin-top:1rem; padding:0.7rem 1rem; border:1px solid #e8e8e8; background:#fafafa;">
      <div style="font-size:0.6rem;font-weight:600;letter-spacing:0.18em;color:#888;text-transform:uppercase;margin-bottom:0.5rem;">
        AUTO — 자동 산정 항목
      </div>
      <div style="display:flex;gap:1.5rem;flex-wrap:wrap;">
        <div>
          <div style="font-size:0.58rem;color:#aaa;letter-spacing:0.1em;text-transform:uppercase;">접면 도로 폭</div>
          <div style="font-size:0.82rem;color:#0f0f0f;font-weight:500;">VWorld API 자동 조회</div>
        </div>
        <div>
          <div style="font-size:0.58rem;color:#aaa;letter-spacing:0.1em;text-transform:uppercase;">정북 이격거리</div>
          <div style="font-size:0.82rem;color:#0f0f0f;font-weight:500;">용도지역·높이 기준 자동산정</div>
        </div>
        <div>
          <div style="font-size:0.58rem;color:#aaa;letter-spacing:0.1em;text-transform:uppercase;">계획 주차대수</div>
          <div style="font-size:0.82rem;color:#0f0f0f;font-weight:500;">법정 기준 자동산정 (override 가능)</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ④ 주차 override (선택)
    with st.expander("주차대수 직접 입력 (자동산정 override)", expanded=False):
        parking_provided = st.number_input(
            "계획 주차대수 (0 = 자동)",
            min_value=0, max_value=500, value=0, step=1, key="single_pk",
        )
        st.markdown('<div class="auto-label">0 입력 시 법정 기준 자동산정값 적용</div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    run_btn = st.button("RUN COMPLIANCE CHECK", type="primary", use_container_width=True, key="btn_single")
    st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

    if run_btn:
        if not address.strip():
            st.warning("주소를 입력해주세요.")
            st.stop()

        to_use_code, to_use_str = USE_OPTIONS[use_label]
        provided = parking_provided if parking_provided > 0 else None

        status_box = st.empty()

        try:
            status_box.info(f"주소 분석 중: {address}")
            buf = _io.StringIO()
            old_out = _sys.stdout
            _sys.stdout = buf

            result: LookupResult = build_site_from_address(
                address=address.strip(),
                to_use_code=to_use_code,
                to_use_str=to_use_str,
                north_setback_m=None,   # 자동산정
                road_width_m=6.0,       # VWorld 조회 실패 시 기본값
                parking_provided=provided,
            )

            _sys.stdout = old_out
            api_log = buf.getvalue()
            status_box.success("API 조회 완료")

            render_building_info(result)
            st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

            items = collect_all_items(result.site)
            render_results_table(items)
            st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

            render_action_summary(items)

            with st.expander("API LOG", expanded=False):
                st.code(api_log, language=None)

            txt_report = generate_report(result.site)
            st.download_button(
                label="DOWNLOAD REPORT — 전체 리포트 텍스트",
                data=txt_report.encode("utf-8"),
                file_name=f"COD-ESTATE_{result.building.address[:15].replace(' ','_')}.txt",
                mime="text/plain",
            )

        except Exception as e:
            _sys.stdout = old_out if "old_out" in dir() else _sys.stdout
            status_box.error(f"오류 발생: {type(e).__name__}: {e}")
            with st.expander("DEBUG", expanded=True):
                st.code(traceback.format_exc())


# ── 다필지 탭 ─────────────────────────────────────────────────────────────────

def tab_multi():
    import io as _io, sys as _sys

    st.markdown(
        '<div class="input-label"><span class="marker">■</span> 대지 주소 목록 (한 줄에 한 필지)</div>',
        unsafe_allow_html=True,
    )
    addresses_raw = st.text_area(
        label="addresses_multi",
        label_visibility="collapsed",
        placeholder=(
            "주소를 입력하세요\n"
            "서울특별시 동대문구 전농동 530-45\n"
            "서울특별시 동대문구 전농동 530-46"
        ),
        value="",
        height=120,
    )

    st.markdown(
        '<div class="input-label" style="margin-top:0.8rem;"><span class="marker">▲</span> 변경 용도 (전 필지 동일 적용)</div>',
        unsafe_allow_html=True,
    )
    use_label_m = st.selectbox(
        label="use_multi",
        label_visibility="collapsed",
        options=list(USE_OPTIONS.keys()),
        index=0,
    )

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    run_btn = st.button("RUN MULTI-PARCEL CHECK", type="primary", use_container_width=True, key="btn_multi")

    st.markdown(
        '<div class="auto-label" style="margin-top:0.4rem;">※ 필지 수만큼 API를 순차 호출합니다. 필지당 약 2~3초 소요됩니다.</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

    if run_btn:
        addresses = [a.strip() for a in addresses_raw.strip().splitlines() if a.strip()]
        if not addresses:
            st.warning("주소를 입력해주세요.")
            st.stop()

        to_use_code, to_use_str = USE_OPTIONS[use_label_m]

        status_box = st.empty()
        progress_bar = st.progress(0)

        def on_progress(idx, total, addr):
            status_box.info(f"필지 {idx}/{total} 조회 중: {addr}")
            progress_bar.progress(int((idx - 1) / total * 100))

        try:
            report = run_multi_parcel(
                addresses=addresses,
                to_use_code=to_use_code,
                to_use_str=to_use_str,
                road_width_m=6.0,
                north_setback_m=None,
                progress_callback=on_progress,
            )

            progress_bar.progress(100)
            status_box.success(
                f"조회 완료 — {report.success_count}/{report.parcel_count}필지 성공"
                + (f", {report.fail_count}필지 실패" if report.fail_count else "")
            )

            st.markdown('<p class="section-hd">PARCELS — 필지별 검토 결과</p>', unsafe_allow_html=True)
            for p in report.parcels:
                render_parcel_card(p)
                st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

            st.markdown('<p class="section-hd">INTEGRATED — 통합 검토 결과</p>', unsafe_allow_html=True)
            render_integrated_result(report)
            st.markdown('<hr class="divider"/>', unsafe_allow_html=True)

            txt = print_multi_parcel_report(report)
            st.download_button(
                label="DOWNLOAD REPORT — 통합 리포트 텍스트",
                data=txt.encode("utf-8"),
                file_name="COD-ESTATE_다필지_통합검토.txt",
                mime="text/plain",
            )

        except Exception as e:
            status_box.error(f"오류 발생: {type(e).__name__}: {e}")
            with st.expander("DEBUG", expanded=True):
                st.code(traceback.format_exc())


# ── 메인 앱 ──────────────────────────────────────────────────────────────────

def main():
    st.markdown("""
    <div class="ce-header">
        <div class="ce-wordmark">COD-ESTATE</div>
        <div class="ce-title">건축법규 × 부동산 인텔리전스</div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["SINGLE PARCEL — 단일 필지", "MULTI PARCEL — 다필지 동시 검토"])

    with tab1:
        tab_single()

    with tab2:
        tab_multi()

    st.markdown(
        '<div class="ce-footer">COD-ESTATE &mdash; Powered by YM Studio</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
