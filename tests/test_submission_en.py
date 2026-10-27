"""영문 제출 요약(docs/submission-summary-en.md) 테스트."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "submission-summary-en.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


class SubmissionSummaryEnTests(unittest.TestCase):
    def test_file_exists_with_argus_title(self):
        self.assertTrue(DOC.is_file())
        self.assertTrue(_text().startswith("# Argus"))

    def test_theme_line_is_tentative(self):
        text = _text()
        self.assertIn("Build for Your World", text)
        self.assertIn("tentative", text)

    def test_workflow_has_four_steps(self):
        text = _text()
        for step in ("Capture", "SAM counting", "Ledger reconciliation", "Discrepancy report"):
            self.assertIn(step, text)
        for verdict in ("match", "short", "over"):
            self.assertIn(verdict, text)

    def test_mock_honesty_statements(self):
        text = _text()
        self.assertIn("mock", text)
        self.assertIn("has NOT been made yet", text)
        self.assertIn("never claimed as live", text)

    def test_pi_not_yet_verified(self):
        text = _text()
        self.assertIn("Pi", text)
        self.assertIn("not yet verified", text)

    def test_adapter_switch_env_vars(self):
        text = _text()
        self.assertIn("SAM_API_BASE_URL", text)
        self.assertIn("SAM_API_KEY", text)

    def test_demo_numbers(self):
        text = _text()
        self.assertIn("fictional demo data", text)
        self.assertIn("A-01-02", text)
        self.assertIn("B-01-02", text)
        self.assertIn("66.7%", text)
        self.assertIn("Total absolute delta is 6", text)
        self.assertIn("Net delta is 0", text)

    def test_impact_line_starts_with_demo_basis(self):
        lines = [ln for ln in _text().splitlines() if ln.startswith("Demo basis:")]
        self.assertEqual(len(lines), 1)
        self.assertIn("2 mismatches out of 6 bins", lines[0])
        self.assertIn("action priorities", lines[0])

    def test_built_vs_existing_split(self):
        text = _text()
        self.assertIn("Already existed", text)
        self.assertIn("Built for this hackathon", text)
        self.assertIn("2026-10-27", text)
        self.assertIn("17 baseline checks", text)


if __name__ == "__main__":
    unittest.main()
