import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from qa.sam_live_evidence import (
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
        book = ledger[bin_id].book_qty
        qty = counted[bin_id]
        diff = qty - book
        verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
        sha = hashlib.sha256(f"fake-evidence-{bin_id}".encode()).hexdigest()
        bins.append({"bin_id": bin_id, "book_qty": book, "counted_qty": qty,
                     "diff": diff, "verdict": verdict, "image_sha256": sha})
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
        "image_source": "synthetic probe photo, 6 distinct crops",
        "report": {
            "status": "passed",
            "attempted": True,
            "ready_for_live_call": True,
            "blockers": [],
            "session_id": "SAM-PERBIN-TEST",
            "source": "sam",
            "distinct_image_count": 6,
            "bins": bins,
            "summary": summary,
            "error_type": None,
            "honesty": ["빈별 사진은 가상 사진의 서로 다른 잘라내기이며 실제 빈 촬영이나 Pi 실촬영이 아니다"],
        },
    }


class SamLiveEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        self.assertEqual(validate_evidence(make_evidence()), [])

    def test_build_report_valid_and_not_ready(self):
        report = build_report(make_evidence())
        self.assertTrue(report["valid"])
        self.assertEqual(report["problems"], [])
        self.assertFalse(report["submission_ready"])
        self.assertEqual(report["source"], "sam")
        self.assertEqual(validate_report(report), [])

    def test_duplicate_hash_detected(self):
        ev = make_evidence()
        ev["report"]["bins"][1]["image_sha256"] = ev["report"]["bins"][0]["image_sha256"]
        problems = validate_evidence(ev)
        self.assertTrue(any("distinct" in p for p in problems))

    def test_summary_tamper_detected(self):
        ev = make_evidence()
        ev["report"]["summary"]["net_diff"] += 1
        problems = validate_evidence(ev)
        self.assertTrue(any("summary" in p for p in problems))

    def test_diff_and_verdict_tamper_detected(self):
        ev = make_evidence()
        ev["report"]["bins"][0]["diff"] += 1
        problems = validate_evidence(ev)
        self.assertTrue(any("diff" in p or "verdict" in p for p in problems))

    def test_mock_source_and_blocked_status_detected(self):
        ev = make_evidence()
        ev["report"]["source"] = "mock"
        ev["report"]["status"] = "blocked"
        problems = validate_evidence(ev)
        self.assertTrue(any("source" in p for p in problems))
        self.assertTrue(any("status" in p for p in problems))

    def test_wrong_endpoint_and_bridge_detected(self):
        ev = make_evidence()
        ev["endpoint"] = "https://example.invalid/v1/responses"
        ev["bridge"] = "unknown"
        problems = validate_evidence(ev)
        self.assertTrue(any("endpoint" in p for p in problems))
        self.assertTrue(any("bridge" in p for p in problems))

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
            out2 = io.StringIO()
            with redirect_stdout(out2):
                code2 = main(["--file", path, "--json"])
            self.assertEqual(code2, 0)
            self.assertTrue(json.loads(out2.getvalue())["valid"])
            self.assertEqual(main(["--file", os.path.join(tmp, "nope.json")]), 2)

    def test_text_report_honesty(self):
        text = format_text_report(build_report(make_evidence()))
        self.assertIn("SUBMISSION_READY: false", text)
        self.assertIn("Pi 실촬영이 아니다", text)


if __name__ == "__main__":
    unittest.main()
