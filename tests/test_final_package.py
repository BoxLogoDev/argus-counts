import io
import json
import unittest
from contextlib import redirect_stdout

from qa import final_package as fp


def _base(**overrides):
    kwargs = dict(
        inventory_present=18,
        inventory_total=18,
        inventory_missing=[],
        deadline_status="before_deadline",
        remaining_seconds=457800,
        fallback_status="pending",
        fallback_adopted=False,
        blockers=["pi_real_capture_pending"],
    )
    kwargs.update(overrides)
    return fp.evaluate_final_package(**kwargs)


class FinalPackageTests(unittest.TestCase):
    def test_constants_and_honesty(self):
        self.assertEqual(fp.PACKAGE_DATE_TARGET, "2026-11-03")
        joined = " ".join(fp.HONESTY)
        self.assertIn("실제로 제출하지 않는다", joined)
        self.assertIn("Pi 실촬영 검증 전", joined)

    def test_blocked_when_blockers_remain(self):
        r = _base()
        self.assertEqual(r["status"], "blocked")
        self.assertFalse(r["submission_ready"])
        self.assertEqual(r["blockers"], ["pi_real_capture_pending"])

    def test_ready_for_packaging_when_no_blockers(self):
        r = _base(blockers=[])
        self.assertEqual(r["status"], "ready_for_packaging")
        # 이 하네스 단독으로는 제출 완료가 아니므로 항상 False다.
        self.assertFalse(r["submission_ready"])

    def test_incomplete_when_inventory_missing(self):
        r = _base(inventory_present=17, inventory_missing=["README.md"], blockers=[])
        self.assertEqual(r["status"], "incomplete")

    def test_overdue_takes_precedence(self):
        r = _base(
            deadline_status="overdue",
            remaining_seconds=0,
            inventory_present=0,
            inventory_missing=["README.md"],
        )
        self.assertEqual(r["status"], "overdue")

    def test_validate_passes_and_detects_tamper(self):
        r = _base()
        self.assertEqual(fp.validate_final_package(r), [])
        bad = dict(r, status="ready_for_packaging")
        self.assertTrue(any("status" in p for p in fp.validate_final_package(bad)))
        bad2 = dict(r, submission_ready=True)
        self.assertTrue(
            any("submission_ready" in p for p in fp.validate_final_package(bad2))
        )
        bad3 = dict(r, inventory_present=10)
        self.assertTrue(
            any("inventory_present" in p for p in fp.validate_final_package(bad3))
        )

    def test_build_real_root_blocked(self):
        r = fp.build_final_package(
            now="2026-10-31T04:50:00+09:00", today="2026-10-31"
        )
        self.assertEqual(r["inventory_total"], 18)
        self.assertEqual(r["inventory_present"], 18)
        self.assertEqual(r["inventory_missing"], [])
        self.assertEqual(r["deadline_status"], "before_deadline")
        self.assertEqual(r["fallback_status"], "pending")
        self.assertFalse(r["fallback_adopted"])
        self.assertEqual(r["status"], "blocked")
        self.assertEqual(fp.validate_final_package(r), [])

    def test_evaluate_without_export_fields_is_none(self):
        r = _base()
        self.assertIsNone(r["export_copied"])
        self.assertIsNone(r["export_total"])
        self.assertIsNone(r["export_missing"])
        self.assertIsNone(r["export_total_bytes"])
        self.assertEqual(fp.validate_final_package(r), [])

    def test_export_mismatch_is_incomplete(self):
        r = _base(
            export_copied=17,
            export_total=18,
            export_missing=["README.md"],
            export_total_bytes=1234,
            blockers=[],
        )
        self.assertEqual(r["status"], "incomplete")

    def test_export_ok_keeps_blocked(self):
        r = _base(
            export_copied=18,
            export_total=18,
            export_missing=[],
            export_total_bytes=2136591,
        )
        self.assertEqual(r["status"], "blocked")
        self.assertEqual(fp.validate_final_package(r), [])

    def test_validate_detects_export_tamper(self):
        r = _base(
            export_copied=18,
            export_total=18,
            export_missing=[],
            export_total_bytes=2136591,
        )
        bad = dict(r, export_copied=10)
        self.assertTrue(
            any("export" in p for p in fp.validate_final_package(bad))
        )
        bad2 = dict(r, export_total_bytes=0)
        self.assertTrue(
            any("export_total_bytes" in p for p in fp.validate_final_package(bad2))
        )

    def test_build_includes_export_evidence(self):
        from qa.submission_inventory import build_inventory

        r = fp.build_final_package(
            now="2026-10-31T12:50:00+09:00", today="2026-10-31"
        )
        self.assertEqual(r["export_copied"], 18)
        self.assertEqual(r["export_total"], 18)
        self.assertEqual(r["export_missing"], [])
        self.assertEqual(
            r["export_total_bytes"], build_inventory()["total_bytes"]
        )
        self.assertEqual(fp.validate_final_package(r), [])

    def test_cli_text_includes_export_lines(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fp.main(
                ["--now", "2026-10-31T12:50:00+09:00", "--date", "2026-10-31"]
            )
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("EXPORT_COPIED: 18", out)
        self.assertIn("EXPORT_TOTAL: 18", out)
        self.assertIn("EXPORT_MISSING: []", out)

    def test_cli_text_blocked_exit_0(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fp.main(
                ["--now", "2026-10-31T04:50:00+09:00", "--date", "2026-10-31"]
            )
        out = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("STATUS: blocked", out)
        self.assertIn("INVENTORY_PRESENT: 18", out)
        self.assertIn("SUBMISSION_READY: false", out)

    def test_cli_json_and_invalid_date_exit_2(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = fp.main(
                [
                    "--now",
                    "2026-10-31T04:50:00+09:00",
                    "--date",
                    "2026-10-31",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["status"], "blocked")
        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            code2 = fp.main(["--date", "not-a-date"])
        self.assertEqual(code2, 2)
        self.assertIn("invalid input", buf2.getvalue())


if __name__ == "__main__":
    unittest.main()
