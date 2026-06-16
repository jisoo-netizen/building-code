"""
건축법규 검토 엔진 — API 연동 실행

사용법:
  python main.py                         기본 케이스 (전농동 530-45) 실행
  python main.py "주소" "변경용도"         임의 주소·용도 실행
  python main.py --validate              법규 자체 검증 모드 (3개 케이스 일괄 검증)
  python main.py "주소" "용도" --validate 특정 주소 실행 후 검증
"""

import sys
import io
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from api.lookup import build_site_from_address
from building_code_engine import generate_report
from building_code_engine.use_change import BuildingUseCode


def run(
    address: str,
    to_use_code: BuildingUseCode,
    to_use_str: str,
    north_setback_m=None,
    road_width_m: float = 6.0,
    parking_provided=None,
    designer: str = "",
    note: str = "",
):
    try:
        result = build_site_from_address(
            address=address,
            to_use_code=to_use_code,
            to_use_str=to_use_str,
            north_setback_m=north_setback_m,
            road_width_m=road_width_m,
            parking_provided=parking_provided,
            designer=designer,
            note=note,
        )
        print("\n" + generate_report(result.site))

    except Exception as e:
        print(f"\n[API 오류] {type(e).__name__}: {e}")
        print("\n--- 디버그 트레이스 ---")
        traceback.print_exc()
        print("\n※ API 키 만료·네트워크 차단·PNU 오류 등을 확인하세요.")


def run_validate():
    """법규 자체 검증 모드: 3개 케이스를 엔진으로 계산하고 법령 기준값과 대조."""
    print("=" * 72)
    print("  건축법규 엔진 자체 검증 모드")
    print("  근거: 주차장법·건축법·하수도법·소방시설법 시행령 기준값 하드코딩 대조")
    print("=" * 72)

    # test_cases.py는 tests/ 아래 있으므로 경로 추가
    sys.path.insert(0, ".")
    from tests.test_cases import run_all_cases, print_summary
    from tests.validate_legal import print_validation_report

    try:
        reports = run_all_cases()
    except AssertionError as e:
        print(f"\n[오류] 예상 정답 불일치 — {e}")
        print("엔진 로직을 확인하세요.")
        sys.exit(1)

    for r in reports:
        print_validation_report(r)

    print_summary(reports)


_USE_CODE_MAP = {
    "제1종근린생활시설": BuildingUseCode.FIRST_NEIGHBORHOOD,
    "1종근생": BuildingUseCode.FIRST_NEIGHBORHOOD,
    "제2종근린생활시설": BuildingUseCode.SECOND_NEIGHBORHOOD,
    "2종근생": BuildingUseCode.SECOND_NEIGHBORHOOD,
    "업무시설": BuildingUseCode.OFFICE,
    "단독주택": BuildingUseCode.SINGLE_HOUSE,
    "다가구주택": BuildingUseCode.MULTI_FAMILY,
    "공동주택": BuildingUseCode.APARTMENT,
}


# ── 진입점 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--validate"]
    do_validate = "--validate" in sys.argv

    if args:
        # python main.py "주소" ["변경용도"]
        addr = args[0]
        use_str = args[1] if len(args) > 1 else "제1종근린생활시설"
        use_code = _USE_CODE_MAP.get(use_str, BuildingUseCode.FIRST_NEIGHBORHOOD)
    else:
        addr = "서울특별시 동대문구 전농동 530-45"
        use_str = "제1종근린생활시설"
        use_code = BuildingUseCode.FIRST_NEIGHBORHOOD

    run(
        address=addr,
        to_use_code=use_code,
        to_use_str=use_str,
        north_setback_m=None,
        road_width_m=6.0,
        parking_provided=None,
        designer="자동 검토",
        note=f"{use_str}(카페) 용도변경 검토",
    )

    if do_validate:
        print()
        run_validate()
