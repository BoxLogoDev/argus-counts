"""Pi 카메라 캡처 경계 테스트.

Pi 실기가 없으므로 가짜 which와 가짜 runner만 쓴다. 실제 촬영을
주장하지 않으며, 명령 부재·실패·산출 이상이 PiCaptureError로
모이는지, 성공 시 CaptureRecord의 해시가 가짜 바이트와 맞는지를 본다.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from terminal.photo_intake import CaptureRecord
from terminal.pi_capture import (
    CAPTURE_COMMAND_CANDIDATES,
    PiCaptureError,
    build_capture_command,
    capture_photo,
    main,
    probe_pi_camera,
)


def _no_command(name):
    return None


def _libcamera(name):
    return f"/usr/bin/{name}" if name == "libcamera-still" else None


def _ok_runner(content=b"fake-pi-jpeg"):
    def run(argv, capture_output=True, text=True, timeout=30):
        out = Path(argv[argv.index("-o") + 1])
        out.write_bytes(content)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    return run


class ProbeTests(unittest.TestCase):
    def test_probe_no_command(self):
        probe = probe_pi_camera(which=_no_command)
        self.assertFalse(probe["available"])
        self.assertIsNone(probe["command"])
        self.assertIsNone(probe["command_path"])
        self.assertEqual(probe["candidates_checked"], list(CAPTURE_COMMAND_CANDIDATES))
        self.assertTrue(any("검증 전" in line for line in probe["honesty"]))

    def test_probe_finds_libcamera_first(self):
        probe = probe_pi_camera(which=lambda name: f"/bin/{name}")
        self.assertTrue(probe["available"])
        self.assertEqual(probe["command"], "libcamera-still")
        self.assertEqual(probe["command_path"], "/bin/libcamera-still")


class BuildCommandTests(unittest.TestCase):
    def test_libcamera_command_shape(self):
        argv = build_capture_command("libcamera-still", "/tmp/x.jpg")
        self.assertEqual(argv[0], "libcamera-still")
        self.assertEqual(argv[argv.index("-o") + 1], "/tmp/x.jpg")
        self.assertIn("--width", argv)
        self.assertIn("1920", argv)

    def test_raspistill_command_shape(self):
        argv = build_capture_command("raspistill", "/tmp/x.jpg", width=1280, height=720)
        self.assertEqual(argv[argv.index("-w") + 1], "1280")
        self.assertEqual(argv[argv.index("-h") + 1], "720")

    def test_unknown_command_raises(self):
        with self.assertRaises(PiCaptureError):
            build_capture_command("webcam-capture", "/tmp/x.jpg")


class CapturePhotoTests(unittest.TestCase):
    def test_no_command_raises_and_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "x.jpg"
            with self.assertRaises(PiCaptureError):
                capture_photo("A-01-02", out, runner=_ok_runner(), which=_no_command)
            self.assertFalse(out.exists())

    def test_success_returns_capture_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "x.jpg"
            record = capture_photo("A-01-02", out, runner=_ok_runner(), which=_libcamera)
            self.assertIsInstance(record, CaptureRecord)
            self.assertEqual(record.bin_id, "A-01-02")
            self.assertEqual(record.sha256, hashlib.sha256(b"fake-pi-jpeg").hexdigest())
            self.assertEqual(record.suffix, ".jpg")

    def test_nonzero_returncode_raises_without_stderr_copy(self):
        def run(argv, capture_output=True, text=True, timeout=30):
            return SimpleNamespace(returncode=2, stdout="", stderr="sensitive-detail")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PiCaptureError) as ctx:
                capture_photo("A-01-02", Path(tmp) / "x.jpg", runner=run, which=_libcamera)
            self.assertIn("returncode=2", str(ctx.exception))
            self.assertNotIn("sensitive-detail", str(ctx.exception))

    def test_missing_output_raises(self):
        def run(argv, capture_output=True, text=True, timeout=30):
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PiCaptureError):
                capture_photo("A-01-02", Path(tmp) / "x.jpg", runner=run, which=_libcamera)


class PiCaptureCliTests(unittest.TestCase):
    def test_cli_probe_json(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(["--probe"])
        self.assertEqual(code, 0)
        payload = json.loads(buf.getvalue())
        self.assertIn("available", payload)
        self.assertIn("honesty", payload)


if __name__ == "__main__":
    unittest.main()
