import io
import json
import unittest
from contextlib import redirect_stdout

from qa import deadline as dl


class DeadlineTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(dl.DEADLINE_KST_ISO, "2026-11-05T11:00:00+09:00")
        self.assertEqual(dl.DEADLINE_ET_TEXT, "2026-11-04 21:00 ET")
        self.assertEqual(dl.DEADLINE_KST_TEXT, "2026-11-05 11:00 KST")
        self.assertEqual(dl.DUE_SOON_HOURS, 24)

    def test_before_deadline(self):
        r = dl.evaluate_deadline("2026-10-31T01:50:00+09:00")
        self.assertEqual(r["status"], "before_deadline")
        self.assertFalse(r["is_overdue"])
        self.assertGreater(r["remaining_seconds"], 24 * 3600)
        # 2026-10-31 01:50 -> 2026-11-05 11:00 = 5 days 9h10m
        self.assertEqual(r["remaining_seconds"], 5 * 86400 + 9 * 3600 + 10 * 60)
        self.assertFalse(r["submission_ready"])
        self.assertEqual(r["blockers"], ["pi_real_capture_pending"])

    def test_due_soon_within_24h(self):
        r = dl.evaluate_deadline("2026-11-04T12:00:00+09:00")
        self.assertEqual(r["status"], "due_soon")
        self.assertFalse(r["is_overdue"])
        self.assertEqual(r["remaining_seconds"], 23 * 3600)

    def test_overdue_at_and_after_deadline(self):
        at = dl.evaluate_deadline("2026-11-05T11:00:00+09:00")
        self.assertEqual(at["status"], "overdue")
        self.assertTrue(at["is_overdue"])
        self.assertEqual(at["remaining_seconds"], 0)
        after = dl.evaluate_deadline("2026-11-05T12:00:00+09:00")
        self.assertEqual(after["status"], "overdue")
        self.assertEqual(after["remaining_seconds"], -3600)

    def test_naive_now_assumed_kst(self):
        r = dl.evaluate_deadline("2026-11-04T12:00:00")
        self.assertEqual(r["status"], "due_soon")
        self.assertTrue(r["now"].endswith("+09:00"))

    def test_validate_passes_and_detects_tamper(self):
        r = dl.evaluate_deadline("2026-10-31T01:50:00+09:00")
        self.assertEqual(dl.validate_deadline(r), [])
        bad = dict(r, status="overdue")
        self.assertTrue(any("status" in p for p in dl.validate_deadline(bad)))
        bad2 = dict(r, remaining_seconds=1)
        self.assertTrue(
            any("remaining_seconds" in p for p in dl.validate_deadline(bad2))
        )
        bad3 = dict(r, submission_ready=True)
        self.assertTrue(
            any("submission_ready" in p for p in dl.validate_deadline(bad3))
        )

    def test_cli_text_before_deadline_exit_0(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = dl.main(["--now", "2026-10-31T01:50:00+09:00"])
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("STATUS: before_deadline", out)
        self.assertIn("DEADLINE_KST: 2026-11-05T11:00:00+09:00", out)
        self.assertIn("SUBMISSION_READY: false", out)

    def test_cli_json_overdue_exit_1(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = dl.main(["--now", "2026-11-06T00:00:00+09:00", "--json"])
        self.assertEqual(code, 1)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["status"], "overdue")
        self.assertTrue(data["is_overdue"])

    def test_cli_invalid_now_exit_2_and_honesty(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = dl.main(["--now", "not-a-date"])
        self.assertEqual(code, 2)
        self.assertIn("invalid now", buf.getvalue())
        r = dl.build_deadline(now="2026-10-31T01:50:00+09:00")
        joined = " ".join(r["honesty"])
        self.assertIn("실제로 제출하지 않는다", joined)
        self.assertIn("지각 제출은 고려되지 않는다", joined)


if __name__ == "__main__":
    unittest.main()
