"""제출물 인벤토리 하네스.

11/03 제출 패키지 마감 전에, 제출물로 올릴 파일 목록을 존재·크기·
SHA-256으로 고정해 두는 하네스다. 제출 직전에 이 인벤토리와 실제
파일을 다시 대조하면, 낡은 영상·문서가 섞인 채로 제출하는 사고를
기계적으로 잡을 수 있다.

이 인벤토리는 파일 대조만 하며 실제로 제출하지 않는다. 인벤토리가
온전해도 제출 가능을 뜻하지 않는다 — 제출 블로커(pi_real_capture_pending)가
남아 있는 동안 제출 상태는 SUBMISSION_READY: false다.
Pi 실촬영 검증 전이며, 데모 컷 3은 플레이스홀더 상태다.

인벤토리 산출 파일(submission-inventory.json/.txt) 자체는
DELIVERABLES에 넣지 않는다 — 자기 해시를 자기 안에 적는 모순을
피하기 위해서다.

실행: 프로젝트 루트에서 `python3 -m qa.submission_inventory`
`--json`을 주면 같은 내용을 JSON으로 출력하고, `--out-dir <경로>`를
주면 인벤토리 파일을 그 디렉터리에 쓴다.
종료코드: 검증 통과 0, 실패 1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPO_URL = "https://github.com/BoxLogoDev/argus-counts"

DEADLINE = "2026-11-04 21:00 ET = 2026-11-05 11:00 KST"

# 현재 사실인 제출 블로커. qa.pre_submission.BLOCKERS와 동일 문구이며,
# 코드가 임의로 해소 판정하지 않고 항상 보고한다.
BLOCKERS = [
    {
        "id": "pi_real_capture_pending",
        "detail": "Pi 실촬영 검증 전 — 데모 컷 3은 플레이스홀더이며 Pi 도착 후 교체해야 한다",
    },
]

HONESTY = [
    "인벤토리는 파일 존재·크기·해시 대조만 하며 실제로 제출하지 않는다",
    "Pi 실촬영 검증 전",
    "수치는 데모 기준",
    "인벤토리가 온전해도 제출 가능을 뜻하지 않는다",
]

DELIVERABLES = (
    ("document", "README.md"),
    ("document", "docs/devpost-submission.md"),
    ("document", "docs/submission-runbook.md"),
    ("document", "docs/submission-story.md"),
    ("document", "docs/submission-summary-en.md"),
    ("document", "docs/demo-script.md"),
    ("video", "demo/assets/argus-demo-draft.mp4"),
    ("video", "demo/assets/argus-demo-fallback-draft.mp4"),
    ("demo_asset", "demo/assets/captions.srt"),
    ("demo_asset", "demo/assets/captions.vtt"),
    ("demo_asset", "demo/assets/shot-list.json"),
    ("demo_asset", "demo/assets/assembly.json"),
    ("demo_asset", "demo/assets/assembly.txt"),
    ("demo_asset", "demo/assets/narration.json"),
    ("demo_asset", "demo/assets/narration.txt"),
    ("demo_asset", "demo/assets/fallback.json"),
    ("demo_asset", "demo/assets/fallback.txt"),
    ("demo_asset", "demo/assets/captures/capture-manifest.json"),
)


def _file_entry(root: Path, category: str, rel: str) -> dict:
    path = root / rel
    if not path.is_file():
        return {
            "category": category,
            "path": rel,
            "exists": False,
            "size_bytes": None,
            "sha256": None,
        }
    data = path.read_bytes()
    return {
        "category": category,
        "path": rel,
        "exists": True,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def build_inventory(root: Path | None = None) -> dict:
    """제출물 인벤토리를 만든다. 파일은 읽기만 하며 아무것도 제출하지 않는다."""
    root = Path(root) if root is not None else ROOT
    deliverables = [_file_entry(root, category, rel) for category, rel in DELIVERABLES]
    missing = [entry["path"] for entry in deliverables if not entry["exists"]]
    return {
        "title": "Argus 제출물 인벤토리",
        "repo_url": REPO_URL,
        "deadline": DEADLINE,
        "deliverables": deliverables,
        "missing": missing,
        "total_files": len(deliverables),
        "present_files": len(deliverables) - len(missing),
        "total_bytes": sum(
            entry["size_bytes"] for entry in deliverables if entry["exists"]
        ),
        "blockers": [dict(b) for b in BLOCKERS],
        # 블로커가 남아 있는 한 인벤토리 완결과 무관하게 항상 False다.
        "submission_ready": False,
        "honesty": list(HONESTY),
    }


def validate_inventory(inventory, root: Path | None = None) -> list[str]:
    """인벤토리를 실제 파일과 다시 대조해 문제 목록을 돌려준다."""
    if not isinstance(inventory, dict):
        return [f"inventory is not a dict: {inventory!r}"]
    root = Path(root) if root is not None else ROOT
    problems: list[str] = []

    if inventory.get("repo_url") != REPO_URL:
        problems.append(f"repo_url={inventory.get('repo_url')!r} != {REPO_URL!r}")
    if inventory.get("deadline") != DEADLINE:
        problems.append(f"deadline={inventory.get('deadline')!r} != {DEADLINE!r}")
    if inventory.get("submission_ready") is not False:
        problems.append(
            f"submission_ready={inventory.get('submission_ready')!r} is not False"
        )
    blocker_ids = [
        b.get("id") if isinstance(b, dict) else None
        for b in (inventory.get("blockers") or [])
    ]
    if blocker_ids != [b["id"] for b in BLOCKERS]:
        problems.append(f"blocker ids={blocker_ids!r} != {[b['id'] for b in BLOCKERS]!r}")

    deliverables = inventory.get("deliverables")
    if not isinstance(deliverables, list):
        problems.append(f"deliverables is not a list: {deliverables!r}")
        deliverables = []
    expected_shape = [
        {"category": category, "path": rel} for category, rel in DELIVERABLES
    ]
    actual_shape = [
        {
            "category": entry.get("category") if isinstance(entry, dict) else None,
            "path": entry.get("path") if isinstance(entry, dict) else None,
        }
        for entry in deliverables
    ]
    if actual_shape != expected_shape:
        problems.append("deliverables category/path/order mismatch with DELIVERABLES")

    fresh = build_inventory(root)
    fresh_by_path = {entry["path"]: entry for entry in fresh["deliverables"]}
    for entry in deliverables:
        if not isinstance(entry, dict):
            problems.append(f"deliverable entry is not a dict: {entry!r}")
            continue
        rel = entry.get("path")
        expected = fresh_by_path.get(rel)
        if expected is None:
            continue
        for key in ("exists", "size_bytes", "sha256"):
            if entry.get(key) != expected[key]:
                problems.append(
                    f"{rel}: {key}={entry.get(key)!r} != actual {expected[key]!r}"
                )
    if inventory.get("missing") != fresh["missing"]:
        problems.append(
            f"missing={inventory.get('missing')!r} != actual {fresh['missing']!r}"
        )
    for key in ("total_files", "present_files", "total_bytes"):
        if inventory.get(key) != fresh[key]:
            problems.append(f"{key}={inventory.get(key)!r} != actual {fresh[key]!r}")

    honesty = inventory.get("honesty") or []
    joined = " ".join(str(line) for line in honesty)
    for phrase in ("실제로 제출하지 않는다", "Pi 실촬영 검증 전", "데모 기준"):
        if phrase not in joined:
            problems.append(f"honesty missing {phrase!r}")
    return problems


def build_inventory_text(inventory: dict | None = None, root: Path | None = None) -> str:
    if inventory is None:
        inventory = build_inventory(root)
    lines = [
        str(inventory["title"]),
        f"저장소: {inventory['repo_url']}",
        f"제출 마감: {inventory['deadline']}",
        (
            f"제출물 {inventory['present_files']}/{inventory['total_files']}개 존재 · "
            f"합계 {inventory['total_bytes']}바이트"
        ),
    ]
    for entry in inventory["deliverables"]:
        sha = (entry["sha256"] or "-")[:12]
        size = entry["size_bytes"] if entry["size_bytes"] is not None else "-"
        lines.append(
            f"- [{entry['category']}] {entry['path']} · exists={entry['exists']} · "
            f"size={size} · sha256={sha}"
        )
    if inventory["missing"]:
        lines.append(f"누락: {', '.join(inventory['missing'])}")
    lines.append(f"BLOCKERS: {len(inventory['blockers'])}")
    for blocker in inventory["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    lines.append("SUBMISSION_READY: false")
    for line in inventory["honesty"]:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def write_inventory(out_dir, root: Path | None = None) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    inventory = build_inventory(root)
    json_path = out / "submission-inventory.json"
    json_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    text_path = out / "submission-inventory.txt"
    text_path.write_text(build_inventory_text(inventory), encoding="utf-8")
    return [json_path, text_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 제출물 인벤토리")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args(argv)

    inventory = build_inventory()
    problems = validate_inventory(inventory)
    if args.out_dir:
        write_inventory(args.out_dir)
    if args.json:
        sys.stdout.write(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(build_inventory_text(inventory))
    if problems:
        for problem in problems:
            sys.stderr.write(f"PROBLEM: {problem}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
