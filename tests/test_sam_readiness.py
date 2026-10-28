import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from qa.sam_readiness import build_report, check_readiness, format_text_report, main

SENTINEL = "SECRET-SENTINEL-12345"
READY_ENV = {"SAM_API_BASE_URL": f"https://{SENTINEL}.example.invalid", "SAM_API_KEY": SENTINEL}


class SamReadinessTests(unittest.TestCase):
    def test_all_missing_blockers_in_order(self):
        report = check_readiness(env={}, credit_confirmed=False)
        self.assertFalse(report["base_url_present"])
        self.assertFalse(report["api_key_present"])
        self.assertFalse(report["ready_for_live_call"])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["sam_credit_not_confirmed", "sam_base_url_missing", "sam_api_key_missing"],
        )

    def test_all_ready(self):
        report = check_readiness(env=READY_ENV, credit_confirmed=True)
        self.assertTrue(report["base_url_present"])
        self.assertTrue(report["api_key_present"])
        self.assertTrue(report["would_select_live"])
        self.assertTrue(report["ready_for_live_call"])
        self.assertEqual(report["blockers"], [])

    def test_credit_is_only_blocker_when_env_ready(self):
        report = check_readiness(env=READY_ENV, credit_confirmed=False)
        self.assertTrue(report["would_select_live"])
        self.assertFalse(report["ready_for_live_call"])
        self.assertEqual([b["id"] for b in report["blockers"]], ["sam_credit_not_confirmed"])

    def test_empty_string_counts_as_missing(self):
        report = check_readiness(
            env={"SAM_API_BASE_URL": "", "SAM_API_KEY": ""}, credit_confirmed=True
        )
        self.assertFalse(report["base_url_present"])
        self.assertFalse(report["api_key_present"])
        self.assertFalse(report["ready_for_live_call"])

    def test_env_values_never_leak_into_outputs(self):
        report = build_report(env=READY_ENV, credit_confirmed=True)
        self.assertNotIn(SENTINEL, json.dumps(report, ensure_ascii=False))
        self.assertNotIn(SENTINEL, format_text_report(report))

    def test_honesty_declares_no_real_call(self):
        report = check_readiness(env={}, credit_confirmed=False)
        joined = " ".join(report["honesty"])
        self.assertIn("호출하지 않는다", joined)
        self.assertIn("존재 여부만", joined)
        self.assertIn("성공을 뜻하지 않는다", joined)

    def test_text_report_ready_line(self):
        ready = format_text_report(check_readiness(env=READY_ENV, credit_confirmed=True))
        self.assertIn("READY_FOR_LIVE_CALL: true", ready)
        blocked = format_text_report(check_readiness(env={}, credit_confirmed=False))
        self.assertIn("READY_FOR_LIVE_CALL: false", blocked)
        self.assertIn("BLOCKERS: 3", blocked)

    def test_main_json_exit_zero_when_ready(self):
        with patch.dict(os.environ, READY_ENV, clear=True):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--credit-confirmed", "--json"])
        self.assertEqual(code, 0)
        parsed = json.loads(out.getvalue())
        self.assertTrue(parsed["ready_for_live_call"])
        self.assertNotIn(SENTINEL, out.getvalue())

    def test_main_exit_one_when_not_ready(self):
        with patch.dict(os.environ, {}, clear=True):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([])
        self.assertEqual(code, 1)
        self.assertIn("READY_FOR_LIVE_CALL: false", out.getvalue())


if __name__ == "__main__":
    unittest.main()
