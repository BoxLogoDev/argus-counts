"""제출 마감 점검 하네스.

제출 마감은 2026-11-04 21:00 ET = 2026-11-05 11:00 KST이며, 지각
제출은 고려되지 않는다. 이 하네스는 제공된 기준 시각과 마감 시각의
차이로 남은 시간과 상태(before_deadline·due_soon·overdue)를 판정한다.

이 하네스는 실제로 제출하지 않으며, 마감 전이어도 제출 준비 완료를
뜻하지 않는다. submission_ready는 이 하네스 단독으로는 항상 False다.

실행: 프로젝트 루트에서 `python3 -m qa.deadline [--now ISO8601] [--json]`
종료코드는 유효하고 마감이 지나지 않았으면 0, 마감이 지났으면 1,
입력이 유효하지 않거나 보고가 무효면 2다.
"""
from __future__ import annotations

import datetime
import json
import sys

KST = datetime.timezone(datetime.timedelta(hours=9))

DEADLINE_KST_ISO = "2026-11-05T11:00:00+09:00"
DEADLINE_ET_TEXT = "2026-11-04 21:00 ET"
DEADLINE_KST_TEXT = "2026-11-05 11:00 KST"
DUE_SOON_HOURS = 24
DEFAULT_BLOCKERS = ["pi_real_capture_pending"]

HONESTY = [
    "마감 점검은 실제로 제출하지 않는다",
    "마감 전이어도 제출 준비 완료를 뜻하지 않는다",
    "지각 제출은 고려되지 않는다",
    "남은 시간은 제공된 기준 시각으로만 계산한다",
]

_REQUIRED_KEYS = (
    "now",
    "deadline_kst",
    "deadline_et",
    "status",
    "is_overdue",
    "remaining_seconds",
    "remaining_hours",
    "blockers",
    "submission_ready",
    "honesty",
)


def _parse_now(value: str) -> datetime.datetime:
    parsed = datetime.datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=KST)
    return parsed.astimezone(KST)


def _deadline() -> datetime.datetime:
    return datetime.datetime.fromisoformat(DEADLINE_KST_ISO).astimezone(KST)


def evaluate_deadline(now_iso: str, blockers=None) -> dict:
    now = _parse_now(now_iso)
    deadline = _deadline()
    remaining_seconds = int((deadline - now).total_seconds())
    if remaining_seconds <= 0:
        status = "overdue"
        is_overdue = True
    elif remaining_seconds <= DUE_SOON_HOURS * 3600:
        status = "due_soon"
        is_overdue = False
    else:
        status = "before_deadline"
        is_overdue = False
    return {
        "now": now.isoformat(timespec="seconds"),
        "deadline_kst": DEADLINE_KST_ISO,
        "deadline_et": DEADLINE_ET_TEXT,
        "status": status,
        "is_overdue": is_overdue,
        "remaining_seconds": remaining_seconds,
        "remaining_hours": round(remaining_seconds / 3600, 2),
        "blockers": list(blockers if blockers is not None else DEFAULT_BLOCKERS),
        "submission_ready": False,
        "honesty": list(HONESTY),
    }


def build_deadline(now=None, blockers=None) -> dict:
    if now is None:
        now = datetime.datetime.now(KST).isoformat(timespec="seconds")
    return evaluate_deadline(str(now), blockers=blockers)


def validate_deadline(report: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    for key in _REQUIRED_KEYS:
        if key not in report:
            problems.append(f"missing key: {key}")
    if problems:
        return problems
    if report["deadline_kst"] != DEADLINE_KST_ISO:
        problems.append(
            f"deadline_kst={report['deadline_kst']!r} != {DEADLINE_KST_ISO!r}"
        )
    if report["deadline_et"] != DEADLINE_ET_TEXT:
        problems.append(
            f"deadline_et={report['deadline_et']!r} != {DEADLINE_ET_TEXT!r}"
        )
    if report["submission_ready"] is not False:
        problems.append("submission_ready is not False")
    try:
        expected = evaluate_deadline(str(report["now"]), list(report["blockers"]))
    except (ValueError, TypeError) as exc:
        problems.append(f"now is not ISO datetime: {report['now']!r} ({exc})")
        return problems
    for key in ("status", "is_overdue", "remaining_seconds", "remaining_hours"):
        if report[key] != expected[key]:
            problems.append(f"{key}={report[key]!r} != {expected[key]!r}")
    joined = " ".join(str(x) for x in (report.get("honesty") or []))
    for marker in (
        "실제로 제출하지 않는다",
        "제출 준비 완료를 뜻하지 않는다",
        "지각 제출은 고려되지 않는다",
    ):
        if marker not in joined:
            problems.append(f"honesty missing {marker!r}")
    return problems


def format_text_report(report: dict) -> str:
    lines = [
        f"STATUS: {report['status']}",
        f"NOW: {report['now']}",
        f"DEADLINE_KST: {report['deadline_kst']}",
        f"DEADLINE_ET: {report['deadline_et']}",
        f"REMAINING_SECONDS: {report['remaining_seconds']}",
        f"REMAINING_HOURS: {report['remaining_hours']}",
        f"IS_OVERDUE: {str(report['is_overdue']).lower()}",
        f"BLOCKERS: {report['blockers']}",
        f"SUBMISSION_READY: {str(report['submission_ready']).lower()}",
    ]
    for line in report["honesty"]:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    now = None
    if "--now" in argv:
        idx = argv.index("--now")
        if idx + 1 < len(argv):
            now = argv[idx + 1]
    try:
        report = build_deadline(now=now)
    except ValueError as exc:
        sys.stdout.write(f"invalid now: {exc}\n")
        return 2
    problems = validate_deadline(report)
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    if problems:
        for problem in problems:
            sys.stdout.write(f"PROBLEM: {problem}\n")
        return 2
    return 1 if report["is_overdue"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
