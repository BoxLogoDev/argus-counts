"""demo.fallback(파일 입력 폴백 데모 자산) 테스트."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from demo.fallback import (
    CUT_INDEX,
    DECISION_DATE,
    FALLBACK_SESSION_ID,
    build_fallback_manifest,
    build_fallback_text,
    fake_photo_bytes,
    validate_fallback,
    write_fallback,
)


class TestFallbackManifest(unittest.TestCase):
    def test_cut_and_flags(self):
        manifest = build_fallback_manifest()
        self.assertEqual(manifest["cut_index"], CUT_INDEX)
        self.assertEqual(manifest["cut_index"], 3)
        self.assertEqual(manifest["replaces"], "pi-placeholder")
        self.assertEqual(manifest["decision_date"], DECISION_DATE)
        self.assertEqual(manifest["decision_date"], "2026-11-02")
        self.assertIs(manifest["is_pi_real_capture"], False)
        self.assertEqual(manifest["session_id"], FALLBACK_SESSION_ID)

    def test_summary_matches_demo_basis(self):
        summary = build_fallback_manifest()["summary"]
        self.assertEqual(summary["counted_bins"], 6)
        self.assertEqual(summary["matched"], 4)
        self.assertEqual(summary["mismatched"], 2)
        self.assertEqual(summary["abs_diff_total"], 6)
        self.assertEqual(summary["net_diff"], 0)

    def test_capture_source_file_and_source_mock(self):
        manifest = build_fallback_manifest()
        self.assertEqual(manifest["capture_source"], "file")
        self.assertEqual(manifest["source"], "mock")

    def test_bins_photo_sha_matches_fake_bytes(self):
        manifest = build_fallback_manifest()
        self.assertEqual(len(manifest["bins"]), 6)
        for entry in manifest["bins"]:
            expected = hashlib.sha256(fake_photo_bytes(entry["bin_id"])).hexdigest()
            self.assertEqual(entry["photo"]["sha256"], expected)
        a0102 = [b for b in manifest["bins"] if b["bin_id"] == "A-01-02"][0]
        self.assertEqual(a0102["verdict"], "short")
        self.assertEqual(a0102["diff"], -3)
        self.assertEqual(a0102["book_qty"], 8)
        self.assertEqual(a0102["counted_qty"], 5)

    def test_honesty_markers(self):
        manifest = build_fallback_manifest()
        joined = " ".join(manifest["honesty"])
        self.assertIn("Pi 실촬영이 아닙니다", joined)
        self.assertIn("Pi 실촬영 검증 전", joined)
        self.assertIn("SAM 실호출 미실시", joined)
        self.assertIn("데모 기준", joined)


class TestValidateFallback(unittest.TestCase):
    def test_validate_passes_on_real_manifest(self):
        self.assertEqual(validate_fallback(build_fallback_manifest()), [])

    def test_validate_detects_pi_real_capture_tamper(self):
        manifest = build_fallback_manifest()
        manifest["is_pi_real_capture"] = True
        problems = validate_fallback(manifest)
        self.assertTrue(any("is_pi_real_capture" in p for p in problems), problems)

    def test_validate_detects_capture_source_tamper(self):
        manifest = build_fallback_manifest()
        manifest["capture_source"] = "pi-camera"
        problems = validate_fallback(manifest)
        self.assertTrue(any("capture_source" in p for p in problems), problems)


class TestWriteFallback(unittest.TestCase):
    def test_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "assets"
            written = write_fallback(out)
            self.assertEqual(sorted(p.name for p in written), ["fallback.json", "fallback.txt"])
            data = json.loads((out / "fallback.json").read_text(encoding="utf-8"))
            self.assertEqual(data["cut_index"], 3)
            self.assertIs(data["is_pi_real_capture"], False)
            self.assertEqual(data["summary"]["matched"], 4)
            text = (out / "fallback.txt").read_text(encoding="utf-8")
            self.assertIn("파일 입력 폴백", text)
            self.assertIn("데모 기준", build_fallback_text(data))


if __name__ == "__main__":
    unittest.main()
