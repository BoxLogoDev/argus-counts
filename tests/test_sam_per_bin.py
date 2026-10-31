import hashlib
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from qa.sam_per_bin import build_report, format_text_report, main, run_sam_per_bin
from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids
from terminal.models import CountResult
from terminal.sam_adapter import SamCountingError

SENTINEL = "SECRET-SENTINEL-PERBIN"
READY_ENV = {"SAM_API_BASE_URL": f"https://{SENTINEL}.example.invalid", "SAM_API_KEY": SENTINEL}


def make_refs(testcase):
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    refs = {}
    for bin_id in demo_bin_ids():
        path = os.path.join(tmp.name, f"{bin_id}.jpg")
        with open(path, "wb") as handle:
            handle.write(f"fake-per-bin-photo-{bin_id}".encode())
        refs[bin_id] = path
    return refs


def sha_of(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


class FakeCounter:
    source = "sam"

    def __init__(self, counts=None):
        self.counts = dict(counts) if counts is not None else dict(DEMO_COUNTED_QTY)
        self.calls = []

    def count(self, bin_id, image_ref=None):
        self.calls.append((bin_id, image_ref))
        return CountResult(bin_id=bin_id, counted_qty=self.counts[bin_id], source="sam")


class MockSourceCounter:
    source = "mock"

    def count(self, bin_id, image_ref=None):
        return CountResult(bin_id=bin_id, counted_qty=5, source="mock")


class RaisingCounter:
    source = "sam"

    def count(self, bin_id, image_ref=None):
        raise SamCountingError("fake failure")


class LeakyCounter:
    source = "sam"

    def count(self, bin_id, image_ref=None):
        raise RuntimeError(f"boom {SENTINEL}")


class SamPerBinTests(unittest.TestCase):
    def test_blocked_when_not_ready_and_counter_not_called(self):
        counter = FakeCounter()
        report = run_sam_per_bin(env={}, credit_confirmed=False,
                                 image_refs=make_refs(self), counter=counter)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["attempted"])
        self.assertEqual(counter.calls, [])
        self.assertEqual(report["distinct_image_count"], 0)
        self.assertEqual(
            [b["id"] for b in report["blockers"]],
            ["sam_credit_not_confirmed", "sam_base_url_missing", "sam_api_key_missing"],
        )

    def test_passed_with_distinct_images_and_hashes(self):
        refs = make_refs(self)
        counter = FakeCounter()
        report = run_sam_per_bin(env=READY_ENV, credit_confirmed=True,
                                 image_refs=refs, counter=counter, session_id="SAM-PB-TEST")
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["attempted"])
        self.assertEqual(report["source"], "sam")
        self.assertEqual(report["distinct_image_count"], 6)
        self.assertEqual([c[0] for c in counter.calls], demo_bin_ids())
        self.assertEqual(dict(counter.calls), refs)
        by_bin = {b["bin_id"]: b for b in report["bins"]}
        for bin_id in demo_bin_ids():
            self.assertEqual(by_bin[bin_id]["image_sha256"], sha_of(refs[bin_id]))
        self.assertEqual(by_bin["A-01-02"]["diff"], -3)
        self.assertEqual(by_bin["A-01-02"]["verdict"], "short")
        self.assertEqual(by_bin["B-01-02"]["diff"], 3)
        summary = report["summary"]
        self.assertEqual(summary["matched"], 4)
        self.assertEqual(summary["mismatched"], 2)
        self.assertEqual(summary["abs_diff_total"], 6)
        self.assertEqual(summary["net_diff"], 0)

    def test_missing_image_fails_without_calling(self):
        refs = make_refs(self)
        del refs["B-02-02"]
        counter = FakeCounter()
        report = run_sam_per_bin(env=READY_ENV, credit_confirmed=True,
                                 image_refs=refs, counter=counter)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "missing_image")
        self.assertFalse(report["attempted"])
        self.assertEqual(counter.calls, [])

    def test_missing_file_fails_without_calling(self):
        refs = make_refs(self)
        refs["A-01-01"] = os.path.join(os.path.dirname(refs["A-01-01"]), "nope.jpg")
        counter = FakeCounter()
        report = run_sam_per_bin(env=READY_ENV, credit_confirmed=True,
                                 image_refs=refs, counter=counter)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "image_file_missing")
        self.assertEqual(counter.calls, [])

    def test_duplicate_image_fails_without_calling(self):
        refs = make_refs(self)
        refs["B-01-02"] = refs["A-01-02"]
        counter = FakeCounter()
        report = run_sam_per_bin(env=READY_ENV, credit_confirmed=True,
                                 image_refs=refs, counter=counter)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "duplicate_image")
        self.assertFalse(report["attempted"])
        self.assertEqual(counter.calls, [])

    def test_mock_source_fails_whole_session(self):
        report = run_sam_per_bin(env=READY_ENV, credit_confirmed=True,
                                 image_refs=make_refs(self), counter=MockSourceCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "unexpected_source")
        self.assertIsNone(report["summary"])

    def test_sam_error_fails_without_mock_fallback(self):
        report = run_sam_per_bin(env=READY_ENV, credit_confirmed=True,
                                 image_refs=make_refs(self), counter=RaisingCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "SamCountingError")
        self.assertIsNone(report["summary"])

    def test_generic_error_does_not_leak_values(self):
        report = run_sam_per_bin(env=READY_ENV, credit_confirmed=True,
                                 image_refs=make_refs(self), counter=LeakyCounter())
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["error_type"], "RuntimeError")
        blob = json.dumps(report, ensure_ascii=False) + format_text_report(report)
        self.assertNotIn(SENTINEL, blob)

    def test_text_report_and_honesty(self):
        report = run_sam_per_bin(env={}, credit_confirmed=False)
        text = format_text_report(report)
        self.assertIn("STATUS: blocked", text)
        self.assertIn("DISTINCT_IMAGES: 0", text)
        self.assertIn("SESSION_PASSED: false", text)
        joined = " ".join(report["honesty"])
        self.assertIn("서로 다른 사진", joined)
        self.assertIn("Pi 실촬영이 아니다", joined)

    def test_main_blocked_exit_one_and_json(self):
        with patch.dict(os.environ, {}, clear=True):
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--json"])
        self.assertEqual(code, 1)
        parsed = json.loads(out.getvalue())
        self.assertEqual(parsed["status"], "blocked")
        self.assertEqual(parsed["distinct_image_count"], 0)
        self.assertIsNone(parsed["summary"])
        # build_report alias도 같은 계약을 지켜야 한다.
        alias = build_report(env={}, credit_confirmed=False)
        self.assertEqual(alias["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
