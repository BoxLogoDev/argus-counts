"""qa.standalone 점검 모듈 테스트."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from qa.standalone import run_standalone_checks, scan_text


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_root(root: Path) -> None:
    for rel in (
        "README.md",
        "terminal/sam_adapter.py",
        "terminal/reconcile.py",
        "terminal/report.py",
        "console/server.py",
        "qa/harness.py",
        ".claude/skills/verify-argus/SKILL.md",
        ".claude/skills/verify-argus/features/README.md",
    ):
        _write(root, rel, "ok\n")
    _write(root, "docs/submission-story.md", "모의 어댑터, 데모 기준 수치, 테마 가안\n")
    _write(root, "docs/submission-summary-en.md", "mock adapter, Demo basis: figures, tentative theme\n")
    _write(root, "docs/demo-script.md", "Pi 실촬영 교체 예정, 모의 표기 확인\n")
    _write(root, "docs/submission-runbook.md", "모의 어댑터, 검증 전, 미실시 상태 런북\n")
    _write(root, "docs/devpost-submission.md", "모의 어댑터, 데모 기준, 제출 문안\n")


class ScanTextTests(unittest.TestCase):
    def test_clean_text_has_no_hits(self):
        self.assertEqual(scan_text("창고 재고 실사 데모\n"), [])

    def test_company_identifier_is_flagged(self):
        hits = scan_text("예시 " + "LS" + "MTRON" + " 자료\n")
        self.assertTrue(any("forbidden" in h for h in hits))

    def test_private_key_is_flagged(self):
        hits = scan_text("-----BEGIN RSA PRIVATE " + "KEY-----\n")
        self.assertTrue(any("secret" in h for h in hits))

    def test_hardcoded_api_key_is_flagged(self):
        hits = scan_text("api" + '_key = "abcd1234efgh"\n')
        self.assertTrue(any("secret" in h for h in hits))

    def test_env_var_reference_is_not_flagged(self):
        hits = scan_text('api_key = os.environ.get("SAM_API_KEY")\n')
        self.assertEqual(hits, [])


class StandaloneCheckTests(unittest.TestCase):
    def test_minimal_clean_root_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            checks = run_standalone_checks(root)
            self.assertTrue(all(c.passed for c in checks), checks)

    def test_missing_required_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            (root / "docs/demo-script.md").unlink()
            checks = run_standalone_checks(root)
            by_name = {c.name: c.passed for c in checks}
            self.assertFalse(by_name["required_files_present"])

    def test_forbidden_content_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(root, "docs/extra.md", "실제 " + "LS" + "엠트론" + " 자료\n")
            checks = run_standalone_checks(root)
            by_name = {c.name: c.passed for c in checks}
            self.assertFalse(by_name["no_forbidden_or_secret_content"])

    def test_missing_honesty_marker_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(root, "docs/submission-story.md", "정직성 표기가 없는 서술\n")
            checks = run_standalone_checks(root)
            by_name = {c.name: c.passed for c in checks}
            self.assertFalse(by_name["honesty_markers:docs/submission-story.md"])

    def test_claims_audit_check_present_and_passes_on_minimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            checks = run_standalone_checks(root)
            by_name = {c.name: c for c in checks}
            self.assertIn("claims_audit_clean", by_name)
            self.assertTrue(by_name["claims_audit_clean"].passed)
            self.assertIn("files clean", by_name["claims_audit_clean"].detail)
            self.assertEqual(checks[-1].name, "claims_audit_clean")

    def test_bare_claim_fails_claims_audit_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(root, "README.md", "SAM 3.1 실호출을 연동했습니다.\n")
            checks = run_standalone_checks(root)
            by_name = {c.name: c.passed for c in checks}
            self.assertFalse(by_name["claims_audit_clean"])

    def test_missing_scan_file_fails_claims_audit_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            (root / "docs/submission-summary-en.md").unlink()
            checks = run_standalone_checks(root)
            by_name = {c.name: c.passed for c in checks}
            self.assertFalse(by_name["claims_audit_clean"])


if __name__ == "__main__":
    unittest.main()
