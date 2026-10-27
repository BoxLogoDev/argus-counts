"""QA 하네스 자체의 단위 테스트.

하네스가 항상 통과만 하는 껍데기가 되지 않도록, 기준값 테이블이
데모 데이터와 실제로 맞물려 있는지(드리프트 가드)와 실패 감지가
동작하는지까지 검증한다.
"""
from __future__ import annotations

import contextlib
import io
import unittest

from qa import harness
from qa.harness import (
    EXPECTED_BOOK_QTY,
    EXPECTED_COUNTED_QTY,
    EXPECTED_DIFFS,
    EXPECTED_OVERAGE_BINS,
    EXPECTED_SHORTAGE_BINS,
    EXPECTED_VERDICTS,
    QACheck,
    main,
    run_checks,
)
from terminal.demo_data import DEMO_COUNTED_QTY, demo_ledger


class TestQAHarness(unittest.TestCase):
    def test_all_checks_pass(self):
        checks = run_checks()
        failed = [c.name for c in checks if not c.passed]
        self.assertEqual(failed, [], f"failed checks: {failed}")

    def test_check_count_and_names(self):
        names = [c.name for c in run_checks()]
        self.assertGreaterEqual(len(names), 17)
        for required in (
            "bin_set_matches",
            "book_qty_per_bin",
            "counted_qty_per_bin",
            "verdict_per_bin",
            "diff_per_bin",
            "shortage_bins_exact",
            "overage_bins_exact",
            "summary_match_rate",
            "source_is_mock",
            "console_metrics_match",
            "console_differences_match",
        ):
            self.assertIn(required, names)

    def test_expected_book_matches_demo_ledger(self):
        ledger = demo_ledger()
        actual = {bin_id: e.book_qty for bin_id, e in ledger.items()}
        self.assertEqual(EXPECTED_BOOK_QTY, actual)

    def test_expected_counted_matches_demo_counts(self):
        self.assertEqual(EXPECTED_COUNTED_QTY, DEMO_COUNTED_QTY)

    def test_expected_verdict_distribution(self):
        verdicts = list(EXPECTED_VERDICTS.values())
        self.assertEqual(verdicts.count("match"), 4)
        self.assertEqual(verdicts.count("short"), 1)
        self.assertEqual(verdicts.count("over"), 1)
        self.assertEqual(
            [b for b, v in EXPECTED_VERDICTS.items() if v == "short"],
            EXPECTED_SHORTAGE_BINS,
        )
        self.assertEqual(
            [b for b, v in EXPECTED_VERDICTS.items() if v == "over"],
            EXPECTED_OVERAGE_BINS,
        )

    def test_expected_diffs_consistent_with_quantities(self):
        for bin_id in EXPECTED_BOOK_QTY:
            self.assertEqual(
                EXPECTED_DIFFS[bin_id],
                EXPECTED_COUNTED_QTY[bin_id] - EXPECTED_BOOK_QTY[bin_id],
            )
        self.assertEqual(sum(abs(d) for d in EXPECTED_DIFFS.values()), 6)
        self.assertEqual(sum(EXPECTED_DIFFS.values()), 0)

    def test_main_exit_zero_and_output_format(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main()
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("[PASS] bin_set_matches", out)
        total = len(run_checks())
        self.assertIn(f"QA: {total}/{total} passed", out)

    def test_qacheck_is_frozen(self):
        check = QACheck(name="x", passed=True, detail="d")
        with self.assertRaises(Exception):
            check.passed = False  # type: ignore[misc]

    def test_harness_detects_drift(self):
        """기준값이 깨지면 하네스가 실패로 잡아내는지 확인한다."""
        original = harness.EXPECTED_BOOK_QTY["A-01-01"]
        try:
            harness.EXPECTED_BOOK_QTY["A-01-01"] = original + 1
            checks = {c.name: c for c in run_checks()}
            self.assertFalse(checks["book_qty_per_bin"].passed)
            # 기준값 테이블끼리의 정합성도 함께 깨져야 한다
            self.assertNotEqual(
                harness.EXPECTED_DIFFS["A-01-01"],
                harness.EXPECTED_COUNTED_QTY["A-01-01"]
                - harness.EXPECTED_BOOK_QTY["A-01-01"],
            )
        finally:
            harness.EXPECTED_BOOK_QTY["A-01-01"] = original


if __name__ == "__main__":
    unittest.main()
