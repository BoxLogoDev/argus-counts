"""현재형 주장 감사 하네스(qa/claims_audit) 테스트."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from qa import claims_audit


class AuditTextTests(unittest.TestCase):
    def test_clean_text_no_violations(self):
        text = "Argus는 모의 데이터로 동작합니다.\n빈 6개를 대조합니다.\n"
        self.assertEqual(claims_audit.audit_text("README.md", text), [])

    def test_bare_real_call_claim_flagged(self):
        text = "SAM 3.1 실호출을 연동했습니다.\n"
        v = claims_audit.audit_text("docs/x.md", text)
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0]["line"], 1)
        self.assertEqual(v[0]["file"], "docs/x.md")

    def test_honesty_marker_suppresses(self):
        text = "SAM 3.1 실호출은 아직 미실시이며 모의 어댑터로 동작합니다.\n"
        self.assertEqual(claims_audit.audit_text("docs/x.md", text), [])

    def test_real_filming_claim_flagged(self):
        text = "Pi 실촬영으로 전체 플로우를 검증 완료했습니다.\n"
        v = claims_audit.audit_text("docs/x.md", text)
        self.assertGreaterEqual(len(v), 1)

    def test_english_live_claim_flagged(self):
        text = "The demo uses a live SAM integration in production.\n"
        v = claims_audit.audit_text("docs/x.md", text)
        self.assertGreaterEqual(len(v), 1)

    def test_english_honesty_suppresses(self):
        text = "No real SAM call has been made yet; results are mock.\n"
        self.assertEqual(claims_audit.audit_text("docs/x.md", text), [])


class AuditFilesTests(unittest.TestCase):
    def test_missing_file_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            result = claims_audit.audit_files(d)
            self.assertEqual(result["checked_files"], 0)
            self.assertEqual(len(result["missing"]), len(claims_audit.SCAN_FILES))

    def test_real_docs_pass(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        result = claims_audit.audit_files(root)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["checked_files"], len(claims_audit.SCAN_FILES))

    def test_main_returns_zero_on_real_docs(self):
        # main()의 기본 루트는 모듈 위치 기준 프로젝트 루트다.
        self.assertEqual(claims_audit.main([]), 0)


if __name__ == "__main__":
    unittest.main()
