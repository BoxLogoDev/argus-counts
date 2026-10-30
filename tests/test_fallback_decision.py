import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qa.fallback_decision import (
    DECISION_DATE,
    FALLBACK_ASSET,
    FALLBACK_RENDER,
    build_decision,
    evaluate_decision,
    format_text_report,
    validate_decision,
)

READY_PROBE = {"available": True, "command": "libcamera-still", "candidates_checked": ["libcamera-still", "raspistill"]}
MISSING_PROBE = {"available": False, "command": None, "candidates_checked": ["libcamera-still", "raspistill"]}
BLOCKERS = ["pi_device_arrival_not_confirmed", "pi_camera_command_missing"]


class FallbackDecisionTests(unittest.TestCase):
    def test_pending_before_decision_date(self):
        r = evaluate_decision("2026-10-30", False, BLOCKERS)
        self.assertEqual(r["status"], "pending")
        self.assertFalse(r["fallback_adopted"])
        self.assertEqual(r["decision_date"], DECISION_DATE)
        self.assertEqual(validate_decision(r), [])

    def test_fallback_due_on_decision_date(self):
        r = evaluate_decision("2026-11-02", False, BLOCKERS)
        self.assertEqual(r["status"], "fallback_due")
        self.assertTrue(r["fallback_adopted"])
        self.assertEqual(r["fallback_asset"], FALLBACK_ASSET)
        self.assertEqual(r["fallback_render"], FALLBACK_RENDER)
        self.assertIs(r["is_pi_real_capture"], False)
        self.assertEqual(validate_decision(r), [])

    def test_fallback_due_after_decision_date(self):
        r = evaluate_decision("2026-11-03", False, BLOCKERS)
        self.assertEqual(r["status"], "fallback_due")
        self.assertTrue(r["fallback_adopted"])

    def test_pi_ready_never_adopts_fallback(self):
        for day in ("2026-10-30", "2026-11-02", "2026-11-04"):
            r = evaluate_decision(day, True, [])
            self.assertEqual(r["status"], "pi_ready")
            self.assertFalse(r["fallback_adopted"])
            self.assertEqual(validate_decision(r), [])

    def test_build_decision_from_probes(self):
        pending = build_decision(today="2026-10-30", pi_probe=MISSING_PROBE)
        self.assertEqual(pending["status"], "pending")
        self.assertEqual(pending["pi_blockers"], BLOCKERS)
        due = build_decision(today="2026-11-02", pi_probe=MISSING_PROBE)
        self.assertEqual(due["status"], "fallback_due")
        ready = build_decision(today="2026-11-02", pi_probe=READY_PROBE, device_confirmed=True)
        self.assertEqual(ready["status"], "pi_ready")
        self.assertEqual(ready["pi_blockers"], [])

    def test_validate_detects_tampering(self):
        r = evaluate_decision("2026-10-30", False, BLOCKERS)
        r["fallback_adopted"] = True
        problems = validate_decision(r)
        self.assertTrue(any("fallback_adopted" in p for p in problems))
        r2 = evaluate_decision("2026-11-02", False, BLOCKERS)
        r2["is_pi_real_capture"] = True
        self.assertTrue(any("is_pi_real_capture" in p for p in validate_decision(r2)))
        r3 = evaluate_decision("2026-11-02", True, BLOCKERS)
        self.assertTrue(validate_decision(r3))

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_decision("2026-13-40", False, BLOCKERS)

    def test_text_report_markers(self):
        text = format_text_report(evaluate_decision("2026-11-02", False, BLOCKERS))
        self.assertIn("STATUS: fallback_due", text)
        self.assertIn("DECISION_DATE: 2026-11-02", text)
        self.assertIn("FALLBACK_ADOPTED: true", text)
        self.assertIn("Pi 실촬영이 아닙니다", text)

    def test_cli_json_blocked_environment(self):
        out = subprocess.run(
            [sys.executable, "-m", "qa.fallback_decision", "--date", "2026-10-30", "--json"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        data = json.loads(out.stdout)
        self.assertEqual(data["status"], "pending")
        self.assertFalse(data["fallback_adopted"])
        self.assertEqual(data["pi_blockers"], BLOCKERS)


if __name__ == "__main__":
    unittest.main()
