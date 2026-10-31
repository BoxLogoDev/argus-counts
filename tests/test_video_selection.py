import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qa.video_selection import (
    DECISION_DATE,
    FALLBACK_VIDEO,
    PRIMARY_VIDEO,
    build_selection,
    evaluate_selection,
    format_text_report,
    validate_selection,
)

READY_PROBE = {"available": True, "command": "libcamera-still", "candidates_checked": ["libcamera-still", "raspistill"]}
MISSING_PROBE = {"available": False, "command": None, "candidates_checked": ["libcamera-still", "raspistill"]}
BLOCKERS = ["pi_device_arrival_not_confirmed", "pi_camera_command_missing"]
PRIMARY_SIZE = 1_000_000
FALLBACK_SIZE = 1_050_000


class VideoSelectionTests(unittest.TestCase):
    def test_pending_selects_primary_by_default(self):
        r = evaluate_selection("2026-11-01", False, BLOCKERS, PRIMARY_SIZE, FALLBACK_SIZE)
        self.assertEqual(r["fallback_status"], "pending")
        self.assertEqual(r["selected_video"], PRIMARY_VIDEO)
        self.assertEqual(r["selection_reason"], "pending_default")
        self.assertEqual(r["selected_size"], PRIMARY_SIZE)
        self.assertEqual(r["problems"], [])
        self.assertIs(r["submission_ready"], False)
        self.assertEqual(validate_selection(r), [])

    def test_fallback_due_selects_fallback_render(self):
        r = evaluate_selection("2026-11-02", False, BLOCKERS, PRIMARY_SIZE, FALLBACK_SIZE)
        self.assertEqual(r["fallback_status"], "fallback_due")
        self.assertTrue(r["fallback_adopted"])
        self.assertEqual(r["selected_video"], FALLBACK_VIDEO)
        self.assertEqual(r["selection_reason"], "fallback_due")
        self.assertEqual(r["selected_size"], FALLBACK_SIZE)
        self.assertEqual(r["decision_date"], DECISION_DATE)
        self.assertEqual(validate_selection(r), [])

    def test_pi_ready_selects_primary(self):
        r = evaluate_selection("2026-11-03", True, [], PRIMARY_SIZE, FALLBACK_SIZE)
        self.assertEqual(r["fallback_status"], "pi_ready")
        self.assertEqual(r["selected_video"], PRIMARY_VIDEO)
        self.assertEqual(r["selection_reason"], "pi_ready")
        self.assertFalse(r["fallback_adopted"])
        self.assertEqual(validate_selection(r), [])

    def test_missing_selected_video_is_a_problem(self):
        r = evaluate_selection("2026-11-02", False, BLOCKERS, PRIMARY_SIZE, None)
        self.assertIsNone(r["selected_size"])
        self.assertEqual(len(r["problems"]), 1)
        self.assertIn(FALLBACK_VIDEO, r["problems"][0])
        empty = evaluate_selection("2026-11-01", False, BLOCKERS, 0, FALLBACK_SIZE)
        self.assertEqual(len(empty["problems"]), 1)
        self.assertIn("empty", empty["problems"][0])

    def test_build_selection_from_probes_and_real_files(self):
        pending = build_selection(today="2026-11-01", pi_probe=MISSING_PROBE)
        self.assertEqual(pending["selected_video"], PRIMARY_VIDEO)
        self.assertGreater(pending["primary_size"], 0)
        self.assertGreater(pending["fallback_size"], 0)
        self.assertEqual(pending["problems"], [])
        self.assertEqual(validate_selection(pending), [])
        due = build_selection(today="2026-11-02", pi_probe=MISSING_PROBE)
        self.assertEqual(due["selected_video"], FALLBACK_VIDEO)
        ready = build_selection(today="2026-11-02", pi_probe=READY_PROBE, device_confirmed=True)
        self.assertEqual(ready["fallback_status"], "pi_ready")
        self.assertEqual(ready["selected_video"], PRIMARY_VIDEO)

    def test_validate_detects_tampering(self):
        r = evaluate_selection("2026-11-01", False, BLOCKERS, PRIMARY_SIZE, FALLBACK_SIZE)
        bad_video = dict(r, selected_video=FALLBACK_VIDEO)
        self.assertTrue(any("selected_video" in p for p in validate_selection(bad_video)))
        bad_ready = dict(r, submission_ready=True)
        self.assertTrue(any("submission_ready" in p for p in validate_selection(bad_ready)))
        bad_status = dict(r, fallback_status="fallback_due")
        self.assertTrue(any("fallback_status" in p for p in validate_selection(bad_status)))
        bad_honesty = dict(r, honesty=["선택은 실제로 제출하지 않는다"])
        self.assertTrue(any("honesty" in p for p in validate_selection(bad_honesty)))

    def test_text_report_marks_not_ready_and_honesty(self):
        r = evaluate_selection("2026-11-01", False, BLOCKERS, PRIMARY_SIZE, FALLBACK_SIZE)
        text = format_text_report(r)
        self.assertIn(f"SELECTED_VIDEO: {PRIMARY_VIDEO}", text)
        self.assertIn("SUBMISSION_READY: false", text)
        self.assertIn("Pi 실촬영이 아닙니다", text)
        self.assertIn("실제로 제출하지 않는다", text)

    def test_cli_text_and_json(self):
        proc = subprocess.run(
            [sys.executable, "-m", "qa.video_selection", "--date", "2026-11-01"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SELECTED_VIDEO:", proc.stdout)
        proc = subprocess.run(
            [sys.executable, "-m", "qa.video_selection", "--date", "2026-11-02", "--json"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["fallback_status"], "fallback_due")
        self.assertEqual(report["selected_video"], FALLBACK_VIDEO)
        self.assertIs(report["submission_ready"], False)

    def test_cli_invalid_date_exit_2(self):
        proc = subprocess.run(
            [sys.executable, "-m", "qa.video_selection", "--date", "not-a-date"],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
