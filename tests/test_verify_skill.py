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
    "photo-intake.md",
    "pre-submission.md",
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

    def test_photo_intake_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("photo-intake", skill)
        self.assertIn("기능 7종", skill)
        feature = (SKILL_DIR / "features" / "photo-intake.md").read_text(
            encoding="utf-8")
        for marker in ("capture_source", "Pi 실촬영이 아닙니다", "SHA-256",
                       "VERIFY-PHOTO-1"):
            self.assertIn(marker, feature)

    def test_pre_submission_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pre-submission", skill)
        self.assertIn("기능 7종", skill)
        feature = (SKILL_DIR / "features" / "pre-submission.md").read_text(
            encoding="utf-8")
        for marker in ("submission_ready", "pi_real_capture_pending",
                       "sam_real_call_pending", "qa.pre_submission"):
            self.assertIn(marker, feature)

    def test_demo_video_data_panel_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("build_data_panel_lines", skill)
        self.assertIn("data-panel.json", skill)
        feature = (SKILL_DIR / "features" / "demo-video-draft.md").read_text(
            encoding="utf-8")
        for marker in ("video-data-panel", "build_data_panel_lines",
                       "data-panel.json", "실촬영 데이터 없음", "실측 999"):
            self.assertIn(marker, feature)

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

    def test_each_feature_drives_and_passes(self):
        for feature in ("terminal-simulator", "session-list",
                        "difference-report", "demo-video-draft",
                        "photo-intake", "pre-submission"):
            with self.subTest(feature=feature), tempfile.TemporaryDirectory() as tmp:
                evidence = Path(tmp) / "run"
                result = self._run_helper("--feature", feature, evidence=evidence)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("VERIFY: PASS", result.stdout)
                summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
                self.assertEqual(summary["feature"], feature)
                self.assertTrue(summary["all_ok"])
                self.assertTrue((evidence / "transcript.txt").is_file())

    def test_all_features_writes_per_feature_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-all"
            result = self._run_helper("--feature", "all", evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads((evidence / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["all_ok"])
            self.assertEqual(set(summary["features"]), {
                "console-home", "terminal-simulator", "session-list",
                "difference-report", "demo-video-draft", "photo-intake",
                "pre-submission"})
            self.assertTrue(all(summary["features"].values()))
            for name in summary["features"]:
                self.assertTrue((evidence / name / "summary.json").is_file(), name)

    def test_photo_intake_drives_and_records_photo_hash(self):
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-photo"
            result = self._run_helper("--feature", "photo-intake",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "photo-intake")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["source"], "mock")
            self.assertEqual(summary["capture_source"], "file")
            self.assertEqual(summary["intake_summary"]["matched"], 4)
            self.assertEqual(summary["intake_summary"]["mismatched"], 2)
            payload = json.loads((evidence / "photo-intake-stdout.json").read_text(
                encoding="utf-8"))
            by_bin = {b["bin_id"]: b for b in payload["bins"]}
            self.assertEqual(
                by_bin["A-01-02"]["photo"]["sha256"],
                hashlib.sha256(b"fake-photo-A-01-02").hexdigest())
            self.assertTrue((evidence / "photo-intake.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_photo_intake_evidence_keeps_honesty_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-photo-honesty"
            result = self._run_helper("--feature", "photo-intake",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads((evidence / "photo-intake-stdout.json").read_text(
                encoding="utf-8"))
            self.assertEqual(payload["capture_source"], "file")
            self.assertTrue(any("Pi 실촬영이 아닙니다" in line
                                for line in payload["honesty"]))
            self.assertEqual(payload["session_id"], "VERIFY-PHOTO-1")

    def test_pre_submission_drives_and_records_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pre"
            result = self._run_helper("--feature", "pre-submission",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "pre-submission")
            self.assertTrue(summary["all_ok"])
            self.assertTrue(summary["mechanical_pass"])
            self.assertEqual(summary["passed"], 6)
            self.assertEqual(summary["total"], 6)
            self.assertEqual(summary["blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertFalse(summary["submission_ready"])
            self.assertTrue((evidence / "pre-submission.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_pre_submission_evidence_keeps_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pre-honesty"
            result = self._run_helper("--feature", "pre-submission",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads((evidence / "pre-submission.json").read_text(
                encoding="utf-8"))
            self.assertTrue(payload["mechanical_pass"])
            self.assertFalse(payload["submission_ready"])
            self.assertTrue(any("모의" in line for line in payload["honesty"]))
            text = (evidence / "pre-submission-stdout.txt").read_text(
                encoding="utf-8")
            self.assertIn("SUBMISSION_READY: false", text)
            self.assertIn("BLOCKERS: 2", text)

    def test_demo_video_drives_and_records_data_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-video-panel"
            result = self._run_helper("--feature", "demo-video-draft",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "demo-video-draft")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["data_panel_cuts"],
                             [1, 2, 3, 4, 5, 6, 7, 8, 9])
            payload = json.loads((evidence / "data-panel.json").read_text(
                encoding="utf-8"))
            self.assertTrue(payload["custom_counted_qty_reflected"])
            panel = payload["data_panel"]
            self.assertEqual(len(panel["5"]), 6)
            self.assertEqual(len(panel["6"]), 2)
            self.assertEqual(panel["3"],
                             ["실촬영 데이터 없음 — Pi 도착 후 교체"])
            self.assertTrue((evidence / "video-probe.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_demo_video_data_panel_evidence_keeps_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-video-panel-honesty"
            result = self._run_helper("--feature", "demo-video-draft",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads((evidence / "data-panel.json").read_text(
                encoding="utf-8"))
            panel = payload["data_panel"]
            self.assertIn("데모 기준", panel["9"][0])
            self.assertIn("일치율 66.7%", panel["1"][0])
            self.assertTrue(all("장부" in line and "→ 실측" in line
                                for line in panel["5"]))

    def test_unknown_feature_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run_helper("--feature", "nope", evidence=Path(tmp))
            self.assertNotEqual(result.returncode, 0)

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
