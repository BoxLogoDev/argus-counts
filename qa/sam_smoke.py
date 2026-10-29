"""SAM 실호출 단일 빈 스모크 하네스.

제출 런북 3절의 절차를 코드로 고정한다: ``qa.sam_readiness`` 준비
점검을 통과(ready_for_live_call=True)한 뒤에만, 단일 빈 1개에 대해
실호출 계수를 1회 시도한다. 준비가 안 되면 계수를 시도하지 않고
차단(blocked) 보고만 낸다. 이 하네스 자체가 크레딧 입금을 확인할
수는 없으므로, 입금 확인은 ``--credit-confirmed`` 플래그로 외부
확인 결과만 받는다.

성공해도 전체 세션 성공이 아니다. 단일 빈 스모크일 뿐이다.
실패하면 모의 결과로 대체하지 않고 실패로 보고한다.
환경변수 값은 결과와 출력 어디에도 넣지 않는다.
모듈을 불러오는 것만으로 네트워크를 쓰지 않는다.

실행: 프로젝트 루트에서 `python3 -m qa.sam_smoke`
종료코드: 통과 0, 차단 1, 실패 2.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping

from qa.sam_readiness import ENV_BASE_URL, ENV_KEY_VAR, check_readiness
from terminal.demo_data import demo_ledger
from terminal.sam_adapter import LiveSamCounter, SamCountingError

DEFAULT_BIN_ID = "A-01-02"

HONESTY = [
    "준비 점검을 통과하지 못하면 실제 API를 호출하지 않는다",
    "단일 빈 1개만 계수하는 스모크이며 전체 세션 성공을 뜻하지 않는다",
    "실패하면 모의 결과로 대체하지 않는다",
    "환경변수 값은 출력하지 않는다",
]


def _base_report(bin_id: str, book_qty: int | None) -> dict:
    return {
        "status": "blocked",
        "attempted": False,
        "ready_for_live_call": False,
        "blockers": [],
        "bin_id": bin_id,
        "image_ref": None,
        "source": None,
        "counted_qty": None,
        "book_qty": book_qty,
        "diff": None,
        "error_type": None,
        "honesty": list(HONESTY),
    }


def run_smoke(
    env: Mapping[str, str] | None = None,
    credit_confirmed: bool = False,
    bin_id: str = DEFAULT_BIN_ID,
    image_ref: str | None = None,
    counter=None,
) -> dict:
    """단일 빈 스모크를 실행한다. 준비가 안 되면 counter를 부르지 않는다."""
    env_map: Mapping[str, str] = os.environ if env is None else env
    ledger = demo_ledger()
    entry = ledger.get(bin_id)
    report = _base_report(bin_id, entry.book_qty if entry else None)
    report["image_ref"] = image_ref

    if entry is None:
        report["status"] = "failed"
        report["error_type"] = "unknown_bin"
        return report

    readiness = check_readiness(env=env_map, credit_confirmed=credit_confirmed)
    report["ready_for_live_call"] = bool(readiness["ready_for_live_call"])
    report["blockers"] = list(readiness["blockers"])
    if not readiness["ready_for_live_call"]:
        return report

    active = counter
    if active is None:
        active = LiveSamCounter(
            base_url=str(env_map.get(ENV_BASE_URL, "")),
            api_key=str(env_map.get(ENV_KEY_VAR, "")),
        )

    report["attempted"] = True
    try:
        result = active.count(bin_id, image_ref)
    except SamCountingError:
        report["status"] = "failed"
        report["error_type"] = "SamCountingError"
        return report
    except Exception as exc:  # 원본 메시지는 복사하지 않는다(값 누출 방지).
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
        return report

    if getattr(result, "source", None) != "sam":
        report["status"] = "failed"
        report["error_type"] = "unexpected_source"
        report["source"] = getattr(result, "source", None)
        return report

    report["status"] = "passed"
    report["source"] = "sam"
    report["counted_qty"] = result.counted_qty
    report["diff"] = result.counted_qty - entry.book_qty
    return report


def build_report(**kwargs) -> dict:
    return run_smoke(**kwargs)


def format_text_report(report: dict) -> str:
    lines = [
        f"STATUS: {report['status']}",
        f"ATTEMPTED: {str(report['attempted']).lower()}",
        f"BIN: {report['bin_id']}",
        f"SOURCE: {report['source']}",
        f"COUNTED_QTY: {report['counted_qty']}",
        f"BOOK_QTY: {report['book_qty']}",
        f"DIFF: {report['diff']}",
        f"BLOCKERS: {len(report['blockers'])}",
    ]
    for blocker in report["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    if report["error_type"]:
        lines.append(f"ERROR_TYPE: {report['error_type']}")
    passed = "true" if report["status"] == "passed" else "false"
    lines.append(f"SMOKE_PASSED: {passed}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus SAM single-bin smoke")
    parser.add_argument("--credit-confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--bin", default=DEFAULT_BIN_ID, dest="bin_id")
    parser.add_argument("--image-ref", default=None)
    args = parser.parse_args(argv)

    report = run_smoke(
        credit_confirmed=args.credit_confirmed,
        bin_id=args.bin_id,
        image_ref=args.image_ref,
    )
    if args.json:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    if report["status"] == "passed":
        return 0
    if report["status"] == "blocked":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
