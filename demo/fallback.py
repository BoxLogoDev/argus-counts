"""파일 입력 폴백 데모 자산 생성.

Pi 실기가 2026-11-02 기준일까지 늦을 경우를 대비한 대체 경로다.
데모 컷 3(Pi 촬영 자리)을 Pi 실촬영으로 주장하지 않고, 파일 기반
사진 입력 파이프라인(terminal.photo_intake)으로 촬영 단계를 보여 주는
자산(fallback.json·fallback.txt)을 만든다.

이 자산은 Pi 실촬영이 아니며, 계수는 모의 어댑터 기준이고
이 폴백 실행에서는 SAM 3.1 실호출을 하지 않았다. 그 사실을 HONESTY에 명시한다.

실행: 프로젝트 루트에서 `python3 -m demo.fallback` (기본 출력 demo/assets/)
표준 라이브러리만 사용한다(프로젝트 내부 모듈 제외).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from terminal.demo_data import demo_bin_ids
from terminal.photo_intake import run_photo_intake

FALLBACK_SESSION_ID = "FALLBACK-FILE-INPUT"
CUT_INDEX = 3
DECISION_DATE = "2026-11-02"
FAKE_PREFIX = "fake-fallback-photo-"

HONESTY = [
    "파일 입력 폴백 자산이며 Pi 실촬영이 아닙니다",
    "Pi 실촬영 검증 전",
    "계수는 모의 어댑터 기준이며 이 폴백 실행에서는 SAM 실호출을 하지 않았다",
    "수치는 데모 기준",
]


def fake_photo_bytes(bin_id: str) -> bytes:
    return (FAKE_PREFIX + bin_id).encode("utf-8")


def build_fallback_report() -> dict:
    bin_ids = demo_bin_ids()
    with tempfile.TemporaryDirectory() as tmp:
        captures: dict[str, Path] = {}
        for bin_id in bin_ids:
            path = Path(tmp) / f"{bin_id}.jpg"
            path.write_bytes(fake_photo_bytes(bin_id))
            captures[bin_id] = path
        return run_photo_intake(captures, session_id=FALLBACK_SESSION_ID)


def build_fallback_manifest(report: dict | None = None) -> dict:
    if report is None:
        report = build_fallback_report()
    return {
        "title": "Argus 파일 입력 폴백 데모 자산",
        "cut_index": CUT_INDEX,
        "replaces": "pi-placeholder",
        "decision_date": DECISION_DATE,
        "is_pi_real_capture": False,
        "capture_source": report["capture_source"],
        "source": report["source"],
        "session_id": report["session_id"],
        "summary": report["summary"],
        "bins": report["bins"],
        "honesty": list(HONESTY),
    }


def validate_fallback(manifest: dict) -> list[str]:
    problems: list[str] = []
    if not isinstance(manifest, dict):
        return [f"manifest is not a dict: {manifest!r}"]
    if manifest.get("cut_index") != CUT_INDEX:
        problems.append(f"cut_index={manifest.get('cut_index')!r} != {CUT_INDEX}")
    if manifest.get("is_pi_real_capture") is not False:
        problems.append(
            f"is_pi_real_capture={manifest.get('is_pi_real_capture')!r} is not False"
        )
    if manifest.get("capture_source") != "file":
        problems.append(f"capture_source={manifest.get('capture_source')!r} != 'file'")
    if manifest.get("source") != "mock":
        problems.append(f"source={manifest.get('source')!r} != 'mock'")
    summary = manifest.get("summary") or {}
    expected_summary = {
        "counted_bins": 6,
        "matched": 4,
        "mismatched": 2,
        "abs_diff_total": 6,
        "net_diff": 0,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            problems.append(f"summary.{key}={summary.get(key)!r} != {expected}")
    bins = manifest.get("bins") or []
    if len(bins) != 6:
        problems.append(f"bins len={len(bins)} != 6")
    for entry in bins:
        if not isinstance(entry, dict):
            problems.append(f"bin entry is not a dict: {entry!r}")
            continue
        bin_id = entry.get("bin_id")
        photo = entry.get("photo") or {}
        expected_sha = hashlib.sha256(fake_photo_bytes(str(bin_id))).hexdigest()
        if photo.get("sha256") != expected_sha:
            problems.append(
                f"bin {bin_id}: photo sha256={photo.get('sha256')!r} != {expected_sha}"
            )
        if bin_id == "A-01-02":
            if entry.get("verdict") != "short":
                problems.append(f"A-01-02 verdict={entry.get('verdict')!r} != 'short'")
            if entry.get("diff") != -3:
                problems.append(f"A-01-02 diff={entry.get('diff')!r} != -3")
    honesty = manifest.get("honesty") or []
    joined = " ".join(str(line) for line in honesty)
    if "Pi 실촬영이 아닙니다" not in joined:
        problems.append("honesty missing 'Pi 실촬영이 아닙니다'")
    if "데모 기준" not in joined:
        problems.append("honesty missing '데모 기준'")
    return problems


def build_fallback_text(manifest: dict | None = None) -> str:
    if manifest is None:
        manifest = build_fallback_manifest()
    summary = manifest["summary"]
    lines = [
        f"{manifest['title']}",
        f"컷 {manifest['cut_index']} · 세션 {manifest['session_id']} · "
        f"capture_source={manifest['capture_source']} · source={manifest['source']}",
        (
            f"데모 기준: 빈 {summary['counted_bins']}개 중 일치 {summary['matched']}건, "
            f"불일치 {summary['mismatched']}건, 절대 차이 {summary['abs_diff_total']}개, "
            f"순차이 {summary['net_diff']}"
        ),
    ]
    for line in manifest["honesty"]:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def write_fallback(out_dir) -> list[Path]:
    manifest = build_fallback_manifest()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    targets = {
        "fallback.json": json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        "fallback.txt": build_fallback_text(manifest),
    }
    written: list[Path] = []
    for name, text in targets.items():
        path = out / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 파일 입력 폴백 데모 자산 생성")
    parser.add_argument("--out", default="demo/assets", help="출력 디렉터리")
    args = parser.parse_args(argv)
    for path in write_fallback(args.out):
        print(path)
    problems = validate_fallback(build_fallback_manifest())
    if problems:
        for problem in problems:
            print(f"문제: {problem}")
        return 1
    print("검증 통과: 문제 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
