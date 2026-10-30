import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from qa.sam_session import build_report, format_text_report, main, run_sam_session
from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids
from terminal.models import CountResult
from terminal.sam_adapter import SamCountingError

SENTINEL = "SECRET-SENTINEL-67890"
READY_ENV = {"SAM_API_BASE_URL": f"https://{SENTINEL}.example.invalid", "SAM_API_KEY": SENTINEL}


class FakeCounter:
    source = "sam"

    def __init__(self, counts=None):
        self.counts = dict(counts) if counts is not None else dict(DEMO_COUNTED_QTY)
        self.calls = []

    def count(self, bin_id, image_ref=None):
        self.calls.append((bin_id, image_ref))
        return CountResult(bin_id=bin_id, counted_qty=self.counts[bin_id], source="sam")


class MockSourceCounter:
    source = "mock"

    def count(self, bin_id, image_ref=None):
        return CountResult(bin_id=bin_id, counted_qty=5, source="mock")


class RaisingCounter:
    source = "sam"

    def count(self, bin_id, image_ref=None):
        raise SamCountingError("fake failure")


class LeakyCounter:
    source = "sam"

    def count(self, bin_id, image_ref=None):
        raise RuntimeError(f"boom {SENTINEL}")


class SamSessionTests(unittest.TestCase):
    def test_blocked_when_not_ready_and_counter_not_called(self):
        counter = FakeCounter()
        report = run_sam_session(env={}, credit_confirmed=False, counter=counter)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["attempted"])
        self.assertEqual(counter.calls, [])
        self.assertEqual(report["bins"], [])
        self.assertIsNone(report["summary"])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["sam_credit_not_confirmed", "sam_base_url_missing", "sam_api_key_missing"],
        )

    def test_passed_full_session_with_fake_counter(self):
        counter = FakeCounter()
        report = run_sam_session(
            env=READY_ENV, credit_confirmed=True, counter=counter, session_id="SAM-TEST"
        )
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["attempted"])
        self.assertEqual(report["source"], "sam")
        self.assertEqual(report["session_id"], "SAM-TEST")
        self.assertEqual([c[0] for c in counter.calls], demo_bin_ids())
        self.assertEqual(len(report["bins"]), 6)
        by_bin = {b["bin_id"]: b for b in report["bins"]}
        self.assertEqual(by_bin["A-01-02"]["book_qty"], 8)
        self.assertEqual(by_bin["A-01-02"]["counted_qty"], 5)
        self.assertEqual(by_bin["A-01-02"]["diff"], -3)
        self.assertEqual(by_bin["A-01-02"]["verdict"], "short")
        self.assertEqual(by_bin["B-01-02"]["diff"], 3)
        self.assertEqual(by_bin["B-01-02"]["verdict"], "over")
        summary = report["summary"]
        self.assertEqual(summary["counted_bins"], 6)
        self.assertEqual(summary["matched"], 4)
        self.assertEqual(summary["mismatched"], 2)
        self.assertEqual(summary["abs_diff_total"], 6)
        self.assertEqual(summary["net_diff"], 0)
        self.assertAlmostEqual(summary["match_rate"], 4 / 6)

    def test_image_refs_are_passed_per_bin(self):
        counter = FakeCounter()
        refs = {"A-01-02": "photo-a.jpg", "B-01-02": "photo-b.jpg"}
        report = run_sam_session(
            env=READY_ENV, credit_confirmed=True, counter=counter,
            image_refs=refs, image_ref="photo-default.jpg",
        )
        self.assertEqual(report["status"], "passed")
        seen = dict(counter.calls)
        self.assertEqual(seen["A-01-02"], "photo-a.jpg")
        self.assertEqual(seen["B-01-02"], "photo-b.jpg")
        self.assertEqual(seen["A-01-01"], "photo-default.jpg")

    def test_uniform_live_counts_reconcile_arithmetically(self):
        counter = FakeCounter(counts={bin_id: 14 for bin_id in demo_bin_ids()})
        report = run_sam_session(env=READY_ENV, credit_confirmed=True, counter=counter)
        self.assertEqual(report["status"], "passed")
        summary = report["summary"]
        self.assertEqual(summary["matched"], 0)
        self.assertEqual(summary["mismatched"], 6)
        self.assertEqual(summary["abs_diff_total"], 25)
        self.assertEqual(summary["net_diff"], 15)
        for comp in report["bins"]:
            self.assertEqual(comp["diff"], comp["counted_qty"] - comp["book_qty"])

    def test_mock_source_fails_whole_session(self):
        report = run_sam_session(env=READY_ENV, credit_confirmed=True, counter=MockSourceCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unexpected_source")
        self.assertTrue(report["attempted"])
        self.assertEqual(report["bins"], [])
        self.assertIsNone(report["summary"])

    def test_sam_error_fails_without_mock_fallback(self):
        report = run_sam_session(env=READY_ENV, credit_confirmed=True, counter=RaisingCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "SamCountingError")
        self.assertIsNone(report["source"])
        self.assertIsNone(report["summary"])

    def test_generic_error_does_not_leak_values(self):
        report = run_sam_session(env=READY_ENV, credit_confirmed=True, counter=LeakyCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "RuntimeError")
        blob = json.dumps(report, ensure_ascii=False) + format_text_report(report)
        self.assertNotIn(SENTINEL, blob)

    def test_env_values_never_leak_blocked_or_passed(self):
        passed = build_report(env=READY_ENV, credit_confirmed=True, counter=FakeCounter())
        blocked = build_report(env=READY_ENV, credit_confirmed=False, counter=FakeCounter())
        for report in (passed, blocked):
            blob = json.dumps(report, ensure_ascii=False) + format_text_report(report)
            self.assertNotIn(SENTINEL, blob)

    def test_text_report_and_honesty(self):
        report = run_sam_session(env={}, credit_confirmed=False)
        text = format_text_report(report)
        self.assertIn("STATUS: blocked", text)
        self.assertIn("SESSION_PASSED: false", text)
        self.assertIn("BLOCKERS: 3", text)
        joined = " ".join(report["honesty"])
        self.assertIn("호출하지 않는다", joined)
        self.assertIn("대체하지 않는다", joined)
        self.assertIn("Pi 실촬영이 아니며", joined)

    def test_main_blocked_exit_one_and_json(self):
        with patch.dict(os.environ, {}, clear=True):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--json"])
        self.assertEqual(code, 1)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["status"], "blocked")
        self.assertFalse(parsed["attempted"])
        self.assertEqual(parsed["bins"], [])


if __name__ == "__main__":
    unittest.main()
