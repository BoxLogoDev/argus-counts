"""SAM 3.1 파일 입력 경로 실호출 증거 검증 하네스.

커넥터 브리지로 수행한 SAM 3.1 파일 입력 경로 실호출의 증거 JSON
파일(최상위 bridge·endpoint·path·image_source·report, report는
``terminal.photo_intake.run_photo_intake`` 출력)을 다시 읽어 내부
정합만 검증한다. 이 하네스는 실제 API를 호출하지 않고 환경변수
값을 다루지 않는다. 증거 검증이 통과해도 실제 빈 촬영이나 Pi
실촬영을 뜻하지 않으며, 제출 준비 완료를 뜻하지도 않는다.

실행: 프로젝트 루트에서
`python3 -m qa.sam_photo_evidence --file <증거 JSON 경로> [--json]`
종료코드: 유효 0, 무효 1, 파일 오류 2.
"""
from __future__ import annotations

import argparse
import json
import sys

from terminal.demo_data import demo_bin_ids, demo_ledger
from terminal.photo_intake import SUPPORTED_EXTENSIONS

EXPECTED_ENDPOINT = "https://api.meta.ai/v1/responses"
EXPECTED_BRIDGE_MARKER = "custom.meta-model-api"
EXPECTED_PATH_MARKER = "photo_intake"
EXPECTED_SOURCE = "sam"
EXPECTED_CAPTURE_SOURCE = "file"

HONESTY = [
    "실호출 증거의 내부 정합만 검증하며 API를 호출하지 않는다",
    "빈별 사진은 가상 사진의 서로 다른 잘라내기이며 실제 빈 촬영이나 Pi 실촬영이 아니다",
    "증거 검증 통과는 제출 준비 완료를 뜻하지 않는다",
]

_REQUIRED_KEYS = (
    "bridge", "endpoint", "path", "image_source", "report",
)
_REQUIRED_REPORT_KEYS = (
    "session_id", "generated_at", "source", "capture_source",
    "honesty", "bins", "summary",
)
_REQUIRED_PHOTO_KEYS = ("image_ref", "size_bytes", "sha256", "suffix")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_sha256(value: object) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _expected_verdict(diff: int) -> str:
    if diff == 0:
        return "match"
    return "short" if diff < 0 else "over"


def _recompute_summary(bins: list) -> dict | None:
    try:
        counted = len(bins)
        matched = sum(1 for b in bins if b["diff"] == 0)
        return {
            "counted_bins": counted,
            "matched": matched,
            "mismatched": counted - matched,
            "match_rate": (matched / counted) if counted else 0.0,
            "abs_diff_total": sum(abs(b["diff"]) for b in bins),
            "net_diff": sum(b["diff"] for b in bins),
        }
    except (KeyError, TypeError):
        return None


def validate_evidence(evidence: object) -> list[str]:
    """파일 입력 경로 실호출 증거 dict의 내부 정합 문제 목록."""
    problems: list[str] = []
    if not isinstance(evidence, dict):
        return ["evidence is not an object"]
    for key in _REQUIRED_KEYS:
        if key not in evidence:
            problems.append(f"evidence missing key: {key}")
    bridge = evidence.get("bridge")
    if not isinstance(bridge, str) or EXPECTED_BRIDGE_MARKER not in bridge:
        problems.append("bridge does not name the connector bridge")
    if evidence.get("endpoint") != EXPECTED_ENDPOINT:
        problems.append("endpoint mismatch")
    path = evidence.get("path")
    if not isinstance(path, str) or EXPECTED_PATH_MARKER not in path:
        problems.append("path does not name the photo_intake path")
    if not isinstance(evidence.get("image_source"), str) or not evidence.get("image_source"):
        problems.append("image_source missing")
    report = evidence.get("report")
    if not isinstance(report, dict):
        problems.append("report is not an object")
        return problems
    for key in _REQUIRED_REPORT_KEYS:
        if key not in report:
            problems.append(f"report missing key: {key}")
    if problems:
        return problems
    if report["source"] != EXPECTED_SOURCE:
        problems.append("report source is not sam")
    if report["capture_source"] != EXPECTED_CAPTURE_SOURCE:
        problems.append("report capture_source is not file")
    bins = report["bins"]
    if not isinstance(bins, list) or not bins:
        problems.append("report bins is not a non-empty list")
        return problems
    expected_ids = list(demo_bin_ids())
    actual_ids = [b.get("bin_id") if isinstance(b, dict) else None for b in bins]
    if actual_ids != expected_ids:
        problems.append("report bins order does not match demo bins")
    ledger = demo_ledger()
    hashes: list[str] = []
    bins_ok = True
    for entry in bins:
        if not isinstance(entry, dict):
            bins_ok = False
            continue
        bin_id = entry.get("bin_id")
        book, counted, diff = entry.get("book_qty"), entry.get("counted_qty"), entry.get("diff")
        if not (_is_int(book) and _is_int(counted) and _is_int(diff)):
            bins_ok = False
            problems.append(f"bin {bin_id}: quantities are not integers")
            continue
        expected = ledger[bin_id] if bin_id in ledger else None
        if expected is None:
            bins_ok = False
            problems.append(f"bin {bin_id}: not a demo bin")
            continue
        if entry.get("item_code") != expected.item_code:
            bins_ok = False
            problems.append(f"bin {bin_id}: item_code does not match demo ledger")
        if book != expected.book_qty:
            bins_ok = False
            problems.append(f"bin {bin_id}: book_qty does not match demo ledger")
        if diff != counted - book:
            bins_ok = False
            problems.append(f"bin {bin_id}: diff != counted - book")
        if entry.get("verdict") != _expected_verdict(diff):
            bins_ok = False
            problems.append(f"bin {bin_id}: verdict mismatch")
        photo = entry.get("photo")
        if not isinstance(photo, dict):
            bins_ok = False
            problems.append(f"bin {bin_id}: photo is not an object")
            continue
        for key in _REQUIRED_PHOTO_KEYS:
            if key not in photo:
                bins_ok = False
                problems.append(f"bin {bin_id}: photo missing key: {key}")
        if not _is_sha256(photo.get("sha256")):
            bins_ok = False
            problems.append(f"bin {bin_id}: photo sha256 is not 64-char hex")
        else:
            hashes.append(photo["sha256"])
        if not _is_int(photo.get("size_bytes")) or photo.get("size_bytes", 0) <= 0:
            bins_ok = False
            problems.append(f"bin {bin_id}: photo size_bytes is not a positive integer")
        suffix = photo.get("suffix")
        if suffix not in SUPPORTED_EXTENSIONS:
            bins_ok = False
            problems.append(f"bin {bin_id}: photo suffix is not supported")
        elif photo.get("image_ref") != f"{bin_id}{suffix}":
            bins_ok = False
            problems.append(f"bin {bin_id}: photo image_ref does not match bin and suffix")
    if len(set(hashes)) != len(hashes):
        problems.append("bin photo hashes are not all distinct")
    if bins_ok:
        recomputed = _recompute_summary(bins)
        summary = report["summary"]
        if not isinstance(summary, dict):
            problems.append("report summary is not an object")
        elif recomputed is not None:
            for key, value in recomputed.items():
                if summary.get(key) != value:
                    problems.append(f"summary {key} mismatch")
    honesty = report["honesty"]
    if not isinstance(honesty, list) or not any(
            isinstance(h, str) and "Pi 실촬영이 아닙니다" in h for h in honesty):
        problems.append("report honesty missing Pi capture disclaimer")
    return problems


def build_report(evidence: object) -> dict:
    problems = validate_evidence(evidence)
    report = evidence.get("report") if isinstance(evidence, dict) else None
    if not isinstance(report, dict):
        report = {}
    bins = report.get("bins") if isinstance(report.get("bins"), list) else []
    hashes = [b["photo"]["sha256"] for b in bins
              if isinstance(b, dict) and isinstance(b.get("photo"), dict)
              and _is_sha256(b["photo"].get("sha256"))]
    return {
        "valid": not problems,
        "problems": problems,
        "session_id": report.get("session_id"),
        "source": report.get("source"),
        "capture_source": report.get("capture_source"),
        "distinct_image_count": len(set(hashes)),
        "summary": report.get("summary"),
        "blockers": [],
        "submission_ready": False,
        "honesty": list(HONESTY),
    }


def validate_report(report: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(report, dict):
        return ["report is not an object"]
    if report.get("valid") != (not report.get("problems")):
        problems.append("valid does not match problems")
    if report.get("submission_ready") is not False:
        problems.append("submission_ready is not false")
    if report.get("blockers") != []:
        problems.append("blockers is not empty")
    if report.get("valid") is True:
        if report.get("source") != EXPECTED_SOURCE:
            problems.append("valid report source is not sam")
        if report.get("capture_source") != EXPECTED_CAPTURE_SOURCE:
            problems.append("valid report capture_source is not file")
    honesty = report.get("honesty")
    if not isinstance(honesty, list) or not any(
            isinstance(h, str) and "API를 호출하지 않는다" in h for h in honesty):
        problems.append("honesty missing no-call disclaimer")
    return problems


def format_text_report(report: dict) -> str:
    lines = [
        "Argus SAM 파일 입력 경로 실호출 증거 검증",
        f"VALID: {str(report['valid']).lower()}",
        f"SESSION: {report.get('session_id')}",
        f"SOURCE: {report.get('source')}",
        f"CAPTURE_SOURCE: {report.get('capture_source')}",
        f"DISTINCT_IMAGES: {report.get('distinct_image_count')}",
        f"PROBLEMS: {report.get('problems')}",
        "SUBMISSION_READY: false",
    ]
    lines.extend(f"HONESTY: {h}" for h in HONESTY)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SAM 파일 입력 경로 실호출 증거 검증")
    parser.add_argument("--file", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        with open(args.file, encoding="utf-8") as handle:
            evidence = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"증거 파일을 읽을 수 없습니다: {type(exc).__name__}", file=sys.stderr)
        return 2
    if not isinstance(evidence, dict):
        print("증거 파일이 객체가 아닙니다.", file=sys.stderr)
        return 2
    report = build_report(evidence)
    problems = validate_report(report)
    if problems:
        report["valid"] = False
        report["problems"] = list(report["problems"]) + problems
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text_report(report), end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
