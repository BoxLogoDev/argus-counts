"""Pi 폴백 결정 점검 하네스.

2026-11-02 기준일까지 Pi 실기가 늦으면 파일 입력 경로로 데모 컷 3을
전환한다는 대체안(새판 계획)을 기계적으로 판정한다.
결정일 전이고 Pi가 준비되지 않았으면 pending, 결정일 이후에도 Pi가
준비되지 않았으면 fallback_due(폴백 채택), Pi가 준비됐으면 pi_ready다.

이 하네스는 실제 촬영을 하지 않고, Pi 준비 상태는 qa.pi_readiness를
재사용해 존재 탐지만으로 확인한다. 폴백 채택은 Pi 실촬영 검증 완료를
뜻하지 않으며, 폴백 자산은 Pi 실촬영이 아니다.

실행: 프로젝트 루트에서 `python3 -m qa.fallback_decision [--date YYYY-MM-DD] [--device-confirmed] [--json]`
종료코드는 보고가 유효하면 0, validate 문제가 있으면 2다.
"""
from __future__ import annotations

import datetime
import json
import sys

from qa.pi_readiness import check_readiness

DECISION_DATE = "2026-11-02"
FALLBACK_ASSET = "demo/assets/fallback.json"
FALLBACK_RENDER = "demo/assets/argus-demo-fallback-draft.mp4"

HONESTY = [
    "파일 입력 폴백은 Pi 실촬영이 아닙니다",
    "폴백 결정은 Pi 실촬영 검증 완료를 뜻하지 않는다",
    "결정일 전에는 폴백을 확정하지 않는다",
    "실제 촬영을 하지 않는다",
]

_REQUIRED_KEYS = (
    "date",
    "decision_date",
    "pi_ready",
    "pi_blockers",
    "status",
    "fallback_adopted",
    "fallback_asset",
    "fallback_render",
    "is_pi_real_capture",
    "honesty",
)


def _parse_date(value: str) -> datetime.date:
    return datetime.date.fromisoformat(value)


def evaluate_decision(today: str, pi_ready: bool, pi_blockers=None) -> dict:
    _parse_date(today)
    blockers = list(pi_blockers or [])
    if pi_ready:
        status = "pi_ready"
        adopted = False
    elif today < DECISION_DATE:
        status = "pending"
        adopted = False
    else:
        status = "fallback_due"
        adopted = True
    return {
        "date": today,
        "decision_date": DECISION_DATE,
        "pi_ready": bool(pi_ready),
        "pi_blockers": blockers,
        "status": status,
        "fallback_adopted": adopted,
        "fallback_asset": FALLBACK_ASSET,
        "fallback_render": FALLBACK_RENDER,
        "is_pi_real_capture": False,
        "honesty": list(HONESTY),
    }


def build_decision(today=None, pi_probe=None, device_confirmed: bool = False, which=None) -> dict:
    if today is None:
        today = datetime.date.today().isoformat()
    readiness = check_readiness(probe=pi_probe, device_confirmed=device_confirmed, which=which)
    blocker_ids = [b["id"] for b in readiness["blockers"]]
    return evaluate_decision(today, bool(readiness["ready_for_real_capture"]), blocker_ids)


def validate_decision(report: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    for key in _REQUIRED_KEYS:
        if key not in report:
            problems.append(f"missing key: {key}")
    if problems:
        return problems
    if report["decision_date"] != DECISION_DATE:
        problems.append(f"decision_date={report['decision_date']!r} != {DECISION_DATE!r}")
    if report["is_pi_real_capture"] is not False:
        problems.append("is_pi_real_capture is not False")
    if report["fallback_asset"] != FALLBACK_ASSET:
        problems.append(f"fallback_asset={report['fallback_asset']!r} != {FALLBACK_ASSET!r}")
    if report["fallback_render"] != FALLBACK_RENDER:
        problems.append(f"fallback_render={report['fallback_render']!r} != {FALLBACK_RENDER!r}")
    try:
        _parse_date(str(report["date"]))
    except ValueError:
        problems.append(f"date is not ISO date: {report['date']!r}")
        return problems
    expected = evaluate_decision(str(report["date"]), bool(report["pi_ready"]), list(report["pi_blockers"]))
    if report["status"] != expected["status"]:
        problems.append(f"status={report['status']!r} != {expected['status']!r}")
    if report["fallback_adopted"] != expected["fallback_adopted"]:
        problems.append(
            f"fallback_adopted={report['fallback_adopted']!r} != {expected['fallback_adopted']!r}"
        )
    if report["pi_ready"] and report["pi_blockers"]:
        problems.append("pi_ready True but pi_blockers not empty")
    joined = " ".join(str(x) for x in (report.get("honesty") or []))
    for marker in ("Pi 실촬영이 아닙니다", "Pi 실촬영 검증 완료를 뜻하지 않는다", "결정일 전에는 폴백을 확정하지 않는다"):
        if marker not in joined:
            problems.append(f"honesty missing {marker!r}")
    return problems


def format_text_report(report: dict) -> str:
    lines = [
        f"STATUS: {report['status']}",
        f"DATE: {report['date']}",
        f"DECISION_DATE: {report['decision_date']}",
        f"PI_READY: {str(report['pi_ready']).lower()}",
        f"FALLBACK_ADOPTED: {str(report['fallback_adopted']).lower()}",
        f"FALLBACK_ASSET: {report['fallback_asset']}",
        f"FALLBACK_RENDER: {report['fallback_render']}",
        f"PI_BLOCKERS: {report['pi_blockers']}",
    ]
    for line in report["honesty"]:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    today = None
    if "--date" in argv:
        idx = argv.index("--date")
        if idx + 1 < len(argv):
            today = argv[idx + 1]
    try:
        report = build_decision(today=today, device_confirmed="--device-confirmed" in argv)
    except ValueError as exc:
        sys.stdout.write(f"invalid date: {exc}\n")
        return 2
    problems = validate_decision(report)
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    if problems:
        for problem in problems:
            sys.stdout.write(f"PROBLEM: {problem}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
