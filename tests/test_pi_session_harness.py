"""Pi 실촬영 전체 세션 하네스(qa.pi_session) 테스트.

Pi 실기가 없으므로 가짜 which·가짜 session_fn·가짜 runner만 쓴다.
준비 점검을 통과하지 못하면 촬영 세션을 부르지 않는지, 준비됐을 때만
데모 빈 6개 전체를 시도하는지, 한 빈이라도 어긋나면 전체를 실패로
보고 실패를 가짜 파일이나 모의로 대체하지 않는지를 본다.
가짜 성공을 실제 Pi 실촬영 성공으로 주장하지 않는다.
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

from qa.pi_session import build_report, format_text_report, main, run_pi_full_session
from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids, demo_ledger
from terminal.pi_capture import PiCaptureError

SENTINEL = "SECRET-SENTINEL-67890"
FAKE_CONTENT = b"fake-pi-session-jpeg"
FAKE_SHA = "f" * 64


def _no_command(name):
    return None


def _libcamera(name):
    return f"/usr/bin/{name}" if name == "libcamera-still" else None


def _ok_runner(argv, capture_output=True, text=True, timeout=30):
    out = Path(argv[argv.index("-o") + 1])
    out.write_bytes(FAKE_CONTENT)
    return SimpleNamespace(returncode=0, stdout="", stderr="")


def _passed_result():
    ledger = demo_ledger()
    bins = []
    for bin_id in demo_bin_ids():
        counted = DEMO_COUNTED_QTY[bin_id]
        book = ledger[bin_id].book_qty
        diff = counted - book
        verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
        bins.append(
            {
                "bin_id": bin_id,
                "book_qty": book,
                "counted_qty": counted,
                "diff": diff,
                "verdict": verdict,
                "photo": {"sha256": FAKE_SHA, "image_ref": f"{bin_id}.jpg"},
            }
        )
    return {
        "session_id": "PI-TEST",
        "source": "mock",
        "capture_source": "pi-camera",
        "bins": bins,
        "summary": {
            "counted_bins": 6,
            "matched": 4,
            "mismatched": 2,
            "match_rate": 4 / 6,
            "abs_diff_total": 6,
            "net_diff": 0,
        },
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


class PiFullSessionTests(unittest.TestCase):
    def test_blocked_when_not_ready_and_session_not_called(self):
        session = FakeSession()
        report = run_pi_full_session(
            device_confirmed=False, which=_no_command, session_fn=session
        )
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["attempted"])
        self.assertFalse(report["ready_for_real_capture"])
        self.assertEqual(session.calls, [])
        self.assertEqual(report["bins"], [])
        self.assertIsNone(report["summary"])
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_device_arrival_not_confirmed", "pi_camera_command_missing"],
        )

    def test_blocked_camera_only(self):
        session = FakeSession()
        report = run_pi_full_session(
            device_confirmed=True, which=_no_command, session_fn=session
        )
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["pi_camera_command_missing"],
        )
        self.assertEqual(session.calls, [])

    def test_passed_full_session_with_fake_session(self):
        session = FakeSession()
        with tempfile.TemporaryDirectory() as tmp:
            report = run_pi_full_session(
                output_dir=Path(tmp) / "c", device_confirmed=True,
                which=_libcamera, session_fn=session, session_id="PI-TEST",
            )
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["attempted"])
        self.assertTrue(report["ready_for_real_capture"])
        self.assertEqual(report["source"], "mock")
        self.assertEqual(report["capture_source"], "pi-camera")
        self.assertEqual(report["session_id"], "PI-TEST")
        self.assertEqual(session.calls[0]["bin_ids"], demo_bin_ids())
        self.assertEqual(len(report["bins"]), 6)
        by_bin = {b["bin_id"]: b for b in report["bins"]}
        self.assertEqual(by_bin["A-01-02"]["diff"], -3)
        self.assertEqual(by_bin["A-01-02"]["verdict"], "short")
        self.assertEqual(by_bin["A-01-02"]["photo_sha256"], FAKE_SHA)
        self.assertEqual(by_bin["A-01-02"]["photo_image_ref"], "A-01-02.jpg")
        self.assertEqual(by_bin["B-01-02"]["diff"], 3)
        summary = report["summary"]
        self.assertEqual(summary["counted_bins"], 6)
        self.assertEqual(summary["matched"], 4)
        self.assertEqual(summary["mismatched"], 2)
        self.assertEqual(summary["abs_diff_total"], 6)
        self.assertEqual(summary["net_diff"], 0)

    def test_passed_with_real_pi_session_and_fake_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "captures"
            report = run_pi_full_session(
                output_dir=out_dir, device_confirmed=True,
                which=_libcamera, runner=_ok_runner, session_id="PI-REAL-FAKE",
            )
            for bin_id in demo_bin_ids():
                self.assertTrue((out_dir / f"{bin_id}.jpg").is_file())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["capture_source"], "pi-camera")
        expected_sha = hashlib.sha256(FAKE_CONTENT).hexdigest()
        for entry in report["bins"]:
            self.assertEqual(entry["photo_sha256"], expected_sha)
        self.assertEqual(report["summary"]["matched"], 4)

    def test_unexpected_capture_source_fails(self):
        result = _passed_result()
        result["capture_source"] = "file"
        report = run_pi_full_session(
            device_confirmed=True, which=_libcamera,
            session_fn=FakeSession(result),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unexpected_capture_source")
        self.assertEqual(report["capture_source"], "file")
        self.assertEqual(report["bins"], [])
        self.assertIsNone(report["summary"])

    def test_unexpected_bins_fails(self):
        result = _passed_result()
        result["bins"] = result["bins"][:-1]
        report = run_pi_full_session(
            device_confirmed=True, which=_libcamera,
            session_fn=FakeSession(result),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unexpected_bins")

    def test_inconsistent_diff_fails(self):
        result = _passed_result()
        result["bins"][1]["diff"] = 0
        report = run_pi_full_session(
            device_confirmed=True, which=_libcamera,
            session_fn=FakeSession(result),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "inconsistent_diff")

    def test_inconsistent_summary_fails(self):
        result = _passed_result()
        result["summary"] = dict(result["summary"], net_diff=7)
        report = run_pi_full_session(
            device_confirmed=True, which=_libcamera,
            session_fn=FakeSession(result),
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "inconsistent_summary")

    def test_pi_capture_error_fails_without_fallback(self):
        def raising(*args, **kwargs):
            raise PiCaptureError("fake failure")

        report = run_pi_full_session(
            device_confirmed=True, which=_libcamera, session_fn=raising
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "PiCaptureError")
        self.assertTrue(report["attempted"])
        self.assertEqual(report["bins"], [])
        self.assertIsNone(report["summary"])

    def test_generic_error_does_not_leak_exception_values(self):
        def leaky(*args, **kwargs):
            raise RuntimeError(f"boom {SENTINEL}")

        report = run_pi_full_session(
            device_confirmed=True, which=_libcamera, session_fn=leaky
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "RuntimeError")
        blob = json.dumps(report, ensure_ascii=False) + format_text_report(report)
        self.assertNotIn(SENTINEL, blob)

    def test_text_report_honesty_and_main_blocked(self):
        report = build_report(device_confirmed=False, which=_no_command)
        text = format_text_report(report)
        self.assertIn("STATUS: blocked", text)
        self.assertIn("SESSION_PASSED: false", text)
        self.assertIn("BLOCKERS: 2", text)
        joined = " ".join(report["honesty"])
        self.assertIn("촬영하지 않는다", joined)
        self.assertIn("대체하지 않는다", joined)
        self.assertIn("검증 완료를 뜻하지 않는다", joined)
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--json"])
        self.assertEqual(code, 1)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["status"], "blocked")
        self.assertFalse(parsed["attempted"])
        self.assertEqual(parsed["bins"], [])


if __name__ == "__main__":
    unittest.main()
