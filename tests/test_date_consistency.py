"""qa.date_consistency 테스트 (143회차 청크 B 초안)."""
from __future__ import annotations

import datetime
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qa.date_consistency import (  # noqa: E402
    DECISION_MODULES,
    DEFAULT_BLOCKERS,
    NAIVE_PATTERNS,
    UTC_NOW_ALLOWLIST,
    build_report,
    check_decision_defaults,
    scan_naive_patterns,
    scan_utc_allowlist,
    validate_report,
)
from qa.deadline import KST  # noqa: E402


def _write_tree(files: dict[str, str]) -> tempfile.TemporaryDirectory:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    tmp.root_path = root  # type: ignore[attr-defined]
    return tmp


class DateConsistencyReportTests(unittest.TestCase):
    def test_real_root_report_is_consistent(self):
        report = build_report(ROOT)
        self.assertEqual(report["problems"], [])
        self.assertTrue(report["consistent"])
        self.assertFalse(report["submission_ready"])
        self.assertEqual(report["blockers"], DEFAULT_BLOCKERS)
        self.assertEqual(validate_report(report), [])

    def test_functional_defaults_match_kst(self):
        functional, problems = check_decision_defaults()
        expected = datetime.datetime.now(KST).date().isoformat()
        self.assertEqual(problems, [])
        self.assertEqual(functional["today_kst"], expected)
        self.assertEqual(functional["fallback_default_date"], expected)
        self.assertTrue(functional["deadline_now"].endswith("+09:00"))

    def test_scanned_files_cover_decision_modules(self):
        report = build_report(ROOT)
        self.assertGreater(report["scanned_files"], 30)
        for rel in DECISION_MODULES:
            self.assertTrue((ROOT / rel).is_file(), rel)


class DateConsistencyScanTests(unittest.TestCase):
    def test_naive_pattern_detected_in_temp_tree(self):
        bad_line = "value = datetime.date." + "today()\n"
        with _write_tree({"qa/sample.py": bad_line}) as tmp:
            problems = scan_naive_patterns(Path(tmp))
        self.assertEqual(len(problems), 1)
        self.assertIn("qa/sample.py:1", problems[0])
        self.assertIn("today_call", problems[0])

    def test_now_without_tz_detected_in_temp_tree(self):
        bad_line = "value = datetime.datetime." + "now()\n"
        with _write_tree({"qa/sample.py": bad_line}) as tmp:
            problems = scan_naive_patterns(Path(tmp))
        self.assertTrue(any("now_without_tz" in p for p in problems))

    def test_tests_directory_is_excluded(self):
        bad_line = "value = datetime.date." + "today()\n"
        with _write_tree({"tests/test_sample.py": bad_line}) as tmp:
            problems = scan_naive_patterns(Path(tmp))
        self.assertEqual(problems, [])

    def test_utc_now_outside_allowlist_detected(self):
        line = "value = datetime." + "now(timezone.utc)\n"
        with _write_tree({"qa/other.py": line}) as tmp:
            problems = scan_utc_allowlist(Path(tmp))
        self.assertTrue(any("outside allowlist" in p for p in problems))

    def test_utc_allowlist_counts_match_real_root(self):
        self.assertEqual(scan_utc_allowlist(ROOT), [])
        total = sum(UTC_NOW_ALLOWLIST.values())
        self.assertEqual(total, 7)

    def test_validate_rejects_inconsistent_report(self):
        report = build_report(ROOT)
        report["consistent"] = False
        problems = validate_report(report)
        self.assertTrue(any("consistent" in p for p in problems))


class DateConsistencyCliTests(unittest.TestCase):
    def test_cli_text_and_json(self):
        text = subprocess.run(
            [sys.executable, "-m", "qa.date_consistency"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(text.returncode, 0, text.stdout + text.stderr)
        self.assertIn("CONSISTENT: true", text.stdout)
        self.assertIn("SUBMISSION_READY: false", text.stdout)
        js = subprocess.run(
            [sys.executable, "-m", "qa.date_consistency", "--json"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(js.returncode, 0, js.stdout + js.stderr)
        self.assertIn('"consistent": true', js.stdout)

    def test_naive_patterns_do_not_match_module_source(self):
        source = (ROOT / "qa" / "date_consistency.py").read_text(encoding="utf-8")
        for name, pattern in NAIVE_PATTERNS:
            self.assertIsNone(re.search(pattern, source), name)


if __name__ == "__main__":
    unittest.main()
