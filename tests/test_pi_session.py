"""Pi 촬영 세션 오케스트레이션 테스트.

Pi 실기가 없으므로 가짜 which와 가짜 runner만 쓴다. 실제 촬영을
주장하지 않으며, 캡처→사진 입력→대조가 한 호출로 이어지는지,
카메라 명령이 없으면 가짜로 대체하지 않고 실패하는지를 본다.
"""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

from terminal.pi_capture import PiCaptureError
from terminal.pi_session import capture_filename, main, run_pi_session

FAKE_CONTENT = b"fake-pi-session-jpeg"


def _no_command(name):
    return None


def _libcamera(name):
    return f"/usr/bin/{name}" if name == "libcamera-still" else None


def _ok_runner(content=FAKE_CONTENT):
    def run(argv, capture_output=True, text=True, timeout=30):
        out = Path(argv[argv.index("-o") + 1])
        out.write_bytes(content)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    return run


class CaptureFilenameTests(unittest.TestCase):
    def test_filename_is_bin_id_jpg(self):
        self.assertEqual(capture_filename("A-01-02"), "A-01-02.jpg")
        self.assertEqual(capture_filename("B-02-02"), "B-02-02.jpg")


class RunPiSessionTests(unittest.TestCase):
    def test_full_session_matches_demo_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "captures"
            report = run_pi_session(
                out_dir, session_id="PI-TEST-1",
                runner=_ok_runner(), which=_libcamera,
            )
            self.assertEqual(report["session_id"], "PI-TEST-1")
            self.assertEqual(report["source"], "mock")
            self.assertEqual(report["capture_source"], "pi-camera")
            summary = report["summary"]
            self.assertEqual(summary["counted_bins"], 6)
            self.assertEqual(summary["matched"], 4)
            self.assertEqual(summary["mismatched"], 2)
            self.assertEqual(summary["abs_diff_total"], 6)
            self.assertEqual(summary["net_diff"], 0)
            by_bin = {b["bin_id"]: b for b in report["bins"]}
            self.assertEqual(by_bin["A-01-02"]["verdict"], "short")
            self.assertEqual(by_bin["A-01-02"]["diff"], -3)
            self.assertEqual(by_bin["B-01-02"]["verdict"], "over")

    def test_photo_hashes_come_from_captured_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "captures"
            report = run_pi_session(
                out_dir, session_id="PI-TEST-2",
                runner=_ok_runner(), which=_libcamera,
            )
            expected = hashlib.sha256(FAKE_CONTENT).hexdigest()
            for entry in report["bins"]:
                self.assertEqual(entry["photo"]["sha256"], expected)
                self.assertEqual(
                    entry["photo"]["image_ref"], f"{entry['bin_id']}.jpg"
                )
                self.assertTrue((out_dir / f"{entry['bin_id']}.jpg").is_file())

    def test_probe_and_honesty_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_pi_session(
                Path(tmp) / "c", session_id="PI-TEST-3",
                runner=_ok_runner(), which=_libcamera,
            )
            self.assertTrue(report["probe"]["available"])
            self.assertEqual(report["probe"]["command"], "libcamera-still")
            self.assertIn(
                "raspistill", report["probe"]["candidates_checked"]
            )
            self.assertTrue(
                any("Pi 실촬영 검증 전" in line for line in report["honesty"])
            )

    def test_no_camera_raises_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "captures"
            with self.assertRaises(PiCaptureError):
                run_pi_session(
                    out_dir, runner=_ok_runner(), which=_no_command
                )
            self.assertFalse(out_dir.exists())

    def test_empty_bin_ids_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_pi_session(
                    Path(tmp) / "c", bin_ids=[],
                    runner=_ok_runner(), which=_libcamera,
                )

    def test_subset_of_bins(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run_pi_session(
                Path(tmp) / "c", bin_ids=["B-02-02", "A-01-01"],
                session_id="PI-TEST-4",
                runner=_ok_runner(), which=_libcamera,
            )
            self.assertEqual(report["summary"]["counted_bins"], 2)
            self.assertEqual(report["summary"]["matched"], 2)
            self.assertEqual(
                [b["bin_id"] for b in report["bins"]],
                ["A-01-01", "B-02-02"],
            )

    def test_runner_failure_propagates_as_pi_capture_error(self):
        def failing(argv, capture_output=True, text=True, timeout=30):
            return SimpleNamespace(returncode=2, stdout="", stderr="x")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PiCaptureError):
                run_pi_session(
                    Path(tmp) / "c", runner=failing, which=_libcamera
                )


class PiSessionCliTests(unittest.TestCase):
    def test_cli_blocked_without_camera_returns_1(self):
        # 이 VM에는 카메라 명령이 없어 실제 CLI는 정직하게 실패해야 한다.
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "captures"
            err = io.StringIO()
            with redirect_stderr(err):
                code = main(["--out-dir", str(out_dir)])
            self.assertEqual(code, 1)
            self.assertIn("Pi 카메라 명령을 찾을 수 없습니다", err.getvalue())
            self.assertFalse(out_dir.exists())

    def test_cli_requires_out_dir(self):
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                main([])


if __name__ == "__main__":
    unittest.main()
