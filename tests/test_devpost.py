"""제출 문안 패키지(docs/devpost-submission.md) 테스트."""
from __future__ import annotations

import unittest
from pathlib import Path

from qa.claims_audit import SCAN_FILES, audit_text
from qa.standalone import REQUIRED_FILES

ROOT = Path(__file__).resolve().parent.parent
DEVPOST = ROOT / "docs" / "devpost-submission.md"

SECTION_HEADERS = [
    "## 프로젝트 이름",
    "## 한 줄 소개",
    "## 소개",
    "## 동작 방식",
    "## Meta AI 도구 활용",
    "## 기술 구성",
    "## 데모 데이터",
    "## 해커톤 기간 중 신규 제작",
    "## 데모 영상",
    "## 현재 블로커와 제출 상태",
    "## 제출 전 교체할 항목",
]


def _text() -> str:
    return DEVPOST.read_text(encoding="utf-8")


class DevpostSubmissionTests(unittest.TestCase):
    def test_devpost_exists(self):
        self.assertTrue(DEVPOST.is_file())

    def test_sections_in_order(self):
        text = _text()
        positions = [text.index(header) for header in SECTION_HEADERS]
        self.assertEqual(positions, sorted(positions))

    def test_name_tagline_and_workflow(self):
        text = _text()
        self.assertIn("Argus", text)
        self.assertIn("재고실사 코파일럿", text)
        for step in ("촬영", "계수", "대조", "리포트"):
            self.assertIn(step, text)

    def test_meta_ai_honesty(self):
        text = _text()
        self.assertIn("SAM 3.1", text)
        self.assertIn("모의 어댑터가 동작 중이지만 SAM 3.1 실호출은 단일 빈 스모크로 검증했다", text)
        self.assertIn("가짜 transport", text)
        self.assertIn("Secure Vault", text)
        self.assertIn("가안", text)

    def test_demo_data_is_demo_basis(self):
        text = _text()
        self.assertIn("데모 기준: 빈 6개 중 일치 4건, 불일치 2건", text)
        self.assertIn("일치율 66.7%", text)
        self.assertIn("실제 창고 성과가 아니다", text)

    def test_new_work_and_video_placeholder(self):
        text = _text()
        self.assertIn("전부 해커톤 기간(2026-10-27~11-04) 안에 새로 작성", text)
        self.assertIn("180초", text)
        self.assertIn("컷 3은 Pi 실촬영 교체 예정인 플레이스홀더", text)

    def test_blockers_ready_and_deadline(self):
        text = _text()
        self.assertIn("pi_real_capture_pending", text)
        self.assertNotIn("sam_real_call_pending", text)
        self.assertIn("SUBMISSION_READY: false", text)
        self.assertIn("https://github.com/BoxLogoDev/argus-counts", text)
        self.assertIn("2026-11-04 21:00 ET", text)
        self.assertIn("2026-11-05 11:00 KST", text)

    def test_claims_audit_clean_and_scanned(self):
        violations = audit_text("docs/devpost-submission.md", _text())
        self.assertEqual(violations, [])
        self.assertIn("docs/devpost-submission.md", SCAN_FILES)

    def test_required_by_standalone_and_no_forbidden_phrase(self):
        self.assertIn("docs/devpost-submission.md", REQUIRED_FILES)
        self.assertNotIn("코드 " + "참고", _text())


if __name__ == "__main__":
    unittest.main()
