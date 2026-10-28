"""파일 기반 사진 입력 파이프라인.

Pi 카메라가 찍은 사진 파일을 빈(bin)별로 받아 기존 실사 흐름
(계수 → 대조 → 리포트)에 태우는 입력 경계다. Pi 실촬영이 아니며,
이미 존재하는 이미지 파일만 입력으로 쓴다. 계수는 직접 수행하지 않고
기존 terminal/sam_adapter.py의 build_counter 경유만 사용한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .demo_data import DEMO_COUNTED_QTY, demo_ledger
from .models import CountSession
from .reconcile import reconcile
from .sam_adapter import build_counter

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})


@dataclass(frozen=True)
class CaptureRecord:
    bin_id: str
    image_ref: str
    size_bytes: int
    sha256: str
    suffix: str


def load_capture(bin_id: str, photo_path: str | Path) -> CaptureRecord:
    path = Path(photo_path)
    if not path.is_file():
        raise FileNotFoundError(f"capture file not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"unsupported image extension: {suffix or '(none)'}")
    data = path.read_bytes()
    if len(data) == 0:
        raise ValueError(f"capture file is empty: {path}")
    return CaptureRecord(
        bin_id=bin_id,
        image_ref=path.name,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        suffix=suffix,
    )


def run_photo_intake(
    captures: dict[str, str | Path],
    session_id: str | None = None,
    counted_qty: dict[str, int] | None = None,
) -> dict:
    if not captures:
        raise ValueError("captures must not be empty")
    if session_id is None:
        session_id = datetime.now(timezone.utc).strftime("PHOTO-%Y%m%d-%H%M%S")
    sorted_bin_ids = sorted(captures)
    records = {
        bin_id: load_capture(bin_id, captures[bin_id])
        for bin_id in sorted_bin_ids
    }
    counter = build_counter(
        counted_qty if counted_qty is not None else DEMO_COUNTED_QTY
    )
    session = CountSession(session_id=session_id, bin_ids=sorted_bin_ids)
    session.begin()
    for bin_id in sorted_bin_ids:
        record = records[bin_id]
        session.record(counter.count(bin_id, image_ref=record.image_ref))
    session.mark_reconciled()
    report = reconcile(session_id, demo_ledger(), session.results)
    bins = []
    for comp in report.comparisons:
        record = records[comp.bin_id]
        bins.append(
            {
                "bin_id": comp.bin_id,
                "item_code": comp.item_code,
                "book_qty": comp.book_qty,
                "counted_qty": comp.counted_qty,
                "diff": comp.diff,
                "verdict": comp.verdict.value,
                "photo": {
                    "image_ref": record.image_ref,
                    "size_bytes": record.size_bytes,
                    "sha256": record.sha256,
                    "suffix": record.suffix,
                },
            }
        )
    return {
        "session_id": session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": counter.source,
        "capture_source": "file",
        "honesty": [
            "파일 기반 입력이며 Pi 실촬영이 아닙니다",
            "계수는 모의 어댑터 결과일 수 있으며 source 필드로 구분합니다",
        ],
        "bins": bins,
        "summary": {
            "counted_bins": report.counted_bins,
            "matched": report.matched,
            "mismatched": report.mismatched,
            "match_rate": report.match_rate,
            "abs_diff_total": report.abs_diff_total,
            "net_diff": report.net_diff,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="파일 기반 사진 입력 파이프라인")
    parser.add_argument(
        "--capture",
        action="append",
        required=True,
        help="빈과 사진 경로. 형식: BIN=PATH (예: A-01-02=/tmp/a.jpg)",
    )
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    captures: dict[str, str | Path] = {}
    for raw in args.capture:
        bin_id, sep, photo_path = raw.partition("=")
        if not sep or not bin_id or not photo_path:
            parser.error(f"invalid --capture format (expected BIN=PATH): {raw}")
        captures[bin_id] = photo_path
    result = run_photo_intake(captures, session_id=args.session_id)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out is not None:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
