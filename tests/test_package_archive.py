import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qa.package_archive import (
    build_archive,
    build_archive_verify,
    evaluate_archive,
    format_text_report,
    validate_archive,
)
from qa.video_selection import FALLBACK_VIDEO

BASE = dict(
    out_dir="/tmp/archive-x",
    mode="export",
    copied=18,
    total=18,
    missing=[],
    total_bytes=2_000_000,
    verify_verified=True,
    verify_copied=18,
    verify_total_bytes=2_000_000,
    final_status="blocked",
    final_inventory_present=18,
    final_inventory_total=18,
    final_export_copied=18,
    final_export_total=18,
    final_export_total_bytes=2_000_000,
    selected_video=FALLBACK_VIDEO,
    selected_size=1_050_000,
    selected_copied=True,
    selected_size_in_archive=1_050_000,
    selected_sha256="a" * 64,
)


class PackageArchiveTests(unittest.TestCase):
    def test_evaluate_archived_when_all_cross_checks_match(self):
        r = evaluate_archive(**BASE)
        self.assertEqual(r["status"], "archived")
        self.assertTrue(r["archive_verified"])
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["blockers"], ["pi_real_capture_pending"])
        self.assertIs(r["submission_ready"], False)
        self.assertEqual(validate_archive(r), [])

    def test_evaluate_missing_files_is_incomplete(self):
        r = evaluate_archive(**dict(BASE, copied=17, missing=["README.md"]))
        self.assertEqual(r["status"], "incomplete")
        self.assertFalse(r["archive_verified"])
        self.assertTrue(any("missing" in p for p in r["problems"]))
        self.assertEqual(validate_archive(r), [])

    def test_evaluate_unverified_export_is_mismatch(self):
        r = evaluate_archive(**dict(BASE, verify_verified=False))
        self.assertEqual(r["status"], "mismatch")
        self.assertTrue(any("re-verification" in p for p in r["problems"]))

    def test_evaluate_final_package_mismatch_is_detected(self):
        r = evaluate_archive(**dict(BASE, final_inventory_present=17))
        self.assertEqual(r["status"], "mismatch")
        self.assertTrue(any("inventory_present" in p for p in r["problems"]))
        r2 = evaluate_archive(**dict(BASE, final_export_total_bytes=1))
        self.assertTrue(any("export_total_bytes" in p for p in r2["problems"]))

    def test_evaluate_selected_video_problems_are_detected(self):
        r = evaluate_archive(**dict(BASE, selected_copied=False))
        self.assertTrue(any("not copied" in p for p in r["problems"]))
        r2 = evaluate_archive(**dict(BASE, selected_size_in_archive=999))
        self.assertTrue(any("selected_size_in_archive" in p for p in r2["problems"]))

    def test_build_archive_creates_persistent_verified_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            r = build_archive(out)
            self.assertEqual(r["status"], "archived", r["problems"])
            self.assertTrue(r["archive_verified"])
            self.assertEqual((r["copied"], r["total"]), (18, 18))
            self.assertEqual(r["selected_video"], FALLBACK_VIDEO)
            self.assertTrue((out / "package-manifest.json").is_file())
            copied_video = out / FALLBACK_VIDEO
            self.assertTrue(copied_video.is_file())
            self.assertEqual(
                hashlib.sha256(copied_video.read_bytes()).hexdigest(),
                r["selected_sha256"])
            self.assertEqual(validate_archive(r), [])

    def test_build_archive_verify_reads_existing_archive_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_archive(out)
            before = {
                p.relative_to(out): p.stat().st_mtime_ns
                for p in out.rglob("*") if p.is_file()
            }
            r = build_archive_verify(out)
            self.assertEqual(r["mode"], "verify")
            self.assertEqual(r["status"], "archived", r["problems"])
            after = {
                p.relative_to(out): p.stat().st_mtime_ns
                for p in out.rglob("*") if p.is_file()
            }
            self.assertEqual(before, after)
            self.assertEqual(validate_archive(r), [])

    def test_build_archive_verify_detects_tampered_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_archive(out)
            target = out / "README.md"
            target.write_bytes(target.read_bytes() + b"tamper")
            r = build_archive_verify(out)
            self.assertNotEqual(r["status"], "archived")
            self.assertFalse(r["archive_verified"])
            self.assertTrue(r["problems"])

    def test_build_archive_verify_missing_manifest_is_not_archived(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = build_archive_verify(Path(tmp) / "nope")
            self.assertFalse(r["archive_verified"])
            self.assertNotEqual(r["status"], "archived")
            self.assertIs(r["submission_ready"], False)

    def test_validate_detects_tampering(self):
        r = evaluate_archive(**BASE)
        bad_ready = dict(r, submission_ready=True)
        self.assertTrue(any("submission_ready" in p for p in validate_archive(bad_ready)))
        bad_status = dict(r, status="mismatch")
        self.assertTrue(any("status" in p for p in validate_archive(bad_status)))
        bad_honesty = dict(r, honesty=["아카이브는 staging 디렉터리로 파일을 복사할 뿐 실제로 제출하지 않는다"])
        self.assertTrue(any("honesty" in p for p in validate_archive(bad_honesty)))

    def test_text_report_marks_not_ready_and_honesty(self):
        text = format_text_report(evaluate_archive(**BASE))
        self.assertIn("STATUS: archived", text)
        self.assertIn(f"SELECTED_VIDEO: {FALLBACK_VIDEO}", text)
        self.assertIn("SUBMISSION_READY: false", text)
        self.assertIn("실제로 제출하지 않는다", text)
        self.assertIn("Pi 실촬영 검증 전", text)

    def test_cli_export_verify_and_argument_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "pkg")
            proc = subprocess.run(
                [sys.executable, "-m", "qa.package_archive", "--out-dir", out],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("STATUS: archived", proc.stdout)
            proc = subprocess.run(
                [sys.executable, "-m", "qa.package_archive",
                 "--verify-dir", out, "--json"],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["mode"], "verify")
            self.assertTrue(report["archive_verified"])
            proc = subprocess.run(
                [sys.executable, "-m", "qa.package_archive"],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            proc = subprocess.run(
                [sys.executable, "-m", "qa.package_archive",
                 "--out-dir", out, "--verify-dir", out],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
