"""제출 패키지 standalone 점검.

공개 저장소가 해커톤 제출용 standalone 패키지인지 기계적으로 확인한다:
필수 파일이 있고, 실제 회사 식별자나 비밀값 패턴이 섞이지 않았으며,
제출 서술에 정직성 표기(모의·데모 기준·테마 가안)가 들어 있는지 본다.
standalone 점검은 현재형 주장 감사도 포함하며 체크는 모두 6개다.

실행: 프로젝트 루트에서 `python3 -m qa.standalone`
전부 통과하면 종료코드 0, 하나라도 실패하면 1.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from qa.claims_audit import audit_files

ROOT = Path(__file__).resolve().parent.parent

TEXT_SUFFIXES = {".py", ".md", ".txt", ".json"}
SKIP_DIRS = {"__pycache__", ".git"}

REQUIRED_FILES = [
    "README.md",
    "docs/submission-story.md",
    "docs/submission-summary-en.md",
    "docs/demo-script.md",
    "terminal/sam_adapter.py",
    "terminal/reconcile.py",
    "terminal/report.py",
    "console/server.py",
    "qa/harness.py",
    ".claude/skills/verify-argus/SKILL.md",
    ".claude/skills/verify-argus/features/README.md",
]

# 금지 식별자는 이 파일 자체가 스캔에 걸리지 않도록 조각으로 조립한다.
FORBIDDEN_TERMS = [
    "LS" + "MTRON",
    "LS " + "MTRON",
    "LS" + "엠트론",
    "엘에스" + "엠트론",
    "LS " + "ITC",
    "사내" + "망",
]

SECRET_PATTERNS = [
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{8,}['\"]"),
]

# 제출 서술에 반드시 있어야 하는 정직성 표기.
HONESTY_MARKERS = {
    "docs/submission-story.md": ["모의", "데모 기준", "가안"],
    "docs/submission-summary-en.md": ["mock", "Demo basis", "tentative"],
    "docs/demo-script.md": ["Pi", "모의"],
}


@dataclass(frozen=True)
class StandaloneCheck:
    name: str
    passed: bool
    detail: str


def iter_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


def scan_text(text: str) -> list[str]:
    hits = []
    for term in FORBIDDEN_TERMS:
        if term in text:
            hits.append(f"forbidden term: {term}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(f"secret pattern: {pattern.pattern[:40]}")
    return hits


def run_standalone_checks(root: Path | None = None) -> list[StandaloneCheck]:
    root = Path(root) if root is not None else ROOT
    checks: list[StandaloneCheck] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append(StandaloneCheck(name=name, passed=bool(passed), detail=str(detail)))

    missing = [rel for rel in REQUIRED_FILES if not (root / rel).is_file()]
    add("required_files_present", not missing,
        f"missing={missing}" if missing else f"{len(REQUIRED_FILES)} files present")

    self_name = Path(__file__).name
    dirty: list[str] = []
    scanned = 0
    for path in iter_text_files(root):
        if path.name == self_name and path.parent.name == "qa":
            continue  # 금지어 리터럴을 담은 점검 모듈 자신은 제외
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for hit in scan_text(text):
            dirty.append(f"{path.relative_to(root)}: {hit}")
    add("no_forbidden_or_secret_content", not dirty,
        "; ".join(dirty) if dirty else f"{scanned} files clean")

    for rel, markers in HONESTY_MARKERS.items():
        target = root / rel
        if not target.is_file():
            add(f"honesty_markers:{rel}", False, "file missing")
            continue
        text = target.read_text(encoding="utf-8")
        absent = [m for m in markers if m not in text]
        add(f"honesty_markers:{rel}", not absent,
            f"absent={absent}" if absent else f"markers={markers}")

    claims = audit_files(root)
    claims_violations = claims["violations"]
    claims_missing = claims["missing"]
    if not claims_violations and not claims_missing:
        add("claims_audit_clean", True, f"{claims['checked_files']} files clean")
    else:
        parts: list[str] = []
        if claims_missing:
            parts.append(f"missing={claims_missing}")
        parts.extend(
            f"{violation['file']}:{violation['line']}: {violation['text']}"
            for violation in claims_violations
        )
        add("claims_audit_clean", False, "; ".join(parts))

    return checks


def main(argv: list[str] | None = None) -> int:
    checks = run_standalone_checks()
    passed = 0
    for check in checks:
        mark = "PASS" if check.passed else "FAIL"
        if check.passed:
            passed += 1
        sys.stdout.write(f"[{mark}] {check.name} — {check.detail}\n")
    sys.stdout.write(f"STANDALONE: {passed}/{len(checks)} passed\n")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
