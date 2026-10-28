import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from qa.pi_readiness import build_report, check_readiness, format_text_report, main

MISSING_PROBE = {
    "available": False,
    "command": None,
    "command_path": None,
    "candidates_checked": ["libcamera-still", "raspistill"],
    "honesty": ["Pi 실촬영 검증 전입니다"],
}
READY_PROBE = {
    "available": True,
    "command": "libcamera-still",
    "command_path": "/usr/bin/libcamera-still",
    "candidates_checked": ["libcamera-still", "raspistill"],
    "honesty": ["Pi 실촬영 검증 전입니다"],
}


class PiReadinessTests(unittest.TestCase):
    def test_all_blockers_in_order(self):
        report = check_readiness(probe=MISSING_PROBE, device_confirmed=False)
        self.assertFalse(report["device_confirmed"])
        self.assertFalse(report["camera_available"])
        self.assertIsNone(report["camera_command"])
        self.assertFalse(report["ready_for_real_capture"])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_device_arrival_not_confirmed", "pi_camera_command_missing"],
        )

    def test_all_ready(self):
        report = check_readiness(probe=READY_PROBE, device_confirmed=True)
        self.assertTrue(report["camera_available"])
        self.assertEqual(report["camera_command"], "libcamera-still")
        self.assertTrue(report["ready_for_real_capture"])
        self.assertEqual(report["blockers"], [])

    def test_device_is_only_blocker_when_camera_present(self):
        report = check_readiness(probe=READY_PROBE, device_confirmed=False)
        self.assertFalse(report["ready_for_real_capture"])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_device_arrival_not_confirmed"],
        )

    def test_camera_is_only_blocker_when_device_confirmed(self):
        report = check_readiness(probe=MISSING_PROBE, device_confirmed=True)
        self.assertFalse(report["ready_for_real_capture"])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_camera_command_missing"],
        )

    def test_candidates_checked_copied(self):
        report = check_readiness(probe=MISSING_PROBE, device_confirmed=False)
        self.assertEqual(
            report["candidates_checked"], ["libcamera-still", "raspistill"]
        )

    def test_which_injection_finds_raspistill(self):
        def fake_which(name):
            return "/usr/bin/raspistill" if name == "raspistill" else None

        report = check_readiness(device_confirmed=True, which=fake_which)
        self.assertTrue(report["camera_available"])
        self.assertEqual(report["camera_command"], "raspistill")
        self.assertTrue(report["ready_for_real_capture"])

    def test_honesty_declares_no_real_capture(self):
        report = build_report(probe=MISSING_PROBE, device_confirmed=False)
        joined = " ".join(report["honesty"])
        self.assertIn("촬영을 하지 않는다", joined)
        self.assertIn("존재만 탐지", joined)
        self.assertIn("성공을 뜻하지 않는다", joined)

    def test_text_report_ready_line(self):
        ready = format_text_report(
            check_readiness(probe=READY_PROBE, device_confirmed=True)
        )
        self.assertIn("READY_FOR_REAL_CAPTURE: true", ready)
        blocked = format_text_report(
            check_readiness(probe=MISSING_PROBE, device_confirmed=False)
        )
        self.assertIn("READY_FOR_REAL_CAPTURE: false", blocked)
        self.assertIn("BLOCKERS: 2", blocked)

    def test_main_json_exit_codes(self):
        out = io.StringIO()
        with patch("qa.pi_readiness.probe_pi_camera", return_value=READY_PROBE):
            with redirect_stdout(out):
                code = main(["--device-confirmed", "--json"])
        self.assertEqual(code, 0)
        parsed = json.loads(out.getvalue())
        self.assertTrue(parsed["ready_for_real_capture"])

        out2 = io.StringIO()
        with patch("qa.pi_readiness.probe_pi_camera", return_value=MISSING_PROBE):
            with redirect_stdout(out2):
                code2 = main([])
        self.assertEqual(code2, 1)
        self.assertIn("READY_FOR_REAL_CAPTURE: false", out2.getvalue())


if __name__ == "__main__":
    unittest.main()
