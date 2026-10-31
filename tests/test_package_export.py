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
    validate_export,
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


if __name__ == "__main__":
    unittest.main()
