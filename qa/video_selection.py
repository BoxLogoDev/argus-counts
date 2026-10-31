"""데모 영상 제출 후보 선택 점검 하네스.

11/03 제출 패키지 마감 작업의 사전 준비로, 패키징 시점에 어떤 기존
MP4를 제출 후보로 골라야 하는지를 기계적으로 정한다. 판정은
``qa.fallback_decision``을 재사용한다: 결정일(2026-11-02)까지 Pi가
준비되지 않아 폴백이 채택되면 폴백 렌더를, Pi가 준비됐으면 기본
영상을, 결정일 전이면 기본 영상을 기본 후보로 고른다. 고른 파일이
실제로 존재하는지와 크기까지 대조한다.

이 하네스는 실제로 제출하지 않고 영상을 새로 만들지도 않는다.
선택은 제출 준비 완료를 뜻하지 않으며, 폴백 영상은 Pi 실촬영이
아니다. Pi 준비 완료만으로 기본 영상이 실촬영본이 되지도 않는다 —
Pi가 준비되면 컷 3 실촬영 교체와 재렌더가 별도로 필요하다.

실행: 프로젝트 루트에서
`python3 -m qa.video_selection [--date YYYY-MM-DD] [--device-confirmed] [--json]`
종료코드는 보고가 유효하면 0, 무효면 2다.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

from qa.fallback_decision import DECISION_DATE, build_decision, evaluate_decision

PRIMARY_VIDEO = "demo/assets/argus-demo-draft.mp4"
FALLBACK_VIDEO = "demo/assets/argus-demo-fallback-draft.mp4"

HONESTY = [
    "선택은 실제로 제출하지 않는다",
    "선택은 제출 준비 완료를 뜻하지 않는다",
    "폴백 영상은 Pi 실촬영이 아닙니다",
    "Pi 준비 완료만으로 기본 영상이 실촬영본이 되지는 않는다",
]

_REQUIRED_KEYS = (
    "date",
    "decision_date",
    "pi_ready",
    "pi_blockers",
    "fallback_status",
    "fallback_adopted",
    "selected_video",
    "selection_reason",
    "primary_size",
    "fallback_size",
    "selected_size",
    "submission_ready",
    "problems",
    "honesty",
)

_REASON_BY_STATUS = {
    "fallback_due": "fallback_due",
    "pi_ready": "pi_ready",
    "pending": "pending_default",
}


def _size_or_none(value) -> int | None:
    if isinstance(value, bool):
        return None
    return value if isinstance(value, int) else None


def evaluate_selection(today: str, pi_ready: bool, pi_blockers=None,
                         primary_size=None, fallback_size=None) -> dict:
    """날짜·Pi 준비 상태·두 영상의 크기로 제출 후보를 정한다."""
    decision = evaluate_decision(today, pi_ready, pi_blockers)
    status = decision["status"]
    if status == "fallback_due":
        selected = FALLBACK_VIDEO
    else:
        selected = PRIMARY_VIDEO
    primary_size = _size_or_none(primary_size)
    fallback_size = _size_or_none(fallback_size)
    selected_size = fallback_size if selected == FALLBACK_VIDEO else primary_size
    problems: list[str] = []
    if selected_size is None:
        problems.append(f"selected video missing: {selected}")
    elif selected_size <= 0:
        problems.append(f"selected video is empty: {selected}")
    return {
        "date": today,
        "decision_date": DECISION_DATE,
        "pi_ready": bool(pi_ready),
        "pi_blockers": list(pi_blockers or []),
        "fallback_status": status,
        "fallback_adopted": bool(decision["fallback_adopted"]),
        "selected_video": selected,
        "selection_reason": _REASON_BY_STATUS[status],
        "primary_size": primary_size,
        "fallback_size": fallback_size,
        "selected_size": selected_size,
        "submission_ready": False,
        "problems": problems,
        "honesty": list(HONESTY),
    }


def _stat_size(root: Path, rel: str) -> int | None:
    try:
        return (root / rel).stat().st_size
    except OSError:
        return None


def build_selection(root=None, today=None, pi_probe=None,
                    device_confirmed: bool = False, which=None) -> dict:
    """폴백 결정과 실제 파일 크기를 모아 선택 보고를 만든다."""
    if root is None:
        root = Path(__file__).resolve().parents[1]
    root = Path(root)
    if today is None:
        today = datetime.date.today().isoformat()
    decision = build_decision(today=today, pi_probe=pi_probe,
                              device_confirmed=device_confirmed, which=which)
    return evaluate_selection(
        today,
        bool(decision["pi_ready"]),
        list(decision["pi_blockers"]),
        primary_size=_stat_size(root, PRIMARY_VIDEO),
        fallback_size=_stat_size(root, FALLBACK_VIDEO),
    )


def validate_selection(report: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    for key in _REQUIRED_KEYS:
        if key not in report:
            problems.append(f"missing key: {key}")
    if problems:
        return problems
    if report["decision_date"] != DECISION_DATE:
        problems.append(
            f"decision_date={report['decision_date']!r} != {DECISION_DATE!r}")
    if report["submission_ready"] is not False:
        problems.append("submission_ready is not False")
    try:
        expected = evaluate_selection(
            str(report["date"]), bool(report["pi_ready"]),
            list(report["pi_blockers"]),
            primary_size=report["primary_size"],
            fallback_size=report["fallback_size"])
    except (ValueError, TypeError) as exc:
        problems.append(f"cannot recompute selection: {exc}")
        return problems
    for key in ("fallback_status", "fallback_adopted", "selected_video",
                "selection_reason", "selected_size", "problems"):
        if report[key] != expected[key]:
            problems.append(f"{key}={report[key]!r} != {expected[key]!r}")
    joined = " ".join(str(x) for x in (report.get("honesty") or []))
    for marker in ("실제로 제출하지 않는다", "제출 준비 완료를 뜻하지 않는다",
                   "Pi 실촬영이 아닙니다", "실촬영본이 되지는 않는다"):
        if marker not in joined:
            problems.append(f"honesty missing {marker!r}")
    return problems


def format_text_report(report: dict) -> str:
    lines = [
        "Argus 데모 영상 제출 후보 선택",
        f"DATE: {report['date']}",
        f"DECISION_DATE: {report['decision_date']}",
        f"FALLBACK_STATUS: {report['fallback_status']}",
        f"FALLBACK_ADOPTED: {str(report['fallback_adopted']).lower()}",
        f"SELECTED_VIDEO: {report['selected_video']}",
        f"SELECTION_REASON: {report['selection_reason']}",
        f"SELECTED_SIZE: {report['selected_size']}",
        f"PRIMARY_SIZE: {report['primary_size']}",
        f"FALLBACK_SIZE: {report['fallback_size']}",
        f"PROBLEMS: {report['problems']}",
        "SUBMISSION_READY: false",
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
        report = build_selection(
            today=today, device_confirmed="--device-confirmed" in argv)
    except ValueError as exc:
        sys.stdout.write(f"invalid date: {exc}\n")
        return 2
    problems = validate_selection(report)
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
