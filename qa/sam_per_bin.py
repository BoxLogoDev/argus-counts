"""SAM 3.1 빈별 서로 다른 사진 실호출 세션 하네스.

전체 세션 하네스(qa.sam_session)의 다음 단계다: 66회차 전체 세션
실호출은 전 빈에 같은 가상 사진 한 장을 재사용했으므로 빈별 정확도를
검증하지 못했다. 이 하네스는 ``qa.sam_readiness`` 준비 점검을
통과(ready_for_live_call=True)한 뒤에만, 데모 빈 6개마다 서로 다른
사진 파일을 받아 각각 계수해 장부와 대조한 세션 리포트를 낸다.
서로 다른 사진 조건은 호출 전에 파일 SHA-256으로 검사한다 — 사진이
빠졌거나, 파일이 없거나, 두 빈이 같은 사진이면 어떤 빈도 호출하지
않고 실패로 보고한다.

실패하면 모의 결과로 대체하지 않는다. 한 빈이라도 출처가 "sam"이
아니거나 계수가 실패하면 세션 전체를 실패로 본다.
환경변수 값은 결과와 출력 어디에도 넣지 않는다.
빈별 사진은 호출자가 제공한 가상 사진의 서로 다른 잘라내기이며
실제 빈 촬영이나 Pi 실촬영이 아니다.
모듈을 불러오는 것만으로 네트워크를 쓰지 않는다.

실행: 프로젝트 루트에서
`python3 -m qa.sam_per_bin --image <빈>=<경로> ...` (빈 6개 전부)
종료코드: 통과 0, 차단 1, 실패 2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timezone

from qa.sam_readiness import ENV_BASE_URL, ENV_KEY_VAR, check_readiness
from terminal.demo_data import demo_bin_ids, demo_ledger
from terminal.reconcile import reconcile
from terminal.sam_adapter import LiveSamCounter, SamCountingError

HONESTY = [
    "준비 점검을 통과하지 못하면 실제 API를 호출하지 않는다",
    "빈마다 서로 다른 사진을 쓰지 않으면 호출하지 않는다",
    "실패하면 모의 결과로 대체하지 않는다",
    "환경변수 값은 출력하지 않는다",
    "빈별 사진은 호출자가 제공한 가상 사진의 서로 다른 잘라내기이며 실제 빈 촬영이나 Pi 실촬영이 아니다",
]


def _default_session_id() -> str:
    return datetime.now(timezone.utc).strftime("SAM-PERBIN-%Y%m%d-%H%M%S")


def _base_report(session_id: str) -> dict:
    return {
        "status": "blocked",
        "attempted": False,
        "ready_for_live_call": False,
        "blockers": [],
        "session_id": session_id,
        "source": None,
        "distinct_image_count": 0,
        "bins": [],
        "summary": None,
        "error_type": None,
        "honesty": list(HONESTY),
    }


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_sam_per_bin(
    env: Mapping[str, str] | None = None,
    credit_confirmed: bool = False,
    image_refs: Mapping[str, str] | None = None,
    counter=None,
    session_id: str | None = None,
) -> dict:
    """빈별 세션을 실행한다. 준비나 사진 조건이 안 되면 counter를 부르지 않는다."""
    env_map: Mapping[str, str] = os.environ if env is None else env
    session_id = session_id or _default_session_id()
    report = _base_report(session_id)

    readiness = check_readiness(env=env_map, credit_confirmed=credit_confirmed)
    report["ready_for_live_call"] = bool(readiness["ready_for_live_call"])
    report["blockers"] = list(readiness["blockers"])
    if not readiness["ready_for_live_call"]:
        return report

    refs = dict(image_refs) if image_refs else {}
    bin_ids = demo_bin_ids()
    # 사진 조건 검사: 전부 갖춰지고 서로 달라야만 호출한다.
    hashes: dict[str, str] = {}
    for bin_id in bin_ids:
        ref = refs.get(bin_id)
        if not ref:
            report["status"] = "failed"
            report["error_type"] = "missing_image"
            return report
        if not os.path.isfile(ref):
            report["status"] = "failed"
            report["error_type"] = "image_file_missing"
            return report
        hashes[bin_id] = _file_sha256(ref)
    if len(set(hashes.values())) != len(bin_ids):
        report["status"] = "failed"
        report["error_type"] = "duplicate_image"
        return report
    report["distinct_image_count"] = len(set(hashes.values()))

    active = counter
    if active is None:
        active = LiveSamCounter(
            base_url=str(env_map.get(ENV_BASE_URL, "")),
            api_key=str(env_map.get(ENV_KEY_VAR, "")),
        )

    ledger = demo_ledger()
    results = {}
    report["attempted"] = True
    for bin_id in bin_ids:
        try:
            result = active.count(bin_id, refs[bin_id])
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
        results[bin_id] = result

    diff_report = reconcile(session_id, ledger, results)
    report["status"] = "passed"
    report["source"] = "sam"
    report["bins"] = [
        {
            "bin_id": comp.bin_id,
            "book_qty": comp.book_qty,
            "counted_qty": comp.counted_qty,
            "diff": comp.diff,
            "verdict": comp.verdict.value,
            "image_sha256": hashes[comp.bin_id],
        }
        for comp in diff_report.comparisons
    ]
    report["summary"] = {
        "counted_bins": diff_report.counted_bins,
        "matched": diff_report.matched,
        "mismatched": diff_report.mismatched,
        "match_rate": diff_report.match_rate,
        "abs_diff_total": diff_report.abs_diff_total,
        "net_diff": diff_report.net_diff,
    }
    return report


def build_report(**kwargs) -> dict:
    return run_sam_per_bin(**kwargs)


def format_text_report(report: dict) -> str:
    lines = [
        f"STATUS: {report['status']}",
        f"ATTEMPTED: {str(report['attempted']).lower()}",
        f"SESSION: {report['session_id']}",
        f"SOURCE: {report['source']}",
        f"DISTINCT_IMAGES: {report['distinct_image_count']}",
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
    for comp in report["bins"]:
        lines.append(
            f"- {comp['bin_id']}: book={comp['book_qty']} "
            f"counted={comp['counted_qty']} diff={comp['diff']} "
            f"verdict={comp['verdict']} sha256={comp['image_sha256'][:8]}"
        )
    lines.append(f"BLOCKERS: {len(report['blockers'])}")
    for blocker in report["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    if report["error_type"]:
        lines.append(f"ERROR_TYPE: {report['error_type']}")
    passed = "true" if report["status"] == "passed" else "false"
    lines.append(f"SESSION_PASSED: {passed}")
    return "\n".join(lines) + "\n"


def _parse_image(values: list[str] | None) -> dict[str, str]:
    refs: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                f"invalid --image format (expected BIN=PATH): {value}"
            )
        bin_id, path = value.split("=", 1)
        if not bin_id or not path:
            raise argparse.ArgumentTypeError(
                f"invalid --image format (expected BIN=PATH): {value}"
            )
        refs[bin_id] = path
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus SAM per-bin live run")
    parser.add_argument("--credit-confirmed", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--image", action="append", default=None,
                        help="BIN=PATH, 빈마다 반복 (6개 전부 필요)")
    args = parser.parse_args(argv)

    try:
        image_refs = _parse_image(args.image)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    report = run_sam_per_bin(
        credit_confirmed=args.credit_confirmed,
        image_refs=image_refs or None,
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
