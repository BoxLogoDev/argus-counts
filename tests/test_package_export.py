"""qa.package_export(제출 패키지 내보내기 하네스) 테스트."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qa.package_export import (
    MANIFEST_NAME,
    build_export,
    build_export_text,
    build_verify_text,
    validate_export,
    verify_export_dir,
)
from qa.submission_inventory import DELIVERABLES

ROOT = Path(__file__).resolve().parent.parent


class TestBuildExport(unittest.TestCase):
    def test_real_root_copies_all_18_with_matching_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            export = build_export(out, ROOT)
            self.assertEqual(export["total_files"], 18)
            self.assertEqual(export["copied_files"], 18)
            self.assertEqual(export["missing"], [])
            total = 0
            for entry in export["files"]:
                self.assertTrue(entry["copied"])
                copied = out / entry["path"]
                data = copied.read_bytes()
                self.assertEqual(entry["size_bytes"], len(data))
                self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(
                    entry["sha256"],
                    hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest(),
                )
                total += len(data)
            self.assertEqual(export["total_bytes"], total)
            self.assertEqual(validate_export(export, out, ROOT), [])

    def test_manifest_written_and_not_self_referential(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            export = build_export(out, ROOT)
            manifest = out / MANIFEST_NAME
            self.assertTrue(manifest.is_file())
            data = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(data["total_files"], 18)
            paths = [f["path"] for f in export["files"]]
            self.assertEqual(paths, [p for _, p in DELIVERABLES])
            self.assertNotIn(MANIFEST_NAME, paths)

    def test_blockers_and_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            export = build_export(Path(tmp) / "pkg", ROOT)
            self.assertEqual(
                [b["id"] for b in export["blockers"]], ["pi_real_capture_pending"]
            )
            self.assertIs(export["submission_ready"], False)

    def test_honesty_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            export = build_export(Path(tmp) / "pkg", ROOT)
            joined = " ".join(export["honesty"])
            self.assertIn("실제로 제출하지 않는다", joined)
            self.assertIn("Pi 실촬영 검증 전", joined)
            self.assertIn("데모 기준", joined)

    def test_missing_source_files_are_reported_not_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty"
            empty.mkdir()
            out = Path(tmp) / "pkg"
            export = build_export(out, empty)
            self.assertEqual(export["copied_files"], 0)
            self.assertEqual(len(export["missing"]), 18)
            self.assertEqual(export["total_bytes"], 0)
            for entry in export["files"]:
                self.assertFalse(entry["copied"])
            self.assertEqual(validate_export(export, out, empty), [])


class TestValidateExport(unittest.TestCase):
    def test_detects_copied_file_tamper_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            export = build_export(out, ROOT)
            (out / "README.md").write_bytes(b"tampered")
            problems = validate_export(export, out, ROOT)
            self.assertTrue(any("README.md" in p for p in problems), problems)

    def test_detects_ready_and_totals_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            export = build_export(out, ROOT)
            export["submission_ready"] = True
            export["total_bytes"] += 1
            problems = validate_export(export, out, ROOT)
            self.assertTrue(any("submission_ready" in p for p in problems), problems)
            self.assertTrue(any("total_bytes" in p for p in problems), problems)

    def test_detects_blocker_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            export = build_export(out, ROOT)
            export["blockers"] = []
            problems = validate_export(export, out, ROOT)
            self.assertTrue(any("blocker" in p for p in problems), problems)


class TestCli(unittest.TestCase):
    def test_cli_json_exit_zero_and_text_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            proc = subprocess.run(
                [sys.executable, "-m", "qa.package_export", "--out-dir", str(out), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["copied_files"], 18)
            self.assertIs(data["submission_ready"], False)
            text = build_export_text(data)
            self.assertIn("SUBMISSION_READY: false", text)
            self.assertIn("pi_real_capture_pending", text)

    def test_cli_requires_out_dir(self):
        proc = subprocess.run(
            [sys.executable, "-m", "qa.package_export"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 2)


class TestVerifyExportDir(unittest.TestCase):
    def test_verify_passes_for_fresh_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_export(out, ROOT)
            export, problems = verify_export_dir(out, ROOT)
            self.assertIsNotNone(export)
            self.assertEqual(problems, [])
            self.assertEqual(export["copied_files"], 18)
            self.assertIs(export["submission_ready"], False)

    def test_verify_detects_copied_file_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_export(out, ROOT)
            (out / "README.md").write_bytes(b"tampered")
            export, problems = verify_export_dir(out, ROOT)
            self.assertIsNotNone(export)
            self.assertTrue(any("README.md" in p for p in problems), problems)

    def test_verify_detects_manifest_total_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_export(out, ROOT)
            manifest = out / MANIFEST_NAME
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["total_bytes"] += 1
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            export, problems = verify_export_dir(out, ROOT)
            self.assertIsNotNone(export)
            self.assertTrue(any("total_bytes" in p for p in problems), problems)

    def test_verify_missing_manifest_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            export, problems = verify_export_dir(Path(tmp) / "nope", ROOT)
            self.assertIsNone(export)
            self.assertEqual(len(problems), 1)
            self.assertIn("manifest missing", problems[0])

    def test_verify_invalid_json_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            out.mkdir()
            (out / MANIFEST_NAME).write_text("{not json", encoding="utf-8")
            export, problems = verify_export_dir(out, ROOT)
            self.assertIsNone(export)
            self.assertTrue(any("manifest unreadable" in p for p in problems), problems)

    def test_verify_moved_staging_still_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_export(out, ROOT)
            moved = Path(tmp) / "moved-pkg"
            out.rename(moved)
            export, problems = verify_export_dir(moved, ROOT)
            self.assertIsNotNone(export)
            self.assertEqual(problems, [])

    def test_verify_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_export(out, ROOT)
            before = {
                str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.rglob("*"))
                if p.is_file()
            }
            verify_export_dir(out, ROOT)
            after = {
                str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.rglob("*"))
                if p.is_file()
            }
            self.assertEqual(before, after)

    def test_cli_verify_json_and_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            build_export(out, ROOT)
            proc = subprocess.run(
                [sys.executable, "-m", "qa.package_export", "--verify-dir", str(out), "--json"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["verified"])
            self.assertEqual(payload["problems"], [])
            self.assertEqual(payload["export"]["copied_files"], 18)
            text = build_verify_text(payload["export"], [], out)
            self.assertIn("제출 패키지 재검증", text)
            self.assertIn("VERIFIED: true", text)
            self.assertIn("SUBMISSION_READY: false", text)

    def test_cli_verify_missing_manifest_exit_2_and_arg_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, "-m", "qa.package_export", "--verify-dir", str(Path(tmp) / "nope")],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 2)
            conflict = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "qa.package_export",
                    "--out-dir",
                    str(Path(tmp) / "a"),
                    "--verify-dir",
                    str(Path(tmp) / "b"),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(conflict.returncode, 2)


if __name__ == "__main__":
    unittest.main()
