import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from qa.sam_photo_evidence import (
    EXPECTED_ENDPOINT,
    build_report,
    format_text_report,
    main,
    validate_evidence,
    validate_report,
)
from terminal.demo_data import demo_bin_ids, demo_ledger


def make_evidence():
    ledger = demo_ledger()
    counted = {"A-01-01": 9, "A-01-02": 3, "A-02-02": 7,
               "A-03-01": 5, "B-01-02": 6, "B-02-02": 11}
    bins = []
    for bin_id in demo_bin_ids():
        entry = ledger[bin_id]
        qty = counted[bin_id]
        diff = qty - entry.book_qty
        verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
        bins.append({
            "bin_id": bin_id,
            "item_code": entry.item_code,
            "book_qty": entry.book_qty,
            "counted_qty": qty,
            "diff": diff,
            "verdict": verdict,
            "photo": {
                "image_ref": f"{bin_id}.jpg",
                "size_bytes": 1000 + len(bin_id),
                "sha256": hashlib.sha256(
                    f"fake-photo-evidence-{bin_id}".encode()).hexdigest(),
                "suffix": ".jpg",
            },
        })
    matched = sum(1 for b in bins if b["diff"] == 0)
    summary = {
        "counted_bins": len(bins),
        "matched": matched,
        "mismatched": len(bins) - matched,
        "match_rate": matched / len(bins),
        "abs_diff_total": sum(abs(b["diff"]) for b in bins),
        "net_diff": sum(b["diff"] for b in bins),
    }
    return {
        "bridge": "custom.meta-model-api connector transport (surrogate)",
        "endpoint": EXPECTED_ENDPOINT,
        "path": "terminal.photo_intake.run_photo_intake with injected LiveSamCounter",
        "image_source": "synthetic probe photo, 6 distinct crops",
        "report": {
            "session_id": "PHOTO-LIVE-TEST",
            "generated_at": "2026-11-02T00:00:00+00:00",
            "source": "sam",
            "capture_source": "file",
            "honesty": ["파일 기반 입력이며 Pi 실촬영이 아닙니다"],
            "bins": bins,
            "summary": summary,
        },
    }


class SamPhotoEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        self.assertEqual(validate_evidence(make_evidence()), [])

    def test_build_report_valid_and_not_ready(self):
        report = build_report(make_evidence())
        self.assertTrue(report["valid"])
        self.assertEqual(report["problems"], [])
        self.assertFalse(report["submission_ready"])
        self.assertEqual(report["source"], "sam")
        self.assertEqual(report["capture_source"], "file")
        self.assertEqual(report["distinct_image_count"], 6)
        self.assertEqual(validate_report(report), [])

    def test_mock_source_and_wrong_capture_source_detected(self):
        ev = make_evidence()
        ev["report"]["source"] = "mock"
        ev["report"]["capture_source"] = "pi-camera"
        problems = validate_evidence(ev)
        self.assertTrue(any("source" in p for p in problems))
        self.assertTrue(any("capture_source" in p for p in problems))

    def test_wrong_path_and_endpoint_detected(self):
        ev = make_evidence()
        ev["path"] = "qa.sam_session.run_sam_session"
        ev["endpoint"] = "https://example.invalid/v1/responses"
        problems = validate_evidence(ev)
        self.assertTrue(any("path" in p for p in problems))
        self.assertTrue(any("endpoint" in p for p in problems))

    def test_duplicate_photo_hash_detected(self):
        ev = make_evidence()
        ev["report"]["bins"][1]["photo"]["sha256"] = (
            ev["report"]["bins"][0]["photo"]["sha256"])
        problems = validate_evidence(ev)
        self.assertTrue(any("distinct" in p for p in problems))

    def test_photo_fields_detected(self):
        ev = make_evidence()
        ev["report"]["bins"][0]["photo"]["size_bytes"] = 0
        ev["report"]["bins"][0]["photo"]["suffix"] = ".gif"
        ev["report"]["bins"][0]["photo"]["image_ref"] = "other.gif"
        problems = validate_evidence(ev)
        self.assertTrue(any("size_bytes" in p for p in problems))
        self.assertTrue(any("suffix" in p for p in problems))

    def test_image_ref_mismatch_detected(self):
        ev = make_evidence()
        ev["report"]["bins"][2]["photo"]["image_ref"] = "A-01-01.jpg"
        problems = validate_evidence(ev)
        self.assertTrue(any("image_ref" in p for p in problems))

    def test_summary_and_ledger_tamper_detected(self):
        ev = make_evidence()
        ev["report"]["summary"]["net_diff"] += 1
        problems = validate_evidence(ev)
        self.assertTrue(any("summary" in p for p in problems))
        ev2 = make_evidence()
        ev2["report"]["bins"][0]["book_qty"] += 1
        problems2 = validate_evidence(ev2)
        self.assertTrue(any("book_qty" in p or "diff" in p for p in problems2))
        ev3 = make_evidence()
        ev3["report"]["bins"][0]["item_code"] = "XXX-000"
        problems3 = validate_evidence(ev3)
        self.assertTrue(any("item_code" in p for p in problems3))

    def test_cli_file_roundtrip_and_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "evidence.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(make_evidence(), handle)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--file", path])
            self.assertEqual(code, 0)
            self.assertIn("VALID: true", out.getvalue())
            self.assertIn("CAPTURE_SOURCE: file", out.getvalue())
            out2 = io.StringIO()
            with redirect_stdout(out2):
                code2 = main(["--file", path, "--json"])
            self.assertEqual(code2, 0)
            parsed = json.loads(out2.getvalue())
            self.assertTrue(parsed["valid"])
            self.assertEqual(parsed["distinct_image_count"], 6)
            self.assertEqual(main(["--file", os.path.join(tmp, "nope.json")]), 2)

    def test_text_report_honesty(self):
        text = format_text_report(build_report(make_evidence()))
        self.assertIn("SUBMISSION_READY: false", text)
        self.assertIn("Pi 실촬영이 아니다", text)


if __name__ == "__main__":
    unittest.main()
