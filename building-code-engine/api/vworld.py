"""
VWorld API 연동
- 주소 → 위경도 + PNU (지오코딩 응답 level4LC 직접 추출)
- 위경도 → 용도지역 (LT_C_UQ111 레이어)
공식 문서: https://www.vworld.kr/dev/v4dv_2ddatadown_s001.do
"""

import requests
import time
from dataclasses import dataclass
from typing import Optional

VWORLD_KEY = "C7A5CAD1-4997-31D8-B659-59AAADE9DCE0"
BASE = "https://api.vworld.kr/req"

# VWorld 용도지역 uname → ZoneType.value 매핑
ZONE_NAME_MAP: dict[str, str] = {
    "제1종전용주거지역": "제1종전용주거지역",
    "제2종전용주거지역": "제2종전용주거지역",
    "제1종일반주거지역": "제1종일반주거지역",
    "제2종일반주거지역": "제2종일반주거지역",
    "제3종일반주거지역": "제3종일반주거지역",
    "준주거지역":       "준주거지역",
    "중심상업지역":     "중심상업지역",
    "일반상업지역":     "일반상업지역",
    "근린상업지역":     "근린상업지역",
    "유통상업지역":     "유통상업지역",
    "전용공업지역":     "전용공업지역",
    "일반공업지역":     "일반공업지역",
    "준공업지역":       "준공업지역",
    "보전녹지지역":     "보전녹지지역",
    "생산녹지지역":     "생산녹지지역",
    "자연녹지지역":     "자연녹지지역",
    # 상위 분류 fallback
    "주거지역":         "제2종일반주거지역",
    "상업지역":         "일반상업지역",
    "공업지역":         "준공업지역",
    "녹지지역":         "자연녹지지역",
}


@dataclass
class GeoPoint:
    lat: float
    lng: float


@dataclass
class ParcelInfo:
    pnu: str                 # 필지고유번호 19자리
    address_jibun: str       # 입력 주소
    address_road: str        # 도로명주소 (refined.text)
    point: GeoPoint


@dataclass
class ZoningInfo:
    zone_name: str           # VWorld uname 원문
    zone_name_mapped: str    # engine 내부 ZoneType.value
    pnu: str
    raw: dict


def _get(url: str, params: dict, timeout: int = 12) -> dict:
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# ── 1단계: 주소 → 위경도 + PNU ───────────────────────────────────────────

def geocode_address(address: str) -> ParcelInfo:
    """
    주소 → 위경도 + PNU.
    VWorld 지번 검색 API 응답의 level4LC 필드에서 PNU 19자리 직접 추출.
    """
    params = {
        "service": "address",
        "request": "getcoord",
        "version": "2.0",
        "crs": "epsg:4326",
        "address": address,
        "refine": "true",
        "simple": "false",
        "format": "json",
        "type": "parcel",
        "key": VWORLD_KEY,
    }
    data = _get(f"{BASE}/address", params)
    status = data.get("response", {}).get("status", "")

    if status != "OK":
        # 지번 실패 → 도로명 재시도
        params["type"] = "road"
        data = _get(f"{BASE}/address", params)
        status = data.get("response", {}).get("status", "")
        if status != "OK":
            raise ValueError(
                f"VWorld 주소 조회 실패 (status={status}): {address}\n"
                f"응답: {data}"
            )

    refined   = data["response"].get("refined", {})
    structure = refined.get("structure", {})
    point_d   = data["response"]["result"]["point"]
    lng = float(point_d["x"])
    lat = float(point_d["y"])

    # level4LC: 19자리 PNU 포함 여부 확인
    level4lc = structure.get("level4LC", "")
    pnu = ""
    if len(level4lc) == 19 and level4lc.isdigit():
        pnu = level4lc
    elif len(level4lc) > 19:
        # 일부 응답에서 더 길게 오는 경우 앞 19자리
        candidate = level4lc[:19]
        if candidate.isdigit():
            pnu = candidate

    if not pnu:
        raise ValueError(
            f"PNU 추출 실패: level4LC={level4lc!r}\n"
            f"구조: {structure}"
        )

    road_text = refined.get("text", address)
    return ParcelInfo(
        pnu=pnu,
        address_jibun=address,
        address_road=road_text,
        point=GeoPoint(lat=lat, lng=lng),
    )


# ── 2단계: 위경도 → 용도지역 ─────────────────────────────────────────────

def get_zoning_by_point(lat: float, lng: float, pnu: str = "") -> ZoningInfo:
    """
    위경도 → 용도지역 (VWorld LT_C_UQ111 레이어).
    uname 필드에서 용도지역명 추출. 여러 피처 반환 시 비어 있지 않은 항목 우선.
    """
    params = {
        "service": "data",
        "request": "GetFeature",
        "version": "2.0",
        "key": VWORLD_KEY,
        "data": "LT_C_UQ111",
        "geomFilter": f"POINT({lng} {lat})",
        "geometry": "false",
        "attribute": "true",
        "format": "json",
        "size": "5",
        "crs": "epsg:4326",
    }
    data = _get(f"{BASE}/data", params)
    status = data.get("response", {}).get("status", "")

    if status != "OK":
        raise ValueError(
            f"VWorld 용도지역 조회 실패 (status={status}): "
            f"lat={lat}, lng={lng}\n응답: {data}"
        )

    features = data["response"]["result"]["featureCollection"]["features"]
    if not features:
        raise ValueError(f"용도지역 조회 결과 없음: ({lat}, {lng})")

    # uname이 비어있지 않은 피처 우선 선택
    zone_raw = ""
    raw_props: dict = {}
    for feat in features:
        props = feat.get("properties", {})
        uname = props.get("uname", "").strip()
        if uname:
            zone_raw = uname
            raw_props = props
            break

    if not zone_raw:
        # 모두 비어 있으면 첫 번째 사용
        raw_props = features[0].get("properties", {})
        zone_raw = raw_props.get("uname", "용도지역미지정").strip() or "용도지역미지정"

    zone_mapped = ZONE_NAME_MAP.get(zone_raw, zone_raw)
    return ZoningInfo(
        zone_name=zone_raw,
        zone_name_mapped=zone_mapped,
        pnu=pnu,
        raw=raw_props,
    )


# ── 통합 호출 ─────────────────────────────────────────────────────────────

def lookup_address(address: str) -> tuple[ParcelInfo, ZoningInfo]:
    """
    주소 → (필지정보, 용도지역).
    내부적으로 2회 API 호출: 지오코딩 → 용도지역.
    """
    print(f"[VWorld] 주소 지오코딩: {address}")
    parcel = geocode_address(address)
    print(f"  → 위경도: ({parcel.point.lat:.6f}, {parcel.point.lng:.6f})")
    print(f"  → PNU: {parcel.pnu}")

    time.sleep(0.2)

    print(f"[VWorld] 용도지역 조회 (LT_C_UQ111)")
    zoning = get_zoning_by_point(parcel.point.lat, parcel.point.lng, parcel.pnu)
    print(f"  → 용도지역: {zoning.zone_name}  (매핑: {zoning.zone_name_mapped})")

    return parcel, zoning
