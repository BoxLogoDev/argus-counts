"""프로젝트 로컬 검증 스킬(verify-argus) 구조·동작 테스트.

검증 스킬 파일이 사양대로 존재하고, 헬퍼 스크립트가 실제로 콘솔
서버를 띄워 사용자 경로를 구동하는지 확인한다.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / ".claude" / "skills" / "verify-argus"
FEATURES = [
    "console-home.md",
    "terminal-simulator.md",
    "session-list.md",
    "difference-report.md",
    "demo-video-draft.md",
]
EXPECTED_H2 = [
    "## Sub-features",
    "## How to get to it (user POV)",
    "## Driving it with verify_argus.py",
    "## Gotchas",
]


class SkillFileTests(unittest.TestCase):
    def test_skill_md_frontmatter_and_sections(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"))
        self.assertIn("name: verify-argus", text)
        self.assertIn("description:", text)
        for section in ("Launch", "Doctor", "Drive", "Evidence", "Cleanup", "Helpers"):
            self.assertIn(section, text)

    def test_skill_md_grounds_in_real_routes(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for marker in ("/api/report", "source=mock", "8765", "ProxyHandler"):
            self.assertIn(marker, text)

    def test_features_index_lists_all_features(self):
        text = (SKILL_DIR / "features" / "README.md").read_text(encoding="utf-8")
        for name in FEATURES:
            self.assertIn(name, text)

    def test_each_feature_has_four_h2_in_order(self):
        for name in FEATURES:
            text = (SKILL_DIR / "features" / name).read_text(encoding="utf-8")
            h2 = [line.strip() for line in text.splitlines() if line.startswith("## ")]
            self.assertEqual(h2, EXPECTED_H2, name)
            self.assertIn("Preconditions:", text, name)

    def test_helper_exists_and_compiles(self):
        helper = SKILL_DIR / "scripts" / "verify_argus.py"
        self.assertTrue(helper.is_file())
        compile(helper.read_text(encoding="utf-8"), str(helper), "exec")


class HelperRunTests(unittest.TestCase):
    def _run_helper(self, *extra: str, evidence: Path) -> subprocess.CompletedProcess:
        helper = SKILL_DIR / "scripts" / "verify_argus.py"
        return subprocess.run(
            [sys.executable, str(helper), "--evidence-dir", str(evidence), *extra],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )

    def test_doctor_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_helper("--doctor", evidence=Path(tmp))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

    def test_drive_writes_evidence_that_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-1"
            result = self._run_helper(evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for name in ("transcript.txt", "home.html", "api-report.json", "summary.json"):
                self.assertTrue((evidence / name).is_file(), name)
            summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["source"], "mock")
            report = json.loads((evidence / "api-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["matched"], 4)
            self.assertEqual(report["summary"]["mismatched"], 2)


if __name__ == "__main__":
    unittest.main()
