"""qa.submission_inventory(제출물 인벤토리 하네스) 테스트."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from qa.submission_inventory import (
    BLOCKERS,
    DEADLINE,
    DELIVERABLES,
    REPO_URL,
    build_inventory,
    build_inventory_text,
    validate_inventory,
    write_inventory,
)

ROOT = Path(__file__).resolve().parent.parent


class TestDeliverablesShape(unittest.TestCase):
    def test_count_and_categories(self):
        self.assertEqual(len(DELIVERABLES), 18)
        categories = [c for c, _ in DELIVERABLES]
        self.assertEqual(categories.count("document"), 6)
        self.assertEqual(categories.count("video"), 2)
        self.assertEqual(categories.count("demo_asset"), 10)
        paths = [p for _, p in DELIVERABLES]
        self.assertEqual(len(set(paths)), 18)
        self.assertEqual(paths[0], "README.md")
        self.assertEqual(paths[-1], "demo/assets/captures/capture-manifest.json")

    def test_inventory_files_not_self_referential(self):
        paths = [p for _, p in DELIVERABLES]
        self.assertNotIn("demo/assets/submission-inventory.json", paths)
        self.assertNotIn("demo/assets/submission-inventory.txt", paths)


class TestBuildInventory(unittest.TestCase):
    def test_real_root_all_present_and_hashes_match(self):
        inventory = build_inventory(ROOT)
        self.assertEqual(inventory["total_files"], 18)
        self.assertEqual(inventory["present_files"], 18)
        self.assertEqual(inventory["missing"], [])
        total = 0
        for entry in inventory["deliverables"]:
            data = (ROOT / entry["path"]).read_bytes()
            self.assertTrue(entry["exists"])
            self.assertEqual(entry["size_bytes"], len(data))
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
            total += len(data)
        self.assertEqual(inventory["total_bytes"], total)

    def test_metadata_blockers_and_not_ready(self):
        inventory = build_inventory(ROOT)
        self.assertEqual(inventory["repo_url"], REPO_URL)
        self.assertEqual(
            inventory["repo_url"], "https://github.com/BoxLogoDev/argus-counts"
        )
        self.assertEqual(inventory["deadline"], DEADLINE)
        self.assertIn("2026-11-05 11:00 KST", inventory["deadline"])
        self.assertEqual(
            [b["id"] for b in inventory["blockers"]],
            [b["id"] for b in BLOCKERS],
        )
        self.assertEqual(
            [b["id"] for b in inventory["blockers"]], ["pi_real_capture_pending"]
        )
        self.assertIs(inventory["submission_ready"], False)

    def test_honesty_markers(self):
        joined = " ".join(build_inventory(ROOT)["honesty"])
        self.assertIn("실제로 제출하지 않는다", joined)
        self.assertIn("Pi 실촬영 검증 전", joined)
        self.assertIn("데모 기준", joined)
        self.assertIn("제출 가능을 뜻하지 않는다", joined)

    def test_missing_files_in_empty_root_are_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            inventory = build_inventory(Path(tmp))
            self.assertEqual(inventory["present_files"], 0)
            self.assertEqual(len(inventory["missing"]), 18)
            self.assertEqual(inventory["total_bytes"], 0)
            for entry in inventory["deliverables"]:
                self.assertFalse(entry["exists"])
                self.assertIsNone(entry["size_bytes"])
                self.assertIsNone(entry["sha256"])
            # 누락을 정직하게 적은 인벤토리 자체는 검증에서 모순이 아니다.
            self.assertEqual(validate_inventory(inventory, Path(tmp)), [])


class TestValidateInventory(unittest.TestCase):
    def test_validate_passes_on_real_inventory(self):
        self.assertEqual(validate_inventory(build_inventory(ROOT), ROOT), [])

    def test_validate_detects_sha_tamper(self):
        inventory = build_inventory(ROOT)
        inventory["deliverables"][0]["sha256"] = "0" * 64
        problems = validate_inventory(inventory, ROOT)
        self.assertTrue(any("README.md" in p and "sha256" in p for p in problems), problems)

    def test_validate_detects_totals_tamper(self):
        inventory = build_inventory(ROOT)
        inventory["total_bytes"] += 1
        problems = validate_inventory(inventory, ROOT)
        self.assertTrue(any("total_bytes" in p for p in problems), problems)

    def test_validate_detects_ready_and_blocker_tamper(self):
        inventory = build_inventory(ROOT)
        inventory["submission_ready"] = True
        inventory["blockers"] = []
        problems = validate_inventory(inventory, ROOT)
        self.assertTrue(any("submission_ready" in p for p in problems), problems)
        self.assertTrue(any("blocker" in p for p in problems), problems)


class TestWriteAndCli(unittest.TestCase):
    def test_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "inventory"
            written = write_inventory(out, ROOT)
            self.assertEqual(
                sorted(p.name for p in written),
                ["submission-inventory.json", "submission-inventory.txt"],
            )
            data = json.loads(
                (out / "submission-inventory.json").read_text(encoding="utf-8")
            )
            self.assertEqual(validate_inventory(data, ROOT), [])
            self.assertEqual(data["total_files"], 18)
            text = (out / "submission-inventory.txt").read_text(encoding="utf-8")
            self.assertIn("SUBMISSION_READY: false", text)
            self.assertIn("pi_real_capture_pending", build_inventory_text(data))

    def test_cli_json_exit_zero(self):
        proc = subprocess.run(
            [sys.executable, "-m", "qa.submission_inventory", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["total_files"], 18)
        self.assertEqual(data["present_files"], 18)
        self.assertIs(data["submission_ready"], False)


if __name__ == "__main__":
    unittest.main()
