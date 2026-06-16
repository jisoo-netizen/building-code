"""
건축물대장 API 연동 (공공데이터포털)
EndPoint: https://apis.data.go.kr/1613000/BldRgstHubService
"""

import requests
import time
from dataclasses import dataclass, field

SERVICE_KEY = "2c556e10a6928cd43ea1ebe5e736aedde181d65e856f259ef9a90aa33bae717b"
BASE_URL    = "https://apis.data.go.kr/1613000/BldRgstHubService"


@dataclass
class BuildingBasicInfo:
    pnu: str
    address: str              # 대지위치 (지번)
    address_road: str         # 도로명주소
    building_name: str
    main_use: str             # 주용도명 (예: 단독주택)
    sub_use: str              # 기타용도 (예: 다가구용단독주택(4가구))
    total_floor_area: float   # 연면적 ㎡
    site_area: float          # 대지면적 ㎡
    building_coverage: float  # 건축면적 ㎡
    bcr_pct: float            # 건폐율 %
    far_pct: float            # 용적률 %
    floors_above: int
    floors_below: int
    height_m: float
    construction_year: int    # 사용승인연도
    structure: str
    roof: str
    households: int           # 가구수
    raw: dict = field(default_factory=dict)


@dataclass
class FloorInfo:
    floor_no: int
    floor_area: float
    use: str


def _get_json(endpoint: str, extra: dict, timeout: int = 15) -> dict:
    params = {
        "serviceKey": SERVICE_KEY,
        "numOfRows": "100",
        "pageNo": "1",
        "_type": "json",
        **extra,
    }
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        raise ValueError(f"JSON 파싱 실패:\n{resp.text[:500]}")


def _extract_items(data: dict) -> list[dict]:
    try:
        body = data["response"]["body"]
        if int(body.get("totalCount", 0)) == 0:
            return []
        items = body["items"]["item"]
        return items if isinstance(items, list) else [items]
    except (KeyError, TypeError):
        return []


def _pnu_to_params(pnu: str) -> dict:
    """
    PNU 19자리 → API 파라미터.
    구조: 시도(2)+시군구(3)+읍면동(3)+리(2)+지목(1)+본번(4)+부번(4)
    """
    if len(pnu) < 19:
        raise ValueError(f"PNU 길이 오류: {pnu!r} (19자리 필요, 현재 {len(pnu)}자리)")
    return {
        "sigunguCd": pnu[0:5],
        "bjdongCd":  pnu[5:10],
        "platGbCd":  "0",        # 0=대지, 1=산, 2=블록
        "bun":       pnu[11:15],
        "ji":        pnu[15:19],
    }


def _sf(v, d: float = 0.0) -> float:
    try:
        return float(v) if v not in (None, "", "null") else d
    except (ValueError, TypeError):
        return d


def _si(v, d: int = 0) -> int:
    try:
        return int(float(str(v).strip())) if str(v).strip() not in ("", "null", "None") else d
    except (ValueError, TypeError):
        return d


def _year(v) -> int:
    try:
        s = str(v).strip()
        return int(s[:4]) if len(s) >= 4 and s[:4].isdigit() else 0
    except Exception:
        return 0


# ── 표제부 조회 (getBrTitleInfo) — 동별 건물 정보 ───────────────────────────

def get_title(pnu: str) -> list[dict]:
    data = _get_json("getBrTitleInfo", _pnu_to_params(pnu))
    return _extract_items(data)


# ── 총괄표제부 (getBrRecapTitleInfo) — 전체 요약 ─────────────────────────────

def get_recap_title(pnu: str) -> list[dict]:
    data = _get_json("getBrRecapTitleInfo", _pnu_to_params(pnu))
    return _extract_items(data)


# ── 층별개요 (getBrFlrOulnInfo) ───────────────────────────────────────────

def get_floor_outline(pnu: str) -> list[dict]:
    data = _get_json("getBrFlrOulnInfo", _pnu_to_params(pnu))
    return _extract_items(data)


# ── 통합 파싱 ────────────────────────────────────────────────────────────

def get_building_info(pnu: str, address_hint: str = "") -> BuildingBasicInfo:
    """
    PNU → 건축물대장 파싱.
    getBrTitleInfo(표제부) 우선 → 없으면 getBrRecapTitleInfo(총괄표제부).
    """
    # 1차: 표제부
    print(f"[건축물대장] 표제부 조회: PNU={pnu}")
    items = get_title(pnu)

    if items:
        t = items[0]
        src = "표제부"
    else:
        print(f"  → 표제부 없음, 총괄표제부 재시도")
        time.sleep(0.2)
        items = get_recap_title(pnu)
        if not items:
            raise ValueError(
                f"건축물대장 조회 결과 없음: PNU={pnu}\n"
                "지번·PNU 분해 오류 또는 미등기 건축물 가능성"
            )
        t = items[0]
        src = "총괄표제부"

    print(f"  → [{src}] {t.get('platPlc','')} / {t.get('mainPurpsCdNm','')} / {t.get('etcPurps','')}")

    # 연면적: totArea (표제부는 동별), 복수 동 합산
    total_fa   = sum(_sf(x.get("totArea")) for x in items)
    bcovr_area = sum(_sf(x.get("archArea")) for x in items)
    site_area  = _sf(t.get("platArea"))
    floors_a   = max(_si(x.get("grndFlrCnt")) for x in items)
    floors_b   = max(_si(x.get("ugrndFlrCnt")) for x in items)
    height     = _sf(t.get("heit"))
    bcr        = _sf(t.get("bcRat"))
    far        = _sf(t.get("vlRat"))
    year       = _year(t.get("useAprDay") or t.get("crtnDay"))
    main_use   = (t.get("mainPurpsCdNm") or "").strip()
    sub_use    = (t.get("etcPurps") or "").strip()
    bld_name   = (t.get("bldNm") or "").strip()
    structure  = (t.get("strctCdNm") or "").strip()
    roof       = (t.get("roofCdNm") or "").strip()
    households = _si(t.get("fmlyCnt"))
    addr       = (t.get("platPlc") or address_hint).strip()
    addr_road  = (t.get("newPlatPlc") or "").strip()

    # 높이 fallback: 층고 3.3m
    if height == 0 and floors_a > 0:
        height = floors_a * 3.3

    return BuildingBasicInfo(
        pnu=pnu,
        address=addr,
        address_road=addr_road,
        building_name=bld_name,
        main_use=main_use,
        sub_use=sub_use,
        total_floor_area=total_fa,
        site_area=site_area,
        building_coverage=bcovr_area,
        bcr_pct=bcr,
        far_pct=far,
        floors_above=floors_a,
        floors_below=floors_b,
        height_m=height,
        construction_year=year,
        structure=structure,
        roof=roof,
        households=households,
        raw=t,
    )


def get_floor_info(pnu: str) -> list[FloorInfo]:
    items = get_floor_outline(pnu)
    floors = []
    for it in items:
        raw_no = str(it.get("flrNo", "0")).strip()
        gb     = str(it.get("flrGbCd", "1")).strip()
        try:
            no = int(float(raw_no))
        except ValueError:
            no = 0
        if gb == "2":
            no = -abs(no)
        floors.append(FloorInfo(
            floor_no=no,
            floor_area=_sf(it.get("area")),
            use=(it.get("mainPurpsCdNm") or it.get("etcPurps") or "").strip(),
        ))
    floors.sort(key=lambda f: f.floor_no)
    return floors
