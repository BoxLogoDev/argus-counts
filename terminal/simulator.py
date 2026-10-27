"""단말 시뮬레이터 CLI.

흐름은 실제 단말과 같다. 데모 장부로 세션을 만들고, 어댑터로 각 빈을
계수하고, 대조한 결과를 JSON으로 낸다.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .demo_data import DEMO_COUNTED_QTY, demo_bin_ids, demo_ledger
from .models import CountSession
from .reconcile import reconcile
from .sam_adapter import build_counter


def _default_session_id() -> str:
    return datetime.now(timezone.utc).strftime("SIM-%Y%m%d-%H%M%S")


def run_simulation(
    session_id: str | None = None,
    counted_qty: dict[str, int] | None = None,
) -> dict:
    session_id = session_id or _default_session_id()
    ledger = demo_ledger()
    session = CountSession(session_id=session_id, bin_ids=demo_bin_ids())
    counter = build_counter(
        counted_qty if counted_qty is not None else DEMO_COUNTED_QTY
    )

    session.begin()
    for bin_id in session.bin_ids:
        session.record(counter.count(bin_id))
    session.mark_reconciled()

    report = reconcile(session.session_id, ledger, session.results)

    return {
        "session_id": report.session_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": counter.source,
        "bins": [
            {
                "bin_id": comp.bin_id,
                "item_code": comp.item_code,
                "book_qty": comp.book_qty,
                "counted_qty": comp.counted_qty,
                "diff": comp.diff,
                "verdict": comp.verdict.value,
            }
            for comp in report.comparisons
        ],
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
    parser = argparse.ArgumentParser(description="Argus terminal simulator")
    parser.add_argument("--out", default=None, help="JSON 리포트를 저장할 경로")
    parser.add_argument("--session-id", default=None, help="세션 id")
    args = parser.parse_args(argv)

    text = json.dumps(
        run_simulation(session_id=args.session_id), ensure_ascii=False, indent=2
    )
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
