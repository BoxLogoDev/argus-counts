"""날짜·시각 기준 일관성 감사 하네스.

2026-11-02 폴백 결정의 기본 날짜가 시스템 로컬 날짜를 썼고 가상머신은
UTC라서, 한국 시간 00:00부터 09:00 사이에는 하루 전으로 판정되는
결함이 있었다. 폴백 결정 하네스의 KST 오늘 날짜 함수와 제출 마감
하네스의 KST 기본 시각으로 고쳤지만 그 회귀를 기계로 막는 감사는
없었다. 이 하네스가 그 감사를 맡는다.

검사는 세 가지다. 첫째, 시간대를 명시하지 않은 날짜와 시각 호출
패턴이 소스 어디에도 없어야 한다. 둘째, 명시적 UTC 현재 시각 호출은
허용 목록에 적힌 파일과 횟수 안에서만 있어야 한다. 셋째, 날짜와
마감을 판정하는 결정 모듈들의 소스 표기와 기본값을 실제 KST 계산과
대조해 일치해야 한다.

세션 식별자와 생성 시각에 쓰는 명시적 UTC는 날짜 판정이 아니다.
그래서 허용 목록으로 분리해 두고, 목록 밖의 사용과 횟수 변화를
문제로 삼는다. 경로 부분 이름이 tests인 파일은 검사에서 제외한다.
테스트 픽스처 문자열이 금지 패턴과 같은 글자를 포함할 수 있기
때문이다.

이 하네스는 실제로 제출하거나 촬영하거나 호출하지 않는다.
감사 통과는 제출 준비 완료를 뜻하지 않는다.

실행: 프로젝트 루트에서 `python3 -m qa.date_consistency [--json]`
종료코드는 일관성이 있으면 0, 일관성 문제가 있으면 1, 보고가
무효면 2다.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

from qa.deadline import KST

DECISION_MODULES = (
    "qa/fallback_decision.py",
    "qa/video_selection.py",
    "qa/deadline.py",
    "qa/final_package.py",
)

NAIVE_PATTERNS = (
    ("today_call", r"\.today\(\s*\)"),
    ("now_without_tz", r"\.now\(\s*\)"),
    ("utcnow_call", r"\.utcnow\("),
)

UTC_NOW_PATTERN = r"datetime\.now\(timezone\.utc\)"

UTC_NOW_ALLOWLIST = {
    "terminal/simulator.py": 2,
    "terminal/photo_intake.py": 2,
    "qa/sam_session.py": 1,
    "qa/pi_session.py": 1,
    "qa/sam_per_bin.py": 1,
}

SCAN_EXCLUDED_PARTS = {"tests", "__pycache__", ".git"}

DEFAULT_BLOCKERS = ["pi_real_capture_pending"]

HONESTY = [
    "날짜·시각 기준만 감사하며 실제로 제출·촬영·호출하지 않는다",
    "감사 통과는 제출 준비 완료를 뜻하지 않는다",
    "세션 식별자와 생성 시각의 명시적 UTC는 날짜 판정이 아니다",
]

_REQUIRED_KEYS = (
    "date_kst",
    "scanned_files",
    "naive_problems",
    "utc_problems",
    "decision_problems",
    "functional",
    "problems",
    "consistent",
    "blockers",
    "submission_ready",
    "honesty",
)


def _root(root=None) -> Path:
    if root is None:
        return Path(__file__).resolve().parents[1]
    return Path(root)


def _iter_source_files(root=None) -> list[str]:
    base = _root(root)
    files: list[str] = []
    for path in base.rglob("*.py"):
        rel_path = path.relative_to(base)
        if any(part in SCAN_EXCLUDED_PARTS for part in rel_path.parts):
            continue
        files.append(rel_path.as_posix())
    return sorted(files)


def _read(root, rel) -> str:
    return (_root(root) / rel).read_text(
        encoding="utf-8", errors="replace")


def scan_naive_patterns(root=None) -> list[str]:
    base = _root(root)
    problems: list[str] = []
    for rel in _iter_source_files(base):
        for lineno, line in enumerate(
                _read(base, rel).splitlines(), start=1):
            for name, pattern in NAIVE_PATTERNS:
                if re.search(pattern, line):
                    problems.append(
                        f"{rel}:{lineno}: naive pattern {name}")
    return problems


def scan_utc_allowlist(root=None) -> list[str]:
    base = _root(root)
    problems: list[str] = []
    for rel in _iter_source_files(base):
        count = len(re.findall(UTC_NOW_PATTERN, _read(base, rel)))
        if rel in UTC_NOW_ALLOWLIST:
            expected = UTC_NOW_ALLOWLIST[rel]
            if count != expected:
                problems.append(
                    f"{rel}: utc now count={count} != "
                    f"expected {expected}")
        elif count:
            problems.append(
                f"{rel}: utc now outside allowlist count={count}")
    return problems


def check_decision_sources(root=None) -> list[str]:
    base = _root(root)
    markers = {
        "qa/fallback_decision.py": ("def today_kst", "now(KST)"),
        "qa/video_selection.py": (
            "from qa.fallback_decision import", "today_kst"),
        "qa/deadline.py": ("datetime.datetime.now(KST)",),
        "qa/final_package.py": ("today=today",),
    }
    problems: list[str] = []
    for rel in DECISION_MODULES:
        if not (base / rel).is_file():
            problems.append(f"{rel}: file missing")
            continue
        text = _read(base, rel)
        for marker in markers.get(rel, ()):
            if marker not in text:
                problems.append(f"{rel}: missing {marker!r}")
    return problems


def check_decision_defaults() -> tuple[dict, list[str]]:
    from qa.deadline import build_deadline
    from qa.fallback_decision import build_decision, today_kst

    today = today_kst()
    functional = {
        "today_kst": today,
        "fallback_default_date": build_decision()["date"],
        "deadline_now": build_deadline()["now"],
    }
    problems: list[str] = []
    independent = datetime.datetime.now(KST).date().isoformat()
    if functional["today_kst"] != independent:
        problems.append(
            f"today_kst={functional['today_kst']!r} != "
            f"independent kst date {independent!r}")
    if functional["fallback_default_date"] != functional["today_kst"]:
        problems.append(
            f"fallback_default_date="
            f"{functional['fallback_default_date']!r} != "
            f"today_kst={functional['today_kst']!r}")
    deadline_now = functional["deadline_now"]
    if not isinstance(deadline_now, str) or not deadline_now.endswith("+09:00"):
        problems.append(
            f"deadline_now={deadline_now!r} does not end with +09:00")
    return functional, problems


def build_report(root=None) -> dict:
    base = _root(root)
    naive_problems = scan_naive_patterns(base)
    utc_problems = scan_utc_allowlist(base)
    source_problems = check_decision_sources(base)
    functional, default_problems = check_decision_defaults()
    decision_problems = source_problems + default_problems
    problems = naive_problems + utc_problems + decision_problems
    return {
        "date_kst": functional["today_kst"],
        "scanned_files": len(_iter_source_files(base)),
        "naive_problems": naive_problems,
        "utc_problems": utc_problems,
        "decision_problems": decision_problems,
        "functional": functional,
        "problems": problems,
        "consistent": not problems,
        "blockers": list(DEFAULT_BLOCKERS),
        "submission_ready": False,
        "honesty": list(HONESTY),
    }


def validate_report(report: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    for key in _REQUIRED_KEYS:
        if key not in report:
            problems.append(f"missing key: {key}")
    if problems:
        return problems
    if report["consistent"] != (not report["problems"]):
        problems.append(
            f"consistent={report['consistent']!r} != "
            f"{not report['problems']!r} for problems")
    if report["submission_ready"] is not False:
        problems.append("submission_ready is not False")
    if report["blockers"] != DEFAULT_BLOCKERS:
        problems.append(
            f"blockers={report['blockers']!r} != "
            f"{DEFAULT_BLOCKERS!r}")
    functional = report["functional"]
    if not isinstance(functional, dict):
        problems.append(f"functional is not a dict: {functional!r}")
    else:
        for key in ("today_kst", "fallback_default_date", "deadline_now"):
            if not isinstance(functional.get(key), str):
                problems.append(
                    f"functional {key} is not a string: "
                    f"{functional.get(key)!r}")
    joined = " ".join(str(x) for x in (report.get("honesty") or []))
    for marker in ("제출 준비 완료를 뜻하지 않는다", "날짜 판정이 아니다"):
        if marker not in joined:
            problems.append(f"honesty missing {marker!r}")
    return problems


def format_text_report(report: dict) -> str:
    lines = [
        f"CONSISTENT: {str(report['consistent']).lower()}",
        f"DATE_KST: {report['date_kst']}",
        f"SCANNED_FILES: {report['scanned_files']}",
        f"NAIVE_PROBLEMS: {len(report['naive_problems'])}",
        f"UTC_PROBLEMS: {len(report['utc_problems'])}",
        f"DECISION_PROBLEMS: {len(report['decision_problems'])}",
        f"FALLBACK_DEFAULT_DATE: "
        f"{report['functional']['fallback_default_date']}",
        f"DEADLINE_NOW: {report['functional']['deadline_now']}",
        f"BLOCKERS: {report['blockers']}",
        f"SUBMISSION_READY: {str(report['submission_ready']).lower()}",
    ]
    for line in report["honesty"]:
        lines.append(f"- {line}")
    for problem in report["problems"]:
        lines.append(f"PROBLEM: {problem}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    report = build_report()
    problems = validate_report(report)
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    if problems:
        for problem in problems:
            sys.stdout.write(f"PROBLEM: {problem}\n")
        return 2
    return 0 if report["consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
