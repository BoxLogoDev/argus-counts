import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from qa.sam_smoke import build_report, format_text_report, main, run_smoke
from terminal.models import CountResult
from terminal.sam_adapter import SamCountingError

SENTINEL = "SECRET-SENTINEL-12345"
READY_ENV = {"SAM_API_BASE_URL": f"https://{SENTINEL}.example.invalid", "SAM_API_KEY": SENTINEL}


class FakeCounter:
    source = "sam"

    def __init__(self, qty=5):
        self.qty = qty
        self.calls = []

    def count(self, bin_id, image_ref=None):
        self.calls.append((bin_id, image_ref))
        return CountResult(bin_id=bin_id, counted_qty=self.qty, source="sam")


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


class SamSmokeTests(unittest.TestCase):
    def test_blocked_when_not_ready_and_counter_not_called(self):
        counter = FakeCounter()
        report = run_smoke(env={}, credit_confirmed=False, counter=counter)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["attempted"])
        self.assertEqual(counter.calls, [])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["sam_credit_not_confirmed", "sam_base_url_missing", "sam_api_key_missing"],
        )

    def test_passed_with_fake_counter_when_ready(self):
        counter = FakeCounter(qty=5)
        report = run_smoke(env=READY_ENV, credit_confirmed=True, counter=counter)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["attempted"])
        self.assertEqual(report["source"], "sam")
        self.assertEqual(report["counted_qty"], 5)
        self.assertEqual(report["book_qty"], 8)
        self.assertEqual(report["diff"], -3)
        self.assertEqual(counter.calls, [("A-01-02", None)])

    def test_mock_source_is_not_counted_as_live_success(self):
        report = run_smoke(env=READY_ENV, credit_confirmed=True, counter=MockSourceCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unexpected_source")
        self.assertTrue(report["attempted"])

    def test_sam_error_fails_without_mock_fallback(self):
        report = run_smoke(env=READY_ENV, credit_confirmed=True, counter=RaisingCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "SamCountingError")
        self.assertIsNone(report["counted_qty"])
        self.assertIsNone(report["source"])

    def test_generic_error_does_not_leak_env_or_exception_values(self):
        report = run_smoke(env=READY_ENV, credit_confirmed=True, counter=LeakyCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "RuntimeError")
        blob = json.dumps(report, ensure_ascii=False) + format_text_report(report)
        self.assertNotIn(SENTINEL, blob)

    def test_unknown_bin_fails_without_call(self):
        counter = FakeCounter()
        report = run_smoke(env=READY_ENV, credit_confirmed=True, bin_id="Z-99-99", counter=counter)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unknown_bin")
        self.assertFalse(report["attempted"])
        self.assertEqual(counter.calls, [])

    def test_env_values_never_leak_blocked_or_passed(self):
        passed = build_report(env=READY_ENV, credit_confirmed=True, counter=FakeCounter())
        blocked = build_report(env=READY_ENV, credit_confirmed=False, counter=FakeCounter())
        for report in (passed, blocked):
            blob = json.dumps(report, ensure_ascii=False) + format_text_report(report)
            self.assertNotIn(SENTINEL, blob)

    def test_text_report_and_honesty(self):
        report = run_smoke(env={}, credit_confirmed=False)
        text = format_text_report(report)
        self.assertIn("STATUS: blocked", text)
        self.assertIn("SMOKE_PASSED: false", text)
        self.assertIn("BLOCKERS: 3", text)
        joined = " ".join(report["honesty"])
        self.assertIn("호출하지 않는다", joined)
        self.assertIn("대체하지 않는다", joined)

    def test_main_blocked_exit_one_and_json(self):
        with patch.dict(os.environ, {}, clear=True):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--json"])
        self.assertEqual(code, 1)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["status"], "blocked")
        self.assertFalse(parsed["attempted"])


if __name__ == "__main__":
    unittest.main()
