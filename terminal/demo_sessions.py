"""데모 세션 3개의 스펙.

장부 수량은 demo_data.demo_ledger() 기준이다. 모든 수량은 모의 데이터다.
"""
from __future__ import annotations

from .demo_data import DEMO_COUNTED_QTY, demo_ledger

_SPECS = (
    {
        "session_id": "DEMO-20261027-A",
        "label": "10/27 오전 실사",
        "counted_qty": dict(DEMO_COUNTED_QTY),
    },
    {
        "session_id": "DEMO-20261027-B",
        "label": "10/27 오후 재실사",
        "counted_qty": {
            bin_id: entry.book_qty for bin_id, entry in demo_ledger().items()
        },
    },
    {
        "session_id": "DEMO-20261026-A",
        "label": "10/26 실사",
        "counted_qty": {
            "A-01-01": 10,
            "A-01-02": 8,
            "A-02-02": 15,
            "A-03-01": 20,
            "B-01-02": 6,
            "B-02-02": 7,
        },
    },
)


def demo_session_specs() -> list[dict]:
    return [
        {
            "session_id": spec["session_id"],
            "label": spec["label"],
            "counted_qty": dict(spec["counted_qty"]),
        }
        for spec in _SPECS
    ]


def counted_qty_for(session_id: str) -> dict | None:
    for spec in _SPECS:
        if spec["session_id"] == session_id:
            return dict(spec["counted_qty"])
    return None
