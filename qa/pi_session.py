"""Pi 실촬영 전체 세션 하네스.

단일 빈 스모크(qa.pi_smoke)의 다음 단계다: ``qa.pi_readiness`` 준비
점검을 통과(ready_for_real_capture=True)한 뒤에만, 데모 빈 6개 전체의
촬영 세션(terminal.pi_session.run_pi_session)을 1회 시도해 표준
보고로 낸다. 준비가 안 되면 어떤 빈도 촬영하지 않고
차단(blocked) 보고만 낸다. 장치 도착은 이 하네스가 확인할 수
없으므로, ``--device-confirmed`` 플래그로 외부 확인 결과만 받는다.

전체 세션을 시도하거나 통과해도 Pi 실촬영 검증 완료를 뜻하지
않는다. 실제 장치에서 통과한 기록이 별도로 필요하다.
실패하면 가짜 파일이나 모의 결과로 대체하지 않고 실패로 보고한다.
한 빈이라도 어긋나면 세션 전체를 실패로 본다 — 부분 성공을 전체
성공처럼 보이지 않게 하기 위해서다.
모듈을 불러오는 것만으로 촬영하지 않는다.

실행: 프로젝트 루트에서 `python3 -m qa.pi_session`
종료코드: 통과 0, 차단 1, 실패 2.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone

from qa.pi_readiness import check_readiness
from terminal.demo_data import demo_bin_ids
from terminal.pi_capture import PiCaptureError
from terminal.pi_session import run_pi_session

HONESTY = [
    "준비 점검을 통과하지 못하면 실제로 촬영하지 않는다",
    "실패하면 가짜 파일이나 모의 결과로 대체하지 않는다",
    "전체 세션을 시도하거나 통과해도 Pi 실촬영 검증 완료를 뜻하지 않는다",
    "계수는 모의 어댑터 결과일 수 있으며 source 필드로 구분한다",
]

_SUMMARY_KEYS = (
    "counted_bins",
    "matched",
    "mismatched",
    "match_rate",
    "abs_diff_total",
    "net_diff",
)


def _default_session_id() -> str:
    return datetime.now(timezone.utc).strftime("PI-%Y%m%d-%H%M%S")


def _base_report(session_id: str) -> dict:
    return {
        "status": "blocked",
        "attempted": False,
        "ready_for_real_capture": False,
        "blockers": [],
        "session_id": session_id,
        "source": None,
        "capture_source": None,
        "capture_dir": None,
        "bins": [],
        "summary": None,
        "error_type": None,
        "honesty": list(HONESTY),
    }


def _fail(report: dict, error_type: str) -> dict:
    report["status"] = "failed"
    report["error_type"] = error_type
    report["bins"] = []
    report["summary"] = None
    return report


def _expected_summary(bins: list[dict]) -> dict:
    matched = sum(1 for b in bins if b["diff"] == 0)
    return {
        "counted_bins": len(bins),
        "matched": matched,
        "mismatched": len(bins) - matched,
        "match_rate": (matched / len(bins)) if bins else 0.0,
        "abs_diff_total": sum(abs(b["diff"]) for b in bins),
        "net_diff": sum(b["diff"] for b in bins),
    }


def run_pi_full_session(
    output_dir=None,
    device_confirmed: bool = False,
    which=None,
    runner=None,
    session_fn=None,
    session_id: str | None = None,
) -> dict:
    """전체 촬영 세션을 실행한다. 준비가 안 되면 세션을 부르지 않는다."""
    session_id = session_id or _default_session_id()
    report = _base_report(session_id)

    readiness = check_readiness(device_confirmed=device_confirmed, which=which)
    report["ready_for_real_capture"] = bool(readiness["ready_for_real_capture"])
    report["blockers"] = list(readiness["blockers"])
    if not readiness["ready_for_real_capture"]:
        return report

    capture_dir = (
        output_dir
        if output_dir is not None
        else tempfile.mkdtemp(prefix="argus-pi-session-")
    )
    report["capture_dir"] = str(capture_dir)
    active = session_fn if session_fn is not None else run_pi_session
    report["attempted"] = True
    try:
        result = active(
            capture_dir,
            bin_ids=list(demo_bin_ids()),
            session_id=session_id,
            runner=runner,
            which=which,
        )
    except PiCaptureError:
        return _fail(report, "PiCaptureError")
    except Exception as exc:  # 원본 메시지는 복사하지 않는다.
        return _fail(report, type(exc).__name__)

    if result.get("capture_source") != "pi-camera":
        report["capture_source"] = result.get("capture_source")
        return _fail(report, "unexpected_capture_source")

    bins = result.get("bins") or []
    if [b.get("bin_id") for b in bins] != list(demo_bin_ids()):
        return _fail(report, "unexpected_bins")

    for entry in bins:
        counted = entry.get("counted_qty")
        book = entry.get("book_qty")
        if counted is None or book is None or entry.get("diff") != counted - book:
            return _fail(report, "inconsistent_diff")

    summary = result.get("summary")
    if not isinstance(summary, dict):
        return _fail(report, "inconsistent_summary")
    expected = _expected_summary(bins)
    for key in _SUMMARY_KEYS:
        actual = summary.get(key)
        if key == "match_rate":
            if actual is None or abs(float(actual) - expected[key]) > 1e-9:
                return _fail(report, "inconsistent_summary")
        elif actual != expected[key]:
            return _fail(report, "inconsistent_summary")

    report["status"] = "passed"
    report["source"] = result.get("source")
    report["capture_source"] = "pi-camera"
    report["bins"] = [
        {
            "bin_id": entry["bin_id"],
            "book_qty": entry["book_qty"],
            "counted_qty": entry["counted_qty"],
            "diff": entry["diff"],
            "verdict": entry.get("verdict"),
            "photo_sha256": (entry.get("photo") or {}).get("sha256"),
            "photo_image_ref": (entry.get("photo") or {}).get("image_ref"),
        }
        for entry in bins
    ]
    report["summary"] = {key: summary[key] for key in _SUMMARY_KEYS}
    return report


def build_report(**kwargs) -> dict:
    return run_pi_full_session(**kwargs)


def format_text_report(report: dict) -> str:
    lines = [
        f"STATUS: {report['status']}",
        f"ATTEMPTED: {str(report['attempted']).lower()}",
        f"SESSION: {report['session_id']}",
        f"SOURCE: {report['source']}",
        f"CAPTURE_SOURCE: {report['capture_source']}",
    ]
    summary = report["summary"]
    if summary is None:
        lines.append("SUMMARY: None")
    else:
        lines.append(
            "SUMMARY: "
            f"counted_bins={summary['counted_bins']} "
            f"matched={summary['matched']} "
            f"mismatched={summary['mismatched']} "
            f"abs_diff_total={summary['abs_diff_total']} "
            f"net_diff={summary['net_diff']}"
        )
    for entry in report["bins"]:
        lines.append(
            f"- {entry['bin_id']}: book={entry['book_qty']} "
            f"counted={entry['counted_qty']} diff={entry['diff']} "
            f"verdict={entry['verdict']}"
        )
    lines.append(f"BLOCKERS: {len(report['blockers'])}")
    for blocker in report["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    if report["error_type"]:
        lines.append(f"ERROR_TYPE: {report['error_type']}")
    passed = "true" if report["status"] == "passed" else "false"
    lines.append(f"SESSION_PASSED: {passed}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus Pi full-session capture")
    parser.add_argument("--device-confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--session-id", default=None)
    args = parser.parse_args(argv)

    report = run_pi_full_session(
        output_dir=args.out_dir,
        device_confirmed=args.device_confirmed,
        session_id=args.session_id,
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
