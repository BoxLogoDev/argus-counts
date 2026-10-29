"""Pi 실촬영 단일 빈 스모크 하네스.

제출 런북의 Pi 촬영 절차를 코드로 고정한다: ``qa.pi_readiness`` 준비
점검을 통과(ready_for_real_capture=True)한 뒤에만, 단일 빈 1개 촬영
세션을 1회 시도한다. 준비가 안 되면 촬영을 시도하지 않고
차단(blocked) 보고만 낸다. 장치 도착은 이 하네스가 확인할 수
없으므로, ``--device-confirmed`` 플래그로 외부 확인 결과만 받는다.

성공해도 전체 세션 성공이 아니다. Pi 실촬영 검증 완료도 아니다.
단일 빈 스모크일 뿐이다.
실패하면 가짜 파일이나 모의 결과로 대체하지 않고 실패로 보고한다.
모듈을 불러오는 것만으로 촬영하지 않는다.

실행: 프로젝트 루트에서 `python3 -m qa.pi_smoke`
종료코드: 통과 0, 차단 1, 실패 2.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from qa.pi_readiness import check_readiness
from terminal.demo_data import demo_ledger
from terminal.pi_capture import PiCaptureError
from terminal.pi_session import run_pi_session

DEFAULT_BIN_ID = "A-01-02"
SMOKE_SESSION_ID = "PI-SMOKE"

HONESTY = [
    "준비 점검을 통과하지 못하면 실제로 촬영하지 않는다",
    "단일 빈 1개만 촬영하는 스모크이며 전체 세션 성공이나 Pi 실촬영 검증 완료를 뜻하지 않는다",
    "실패하면 가짜 파일이나 모의 결과로 대체하지 않는다",
    "계수는 모의 어댑터 결과일 수 있으며 source 필드로 구분한다",
]


def _base_report(bin_id: str, book_qty: int | None) -> dict:
    return {
        "status": "blocked",
        "attempted": False,
        "ready_for_real_capture": False,
        "blockers": [],
        "bin_id": bin_id,
        "source": None,
        "capture_source": None,
        "counted_qty": None,
        "book_qty": book_qty,
        "diff": None,
        "photo_sha256": None,
        "photo_image_ref": None,
        "session_id": None,
        "capture_dir": None,
        "error_type": None,
        "honesty": list(HONESTY),
    }


def run_smoke(
    output_dir: str | Path | None = None,
    device_confirmed: bool = False,
    bin_id: str = DEFAULT_BIN_ID,
    which=None,
    runner=None,
    session_fn=None,
) -> dict:
    """단일 빈 스모크를 실행한다. 준비가 안 되면 촬영 세션을 부르지 않는다."""
    ledger = demo_ledger()
    entry = ledger.get(bin_id)
    report = _base_report(bin_id, entry.book_qty if entry else None)

    if entry is None:
        report["status"] = "failed"
        report["error_type"] = "unknown_bin"
        return report

    readiness = check_readiness(device_confirmed=device_confirmed, which=which)
    report["ready_for_real_capture"] = bool(readiness["ready_for_real_capture"])
    report["blockers"] = list(readiness["blockers"])
    if not readiness["ready_for_real_capture"]:
        return report

    capture_dir = (
        output_dir
        if output_dir is not None
        else tempfile.mkdtemp(prefix="argus-pi-smoke-")
    )
    report["capture_dir"] = str(capture_dir)
    active = session_fn if session_fn is not None else run_pi_session
    report["attempted"] = True
    try:
        result = active(
            capture_dir,
            bin_ids=[bin_id],
            session_id=SMOKE_SESSION_ID,
            runner=runner,
            which=which,
        )
    except PiCaptureError:
        report["status"] = "failed"
        report["error_type"] = "PiCaptureError"
        return report
    except Exception as exc:  # 원본 메시지는 복사하지 않는다.
        report["status"] = "failed"
        report["error_type"] = type(exc).__name__
        return report

    if result.get("capture_source") != "pi-camera":
        report["status"] = "failed"
        report["error_type"] = "unexpected_capture_source"
        report["capture_source"] = result.get("capture_source")
        return report

    bins = result.get("bins") or []
    if len(bins) != 1 or bins[0].get("bin_id") != bin_id:
        report["status"] = "failed"
        report["error_type"] = "unexpected_bins"
        return report

    first_bin = bins[0]
    counted_qty = first_bin.get("counted_qty")
    diff = counted_qty - first_bin.get("book_qty")
    if diff != first_bin.get("diff"):
        report["status"] = "failed"
        report["error_type"] = "inconsistent_diff"
        return report

    report["status"] = "passed"
    report["source"] = result.get("source")
    report["capture_source"] = "pi-camera"
    report["counted_qty"] = counted_qty
    report["diff"] = diff
    report["photo_sha256"] = first_bin.get("photo", {}).get("sha256")
    report["photo_image_ref"] = first_bin.get("photo", {}).get("image_ref")
    report["session_id"] = result.get("session_id")
    return report


def build_report(**kwargs) -> dict:
    return run_smoke(**kwargs)


def format_text_report(report: dict) -> str:
    lines = [
        f"STATUS: {report['status']}",
        f"ATTEMPTED: {str(report['attempted']).lower()}",
        f"BIN: {report['bin_id']}",
        f"SOURCE: {report['source']}",
        f"CAPTURE_SOURCE: {report['capture_source']}",
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
    parser = argparse.ArgumentParser(description="Argus Pi single-bin smoke")
    parser.add_argument("--device-confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--bin", default=DEFAULT_BIN_ID, dest="bin_id")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    report = run_smoke(
        device_confirmed=args.device_confirmed,
        bin_id=args.bin_id,
        output_dir=args.out_dir,
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
