"""데모 시나리오 데이터.

빈 6개로 구성한다: 일치 4, 부족 1(A-01-02, 장부 8 → 실측 5),
초과 1(B-01-02, 장부 6 → 실측 9). 절대 차이 합계 6, 순차이 0.
"""
from __future__ import annotations

from .models import LedgerEntry

_ITEMS = {
    "A-01-01": ("WDG-100", "위젯 본체"),
    "A-01-02": ("WDG-200", "위젯 커버"),
    "A-02-02": ("BLT-050", "볼트 세트"),
    "A-03-01": ("CBL-310", "케이블 릴"),
    "B-01-02": ("SNS-020", "센서 모듈"),
    "B-02-02": ("PKG-900", "포장 박스"),
}

_BOOK_QTY = {
    "A-01-01": 12,
    "A-01-02": 8,
    "A-02-02": 15,
    "A-03-01": 18,
    "B-01-02": 6,
    "B-02-02": 10,
}

# 모의 계수기가 돌려줄 실측 수량 (데모 기준)
DEMO_COUNTED_QTY = {
    "A-01-01": 12,
    "A-01-02": 5,
    "A-02-02": 15,
    "A-03-01": 18,
    "B-01-02": 9,
    "B-02-02": 10,
}


def demo_ledger() -> dict[str, LedgerEntry]:
    return {
        bin_id: LedgerEntry(
            bin_id=bin_id,
            item_code=_ITEMS[bin_id][0],
            item_name=_ITEMS[bin_id][1],
            book_qty=qty,
        )
        for bin_id, qty in _BOOK_QTY.items()
    }


def demo_bin_ids() -> list[str]:
    return sorted(_BOOK_QTY)
