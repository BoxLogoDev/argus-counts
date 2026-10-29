"""Pi 실촬영 단일 빈 스모크 하네스 테스트.

Pi 실기가 없으므로 가짜 which·가짜 session_fn·가짜 runner만 쓴다.
준비 점검을 통과하지 못하면 촬영 세션을 부르지 않는지, 준비됐을 때만
빈 1개를 시도하는지, 실패를 가짜 파일이나 모의로 대체하지 않는지를 본다.
실제 촬영을 주장하지 않는다.
"""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

from qa.pi_smoke import build_report, format_text_report, main, run_smoke
from terminal.pi_capture import PiCaptureError

SENTINEL = "SECRET-SENTINEL-67890"
FAKE_CONTENT = b"fake-pi-smoke-jpeg"
FAKE_SHA = "f" * 64


def _no_command(name):
    return None


def _libcamera(name):
    return f"/usr/bin/{name}" if name == "libcamera-still" else None


def _ok_runner(argv, capture_output=True, text=True, timeout=30):
    out = Path(argv[argv.index("-o") + 1])
    out.write_bytes(FAKE_CONTENT)
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def _passed_result(bin_id="A-01-02"):
    return {
        "session_id": "PI-SMOKE",
        "source": "mock",
        "capture_source": "pi-camera",
        "bins": [
            {
                "bin_id": bin_id,
                "book_qty": 8,
                "counted_qty": 5,
                "diff": -3,
                "photo": {"sha256": FAKE_SHA, "image_ref": f"{bin_id}.jpg"},
            }
        ],
    }


class FakeSession:
    def __init__(self, result=None):
        self.result = result if result is not None else _passed_result()
        self.calls = []

    def __call__(self, output_dir, bin_ids=None, session_id=None, runner=None, which=None):
        self.calls.append(
            {"output_dir": output_dir, "bin_ids": bin_ids, "session_id": session_id}
        )
        return self.result


class PiSmokeTests(unittest.TestCase):
    def test_blocked_when_not_ready_and_session_not_called(self):
        session = FakeSession()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "captures"
            report = run_smoke(
                output_dir=out_dir, device_confirmed=False,
                which=_no_command, session_fn=session,
            )
            self.assertFalse(out_dir.exists())
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["attempted"])
        self.assertEqual(session.calls, [])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_device_arrival_not_confirmed", "pi_camera_command_missing"],
        )

    def test_blocked_device_only(self):
        session = FakeSession()
        report = run_smoke(
            device_confirmed=False, which=_libcamera, session_fn=session
        )
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_device_arrival_not_confirmed"],
        )
        self.assertEqual(session.calls, [])

    def test_blocked_camera_only(self):
        session = FakeSession()
        report = run_smoke(
            device_confirmed=True, which=_no_command, session_fn=session
        )
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_camera_command_missing"],
        )
        self.assertEqual(session.calls, [])

    def test_passed_with_fake_session_when_ready(self):
        session = FakeSession()
        with tempfile.TemporaryDirectory() as tmp:
            report = run_smoke(
                output_dir=Path(tmp) / "c", device_confirmed=True,
                which=_libcamera, session_fn=session,
            )
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["attempted"])
        self.assertTrue(report["ready_for_real_capture"])
        self.assertEqual(report["source"], "mock")
        self.assertEqual(report["capture_source"], "pi-camera")
        self.assertEqual(report["counted_qty"], 5)
        self.assertEqual(report["book_qty"], 8)
        self.assertEqual(report["diff"], -3)
        self.assertEqual(report["photo_sha256"], FAKE_SHA)
        self.assertEqual(session.calls[0]["bin_ids"], ["A-01-02"])
        self.assertEqual(session.calls[0]["session_id"], "PI-SMOKE")

    def test_passed_with_real_pi_session_and_fake_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "captures"
            report = run_smoke(
                output_dir=out_dir, device_confirmed=True,
                which=_libcamera, runner=_ok_runner,
            )
            self.assertTrue((out_dir / "A-01-02.jpg").is_file())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["counted_qty"], 5)
        self.assertEqual(report["diff"], -3)
        self.assertEqual(
            report["photo_sha256"], hashlib.sha256(FAKE_CONTENT).hexdigest()
        )
        self.assertEqual(report["photo_image_ref"], "A-01-02.jpg")

    def test_pi_capture_error_fails_without_fallback(self):
        def raising(*args, **kwargs):
            raise PiCaptureError("fake failure")

        report = run_smoke(
            device_confirmed=True, which=_libcamera, session_fn=raising
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "PiCaptureError")
        self.assertTrue(report["attempted"])
        self.assertIsNone(report["counted_qty"])

    def test_generic_error_does_not_leak_exception_values(self):
        def leaky(*args, **kwargs):
            raise RuntimeError(f"boom {SENTINEL}")

        report = run_smoke(
            device_confirmed=True, which=_libcamera, session_fn=leaky
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "RuntimeError")
        blob = json.dumps(report, ensure_ascii=False) + format_text_report(report)
        self.assertNotIn(SENTINEL, blob)

    def test_unexpected_capture_source_fails(self):
        result = _passed_result()
        result["capture_source"] = "file"
        report = run_smoke(
            device_confirmed=True, which=_libcamera,
            session_fn=FakeSession(result),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unexpected_capture_source")

    def test_unknown_bin_fails_without_call(self):
        session = FakeSession()
        report = run_smoke(
            device_confirmed=True, which=_libcamera,
            bin_id="Z-99-99", session_fn=session,
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unknown_bin")
        self.assertFalse(report["attempted"])
        self.assertEqual(session.calls, [])

    def test_text_report_honesty_and_main_blocked(self):
        report = build_report(device_confirmed=False, which=_no_command)
        text = format_text_report(report)
        self.assertIn("STATUS: blocked", text)
        self.assertIn("SMOKE_PASSED: false", text)
        self.assertIn("BLOCKERS: 2", text)
        joined = " ".join(report["honesty"])
        self.assertIn("촬영하지 않는다", joined)
        self.assertIn("대체하지 않는다", joined)
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--json"])
        self.assertEqual(code, 1)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["status"], "blocked")
        self.assertFalse(parsed["attempted"])


if __name__ == "__main__":
    unittest.main()
