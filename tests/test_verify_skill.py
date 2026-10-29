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
    "pi-capture.md",
    "pi-session.md",
    "sam-live.md",
    "sam-readiness.md",
    "submission-runbook.md",
    "pi-readiness.md",
    "console-readiness.md",
    "sam-smoke.md",
    "pi-smoke.md",
    "devpost-submission.md",
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
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "photo-intake.md").read_text(
            encoding="utf-8")
        for marker in ("capture_source", "Pi 실촬영이 아닙니다", "SHA-256",
                       "VERIFY-PHOTO-1"):
            self.assertIn(marker, feature)

    def test_pre_submission_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pre-submission", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "pre-submission.md").read_text(
            encoding="utf-8")
        for marker in ("submission_ready", "pi_real_capture_pending",
                       "sam_real_call_pending", "qa.pre_submission"):
            self.assertIn(marker, feature)

    def test_pi_capture_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pi-capture", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "pi-capture.md").read_text(
            encoding="utf-8")
        for marker in ("probe_pi_camera", "capture_photo", "Pi 실촬영 검증 전",
                       "fake-pi-jpeg", "PiCaptureError", "libcamera-still"):
            self.assertIn(marker, feature)

    def test_pi_session_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pi-session", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "pi-session.md").read_text(
            encoding="utf-8")
        for marker in ("run_pi_session", "capture_source", "pi-camera",
                       "Pi 실촬영 검증 전", "fake-pi-session-jpeg",
                       "PiCaptureError", "VERIFY-PI-SESSION-1",
                       "libcamera-still", "terminal.pi_session"):
            self.assertIn(marker, feature)

    def test_sam_live_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("sam-live", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "sam-live.md").read_text(
            encoding="utf-8")
        for marker in ("LiveSamCounter", "build_payload", "parse_response",
                       "SamCountingError", "fake transport", "example.invalid",
                       "SAM 실호출 검증 전", "실제 API 호출 없음",
                       "모의 폴백 없음", "Authorization"):
            self.assertIn(marker, feature)

    def test_sam_readiness_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("sam-readiness", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "sam-readiness.md").read_text(
            encoding="utf-8")
        for marker in ("qa.sam_readiness", "check_readiness",
                       "sam_credit_not_confirmed", "sam_base_url_missing",
                       "sam_api_key_missing", "READY_FOR_LIVE_CALL",
                       "호출하지 않는다", "실호출 성공", "존재 여부만"):
            self.assertIn(marker, feature)

    def test_sam_smoke_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("sam-smoke", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "sam-smoke.md").read_text(
            encoding="utf-8")
        for marker in ("qa.sam_smoke", "run_smoke",
                       "sam_credit_not_confirmed", "sam_base_url_missing",
                       "sam_api_key_missing", "SMOKE_PASSED",
                       "호출하지 않는다", "대체하지 않는다", "전체 세션 성공",
                       "sam-smoke-blocked.json", "SamCountingError"):
            self.assertIn(marker, feature)

    def test_pi_smoke_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pi-smoke", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "pi-smoke.md").read_text(
            encoding="utf-8")
        for marker in ("qa.pi_smoke", "run_smoke",
                       "pi_device_arrival_not_confirmed",
                       "pi_camera_command_missing", "SMOKE_PASSED",
                       "촬영하지 않는다", "대체하지 않는다", "전체 세션 성공",
                       "Pi 실촬영 검증 완료", "pi-smoke-blocked.json",
                       "PiCaptureError", "unexpected_capture_source",
                       "libcamera-still", "fake-pi-smoke-jpeg",
                       "--device-confirmed"):
            self.assertIn(marker, feature)

    def test_devpost_submission_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("devpost-submission", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "devpost-submission.md").read_text(
            encoding="utf-8")
        for marker in ("docs/devpost-submission.md", "validate_devpost_text",
                       "drive_devpost_submission", "SUBMISSION_READY: false",
                       "pi_real_capture_pending", "sam_real_call_pending",
                       "Secure Vault", "가짜 transport", "데모 기준",
                       "66.7%", "플레이스홀더", "2026-11-05 11:00 KST", "변조"):
            self.assertIn(marker, feature)

    def test_submission_runbook_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("submission-runbook", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "submission-runbook.md").read_text(
            encoding="utf-8")
        for marker in ("docs/submission-runbook.md", "validate_runbook_text",
                       "drive_submission_runbook", "SUBMISSION_READY: false",
                       "pi_real_capture_pending", "sam_real_call_pending",
                       "Secure Vault", "2026-10-29 09:30",
                       "--credit-confirmed", "2026-11-05 11:00", "변조"):
            self.assertIn(marker, feature)

    def test_pi_readiness_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("pi-readiness", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "pi-readiness.md").read_text(
            encoding="utf-8")
        for marker in ("qa.pi_readiness", "check_readiness",
                       "pi_device_arrival_not_confirmed",
                       "pi_camera_command_missing", "READY_FOR_REAL_CAPTURE",
                       "촬영을 하지 않는다", "성공을 뜻하지 않는다",
                       "존재만 탐지", "libcamera-still", "--device-confirmed"):
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
                        "photo-intake", "pre-submission", "pi-capture",
                        "pi-session", "sam-live", "sam-readiness",
                        "submission-runbook", "pi-readiness",
                        "console-readiness", "sam-smoke", "pi-smoke",
                        "devpost-submission"):
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
                "pre-submission", "pi-capture", "pi-session", "sam-live",
                "sam-readiness", "submission-runbook", "pi-readiness",
                "console-readiness", "sam-smoke", "pi-smoke",
                "devpost-submission"})
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
            self.assertEqual(summary["passed"], 15)
            self.assertEqual(summary["total"], 15)
            self.assertEqual(summary["readiness_en_summary_section_count"], 8)
            self.assertEqual(summary["readiness_en_summary_blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertEqual(summary["readiness_story_section_count"], 7)
            self.assertEqual(summary["readiness_story_blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertEqual(summary["readiness_devpost_section_count"], 11)
            self.assertEqual(summary["readiness_devpost_blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertEqual(summary["blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertEqual(summary["readiness_pi_smoke_status"], "blocked")
            self.assertEqual(summary["readiness_pi_smoke_blockers"], [
                "pi_device_arrival_not_confirmed", "pi_camera_command_missing"])
            self.assertEqual(summary["readiness_smoke_status"], "blocked")
            self.assertEqual(summary["readiness_smoke_blockers"], [
                "sam_credit_not_confirmed", "sam_base_url_missing",
                "sam_api_key_missing"])
            self.assertEqual(summary["readiness_sam_blockers"], [
                "sam_credit_not_confirmed", "sam_base_url_missing",
                "sam_api_key_missing"])
            self.assertEqual(summary["readiness_pi_blockers"], [
                "pi_device_arrival_not_confirmed", "pi_camera_command_missing"])
            self.assertEqual(summary["readiness_console_blocker_count"], 5)
            self.assertFalse(summary["readiness_console_overall_ready"])
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

    def test_pi_capture_drives_and_records_fake_hash(self):
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi"
            result = self._run_helper("--feature", "pi-capture",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "pi-capture")
            self.assertTrue(summary["all_ok"])
            # 이 VM에는 카메라 명령이 없어 탐지는 available=false,
            # CLI --capture는 파일 없이 실패하는 것이 기대 동작이다.
            self.assertFalse(summary["probe_available"])
            self.assertIsNone(summary["probe_command"])
            self.assertTrue(summary["cli_capture_blocked"])
            self.assertEqual(
                summary["fake_capture_sha256"],
                hashlib.sha256(b"fake-pi-jpeg").hexdigest())
            self.assertEqual(summary["fake_capture_suffix"], ".jpg")
            fake = json.loads((evidence / "pi-capture-fake.json").read_text(
                encoding="utf-8"))
            self.assertEqual(fake["bin_id"], "A-01-02")
            self.assertEqual(fake["sha256"], summary["fake_capture_sha256"])
            self.assertTrue((evidence / "pi-capture-probe.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_pi_capture_evidence_keeps_honesty_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi-honesty"
            result = self._run_helper("--feature", "pi-capture",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            probe = json.loads((evidence / "pi-capture-probe.json").read_text(
                encoding="utf-8"))
            self.assertIn("available", probe)
            self.assertTrue(any("Pi 실촬영 검증 전" in line
                                for line in probe["honesty"]))
            fake = json.loads((evidence / "pi-capture-fake.json").read_text(
                encoding="utf-8"))
            self.assertEqual(fake["suffix"], ".jpg")
            self.assertEqual(fake["size_bytes"], len(b"fake-pi-jpeg"))

    def test_pi_session_drives_and_records_fake_hash(self):
        import hashlib

        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi-session"
            result = self._run_helper("--feature", "pi-session",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "pi-session")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["source"], "mock")
            self.assertEqual(summary["capture_source"], "pi-camera")
            self.assertEqual(summary["session_summary"]["matched"], 4)
            self.assertEqual(summary["session_summary"]["mismatched"], 2)
            self.assertEqual(summary["probe_command"], "libcamera-still")
            # 이 VM에는 카메라 명령이 없어 CLI 세션은 파일 없이
            # 실패하고, 무카메라 run_pi_session도 차단되는 것이 기대 동작이다.
            self.assertTrue(summary["cli_session_blocked"])
            self.assertTrue(summary["no_camera_blocked"])
            self.assertEqual(
                summary["fake_capture_sha256"],
                hashlib.sha256(b"fake-pi-session-jpeg").hexdigest())
            report = json.loads((evidence / "pi-session-report.json").read_text(
                encoding="utf-8"))
            self.assertEqual(report["session_id"], "VERIFY-PI-SESSION-1")
            self.assertEqual(report["capture_source"], "pi-camera")
            self.assertTrue((evidence / "pi-session-blocked.txt").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_pi_session_evidence_keeps_honesty_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi-session-honesty"
            result = self._run_helper("--feature", "pi-session",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads((evidence / "pi-session-report.json").read_text(
                encoding="utf-8"))
            self.assertTrue(any("Pi 실촬영 검증 전" in line
                                for line in report["honesty"]))
            self.assertTrue(report["probe"]["available"])
            self.assertEqual(report["probe"]["command"], "libcamera-still")
            blocked = (evidence / "pi-session-blocked.txt").read_text(
                encoding="utf-8")
            self.assertIn("Pi 카메라 명령을 찾을 수 없습니다", blocked)
            by_bin = {b["bin_id"]: b for b in report["bins"]}
            self.assertEqual(by_bin["A-01-02"]["verdict"], "short")
            self.assertEqual(by_bin["A-01-02"]["diff"], -3)

    def test_sam_live_drives_and_records_fake_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-sam-live"
            result = self._run_helper("--feature", "sam-live",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "sam-live")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["source"], "sam")
            self.assertEqual(summary["counted_qty"], 5)
            self.assertEqual(summary["fake_url"], "https://example.invalid/sam")
            self.assertTrue(summary["http_error_blocked"])
            self.assertTrue(summary["transport_error_wrapped"])
            self.assertTrue(summary["mock_selection_ok"])
            fake = json.loads((evidence / "sam-live-fake.json").read_text(
                encoding="utf-8"))
            self.assertEqual(fake["model"], "sam-3.1")
            self.assertEqual(fake["bin_id"], "A-01-02")
            self.assertEqual(fake["counted_qty"], 5)
            self.assertNotIn("test-key-not-real", json.dumps(fake))
            self.assertTrue((evidence / "sam-live-errors.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_sam_live_evidence_keeps_error_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-sam-live-errors"
            result = self._run_helper("--feature", "sam-live",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            errors = json.loads((evidence / "sam-live-errors.json").read_text(
                encoding="utf-8"))
            self.assertTrue(errors["http_error_blocked"])
            self.assertTrue(errors["transport_error_wrapped"])
            self.assertTrue(errors["mock_selection_ok"])
            fake_text = (evidence / "sam-live-fake.json").read_text(
                encoding="utf-8")
            self.assertNotIn("test-key-not-real", fake_text)
            self.assertNotIn("Authorization", fake_text)

    def test_sam_readiness_drives_and_records_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-sam-readiness"
            result = self._run_helper("--feature", "sam-readiness",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "sam-readiness")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["blocked_blockers"], [
                "sam_credit_not_confirmed", "sam_base_url_missing",
                "sam_api_key_missing"])
            self.assertEqual(summary["default_exit_code"], 1)
            self.assertTrue(summary["ready_with_fake_env"])
            self.assertEqual(summary["credit_only_blocker"],
                             ["sam_credit_not_confirmed"])
            self.assertEqual(summary["cli_ready_exit_code"], 0)
            self.assertFalse(summary["sentinel_leaked"])
            self.assertTrue((evidence / "sam-readiness-blocked.json").is_file())
            self.assertTrue((evidence / "sam-readiness-ready.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_sam_readiness_evidence_keeps_no_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-sam-readiness-noleak"
            result = self._run_helper("--feature", "sam-readiness",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            blocked = json.loads(
                (evidence / "sam-readiness-blocked.json").read_text(
                    encoding="utf-8"))
            self.assertFalse(blocked["ready_for_live_call"])
            self.assertTrue(any("호출하지 않는다" in line
                                for line in blocked["honesty"]))
            ready_text = (evidence / "sam-readiness-ready.json").read_text(
                encoding="utf-8")
            self.assertNotIn("sentinel-readiness", ready_text)
            ready = json.loads(ready_text)
            self.assertTrue(ready["ready_for_live_call"])
            self.assertEqual(ready["blockers"], [])

    def test_pi_readiness_drives_and_records_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi-readiness"
            result = self._run_helper("--feature", "pi-readiness",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "pi-readiness")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["blocked_blockers"], [
                "pi_device_arrival_not_confirmed", "pi_camera_command_missing"])
            self.assertEqual(summary["default_exit_code"], 1)
            self.assertTrue(summary["ready_with_fake_probe"])
            self.assertEqual(summary["device_only_blocker"],
                             ["pi_device_arrival_not_confirmed"])
            self.assertEqual(summary["camera_only_blocker"],
                             ["pi_camera_command_missing"])
            self.assertEqual(summary["which_injected_command"], "raspistill")
            self.assertEqual(summary["cli_device_confirmed_exit_code"], 1)
            self.assertEqual(summary["cli_device_confirmed_blockers"],
                             ["pi_camera_command_missing"])
            self.assertTrue((evidence / "pi-readiness-blocked.json").is_file())
            self.assertTrue((evidence / "pi-readiness-ready.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_pi_readiness_evidence_keeps_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi-readiness-honesty"
            result = self._run_helper("--feature", "pi-readiness",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            blocked = json.loads(
                (evidence / "pi-readiness-blocked.json").read_text(
                    encoding="utf-8"))
            self.assertFalse(blocked["ready_for_real_capture"])
            self.assertTrue(any("촬영을 하지 않는다" in line
                                for line in blocked["honesty"]))
            ready = json.loads(
                (evidence / "pi-readiness-ready.json").read_text(
                    encoding="utf-8"))
            self.assertTrue(ready["ready_for_real_capture"])
            self.assertEqual(ready["blockers"], [])
            self.assertEqual(ready["camera_command"], "libcamera-still")

    def test_submission_runbook_drives_and_records_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-runbook"
            result = self._run_helper("--feature", "submission-runbook",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "submission-runbook")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["section_count"], 7)
            self.assertEqual(summary["blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertFalse(summary["submission_ready"])
            self.assertEqual(summary["credit_check_at"], "2026-10-29 09:30")
            self.assertEqual(summary["deadline_kst"], "2026-11-05 11:00")
            self.assertEqual(summary["final_check_command_count"], 8)
            self.assertTrue(summary["claims_audit_clean"])
            self.assertTrue(summary["tamper_detected"])
            self.assertEqual(summary["pre_submission_blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertTrue((evidence / "submission-runbook.json").is_file())
            self.assertTrue((evidence / "submission-runbook.md").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_submission_runbook_evidence_keeps_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-runbook-honesty"
            result = self._run_helper("--feature", "submission-runbook",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(
                (evidence / "submission-runbook.json").read_text(
                    encoding="utf-8"))
            self.assertFalse(payload["submission_ready"])
            self.assertEqual(payload["blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            text = (evidence / "submission-runbook.md").read_text(
                encoding="utf-8")
            self.assertIn("SUBMISSION_READY: false", text)
            self.assertNotIn("SUBMISSION_READY: true", text)
            self.assertIn("Secure Vault", text)

    def test_console_readiness_listed_and_grounded(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("console-readiness", skill)
        self.assertIn("기능 17종", skill)
        feature = (SKILL_DIR / "features" / "console-readiness.md").read_text(
            encoding="utf-8")
        for marker in ("build_readiness", "/api/readiness", "준비 상태",
                       "sam_credit_not_confirmed", "pi_camera_command_missing",
                       "준비 완료는 실호출·실촬영 성공을 뜻하지 않는다",
                       "console-readiness", "임시 포트"):
            self.assertIn(marker, feature)

    def test_console_readiness_drives_and_records_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-console-readiness"
            result = self._run_helper("--feature", "console-readiness",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "console-readiness")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["sam_blockers"], [
                "sam_credit_not_confirmed", "sam_base_url_missing",
                "sam_api_key_missing"])
            self.assertEqual(summary["pi_blockers"], [
                "pi_device_arrival_not_confirmed", "pi_camera_command_missing"])
            self.assertEqual(summary["blocker_count"], 5)
            self.assertFalse(summary["overall_ready"])
            self.assertTrue(summary["fake_overall_ready"])
            self.assertFalse(summary["fake_sam_only_overall"])
            self.assertFalse(summary["fake_pi_only_overall"])
            self.assertFalse(summary["sentinel_leaked"])
            self.assertTrue((evidence / "console-readiness.json").is_file())
            self.assertTrue((evidence / "console-readiness-ready.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_console_readiness_evidence_keeps_honesty(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-console-readiness-honesty"
            result = self._run_helper("--feature", "console-readiness",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(
                (evidence / "console-readiness.json").read_text(
                    encoding="utf-8"))
            self.assertFalse(payload["overall_ready"])
            self.assertTrue(any(
                "준비 완료는 실호출·실촬영 성공을 뜻하지 않는다" in line
                for line in payload["honesty"]))
            ready_text = (evidence / "console-readiness-ready.json").read_text(
                encoding="utf-8")
            self.assertNotIn("sentinel-console-readiness", ready_text)
            self.assertNotIn("console-readiness.example.invalid", ready_text)
            ready = json.loads(ready_text)
            self.assertTrue(ready["overall_ready"])

    def test_sam_smoke_drives_and_records_blocked_and_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-sam-smoke"
            result = self._run_helper("--feature", "sam-smoke",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "sam-smoke")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["blocked_blockers"], [
                "sam_credit_not_confirmed", "sam_base_url_missing",
                "sam_api_key_missing"])
            self.assertEqual(summary["default_exit_code"], 1)
            self.assertTrue(summary["fake_passed"])
            self.assertEqual(summary["counted_qty"], 5)
            self.assertEqual(summary["book_qty"], 8)
            self.assertEqual(summary["diff"], -3)
            self.assertEqual(summary["blocked_counter_calls"], 0)
            self.assertTrue(summary["mock_source_blocked"])
            self.assertTrue(summary["sam_error_blocked"])
            self.assertTrue(summary["unknown_bin_blocked"])
            self.assertFalse(summary["sentinel_leaked"])
            passed = json.loads((evidence / "sam-smoke-passed.json").read_text(
                encoding="utf-8"))
            self.assertEqual(passed["status"], "passed")
            self.assertEqual(passed["source"], "sam")
            self.assertTrue((evidence / "sam-smoke-blocked.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_sam_smoke_evidence_keeps_honesty_and_no_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-sam-smoke-honesty"
            result = self._run_helper("--feature", "sam-smoke",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            blocked = json.loads(
                (evidence / "sam-smoke-blocked.json").read_text(
                    encoding="utf-8"))
            self.assertEqual(blocked["status"], "blocked")
            self.assertFalse(blocked["attempted"])
            self.assertTrue(any("호출하지 않는다" in line
                                for line in blocked["honesty"]))
            self.assertTrue(any("대체하지 않는다" in line
                                for line in blocked["honesty"]))
            for name in ("sam-smoke-blocked.json", "sam-smoke-passed.json"):
                text = (evidence / name).read_text(encoding="utf-8")
                self.assertNotIn("sentinel-smoke", text)

    def test_pi_smoke_drives_and_records_blocked_and_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi-smoke"
            result = self._run_helper("--feature", "pi-smoke",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "pi-smoke")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["blocked_blockers"], [
                "pi_device_arrival_not_confirmed", "pi_camera_command_missing"])
            self.assertEqual(summary["default_exit_code"], 1)
            self.assertEqual(summary["device_confirmed_blockers"], [
                "pi_camera_command_missing"])
            self.assertTrue(summary["fake_passed"])
            self.assertEqual(summary["counted_qty"], 5)
            self.assertEqual(summary["book_qty"], 8)
            self.assertEqual(summary["diff"], -3)
            self.assertEqual(summary["blocked_session_calls"], 0)
            self.assertTrue(summary["real_session_passed"])
            self.assertTrue(summary["unexpected_capture_source_blocked"])
            self.assertTrue(summary["pi_capture_error_blocked"])
            self.assertTrue(summary["unknown_bin_blocked"])
            self.assertFalse(summary["sentinel_leaked"])
            import hashlib

            self.assertEqual(
                summary["fake_capture_sha256"],
                hashlib.sha256(b"fake-pi-smoke-jpeg").hexdigest())
            passed = json.loads((evidence / "pi-smoke-passed.json").read_text(
                encoding="utf-8"))
            self.assertEqual(passed["status"], "passed")
            self.assertEqual(passed["capture_source"], "pi-camera")
            self.assertEqual(passed["source"], "mock")
            self.assertTrue((evidence / "pi-smoke-blocked.json").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_pi_smoke_evidence_keeps_honesty_and_no_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-pi-smoke-honesty"
            result = self._run_helper("--feature", "pi-smoke",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            blocked = json.loads(
                (evidence / "pi-smoke-blocked.json").read_text(
                    encoding="utf-8"))
            self.assertEqual(blocked["status"], "blocked")
            self.assertFalse(blocked["attempted"])
            self.assertTrue(any("촬영하지 않는다" in line
                                for line in blocked["honesty"]))
            self.assertTrue(any("대체하지 않는다" in line
                                for line in blocked["honesty"]))
            for name in ("pi-smoke-blocked.json", "pi-smoke-passed.json"):
                text = (evidence / name).read_text(encoding="utf-8")
                self.assertNotIn("sentinel-pi-smoke", text)

    def test_devpost_submission_drives_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-devpost"
            result = self._run_helper("--feature", "devpost-submission",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("VERIFY: PASS", result.stdout)
            summary = json.loads((evidence / "summary.json").read_text(
                encoding="utf-8"))
            self.assertEqual(summary["feature"], "devpost-submission")
            self.assertTrue(summary["all_ok"])
            self.assertEqual(summary["section_count"], 11)
            self.assertEqual(summary["blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertFalse(summary["submission_ready"])
            self.assertTrue(summary["claims_audit_clean"])
            self.assertTrue(summary["tamper_detected"])
            self.assertEqual(summary["pre_submission_blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            self.assertEqual(summary["deadline_kst"], "2026-11-05 11:00 KST")
            self.assertTrue((evidence / "devpost-submission.json").is_file())
            self.assertTrue((evidence / "devpost-submission.md").is_file())
            self.assertTrue((evidence / "transcript.txt").is_file())

    def test_devpost_submission_evidence_keeps_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "run-devpost-honesty"
            result = self._run_helper("--feature", "devpost-submission",
                                      evidence=evidence)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(
                (evidence / "devpost-submission.json").read_text(
                    encoding="utf-8"))
            self.assertFalse(payload["submission_ready"])
            self.assertEqual(payload["blockers"], [
                "pi_real_capture_pending", "sam_real_call_pending"])
            text = (evidence / "devpost-submission.md").read_text(
                encoding="utf-8")
            self.assertIn("SUBMISSION_READY: false", text)
            self.assertNotIn("SUBMISSION_READY: true", text)
            self.assertIn("모의 어댑터가 동작 중이고 SAM 실호출은 미실시", text)
            self.assertIn("데모 기준", text)

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
