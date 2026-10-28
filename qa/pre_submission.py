"""제출 전 전수 점검 하네스.

기존 점검들(QA 기준값 대조, standalone 점검, 현재형 주장 감사)과
데모 자산의 존재·정합을 한 번에 묶어 기계적으로 확인한다.
기계적 체크가 전부 통과해도 제출 블로커가 남아 있으면 제출 가능
상태가 아니다. 블로커는 종료코드가 아니라 별도 목록으로 보고한다:
Pi 실촬영 검증과 SAM 3.1 실호출은 아직 하지 않은 일이다.

실행: 프로젝트 루트에서 `python3 -m qa.pre_submission`
`--json`을 주면 같은 내용을 JSON으로 출력한다.
기계적 체크가 전부 통과하면 종료코드 0, 하나라도 실패하면 1.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

from qa.claims_audit import audit_files
from qa.harness import run_checks as run_qa_checks
from qa.standalone import run_standalone_checks

ROOT = Path(__file__).resolve().parent.parent

# 현재 사실인 제출 블로커. 코드가 임의로 해소 판정하지 않고 항상 보고한다.
BLOCKERS = [
    {
        "id": "pi_real_capture_pending",
        "detail": "Pi 실촬영 검증 전 — 데모 컷 3은 플레이스홀더이며 Pi 도착 후 교체해야 한다",
    },
    {
        "id": "sam_real_call_pending",
        "detail": "SAM 3.1 실호출 미실시 — 현재 모의(mock) 어댑터이며 크레딧 입금 확인과 API 키 발급 후 전환해야 한다",
    },
]

DEMO_ASSET_FILES = [
    "demo/assets/captions.srt",
    "demo/assets/captions.vtt",
    "demo/assets/shot-list.json",
    "demo/assets/assembly.json",
    "demo/assets/narration.json",
    "demo/assets/captures/capture-manifest.json",
    "demo/assets/argus-demo-draft.mp4",
]

VIDEO_MIN_BYTES = 100_000

HONESTY = [
    "기계적 체크 통과는 제출 가능을 뜻하지 않는다",
    "모의 어댑터 동작 중",
    "수치는 데모 기준",
]


@dataclass(frozen=True)
class PreSubmissionCheck:
    name: str
    passed: bool
    detail: str


def _aggregate(name: str, checks) -> PreSubmissionCheck:
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    return PreSubmissionCheck(name, passed == total, f"{passed}/{total} passed")


def _check_demo_consistency(root: Path) -> PreSubmissionCheck:
    name = "demo_assets_consistent"
    try:
        shot = json.loads((root / "demo/assets/shot-list.json").read_text(encoding="utf-8"))
        assembly = json.loads((root / "demo/assets/assembly.json").read_text(encoding="utf-8"))
        narration = json.loads((root / "demo/assets/narration.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (root / "demo/assets/captures/capture-manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        return PreSubmissionCheck(name, False, f"asset read failed: {exc!r}")
    problems: list[str] = []
    if shot.get("total_seconds") != 180 or shot.get("cut_count") != 9:
        problems.append(
            f"shot-list total_seconds={shot.get('total_seconds')} cut_count={shot.get('cut_count')}"
        )
    placeholders = [s for s in assembly.get("segments", []) if s.get("placeholder")]
    if assembly.get("total_seconds") != 180 or assembly.get("segment_count") != 9:
        problems.append(
            f"assembly total_seconds={assembly.get('total_seconds')} "
            f"segment_count={assembly.get('segment_count')}"
        )
    if len(placeholders) != 1 or placeholders[0].get("index") != 3:
        problems.append(f"assembly placeholders={[s.get('index') for s in placeholders]}")
    if narration.get("total_seconds") != 180 or narration.get("pace_warnings") != []:
        problems.append(
            f"narration total_seconds={narration.get('total_seconds')} "
            f"pace_warnings={narration.get('pace_warnings')}"
        )
    if manifest.get("all_ok") is not True or manifest.get("capture_count") != 4:
        problems.append(
            f"manifest all_ok={manifest.get('all_ok')} capture_count={manifest.get('capture_count')}"
        )
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems))
    return PreSubmissionCheck(name, True, "shot/assembly/narration/manifest consistent at 180s, 9 cuts")


def run_pre_submission_checks(root: Path | None = None) -> dict:
    """전수 점검을 실행한다. 개별 예외는 그 체크만 실패로 기록한다."""
    root = Path(root) if root is not None else ROOT
    checks: list[PreSubmissionCheck] = []

    try:
        checks.append(_aggregate("qa_harness", run_qa_checks()))
    except Exception as exc:
        checks.append(PreSubmissionCheck("qa_harness", False, f"raised: {exc!r}"))

    try:
        checks.append(_aggregate("standalone", run_standalone_checks(root)))
    except Exception as exc:
        checks.append(PreSubmissionCheck("standalone", False, f"raised: {exc!r}"))

    try:
        claims = audit_files(root)
        if not claims["violations"] and not claims["missing"]:
            checks.append(
                PreSubmissionCheck("claims_audit", True, f"{claims['checked_files']} files clean")
            )
        else:
            parts = [f"missing={claims['missing']}"] if claims["missing"] else []
            parts.extend(
                f"{v['file']}:{v['line']}: {v['text']}" for v in claims["violations"]
            )
            checks.append(PreSubmissionCheck("claims_audit", False, "; ".join(parts)))
    except Exception as exc:
        checks.append(PreSubmissionCheck("claims_audit", False, f"raised: {exc!r}"))

    missing = [rel for rel in DEMO_ASSET_FILES if not (root / rel).is_file()]
    checks.append(
        PreSubmissionCheck(
            "demo_assets_present",
            not missing,
            f"missing={missing}" if missing else f"{len(DEMO_ASSET_FILES)} assets present",
        )
    )

    checks.append(_check_demo_consistency(root))

    video = root / "demo/assets/argus-demo-draft.mp4"
    try:
        size = video.stat().st_size if video.is_file() else 0
    except OSError:
        size = 0
    checks.append(
        PreSubmissionCheck(
            "video_draft_present",
            size > VIDEO_MIN_BYTES,
            f"bytes={size}" if size else "video missing",
        )
    )

    passed = sum(1 for c in checks if c.passed)
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "mechanical_pass": passed == len(checks),
        "blockers": [dict(b) for b in BLOCKERS],
        # 블로커가 남아 있는 한 기계적 통과와 무관하게 항상 False다.
        "submission_ready": False,
    }


def build_report(root: Path | None = None) -> dict:
    """run_pre_submission_checks 결과를 JSON 직렬화 가능한 dict로 바꾼다."""
    result = run_pre_submission_checks(root)
    return {
        "checks": [
            {"name": c.name, "passed": c.passed, "detail": c.detail} for c in result["checks"]
        ],
        "passed": result["passed"],
        "total": result["total"],
        "mechanical_pass": result["mechanical_pass"],
        "blockers": result["blockers"],
        "submission_ready": result["submission_ready"],
        "honesty": list(HONESTY),
    }


def format_text_report(report: dict) -> str:
    lines: list[str] = []
    for check in report["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"[{mark}] {check['name']} — {check['detail']}")
    lines.append(
        f"PRE_SUBMISSION: {report['passed']}/{report['total']} mechanical passed"
    )
    lines.append(f"BLOCKERS: {len(report['blockers'])}")
    for blocker in report["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    lines.append("SUBMISSION_READY: false")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    report = build_report()
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    return 0 if report["mechanical_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
