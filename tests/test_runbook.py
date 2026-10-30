"""제출 런북(docs/submission-runbook.md) 테스트."""
from __future__ import annotations

import unittest
from pathlib import Path

from qa.claims_audit import audit_text
from qa.standalone import REQUIRED_FILES

ROOT = Path(__file__).resolve().parent.parent
RUNBOOK = ROOT / "docs" / "submission-runbook.md"

SECTION_HEADERS = [
    "## 0. 현재 상태",
    "## 1. 크레딧 확인",
    "## 2. API 키",
    "## 3. SAM 전환",
    "## 4. Pi 촬영",
    "## 5. 최종 점검",
    "## 6. 제출",
]


def _text() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


class RunbookTests(unittest.TestCase):
    def test_runbook_exists(self):
        self.assertTrue(RUNBOOK.is_file())

    def test_sections_in_order(self):
        text = _text()
        positions = [text.index(header) for header in SECTION_HEADERS]
        self.assertEqual(positions, sorted(positions))

    def test_blockers_and_not_ready_stated(self):
        text = _text()
        self.assertIn("pi_real_capture_pending", text)
        self.assertNotIn("sam_real_call_pending", text)
        self.assertIn("SUBMISSION_READY: false", text)

    def test_credit_and_key_steps(self):
        text = _text()
        self.assertIn("2026-10-29 09:30", text)
        self.assertIn("python3 -m qa.sam_readiness", text)
        self.assertIn("--credit-confirmed", text)
        self.assertIn("Secure Vault", text)
        self.assertIn("SAM_API_BASE_URL", text)
        self.assertIn("SAM_API_KEY", text)

    def test_pi_and_final_check_commands(self):
        text = _text()
        self.assertIn("python3 -m terminal.pi_capture --probe", text)
        self.assertIn("python3 -m terminal.pi_session --out-dir", text)
        self.assertIn("python3 -m unittest discover -s tests", text)
        self.assertIn("python3 -m qa.pre_submission", text)
        self.assertIn("python3 -m demo.render_video", text)
        self.assertIn("verify_argus.py --doctor", text)

    def test_deadline_both_timezones(self):
        text = _text()
        self.assertIn("2026-11-04 21:00", text)
        self.assertIn("2026-11-05 11:00", text)
        self.assertIn("BoxLogoDev/argus-counts", text)

    def test_honesty_markers_present(self):
        text = _text()
        for marker in ("모의", "검증 전", "단일 빈 스모크"):
            self.assertIn(marker, text)

    def test_claims_audit_clean_on_runbook(self):
        violations = audit_text("docs/submission-runbook.md", _text())
        self.assertEqual(violations, [])

    def test_required_by_standalone_and_no_forbidden_phrase(self):
        self.assertIn("docs/submission-runbook.md", REQUIRED_FILES)
        self.assertNotIn("코드 " + "참고", _text())


if __name__ == "__main__":
    unittest.main()
