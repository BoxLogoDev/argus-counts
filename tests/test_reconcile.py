"""대조 엔진 단위 테스트.

기준 케이스는 데모 빈 6개 시나리오: 일치 4 · 부족 1 · 초과 1.
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)

from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids, demo_ledger
from terminal.models import CountResult, CountSession, LedgerEntry, SessionState
from terminal.reconcile import Verdict, compare_bin, reconcile
from terminal.sam_adapter import LiveSamCounter, MockSamCounter, build_counter


def run_demo_report():
    ledger = demo_ledger()
    results = {
        bin_id: CountResult(bin_id=bin_id, counted_qty=qty, source="mock")
        for bin_id, qty in DEMO_COUNTED_QTY.items()
    }
    return reconcile("S-DEMO", ledger, results)


class CompareBinTest(unittest.TestCase):
    def test_match(self):
        entry = LedgerEntry("X-01", "ITM", "품목", 10)
        result = CountResult("X-01", 10, "mock")
        comp = compare_bin(entry, result)
        self.assertIs(comp.verdict, Verdict.MATCH)
        self.assertEqual(comp.diff, 0)

    def test_short(self):
        entry = LedgerEntry("X-01", "ITM", "품목", 10)
        result = CountResult("X-01", 7, "mock")
        comp = compare_bin(entry, result)
        self.assertIs(comp.verdict, Verdict.SHORT)
        self.assertEqual(comp.diff, -3)

    def test_over(self):
        entry = LedgerEntry("X-01", "ITM", "품목", 10)
        result = CountResult("X-01", 13, "mock")
        comp = compare_bin(entry, result)
        self.assertIs(comp.verdict, Verdict.OVER)
        self.assertEqual(comp.diff, 3)

    def test_bin_mismatch_rejected(self):
        entry = LedgerEntry("X-01", "ITM", "품목", 10)
        result = CountResult("X-02", 10, "mock")
        with self.assertRaises(ValueError):
            compare_bin(entry, result)


class DemoScenarioTest(unittest.TestCase):
    """빈 6개 기준선: 일치 4 · 부족 1 · 초과 1."""

    def setUp(self):
        self.report = run_demo_report()

    def test_six_bins_counted(self):
        self.assertEqual(self.report.counted_bins, 6)

    def test_match_and_mismatch_counts(self):
        self.assertEqual(self.report.matched, 4)
        self.assertEqual(self.report.mismatched, 2)

    def test_match_rate(self):
        self.assertAlmostEqual(self.report.match_rate, 4 / 6)

    def test_shortage_bin(self):
        self.assertEqual(self.report.shortage_bins(), ["A-01-02"])
        comp = next(c for c in self.report.comparisons if c.bin_id == "A-01-02")
        self.assertEqual((comp.book_qty, comp.counted_qty, comp.diff), (8, 5, -3))

    def test_overage_bin(self):
        self.assertEqual(self.report.overage_bins(), ["B-01-02"])
        comp = next(c for c in self.report.comparisons if c.bin_id == "B-01-02")
        self.assertEqual((comp.book_qty, comp.counted_qty, comp.diff), (6, 9, 3))

    def test_diff_totals(self):
        self.assertEqual(self.report.abs_diff_total, 6)
        self.assertEqual(self.report.net_diff, 0)

    def test_differences_only_lists_mismatches(self):
        bins = [c.bin_id for c in self.report.differences]
        self.assertEqual(bins, ["A-01-02", "B-01-02"])

    def test_unknown_bin_rejected(self):
        ledger = demo_ledger()
        results = {"Z-99-99": CountResult("Z-99-99", 1, "mock")}
        with self.assertRaises(KeyError):
            reconcile("S-BAD", ledger, results)


class SessionFlowTest(unittest.TestCase):
    def test_full_session_with_mock_counter(self):
        session = CountSession(session_id="S-1", bin_ids=demo_bin_ids())
        counter = MockSamCounter(DEMO_COUNTED_QTY)
        session.begin()
        for bin_id in session.bin_ids:
            session.record(counter.count(bin_id))
        session.mark_reconciled()
        self.assertIs(session.state, SessionState.RECONCILED)
        report = reconcile(session.session_id, demo_ledger(), session.results)
        self.assertEqual(report.matched, 4)
        self.assertTrue(
            all(r.source == "mock" for r in session.results.values())
        )

    def test_reconcile_blocked_until_all_bins_counted(self):
        session = CountSession(session_id="S-2", bin_ids=demo_bin_ids())
        session.begin()
        session.record(CountResult("A-01-01", 12, "mock"))
        with self.assertRaises(RuntimeError):
            session.mark_reconciled()


class AdapterSelectionTest(unittest.TestCase):
    def test_mock_is_default_without_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            counter = build_counter(DEMO_COUNTED_QTY)
        self.assertIsInstance(counter, MockSamCounter)
        self.assertEqual(counter.count("A-01-02").counted_qty, 5)

    def test_live_selected_only_with_both_env_vars(self):
        env = {"SAM_API_BASE_URL": "https://example.invalid", "SAM_API_KEY": "k"}
        with mock.patch.dict(os.environ, env, clear=True):
            counter = build_counter(DEMO_COUNTED_QTY)
        self.assertIsInstance(counter, LiveSamCounter)
        with self.assertRaises(NotImplementedError):
            counter.count("A-01-01")

    def test_partial_env_falls_back_to_mock(self):
        with mock.patch.dict(os.environ, {"SAM_API_KEY": "k"}, clear=True):
            counter = build_counter(DEMO_COUNTED_QTY)
        self.assertIsInstance(counter, MockSamCounter)


if __name__ == "__main__":
    unittest.main()
