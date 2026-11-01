"""제출 패키지 영속 아카이브 하네스.

11/03 제출 패키지 마감을 앞두고, 최종 묶음(qa.final_package)이 임시
staging에서만 확인하던 패키지 내보내기를 영속 디렉터리에 실제로
남기는 하네스다. 내보낸 아카이브는 매니페스트(package-manifest.json)를
기준으로 제출일에 재내보내기 없이 다시 대조할 수 있으며, 이 하네스는
아카이브 수치(복사 수·누락·합계 바이트·재검증 결과·선택 영상)를
최종 묶음 보고와 교차 대조해 한곳에 기록한다.

이 하네스는 실제로 제출하지 않는다. 아카이브 완결은 제출 준비
완료를 뜻하지 않으며, 제출 블로커(pi_real_capture_pending)가 남아
있는 동안 submission_ready는 항상 False다. Pi 실촬영 검증 전이며,
수치는 데모 기준이다.

실행: 프로젝트 루트에서
`python3 -m qa.package_archive --out-dir <경로> [--json]`으로 새
아카이브를 만들고, 이미 만든 아카이브는
`python3 -m qa.package_archive --verify-dir <경로> [--json]`으로
파일을 쓰지 않고 재검증만 한다. --out-dir와 --verify-dir 중 정확히
하나만 지정해야 한다.
종료코드는 아카이브가 완결·검증되면 0, 불완전하거나 최종 묶음과
어긋나면 1, 입력이 유효하지 않거나 보고가 무효면 2다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HONESTY = [
    "아카이브는 staging 디렉터리로 파일을 복사할 뿐 실제로 제출하지 않는다",
    "아카이브 완결은 제출 준비 완료를 뜻하지 않는다",
    "Pi 실촬영 검증 전",
    "수치는 데모 기준",
]

_REQUIRED_KEYS = (
    "out_dir",
    "mode",
    "copied",
    "total",
    "missing",
    "total_bytes",
    "verify_verified",
    "verify_copied",
    "verify_total_bytes",
    "final_status",
    "final_inventory_present",
    "final_inventory_total",
    "final_export_copied",
    "final_export_total",
    "final_export_total_bytes",
    "selected_video",
    "selected_size",
    "selected_copied",
    "selected_size_in_archive",
    "selected_sha256",
    "archive_verified",
    "status",
    "blockers",
    "submission_ready",
    "problems",
    "honesty",
)


def _blocker_ids() -> list[str]:
    from qa.pre_submission import BLOCKERS

    return [b["id"] for b in BLOCKERS]


def evaluate_archive(
    *,
    out_dir,
    mode,
    copied,
    total,
    missing,
    total_bytes,
    verify_verified,
    verify_copied,
    verify_total_bytes,
    final_status,
    final_inventory_present,
    final_inventory_total,
    final_export_copied,
    final_export_total,
    final_export_total_bytes,
    selected_video,
    selected_size,
    selected_copied,
    selected_size_in_archive,
    selected_sha256,
) -> dict:
    """아카이브 실측과 최종 묶음 수치를 교차 대조해 아카이브 보고를 만든다."""
    missing_list = list(missing or [])
    problems: list[str] = []
    if missing_list:
        problems.append(f"missing files: {missing_list}")
    if int(copied) != int(total):
        problems.append(f"copied={copied} != total={total}")
    if verify_verified is not True:
        problems.append("export re-verification did not pass")
    if verify_copied is not None and int(verify_copied) != int(copied):
        problems.append(f"verify_copied={verify_copied} != copied={copied}")
    if verify_total_bytes is not None and int(verify_total_bytes) != int(total_bytes):
        problems.append(
            f"verify_total_bytes={verify_total_bytes} != total_bytes={total_bytes}")
    if int(final_inventory_present) != int(copied):
        problems.append(
            f"final inventory_present={final_inventory_present} != copied={copied}")
    if int(final_inventory_total) != int(total):
        problems.append(
            f"final inventory_total={final_inventory_total} != total={total}")
    if final_export_copied is not None and int(final_export_copied) != int(copied):
        problems.append(
            f"final export_copied={final_export_copied} != copied={copied}")
    if final_export_total is not None and int(final_export_total) != int(total):
        problems.append(
            f"final export_total={final_export_total} != total={total}")
    if final_export_total_bytes is not None and int(final_export_total_bytes) != int(total_bytes):
        problems.append(
            f"final export_total_bytes={final_export_total_bytes} != total_bytes={total_bytes}")
    if selected_copied is not True:
        problems.append(f"selected video not copied into archive: {selected_video}")
    elif selected_size_in_archive != selected_size:
        problems.append(
            f"selected_size_in_archive={selected_size_in_archive} != "
            f"selected_size={selected_size}")
    archive_verified = not problems
    if archive_verified:
        status = "archived"
    elif missing_list or int(copied) != int(total):
        status = "incomplete"
    else:
        status = "mismatch"
    return {
        "out_dir": str(out_dir),
        "mode": str(mode),
        "copied": int(copied),
        "total": int(total),
        "missing": missing_list,
        "total_bytes": int(total_bytes),
        "verify_verified": bool(verify_verified),
        "verify_copied": (
            int(verify_copied) if verify_copied is not None else None),
        "verify_total_bytes": (
            int(verify_total_bytes) if verify_total_bytes is not None else None),
        "final_status": str(final_status),
        "final_inventory_present": int(final_inventory_present),
        "final_inventory_total": int(final_inventory_total),
        "final_export_copied": (
            int(final_export_copied) if final_export_copied is not None else None),
        "final_export_total": (
            int(final_export_total) if final_export_total is not None else None),
        "final_export_total_bytes": (
            int(final_export_total_bytes)
            if final_export_total_bytes is not None else None),
        "selected_video": (
            str(selected_video) if selected_video is not None else None),
        "selected_size": (
            int(selected_size) if selected_size is not None else None),
        "selected_copied": bool(selected_copied),
        "selected_size_in_archive": (
            int(selected_size_in_archive)
            if selected_size_in_archive is not None else None),
        "selected_sha256": (
            str(selected_sha256) if selected_sha256 is not None else None),
        "archive_verified": archive_verified,
        "status": status,
        "blockers": _blocker_ids(),
        "submission_ready": False,
        "problems": problems,
        "honesty": list(HONESTY),
    }


def _evaluate_from_export(out_dir, mode, export, verified_export,
                          verify_problems, root) -> dict:
    from qa.final_package import build_final_package

    final = build_final_package(root)
    if export is None:
        return evaluate_archive(
            out_dir=out_dir, mode=mode, copied=0, total=0, missing=[],
            total_bytes=0, verify_verified=False, verify_copied=None,
            verify_total_bytes=None,
            final_status=final["status"],
            final_inventory_present=final["inventory_present"],
            final_inventory_total=final["inventory_total"],
            final_export_copied=final["export_copied"],
            final_export_total=final["export_total"],
            final_export_total_bytes=final["export_total_bytes"],
            selected_video=final["selected_video"],
            selected_size=final["selected_size"],
            selected_copied=False, selected_size_in_archive=None,
            selected_sha256=None)
    selected_entry = None
    for entry in export.get("files", []):
        if isinstance(entry, dict) and entry.get("path") == final["selected_video"]:
            selected_entry = entry
            break
    verified = (
        isinstance(verified_export, dict) and not verify_problems)
    return evaluate_archive(
        out_dir=out_dir, mode=mode,
        copied=export["copied_files"], total=export["total_files"],
        missing=export["missing"], total_bytes=export["total_bytes"],
        verify_verified=verified,
        verify_copied=(
            verified_export.get("copied_files")
            if isinstance(verified_export, dict) else None),
        verify_total_bytes=(
            verified_export.get("total_bytes")
            if isinstance(verified_export, dict) else None),
        final_status=final["status"],
        final_inventory_present=final["inventory_present"],
        final_inventory_total=final["inventory_total"],
        final_export_copied=final["export_copied"],
        final_export_total=final["export_total"],
        final_export_total_bytes=final["export_total_bytes"],
        selected_video=final["selected_video"],
        selected_size=final["selected_size"],
        selected_copied=(
            bool(selected_entry.get("copied")) if selected_entry else False),
        selected_size_in_archive=(
            selected_entry.get("size_bytes") if selected_entry else None),
        selected_sha256=(
            selected_entry.get("sha256") if selected_entry else None))


def build_archive(out_dir, root: Path | None = None) -> dict:
    """out_dir에 실제로 복사해 아카이브를 만들고 최종 묶음과 대조한다."""
    from qa.package_export import build_export, verify_export_dir

    export = build_export(out_dir, source_root=root)
    verified_export, verify_problems = verify_export_dir(
        out_dir, source_root=root)
    return _evaluate_from_export(
        out_dir, "export", export, verified_export, verify_problems, root)


def build_archive_verify(out_dir, root: Path | None = None) -> dict:
    """기존 아카이브를 매니페스트만으로 재검증한다. 어떤 파일도 쓰지 않는다."""
    from qa.package_export import verify_export_dir

    export, verify_problems = verify_export_dir(out_dir, source_root=root)
    return _evaluate_from_export(
        out_dir, "verify", export, export, verify_problems, root)


def validate_archive(report: dict) -> list[str]:
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
    if report["blockers"] != _blocker_ids():
        problems.append(f"blockers={report['blockers']!r} != {_blocker_ids()!r}")
    try:
        expected = evaluate_archive(
            out_dir=report["out_dir"], mode=report["mode"],
            copied=report["copied"], total=report["total"],
            missing=report["missing"], total_bytes=report["total_bytes"],
            verify_verified=report["verify_verified"],
            verify_copied=report["verify_copied"],
            verify_total_bytes=report["verify_total_bytes"],
            final_status=report["final_status"],
            final_inventory_present=report["final_inventory_present"],
            final_inventory_total=report["final_inventory_total"],
            final_export_copied=report["final_export_copied"],
            final_export_total=report["final_export_total"],
            final_export_total_bytes=report["final_export_total_bytes"],
            selected_video=report["selected_video"],
            selected_size=report["selected_size"],
            selected_copied=report["selected_copied"],
            selected_size_in_archive=report["selected_size_in_archive"],
            selected_sha256=report["selected_sha256"])
    except (TypeError, ValueError) as exc:
        problems.append(f"cannot recompute archive: {exc}")
        return problems
    for key in ("status", "archive_verified", "problems"):
        if report[key] != expected[key]:
            problems.append(f"{key}={report[key]!r} != {expected[key]!r}")
    joined = " ".join(str(x) for x in (report.get("honesty") or []))
    for marker in ("실제로 제출하지 않는다", "제출 준비 완료를 뜻하지 않는다",
                   "Pi 실촬영 검증 전"):
        if marker not in joined:
            problems.append(f"honesty missing {marker!r}")
    return problems


def format_text_report(report: dict) -> str:
    lines = [
        "Argus 제출 패키지 아카이브",
        f"OUT_DIR: {report['out_dir']}",
        f"MODE: {report['mode']}",
        f"STATUS: {report['status']}",
        f"COPIED: {report['copied']}",
        f"TOTAL: {report['total']}",
        f"MISSING: {report['missing']}",
        f"TOTAL_BYTES: {report['total_bytes']}",
        f"VERIFY_VERIFIED: {str(report['verify_verified']).lower()}",
        f"FINAL_STATUS: {report['final_status']}",
        f"SELECTED_VIDEO: {report['selected_video']}",
        f"SELECTED_SIZE: {report['selected_size']}",
        f"ARCHIVE_VERIFIED: {str(report['archive_verified']).lower()}",
        f"BLOCKERS: {report['blockers']}",
        f"PROBLEMS: {report['problems']}",
        "SUBMISSION_READY: false",
    ]
    for line in report["honesty"]:
        lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    out_dir = None
    if "--out-dir" in argv:
        idx = argv.index("--out-dir")
        if idx + 1 < len(argv):
            out_dir = argv[idx + 1]
    verify_dir = None
    if "--verify-dir" in argv:
        idx = argv.index("--verify-dir")
        if idx + 1 < len(argv):
            verify_dir = argv[idx + 1]
    if bool(out_dir) == bool(verify_dir):
        sys.stdout.write(
            "--out-dir와 --verify-dir 중 정확히 하나만 지정해야 합니다\n")
        return 2
    if out_dir:
        report = build_archive(out_dir)
    else:
        report = build_archive_verify(verify_dir)
    problems = validate_archive(report)
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    if problems:
        for problem in problems:
            sys.stdout.write(f"PROBLEM: {problem}\n")
        return 2
    return 0 if report["status"] == "archived" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
