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
이미 내보낸 staging은 `python3 -m qa.package_export --verify-dir <경로>`로
매니페스트(package-manifest.json)만 읽어 읽기 전용으로 재검증할 수 있다 —
재내보내기로 원본 staging을 덮지 않고 복사본을 다시 대조하는 경로다.
종료코드: 검증 통과 0, 검증 실패 1, 인자 오류·매니페스트 없음 2(argparse 포함).
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


def verify_export_dir(out_dir, source_root: Path | None = None):
    """기존 staging 디렉터리를 매니페스트만으로 읽기 전용 재검증한다.

    반환값은 (export, problems)다. 매니페스트가 없거나 JSON이 아니거나
    dict가 아니면 예외를 내지 않고 (None, [문제])를 돌려준다.
    매니페스트에 기록된 out_dir 문자열이 현재 경로와 달라도(이동된
    staging) 그 자체는 문제로 보지 않는다 — 파일 대조는 인자로 받은
    out_dir 기준으로만 한다. 이 함수는 어떤 파일도 쓰지 않는다.
    """
    out = Path(out_dir)
    manifest_path = out / MANIFEST_NAME
    if not manifest_path.is_file():
        return None, [f"manifest missing: {MANIFEST_NAME} not found in {out}"]
    try:
        export = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, [f"manifest unreadable: {MANIFEST_NAME}: {type(exc).__name__}"]
    if not isinstance(export, dict):
        return None, [f"manifest is not a dict: {type(export).__name__}"]
    problems = validate_export(export, out, source_root)
    return export, problems


def build_verify_text(export, problems, out_dir) -> str:
    lines = [
        "Argus 제출 패키지 재검증",
        f"검증 디렉터리: {out_dir}",
    ]
    if export is None:
        lines.append("매니페스트를 읽지 못했습니다")
    else:
        lines.append(
            f"제출물 {export.get('copied_files')}/{export.get('total_files')}개 복사 · "
            f"합계 {export.get('total_bytes')}바이트"
        )
        lines.append(f"매니페스트: {MANIFEST_NAME}")
        blocker_ids = [
            b.get("id") if isinstance(b, dict) else None
            for b in (export.get("blockers") or [])
        ]
        lines.append(f"BLOCKERS: {len(blocker_ids)}")
        for blocker_id in blocker_ids:
            lines.append(f"- {blocker_id}")
    lines.append(f"VERIFIED: {str(not problems).lower()}")
    if problems:
        lines.append(f"PROBLEMS: {len(problems)}")
        for problem in problems:
            lines.append(f"- {problem}")
    lines.append("SUBMISSION_READY: false")
    lines.append("- 재검증은 파일을 복사하거나 수정하지 않는다")
    lines.append("- 재검증은 실제로 제출하지 않는다")
    lines.append("- Pi 실촬영 검증 전")
    return "\n".join(lines) + "\n"


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
    parser.add_argument("--out-dir")
    parser.add_argument("--verify-dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if bool(args.out_dir) == bool(args.verify_dir):
        parser.error("--out-dir와 --verify-dir 중 정확히 하나만 지정해야 합니다")

    if args.verify_dir:
        export, problems = verify_export_dir(args.verify_dir)
        if args.json:
            payload = {
                "verified": export is not None and not problems,
                "problems": problems,
                "export": export,
            }
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        else:
            sys.stdout.write(build_verify_text(export, problems, args.verify_dir))
        if export is None:
            return 2
        return 0 if not problems else 1

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
