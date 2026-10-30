"""제출 패키지 최종 묶음 점검 하네스.

11/03 제출 패키지 마감을 앞두고, 제출물 인벤토리(qa.submission_inventory),
제출 마감(qa.deadline), Pi 폴백 결정(qa.fallback_decision) 세 보고를
한곳에 모아 패키지 상태를 판정한다. 상태는 overdue(마감 경과),
incomplete(제출물 누락), blocked(제출 블로커 잔존),
ready_for_packaging(묶음 준비 완료) 중 하나다.

이 하네스는 실제로 제출하지 않으며, 패키지 준비 상태는 제출 완료를
뜻하지 않는다. submission_ready는 이 하네스 단독으로는 항상 False다.
Pi 실촬영 검증 전이며, 수치는 데모 기준이다.

실행: 프로젝트 루트에서 `python3 -m qa.final_package [--now ISO8601] [--date YYYY-MM-DD] [--device-confirmed] [--json]`
종료코드는 보고가 유효하고 마감이 지나지 않았으면 0, 마감이 지났으면 1,
입력이 유효하지 않거나 보고가 무효면 2다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PACKAGE_DATE_TARGET = "2026-11-03"

HONESTY = [
    "최종 묶음 점검은 실제로 제출하지 않는다",
    "패키지 준비 상태는 제출 완료를 뜻하지 않는다",
    "Pi 실촬영 검증 전",
    "수치는 데모 기준",
]

_REQUIRED_KEYS = (
    "inventory_present",
    "inventory_total",
    "inventory_missing",
    "deadline_status",
    "remaining_seconds",
    "fallback_status",
    "fallback_adopted",
    "blockers",
    "status",
    "submission_ready",
    "honesty",
)


def _package_status(
    *,
    inventory_present,
    inventory_total,
    inventory_missing,
    deadline_status,
    blockers,
) -> str:
    if deadline_status == "overdue":
        return "overdue"
    if inventory_missing or inventory_present != inventory_total:
        return "incomplete"
    if blockers:
        return "blocked"
    return "ready_for_packaging"


def evaluate_final_package(
    *,
    inventory_present,
    inventory_total,
    inventory_missing,
    deadline_status,
    remaining_seconds,
    fallback_status,
    fallback_adopted,
    blockers,
) -> dict:
    missing = list(inventory_missing or [])
    blocker_list = list(blockers or [])
    return {
        "inventory_present": int(inventory_present),
        "inventory_total": int(inventory_total),
        "inventory_missing": missing,
        "deadline_status": str(deadline_status),
        "remaining_seconds": int(remaining_seconds),
        "fallback_status": str(fallback_status),
        "fallback_adopted": bool(fallback_adopted),
        "blockers": blocker_list,
        "status": _package_status(
            inventory_present=int(inventory_present),
            inventory_total=int(inventory_total),
            inventory_missing=missing,
            deadline_status=str(deadline_status),
            blockers=blocker_list,
        ),
        "submission_ready": False,
        "honesty": list(HONESTY),
    }


def build_final_package(
    root: Path | None = None,
    now=None,
    today=None,
    pi_probe=None,
    device_confirmed: bool = False,
    which=None,
) -> dict:
    """세 보고를 재사용해 최종 묶음 보고를 만든다. 제출·촬영·호출은 하지 않는다."""
    from qa.deadline import build_deadline
    from qa.fallback_decision import build_decision
    from qa.pre_submission import BLOCKERS
    from qa.submission_inventory import build_inventory

    inventory = build_inventory(root)
    deadline = build_deadline(now=now)
    decision = build_decision(
        today=today,
        pi_probe=pi_probe,
        device_confirmed=device_confirmed,
        which=which,
    )
    return evaluate_final_package(
        inventory_present=inventory["present_files"],
        inventory_total=inventory["total_files"],
        inventory_missing=inventory["missing"],
        deadline_status=deadline["status"],
        remaining_seconds=deadline["remaining_seconds"],
        fallback_status=decision["status"],
        fallback_adopted=decision["fallback_adopted"],
        blockers=[b["id"] for b in BLOCKERS],
    )


def validate_final_package(report: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    for key in _REQUIRED_KEYS:
        if key not in report:
            problems.append(f"missing key: {key}")
    if problems:
        return problems
    if report["submission_ready"] is not False:
        problems.append("submission_ready is not False")
    missing = list(report["inventory_missing"] or [])
    if report["inventory_present"] + len(missing) != report["inventory_total"]:
        problems.append(
            "inventory_present + len(inventory_missing) != inventory_total: "
            f"{report['inventory_present']} + {len(missing)} != {report['inventory_total']}"
        )
    expected_status = _package_status(
        inventory_present=report["inventory_present"],
        inventory_total=report["inventory_total"],
        inventory_missing=missing,
        deadline_status=report["deadline_status"],
        blockers=list(report["blockers"] or []),
    )
    if report["status"] != expected_status:
        problems.append(f"status={report['status']!r} != {expected_status!r}")
    joined = " ".join(str(x) for x in (report.get("honesty") or []))
    for marker in (
        "실제로 제출하지 않는다",
        "제출 완료를 뜻하지 않는다",
        "Pi 실촬영 검증 전",
    ):
        if marker not in joined:
            problems.append(f"honesty missing {marker!r}")
    return problems


def format_text_report(report: dict) -> str:
    lines = [
        f"STATUS: {report['status']}",
        f"PACKAGE_DATE_TARGET: {PACKAGE_DATE_TARGET}",
        f"INVENTORY_PRESENT: {report['inventory_present']}",
        f"INVENTORY_TOTAL: {report['inventory_total']}",
        f"INVENTORY_MISSING: {report['inventory_missing']}",
        f"DEADLINE_STATUS: {report['deadline_status']}",
        f"REMAINING_SECONDS: {report['remaining_seconds']}",
        f"FALLBACK_STATUS: {report['fallback_status']}",
        f"FALLBACK_ADOPTED: {str(report['fallback_adopted']).lower()}",
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
    today = None
    if "--date" in argv:
        idx = argv.index("--date")
        if idx + 1 < len(argv):
            today = argv[idx + 1]
    try:
        report = build_final_package(
            now=now,
            today=today,
            device_confirmed="--device-confirmed" in argv,
        )
    except ValueError as exc:
        sys.stdout.write(f"invalid input: {exc}\n")
        return 2
    problems = validate_final_package(report)
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    if problems:
        for problem in problems:
            sys.stdout.write(f"PROBLEM: {problem}\n")
        return 2
    return 1 if report["status"] == "overdue" else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
