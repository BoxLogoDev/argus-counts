"""제출 패키지 내보내기 하네스.

11/03 제출 패키지 마감 작업의 한 단위다. 제출물 인벤토리
(qa.submission_inventory)가 고정한 제출물 18개를 staging 디렉터리로
실제로 복사하고, 복사본의 크기·SHA-256을 원본과 다시 대조해
'무엇이 패키지에 들어갔는지'를 파일로 증명한다.

이 내보내기는 파일 복사·해시 대조만 하며 실제로 제출하지 않는다.
내보내기가 온전해도 제출 가능을 뜻하지 않는다 — 제출 블로커
(pi_real_capture_pending)가 남아 있는 동안 제출 상태는
SUBMISSION_READY: false다. Pi 실촬영 검증 전이며, 데모 컷 3은
플레이스홀더 상태이고 수치는 데모 기준이다.

매니페스트(package-manifest.json) 자체는 복사 대상에 넣지 않는다 —
자기 해시를 자기 안에 적는 모순을 피하기 위해서다.

실행: 프로젝트 루트에서 `python3 -m qa.package_export --out-dir <경로>`
`--json`을 주면 같은 내용을 JSON으로 출력한다.
종료코드: 검증 통과 0, 검증 실패 1, 인자 오류 2(argparse).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from qa.submission_inventory import BLOCKERS, HONESTY, build_inventory

ROOT = Path(__file__).resolve().parent.parent

MANIFEST_NAME = "package-manifest.json"

EXPORT_HONESTY = list(HONESTY) + [
    "내보내기는 staging 디렉터리로 파일을 복사할 뿐 실제로 제출하지 않는다",
]


def build_export(out_dir, source_root: Path | None = None) -> dict:
    """제출물을 out_dir 아래 상대경로 그대로 복사하고 매니페스트를 만든다.

    원본이 없는 제출물은 복사하지 않고 missing에 정직하게 남긴다.
    복사한 파일은 바이트를 다시 읽어 크기·SHA-256을 기록한다.
    매니페스트 파일도 out_dir에 쓴다(복사 대상에는 포함하지 않는다).
    """
    source = Path(source_root) if source_root is not None else ROOT
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory(source)

    files: list[dict] = []
    total_bytes = 0
    for entry in inventory["deliverables"]:
        rel = entry["path"]
        if not entry["exists"]:
            files.append(
                {
                    "category": entry["category"],
                    "path": rel,
                    "copied": False,
                    "size_bytes": None,
                    "sha256": None,
                }
            )
            continue
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / rel, dest)
        data = dest.read_bytes()
        files.append(
            {
                "category": entry["category"],
                "path": rel,
                "copied": True,
                "size_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
        total_bytes += len(data)

    export = {
        "title": "Argus 제출 패키지 내보내기",
        "out_dir": str(out),
        "files": files,
        "total_files": len(files),
        "copied_files": sum(1 for f in files if f["copied"]),
        "missing": list(inventory["missing"]),
        "total_bytes": total_bytes,
        "blockers": [dict(b) for b in inventory["blockers"]],
        # 블로커가 남아 있는 한 내보내기 완결과 무관하게 항상 False다.
        "submission_ready": False,
        "honesty": list(EXPORT_HONESTY),
    }
    manifest_path = out / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return export


def validate_export(export, out_dir=None, source_root: Path | None = None) -> list[str]:
    """내보내기 기록을 원본 인벤토리와 staging 실제 파일로 다시 대조한다."""
    if not isinstance(export, dict):
        return [f"export is not a dict: {export!r}"]
    source = Path(source_root) if source_root is not None else ROOT
    problems: list[str] = []

    if export.get("submission_ready") is not False:
        problems.append(
            f"submission_ready={export.get('submission_ready')!r} is not False"
        )
    blocker_ids = [
        b.get("id") if isinstance(b, dict) else None
        for b in (export.get("blockers") or [])
    ]
    if blocker_ids != [b["id"] for b in BLOCKERS]:
        problems.append(f"blocker ids={blocker_ids!r} != {[b['id'] for b in BLOCKERS]!r}")

    files = export.get("files")
    if not isinstance(files, list):
        problems.append(f"files is not a list: {files!r}")
        files = []
    if export.get("total_files") != len(files):
        problems.append(
            f"total_files={export.get('total_files')!r} != len(files)={len(files)}"
        )
    copied = [f for f in files if isinstance(f, dict) and f.get("copied")]
    if export.get("copied_files") != len(copied):
        problems.append(
            f"copied_files={export.get('copied_files')!r} != actual {len(copied)}"
        )
    copied_bytes = sum(f.get("size_bytes") or 0 for f in copied)
    if export.get("total_bytes") != copied_bytes:
        problems.append(
            f"total_bytes={export.get('total_bytes')!r} != copied sum {copied_bytes}"
        )

    inventory = build_inventory(source)
    inv_by_path = {e["path"]: e for e in inventory["deliverables"]}
    expected_missing = [
        e["path"] for e in inventory["deliverables"] if not e["exists"]
    ]
    if export.get("missing") != expected_missing:
        problems.append(
            f"missing={export.get('missing')!r} != actual {expected_missing!r}"
        )

    out = Path(out_dir) if out_dir is not None else (
        Path(export["out_dir"]) if export.get("out_dir") else None
    )
    for entry in files:
        if not isinstance(entry, dict):
            problems.append(f"file entry is not a dict: {entry!r}")
            continue
        rel = entry.get("path")
        inv = inv_by_path.get(rel)
        if inv is None:
            problems.append(f"{rel}: not in inventory deliverables")
            continue
        if entry.get("copied") != inv["exists"]:
            problems.append(
                f"{rel}: copied={entry.get('copied')!r} != source exists {inv['exists']!r}"
            )
            continue
        if not entry.get("copied"):
            continue
        if entry.get("size_bytes") != inv["size_bytes"]:
            problems.append(
                f"{rel}: size_bytes={entry.get('size_bytes')!r} != source {inv['size_bytes']!r}"
            )
        if entry.get("sha256") != inv["sha256"]:
            problems.append(f"{rel}: sha256 does not match source inventory")
        if out is not None:
            dest = out / rel
            if not dest.is_file():
                problems.append(f"{rel}: copied file missing in out_dir")
            else:
                data = dest.read_bytes()
                if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
                    problems.append(f"{rel}: copied file sha256 mismatch on disk")
                if len(data) != entry.get("size_bytes"):
                    problems.append(f"{rel}: copied file size mismatch on disk")

    honesty = export.get("honesty") or []
    joined = " ".join(str(line) for line in honesty)
    for phrase in ("실제로 제출하지 않는다", "Pi 실촬영 검증 전", "데모 기준"):
        if phrase not in joined:
            problems.append(f"honesty missing {phrase!r}")
    return problems


def build_export_text(export: dict) -> str:
    lines = [
        str(export["title"]),
        f"출력 디렉터리: {export['out_dir']}",
        (
            f"제출물 {export['copied_files']}/{export['total_files']}개 복사 · "
            f"합계 {export['total_bytes']}바이트"
        ),
    ]
    for entry in export["files"]:
        sha = (entry["sha256"] or "-")[:12]
        size = entry["size_bytes"] if entry["size_bytes"] is not None else "-"
        lines.append(
            f"- [{entry['category']}] {entry['path']} · copied={entry['copied']} · "
            f"size={size} · sha256={sha}"
        )
    if export["missing"]:
        lines.append(f"누락: {', '.join(export['missing'])}")
    lines.append(f"매니페스트: {MANIFEST_NAME}")
    lines.append(f"BLOCKERS: {len(export['blockers'])}")
    for blocker in export["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    lines.append("SUBMISSION_READY: false")
    for line in export["honesty"]:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 제출 패키지 내보내기")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    export = build_export(args.out_dir)
    problems = validate_export(export, args.out_dir)
    if args.json:
        sys.stdout.write(json.dumps(export, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(build_export_text(export))
    if problems:
        for problem in problems:
            sys.stderr.write(f"PROBLEM: {problem}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
