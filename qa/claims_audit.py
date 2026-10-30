"""현재형 주장 감사 하네스.

README와 docs 문서에서 아직 하지 않은 일을 이미 한 것처럼 현재형으로
단정하는 문장을 잡아낸다. 예를 들어 SAM 실호출을 이미 연동한 것처럼
쓰거나 Pi 실촬영을 이미 검증한 것처럼 쓰는 문장이 대상이다.

정직성 원칙은 단순하다. 하지 않은 일은 하지 않았다고 쓴다.
모의(mock) 결과는 실호출 결과로 주장하지 않는다.
검증 전인 하드웨어 연동을 검증 완료로 쓰지 않는다.
위험 패턴에 걸려도 같은 줄에 모의나 미실시나 예정 같은 정직성
표기가 있으면 위반으로 보지 않는다. SAM 3.1 실호출은 2026-10-30
단일 빈 스모크로 검증했으므로, 단일 빈·스모크로 범위를 한정한
실호출 검증 서술은 정직성 표기로 본다. 전체 세션 실호출 완료 같은
과장 서술은 여전히 위반이다.

실행: 프로젝트 루트에서 `python3 -m qa.claims_audit`
위반이 없으면 종료코드 0, 있으면 1.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCAN_FILES = (
    "README.md",
    "docs/submission-story.md",
    "docs/demo-script.md",
    "docs/submission-summary-en.md",
    "docs/submission-runbook.md",
    "docs/devpost-submission.md",
)

RISKY_PATTERNS = [
    r"SAM 3\.1.*실호출",
    r"실호출.*SAM 3\.1",
    r"SAM.*실호출.*(연동|완료|성공)",
    r"실호출.*연동",
    r"연동.*실호출",
    r"실호출.*(완료|성공|했다|했습니다)",
    r"실촬영",
    r"Pi.*검증.*(완료|성공|마쳤|마친|끝났|됐다|되었다)",
    r"실기.*검증.*(완료|성공|마쳤|마친|끝났|됐다|되었다)",
    r"Pi.*촬영.*(완료|성공)",
    r"real SAM.*call",
    r"live SAM",
]

HONESTY_MARKERS = (
    "모의",
    "mock",
    "미실시",
    "미도착",
    "아직",
    "하지 않",
    "하지 않은",
    "검증 전",
    "예정",
    "교체",
    "플레이스홀더",
    "placeholder",
    "데모 기준",
    "Demo basis",
    "가안",
    "tentative",
    "not yet",
    "no real",
    "크레딧",
    "입금 확인 후",
    "단일 빈",
    "스모크",
    "single-bin",
    "smoke",
    "has not",
    "have not",
    "not been",
)

_COMPILED_PATTERNS = tuple(
    (pattern, re.compile(pattern, re.IGNORECASE)) for pattern in RISKY_PATTERNS
)


def _has_honesty_marker(line: str) -> bool:
    lowered = line.lower()
    return any(marker.lower() in lowered for marker in HONESTY_MARKERS)


def audit_text(rel_path: str, text: str) -> list[dict]:
    """한 문서의 텍스트를 줄 단위로 감사해 위반 목록을 돌려준다."""
    violations: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        matched: str | None = None
        for pattern, compiled in _COMPILED_PATTERNS:
            if compiled.search(line):
                matched = pattern
                break
        if matched is None:
            continue
        if _has_honesty_marker(line):
            continue
        violations.append(
            {
                "file": rel_path,
                "line": lineno,
                "text": line.strip(),
                "pattern": matched,
            }
        )
    return violations


def audit_files(root: str | Path) -> dict:
    """SCAN_FILES를 root 기준으로 읽어 감사 결과를 돌려준다."""
    root_path = Path(root)
    violations: list[dict] = []
    missing: list[str] = []
    checked_files = 0
    for rel_path in SCAN_FILES:
        try:
            text = (root_path / rel_path).read_text(encoding="utf-8")
        except OSError:
            missing.append(rel_path)
            continue
        checked_files += 1
        violations.extend(audit_text(rel_path, text))
    return {
        "violations": violations,
        "missing": missing,
        "checked_files": checked_files,
    }


def main(argv: list[str] | None = None) -> int:
    """프로젝트 루트를 감사한다. argv[0]이 있으면 그 경로를 루트로 쓴다."""
    if argv:
        root = Path(argv[0])
    else:
        root = Path(__file__).resolve().parent.parent
    result = audit_files(root)
    for rel_path in result["missing"]:
        sys.stdout.write(f"MISSING: {rel_path}\n")
    violations = result["violations"]
    if not violations:
        sys.stdout.write(
            f"CLAIMS AUDIT: PASS ({result['checked_files']} files checked)\n"
        )
        return 0
    for violation in violations:
        sys.stdout.write(
            f"{violation['file']}:{violation['line']}: "
            f"[{violation['pattern']}] {violation['text']}\n"
        )
    sys.stdout.write(f"CLAIMS AUDIT: FAIL ({len(violations)} violations)\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
