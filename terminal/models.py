"""데이터 모델: 장부 재고와 실사 세션.

- LedgerEntry: 창고 장부에 기록된 빈(bin)별 재고. 빈 식별자, 품목, 장부 수량.
- CountResult: 한 번의 촬영·계수 결과. 어느 빈을, 몇 개로 셌는지와 계수 출처.
- CountSession: 실사 한 회분의 진행 단위. 대상 빈 목록과 수집된 계수 결과를 모은다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SessionState(Enum):
    PLANNED = "planned"        # 대상 빈이 정해졌고 아직 시작 전
    COUNTING = "counting"      # 촬영·계수가 진행 중
    RECONCILED = "reconciled"  # 대조까지 끝난 상태


@dataclass(frozen=True)
class LedgerEntry:
    bin_id: str      # 예: "A-01-02" (구역-열-단)
    item_code: str   # 품목 코드
    item_name: str   # 품목 이름
    book_qty: int    # 장부 수량

    def __post_init__(self) -> None:
        if self.book_qty < 0:
            raise ValueError("book_qty must be >= 0")


@dataclass(frozen=True)
class CountResult:
    bin_id: str
    counted_qty: int
    source: str  # "mock" 또는 "sam" — 모의 결과와 실호출 결과를 구분하는 표기

    def __post_init__(self) -> None:
        if self.counted_qty < 0:
            raise ValueError("counted_qty must be >= 0")


@dataclass
class CountSession:
    session_id: str
    bin_ids: list[str]
    state: SessionState = SessionState.PLANNED
    results: dict[str, CountResult] = field(default_factory=dict)

    def begin(self) -> None:
        if self.state is not SessionState.PLANNED:
            raise RuntimeError("session already started")
        self.state = SessionState.COUNTING

    def record(self, result: CountResult) -> None:
        if self.state is not SessionState.COUNTING:
            raise RuntimeError("session is not in counting state")
        if result.bin_id not in self.bin_ids:
            raise ValueError(f"bin {result.bin_id} is not in this session")
        self.results[result.bin_id] = result

    def mark_reconciled(self) -> None:
        if self.state is not SessionState.COUNTING:
            raise RuntimeError("session is not in counting state")
        missing = [b for b in self.bin_ids if b not in self.results]
        if missing:
            raise RuntimeError(f"uncounted bins remain: {missing}")
        self.state = SessionState.RECONCILED
