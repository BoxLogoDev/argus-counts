import json
import tempfile
import unittest
from pathlib import Path

from demo.capture import (
    CAPTURE_SPECS,
    HONESTY,
    build_manifest,
    capture_assets,
    fetch_captures,
    validate_manifest,
)


class CaptureSpecTests(unittest.TestCase):
    def test_specs_count_and_unique(self):
        self.assertEqual(len(CAPTURE_SPECS), 4)
        self.assertEqual(len({s.name for s in CAPTURE_SPECS}), 4)
        self.assertEqual(len({s.filename for s in CAPTURE_SPECS}), 4)

    def test_specs_paths_and_kinds(self):
        for spec in CAPTURE_SPECS:
            self.assertTrue(spec.path.startswith("/"))
            self.assertIn(spec.kind, ("html", "json"))
            self.assertTrue(spec.markers)
            self.assertTrue(spec.cut_ref)
            self.assertTrue(spec.purpose)

    def test_honesty_notes(self):
        self.assertTrue(any("PNG" in note for note in HONESTY))
        self.assertTrue(any("모의" in note for note in HONESTY))
        self.assertTrue(any("데모 기준" in note for note in HONESTY))


class CaptureFetchTests(unittest.TestCase):
    def test_fetch_all_200_and_markers(self):
        results = fetch_captures()
        self.assertEqual(len(results), 4)
        for _spec, status, text in results:
            self.assertEqual(status, 200)
            self.assertTrue(text)

    def test_manifest_all_ok(self):
        manifest = build_manifest(fetch_captures())
        self.assertEqual(manifest["capture_count"], 4)
        self.assertTrue(manifest["all_ok"])
        self.assertEqual(validate_manifest(manifest), [])

    def test_api_report_is_mock_json(self):
        results = {spec.name: text for spec, _s, text in fetch_captures()}
        payload = json.loads(results["api-report"])
        self.assertEqual(payload["source"], "mock")
        self.assertEqual(payload["summary"]["matched"], 4)


class CaptureAssetsTests(unittest.TestCase):
    def test_capture_assets_writes_files_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = capture_assets(tmp)
            out = Path(tmp)
            for spec in CAPTURE_SPECS:
                self.assertTrue((out / spec.filename).is_file())
            manifest_path = out / "capture-manifest.json"
            self.assertTrue(manifest_path.is_file())
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertTrue(saved["all_ok"])
            self.assertEqual(saved["capture_count"], 4)
            self.assertTrue(manifest["all_ok"])

    def test_validate_detects_bad_status(self):
        manifest = build_manifest(fetch_captures())
        manifest["captures"][0]["status"] = 500
        manifest["all_ok"] = False
        problems = validate_manifest(manifest)
        self.assertTrue(any("500" in p for p in problems))

    def test_validate_detects_missing_marker(self):
        manifest = build_manifest(fetch_captures())
        first = manifest["captures"][0]
        key = next(iter(first["markers_found"]))
        first["markers_found"][key] = False
        first["all_markers_found"] = False
        manifest["all_ok"] = False
        problems = validate_manifest(manifest)
        self.assertTrue(any("마커" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
