"""대조 엔진: 장부 수량과 계수 결과를 비교해 차이 리포트를 만든다.

판정은 세 가지뿐이다 — 일치(match), 부족(short), 초과(over).
리포트는 차이 항목만 따로 모으고, 요약 지표(실사 완료 수, 일치율,
절대 차이 합계, 순차이)를 함께 낸다.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import CountResult, LedgerEntry


class Verdict(Enum):
    MATCH = "match"
    SHORT = "short"
    OVER = "over"


@dataclass(frozen=True)
class BinComparison:
    bin_id: str
    item_code: str
    book_qty: int
    counted_qty: int
    verdict: Verdict

    @property
    def diff(self) -> int:
        """실측 − 장부. 음수면 부족, 양수면 초과."""
        return self.counted_qty - self.book_qty


@dataclass(frozen=True)
class DifferenceReport:
    session_id: str
    comparisons: tuple[BinComparison, ...]

    @property
    def counted_bins(self) -> int:
        return len(self.comparisons)

    @property
    def matched(self) -> int:
        return sum(1 for c in self.comparisons if c.verdict is Verdict.MATCH)

    @property
    def mismatched(self) -> int:
        return self.counted_bins - self.matched

    @property
    def match_rate(self) -> float:
        if self.counted_bins == 0:
            return 0.0
        return self.matched / self.counted_bins

    @property
    def abs_diff_total(self) -> int:
        return sum(abs(c.diff) for c in self.comparisons)

    @property
    def net_diff(self) -> int:
        return sum(c.diff for c in self.comparisons)

    @property
    def differences(self) -> tuple[BinComparison, ...]:
        """차이가 있는 항목만 (부족·초과)."""
        return tuple(c for c in self.comparisons if c.verdict is not Verdict.MATCH)

    def shortage_bins(self) -> list[str]:
        return [c.bin_id for c in self.comparisons if c.verdict is Verdict.SHORT]

    def overage_bins(self) -> list[str]:
        return [c.bin_id for c in self.comparisons if c.verdict is Verdict.OVER]


def compare_bin(entry: LedgerEntry, result: CountResult) -> BinComparison:
    if entry.bin_id != result.bin_id:
        raise ValueError(
            f"bin mismatch: ledger {entry.bin_id} vs count {result.bin_id}"
        )
    diff = result.counted_qty - entry.book_qty
    if diff == 0:
        verdict = Verdict.MATCH
    elif diff < 0:
        verdict = Verdict.SHORT
    else:
        verdict = Verdict.OVER
    return BinComparison(
        bin_id=entry.bin_id,
        item_code=entry.item_code,
        book_qty=entry.book_qty,
        counted_qty=result.counted_qty,
        verdict=verdict,
    )


def reconcile(
    session_id: str,
    ledger: dict[str, LedgerEntry],
    results: dict[str, CountResult],
) -> DifferenceReport:
    """세션의 계수 결과 전체를 장부와 대조한다.

    장부에 없는 빈의 결과가 들어오면 오류로 알린다. 장부에만 있고
    계수되지 않은 빈은 리포트에 넣지 않는다(미실사는 세션 상태가 막는다).
    """
    comparisons: list[BinComparison] = []
    for bin_id in sorted(results):
        if bin_id not in ledger:
            raise KeyError(f"counted bin {bin_id} has no ledger entry")
        comparisons.append(compare_bin(ledger[bin_id], results[bin_id]))
    return DifferenceReport(session_id=session_id, comparisons=tuple(comparisons))
