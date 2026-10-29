"""qa.pre_submission 제출 전 전수 점검 하네스 테스트."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa.pre_submission import (
    BLOCKERS,
    build_current_data_panel,
    build_report,
    format_text_report,
    run_pre_submission_checks,
    validate_console_readiness,
    validate_data_panel,
    validate_pi_readiness,
    validate_pi_smoke,
    validate_sam_readiness,
    validate_sam_smoke,
    validate_devpost_report,
    validate_devpost_text,
    build_devpost_report,
    validate_runbook_report,
    validate_runbook_text,
    build_runbook_report,
    validate_story_report,
    validate_story_text,
    build_story_report,
    validate_en_summary_report,
    validate_en_summary_text,
    build_en_summary_report,
)

MISSING_PI_PROBE = {
    "available": False,
    "command": None,
    "candidates_checked": ["libcamera-still", "raspistill"],
}

READY_PI_PROBE = {
    "available": True,
    "command": "libcamera-still",
    "candidates_checked": ["libcamera-still", "raspistill"],
}

ROOT = Path(__file__).resolve().parent.parent


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_bytes(root: Path, rel: str, data: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _valid_devpost_text() -> str:
    return "\n".join([
        "# Argus — 제출 문안 패키지",
        "## 프로젝트 이름",
        "- Argus",
        "## 한 줄 소개",
        "- 재고실사 코파일럿",
        "## 소개",
        "- 가상 데모 데이터 기준이다.",
        "## 동작 방식",
        "- 촬영→계수→대조→리포트",
        "## Meta AI 도구 활용",
        "- 모의 어댑터가 동작 중이고 SAM 실호출은 미실시이다.",
        "- 가짜 transport 테스트로만 검증했다.",
        "- API 키를 Secure Vault 경유로 받은 뒤에만 전환한다.",
        "- 테마는 가안이다.",
        "## 기술 구성",
        "- Python",
        "## 데모 데이터",
        "- 데모 기준: 빈 6개 중 일치 4건, 불일치 2건이다.",
        "- 데모 기준: 절대 차이 6개, 순차이 0, 일치율 66.7%이다.",
        "- 위 수치는 실제 창고 성과가 아니다.",
        "## 해커톤 기간 중 신규 제작",
        "- 기간 안에 새로 작성했다.",
        "## 데모 영상",
        "- 컷 3은 Pi 실촬영 교체 예정인 플레이스홀더이다.",
        "## 현재 블로커와 제출 상태",
        "- `pi_real_capture_pending`",
        "- `sam_real_call_pending`",
        "- 현재 정답은 `SUBMISSION_READY: false` 다.",
        "- 공개 저장소: https://github.com/BoxLogoDev/argus-counts",
        "- 제출 마감은 2026-11-04 21:00 ET = 2026-11-05 11:00 KST이다.",
        "## 제출 전 교체할 항목",
        "- 교체할 예정이다.",
        "",
    ])


def _valid_runbook_text() -> str:
    return "\n".join([
        "# Argus 제출 런북",
        "현재는 모의 어댑터가 동작 중이며 Pi 검증 전이고 SAM 미실시 상태다.",
        "## 0. 현재 상태",
        "- `pi_real_capture_pending`",
        "- `sam_real_call_pending`",
        "- 현재 정답은 `SUBMISSION_READY: false` 다.",
        "## 1. 크레딧 확인",
        "- 확인 예정 시각은 2026-10-29 09:30이다.",
        "- 외부에서 확인한 뒤에만 `--credit-confirmed` 플래그를 붙인다.",
        "## 2. API 키",
        "- API 키는 Secure Vault 보안 경로로만 받는다.",
        "- 환경변수 이름은 `SAM_API_BASE_URL` 과 `SAM_API_KEY` 다.",
        "## 3. SAM 전환",
        "- `READY_FOR_LIVE_CALL: true` 가 된 뒤에만 첫 호출을 시작한다.",
        "## 4. Pi 촬영",
        "- Pi 실촬영 검증 전인 동안은 교체를 예정으로만 적는다.",
        "## 5. 최종 점검",
        "- `python3 -m unittest discover -s tests`",
        "- `python3 -m qa`",
        "- `python3 -m qa.standalone`",
        "- `python3 -m qa.claims_audit`",
        "- `python3 -m qa.pre_submission`",
        "- `python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor`",
        "- `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature all`",
        "- `python3 -m demo.render_video`",
        "## 6. 제출",
        "- 제출 마감은 2026-11-04 21:00 ET 다.",
        "- 같은 마감은 한국 시간으로 2026-11-05 11:00 KST 다.",
        "- 공개 저장소 `BoxLogoDev/argus-counts` 를 확인한다.",
        "",
    ])


def _valid_story_text() -> str:
    return "\n".join([
        "# Argus. 창고 재고실사 코파일럿",
        "테마는 Build for Your World를 전제로 한다. 주인님 최종 확정 전 가안이다.",
        "## 문제",
        "- 빈마다 세는 데 시간이 걸린다.",
        "## 해결",
        "- 촬영하고 세고 대조해 리포트를 만든다.",
        "## 이번에 만든 것과 기존에 있던 것",
        "- 이번에 만든 것은 이 저장소의 모든 코드와 문서이며 2026-10-27 이후 해커톤 기간에 새로 작성했다.",
        "## Meta AI 도구 활용",
        "- 현재는 모의(mock) 어댑터로 동작한다.",
        "- SAM 3.1 실호출은 아직 하지 않았다.",
        "- 모의 결과를 실호출 결과로 주장하지 않는다.",
        "- Pi 실기 카메라 연동은 아직 검증 전이다.",
        "## 기술 깊이",
        "- 예시는 전부 가상 데모 데이터다.",
        "- 데모 빈은 6개다.",
        "- 일치는 4건이다.",
        "- 불일치는 2건이다.",
        "- 절대 차이 합계는 6이다.",
        "- 일치율은 66.7%다.",
        "## 영향",
        "- 데모 기준. 빈 6개 중 불일치 2건과 절대 차이 6개를 한 번의 대조로 정리한다.",
        "## 현재 상태",
        "- `pi_real_capture_pending` — Pi 검증 전이다.",
        "- `sam_real_call_pending` — SAM 미실시이다.",
        "- 현재 정답은 `SUBMISSION_READY: false` 다.",
        "",
    ])


def _valid_en_summary_text() -> str:
    return "\n".join([
        "# Argus — Warehouse Stock-Count Copilot",
        "Theme: Build for Your World — tentative, pending final confirmation.",
        "## Problem",
        "- Manual bin counting is slow.",
        "## Workflow",
        "1. Capture. Photograph a bin with the terminal.",
        "## What we built vs. what already existed",
        "- All code and documents in this repository.",
        "- Newly written during the hackathon period starting 2026-10-27.",
        "## Meta AI tools",
        "- A live SAM 3.1 call has NOT been made yet.",
        "- Argus is currently running on the mock adapter.",
        "- Mock results are never claimed as live results.",
        "- Pi device camera integration is not yet verified.",
        "## Technical depth",
        "- The reconciliation engine produces per-bin results.",
        "## Demo data",
        "- There are 6 demo bins.",
        "- 4 bins matched.",
        "- 2 bins mismatched.",
        "- Total absolute delta is 6.",
        "- Match rate is 66.7%.",
        "## Impact",
        "- Demo basis: 2 mismatches out of 6 bins are organised in one pass.",
        "## Current status",
        "- `pi_real_capture_pending` — Pi device camera integration is not yet verified.",
        "- `sam_real_call_pending` — A live SAM 3.1 call has NOT been made yet.",
        "- `SUBMISSION_READY: false`",
        "",
    ])


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
    _write(root, "docs/submission-story.md", _valid_story_text())
    _write(root, "docs/submission-summary-en.md", _valid_en_summary_text())
    _write(root, "docs/demo-script.md", "Pi 실촬영 교체 예정, 모의 표기 확인\n")
    _write(root, "docs/submission-runbook.md", _valid_runbook_text())
    _write(root, "docs/devpost-submission.md", _valid_devpost_text())
    _write(root, "demo/assets/captions.srt", "1\n00:00:00,000 --> 00:00:18,000\nArgus\n")
    _write(root, "demo/assets/captions.vtt", "WEBVTT\n")
    _write(root, "demo/assets/shot-list.json", json.dumps({"total_seconds": 180, "cut_count": 9}))
    _write(
        root,
        "demo/assets/assembly.json",
        json.dumps(
            {
                "total_seconds": 180,
                "segment_count": 9,
                "segments": [{"index": 3, "placeholder": True}]
                + [{"index": i, "placeholder": False} for i in (1, 2, 4, 5, 6, 7, 8, 9)],
            }
        ),
    )
    _write(
        root,
        "demo/assets/narration.json",
        json.dumps({"total_seconds": 180, "pace_warnings": []}),
    )
    _write(
        root,
        "demo/assets/captures/capture-manifest.json",
        json.dumps({"all_ok": True, "capture_count": 4}),
    )
    _write_bytes(root, "demo/assets/argus-demo-draft.mp4", b"\x00" * 100_001)


class BlockerTests(unittest.TestCase):
    def test_blockers_are_the_two_known_pending_items(self):
        ids = [b["id"] for b in BLOCKERS]
        self.assertEqual(ids, ["pi_real_capture_pending", "sam_real_call_pending"])

    def test_real_root_mechanical_pass_but_not_submission_ready(self):
        result = run_pre_submission_checks(ROOT)
        self.assertTrue(result["mechanical_pass"], result["checks"])
        self.assertEqual(result["passed"], result["total"])
        self.assertFalse(result["submission_ready"])
        self.assertEqual(len(result["blockers"]), 2)


class ReportTests(unittest.TestCase):
    def test_build_report_is_json_serializable_and_honest(self):
        report = build_report(ROOT)
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertIn("submission_ready", encoded)
        self.assertFalse(report["submission_ready"])
        self.assertTrue(any("모의" in line for line in report["honesty"]))
        self.assertTrue(any("데모 기준" in line for line in report["honesty"]))

    def test_format_text_report_shows_blockers_and_not_ready(self):
        text = format_text_report(build_report(ROOT))
        self.assertIn("BLOCKERS: 2", text)
        self.assertIn("pi_real_capture_pending", text)
        self.assertIn("sam_real_call_pending", text)
        self.assertIn("SUBMISSION_READY: false", text)


class MinimalRootTests(unittest.TestCase):
    def test_minimal_root_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            result = run_pre_submission_checks(root)
            self.assertTrue(result["mechanical_pass"], result["checks"])
            self.assertFalse(result["submission_ready"])

    def test_missing_demo_asset_fails_present_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            (root / "demo/assets/captions.vtt").unlink()
            result = run_pre_submission_checks(root)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["demo_assets_present"])
            self.assertFalse(result["mechanical_pass"])

    def test_narration_pace_warning_fails_consistency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(
                root,
                "demo/assets/narration.json",
                json.dumps({"total_seconds": 180, "pace_warnings": [1]}),
            )
            result = run_pre_submission_checks(root)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["demo_assets_consistent"])

    def test_assembly_placeholder_must_be_cut3_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(
                root,
                "demo/assets/assembly.json",
                json.dumps(
                    {
                        "total_seconds": 180,
                        "segment_count": 9,
                        "segments": [{"index": 4, "placeholder": True}],
                    }
                ),
            )
            result = run_pre_submission_checks(root)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["demo_assets_consistent"])

    def test_small_video_fails_video_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write_bytes(root, "demo/assets/argus-demo-draft.mp4", b"\x00" * 10)
            result = run_pre_submission_checks(root)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["video_draft_present"])


class DataPanelTests(unittest.TestCase):
    def test_current_panel_is_valid(self):
        self.assertEqual(validate_data_panel(build_current_data_panel()), [])

    def test_validate_detects_cut3_tamper(self):
        panel = build_current_data_panel()
        panel[3] = ["가짜 실촬영 데이터"]
        problems = validate_data_panel(panel)
        self.assertTrue(any("cut 3" in p for p in problems), problems)

    def test_validate_detects_cut5_missing_bin(self):
        panel = build_current_data_panel()
        panel[5] = [line for line in panel[5] if "A-01-01" not in line]
        problems = validate_data_panel(panel)
        self.assertTrue(any("cut 5" in p for p in problems), problems)

    def test_video_check_detail_includes_data_panel(self):
        result = run_pre_submission_checks(ROOT)
        by_name = {c.name: c for c in result["checks"]}
        video = by_name["video_draft_present"]
        self.assertTrue(video.passed, video.detail)
        self.assertIn("data_panel_cuts=9", video.detail)


class ReadinessIntegrationTests(unittest.TestCase):
    def test_real_root_includes_readiness_checks_and_section(self):
        result = run_pre_submission_checks(
            ROOT, sam_env={}, pi_probe=MISSING_PI_PROBE
        )
        names = [c.name for c in result["checks"]]
        self.assertEqual(result["total"], 15)
        self.assertIn("sam_readiness_consistent", names)
        self.assertIn("pi_readiness_consistent", names)
        self.assertIn("console_readiness_consistent", names)
        self.assertTrue(result["mechanical_pass"], result["checks"])
        sam_ids = [b["id"] for b in result["readiness"]["sam"]["blockers"]]
        self.assertEqual(
            sam_ids,
            ["sam_credit_not_confirmed", "sam_base_url_missing", "sam_api_key_missing"],
        )
        pi_ids = [b["id"] for b in result["readiness"]["pi"]["blockers"]]
        self.assertEqual(
            pi_ids, ["pi_device_arrival_not_confirmed", "pi_camera_command_missing"]
        )
        self.assertFalse(result["readiness"]["sam"]["ready_for_live_call"])
        self.assertFalse(result["readiness"]["pi"]["ready_for_real_capture"])
        console = result["readiness"]["console"]
        self.assertEqual(console["blocker_count"], 5)
        self.assertFalse(console["overall_ready"])
        self.assertFalse(console["sam_ready"])
        self.assertFalse(console["pi_ready"])
        self.assertEqual(console["sam_blockers"], sam_ids)
        self.assertEqual(console["pi_blockers"], pi_ids)

    def test_sam_ready_fake_env_passes_but_still_not_submission_ready(self):
        env = {"SAM_API_BASE_URL": "https://example.invalid", "SAM_API_KEY": "fake"}
        result = run_pre_submission_checks(
            ROOT, sam_env=env, sam_credit_confirmed=True, pi_probe=MISSING_PI_PROBE
        )
        by_name = {c.name: c.passed for c in result["checks"]}
        self.assertTrue(by_name["sam_readiness_consistent"])
        self.assertTrue(result["readiness"]["sam"]["ready_for_live_call"])
        self.assertEqual(result["readiness"]["sam"]["blockers"], [])
        self.assertFalse(result["submission_ready"])

    def test_sam_sentinel_values_do_not_leak_into_report(self):
        sentinel = "sentinel-value-must-not-appear"
        env = {"SAM_API_BASE_URL": sentinel, "SAM_API_KEY": sentinel}
        report = build_report(ROOT, sam_env=env, pi_probe=MISSING_PI_PROBE)
        encoded = json.dumps(report, ensure_ascii=False)
        self.assertNotIn(sentinel, encoded)

    def test_pi_ready_fake_probe_passes(self):
        result = run_pre_submission_checks(
            ROOT, sam_env={}, pi_probe=READY_PI_PROBE, pi_device_confirmed=True
        )
        by_name = {c.name: c.passed for c in result["checks"]}
        self.assertTrue(by_name["pi_readiness_consistent"])
        self.assertTrue(result["readiness"]["pi"]["ready_for_real_capture"])
        self.assertEqual(result["readiness"]["pi"]["blockers"], [])

    def test_validate_sam_detects_ready_contradiction(self):
        report = {
            "base_url_present": True,
            "api_key_present": True,
            "credit_confirmed": False,
            "ready_for_live_call": True,
            "would_select_live": True,
            "blockers": [{"id": "sam_credit_not_confirmed"}],
            "honesty": ["준비 완료는 실호출 성공을 뜻하지 않는다"],
        }
        problems = validate_sam_readiness(report)
        self.assertTrue(problems)

    def test_validate_sam_detects_blocker_order(self):
        report = {
            "base_url_present": False,
            "api_key_present": False,
            "credit_confirmed": True,
            "ready_for_live_call": False,
            "would_select_live": False,
            "blockers": [
                {"id": "sam_api_key_missing"},
                {"id": "sam_base_url_missing"},
            ],
            "honesty": ["준비 완료는 실호출 성공을 뜻하지 않는다"],
        }
        problems = validate_sam_readiness(report)
        self.assertTrue(any("subsequence" in p for p in problems), problems)

    def test_validate_pi_detects_missing_submission_blocker_link(self):
        report = {
            "device_confirmed": False,
            "camera_available": False,
            "ready_for_real_capture": False,
            "blockers": [
                {"id": "pi_device_arrival_not_confirmed"},
                {"id": "pi_camera_command_missing"},
            ],
            "honesty": ["준비 완료는 Pi 실촬영 성공을 뜻하지 않는다"],
        }
        problems = validate_pi_readiness(report, blockers=[])
        self.assertTrue(
            any("pi_real_capture_pending" in p for p in problems), problems
        )

    def test_validate_pi_detects_ready_mismatch(self):
        report = {
            "device_confirmed": True,
            "camera_available": False,
            "ready_for_real_capture": True,
            "blockers": [],
            "honesty": ["준비 완료는 Pi 실촬영 성공을 뜻하지 않는다"],
        }
        problems = validate_pi_readiness(report)
        self.assertTrue(problems)

    def test_minimal_root_with_blocked_readiness_still_mechanical_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            result = run_pre_submission_checks(
                root, sam_env={}, pi_probe=MISSING_PI_PROBE
            )
            self.assertEqual(result["total"], 15)
            self.assertTrue(result["mechanical_pass"], result["checks"])
            self.assertFalse(result["submission_ready"])

    def test_console_ready_fake_env_and_probe_still_not_submission_ready(self):
        env = {"SAM_API_BASE_URL": "https://example.invalid", "SAM_API_KEY": "fake"}
        result = run_pre_submission_checks(
            ROOT,
            sam_env=env,
            sam_credit_confirmed=True,
            pi_probe=READY_PI_PROBE,
            pi_device_confirmed=True,
        )
        by_name = {c.name: c.passed for c in result["checks"]}
        self.assertTrue(by_name["console_readiness_consistent"])
        console = result["readiness"]["console"]
        self.assertTrue(console["overall_ready"])
        self.assertEqual(console["blocker_count"], 0)
        self.assertEqual(console["sam_blockers"], [])
        self.assertEqual(console["pi_blockers"], [])
        self.assertFalse(result["submission_ready"])

    def test_validate_console_detects_overall_contradiction(self):
        from console.readiness import build_readiness

        report = build_readiness(env={}, pi_probe=MISSING_PI_PROBE)
        self.assertEqual(validate_console_readiness(report), [])
        report["overall_ready"] = True
        problems = validate_console_readiness(report)
        self.assertTrue(any("overall_ready" in p for p in problems), problems)

    def test_validate_console_detects_blocker_count_mismatch(self):
        from console.readiness import build_readiness

        report = build_readiness(env={}, pi_probe=MISSING_PI_PROBE)
        report["blocker_count"] = 99
        problems = validate_console_readiness(report)
        self.assertTrue(any("blocker_count" in p for p in problems), problems)

    def test_validate_console_detects_cross_mismatch_with_sam_report(self):
        from console.readiness import build_readiness
        from qa.sam_readiness import check_readiness as check_sam

        console = build_readiness(env={}, pi_probe=MISSING_PI_PROBE)
        sam_report = check_sam(
            env={"SAM_API_BASE_URL": "https://example.invalid", "SAM_API_KEY": "fake"},
            credit_confirmed=True,
        )
        problems = validate_console_readiness(console, sam_report=sam_report)
        self.assertTrue(any("sam" in p for p in problems), problems)

    def test_validate_console_detects_missing_honesty(self):
        from console.readiness import build_readiness

        report = build_readiness(env={}, pi_probe=MISSING_PI_PROBE)
        report["honesty"] = ["다른 문구만 있다"]
        problems = validate_console_readiness(report)
        self.assertTrue(any("honesty" in p for p in problems), problems)

    def test_real_root_includes_smoke_check_and_section(self):
        result = run_pre_submission_checks(
            ROOT, sam_env={}, pi_probe=MISSING_PI_PROBE
        )
        names = [c.name for c in result["checks"]]
        self.assertIn("sam_smoke_consistent", names)
        by_name = {c.name: c for c in result["checks"]}
        self.assertTrue(by_name["sam_smoke_consistent"].passed)
        self.assertIn("fake_calls=0", by_name["sam_smoke_consistent"].detail)
        smoke = result["readiness"]["smoke"]
        self.assertEqual(smoke["status"], "blocked")
        self.assertFalse(smoke["attempted"])
        self.assertFalse(smoke["ready_for_live_call"])
        self.assertIsNone(smoke["counted_qty"])
        self.assertEqual(
            [b["id"] for b in smoke["blockers"]],
            [b["id"] for b in result["readiness"]["sam"]["blockers"]],
        )
        self.assertFalse(result["submission_ready"])

    def test_smoke_ready_fake_env_passes_with_fake_counter(self):
        env = {"SAM_API_BASE_URL": "https://example.invalid", "SAM_API_KEY": "fake"}
        result = run_pre_submission_checks(
            ROOT,
            sam_env=env,
            sam_credit_confirmed=True,
            pi_probe=MISSING_PI_PROBE,
        )
        by_name = {c.name: c.passed for c in result["checks"]}
        self.assertTrue(by_name["sam_smoke_consistent"])
        smoke = result["readiness"]["smoke"]
        self.assertEqual(smoke["status"], "passed")
        self.assertTrue(smoke["attempted"])
        self.assertEqual(smoke["source"], "sam")
        self.assertEqual(smoke["counted_qty"], 5)
        self.assertEqual(smoke["book_qty"], 8)
        self.assertEqual(smoke["diff"], -3)
        self.assertFalse(result["submission_ready"])

    def test_validate_smoke_detects_blocked_attempted(self):
        from qa.sam_smoke import run_smoke

        report = run_smoke(env={}, credit_confirmed=False)
        self.assertEqual(validate_sam_smoke(report), [])
        report["attempted"] = True
        problems = validate_sam_smoke(report)
        self.assertTrue(any("attempted" in p for p in problems), problems)

    def test_validate_smoke_detects_cross_mismatch_with_sam_report(self):
        from qa.sam_readiness import check_readiness as check_sam
        from qa.sam_smoke import run_smoke

        smoke = run_smoke(env={}, credit_confirmed=False)
        sam_report = check_sam(
            env={"SAM_API_BASE_URL": "https://example.invalid", "SAM_API_KEY": "fake"},
            credit_confirmed=True,
        )
        problems = validate_sam_smoke(smoke, sam_report=sam_report)
        self.assertTrue(any("sam smoke" in p for p in problems), problems)

    def test_validate_smoke_detects_passed_diff_tamper(self):
        from qa.sam_smoke import run_smoke

        class _Counter:
            def count(self, bin_id, image_ref=None):
                from types import SimpleNamespace

                return SimpleNamespace(source="sam", counted_qty=5)

        env = {"SAM_API_BASE_URL": "https://example.invalid", "SAM_API_KEY": "fake"}
        report = run_smoke(
            env=env, credit_confirmed=True, counter=_Counter()
        )
        self.assertEqual(validate_sam_smoke(report), [])
        report["diff"] = 99
        problems = validate_sam_smoke(report)
        self.assertTrue(any("diff" in p for p in problems), problems)

    def test_real_root_includes_pi_smoke_check_and_section(self):
        result = run_pre_submission_checks(
            ROOT, sam_env={}, pi_probe=MISSING_PI_PROBE
        )
        names = [c.name for c in result["checks"]]
        self.assertIn("pi_smoke_consistent", names)
        by_name = {c.name: c for c in result["checks"]}
        self.assertTrue(by_name["pi_smoke_consistent"].passed)
        self.assertIn("fake_calls=0", by_name["pi_smoke_consistent"].detail)
        pi_smoke = result["readiness"]["pi_smoke"]
        self.assertEqual(pi_smoke["status"], "blocked")
        self.assertFalse(pi_smoke["attempted"])
        self.assertFalse(pi_smoke["ready_for_real_capture"])
        self.assertIsNone(pi_smoke["counted_qty"])
        self.assertEqual(
            [b["id"] for b in pi_smoke["blockers"]],
            [b["id"] for b in result["readiness"]["pi"]["blockers"]],
        )
        self.assertFalse(result["submission_ready"])

    def test_pi_smoke_ready_fake_probe_passes_with_fake_session(self):
        result = run_pre_submission_checks(
            ROOT, sam_env={}, pi_probe=READY_PI_PROBE, pi_device_confirmed=True
        )
        by_name = {c.name: c.passed for c in result["checks"]}
        self.assertTrue(by_name["pi_smoke_consistent"])
        pi_smoke = result["readiness"]["pi_smoke"]
        self.assertEqual(pi_smoke["status"], "passed")
        self.assertTrue(pi_smoke["attempted"])
        self.assertEqual(pi_smoke["capture_source"], "pi-camera")
        self.assertEqual(pi_smoke["source"], "mock")
        self.assertEqual(pi_smoke["counted_qty"], 5)
        self.assertEqual(pi_smoke["book_qty"], 8)
        self.assertEqual(pi_smoke["diff"], -3)
        self.assertTrue(pi_smoke["photo_sha256"])
        self.assertFalse(result["submission_ready"])

    def test_validate_pi_smoke_detects_blocked_attempted(self):
        from qa.pi_smoke import run_smoke

        report = run_smoke(device_confirmed=False, which=lambda name: None)
        self.assertEqual(validate_pi_smoke(report), [])
        report["attempted"] = True
        problems = validate_pi_smoke(report)
        self.assertTrue(any("attempted" in p for p in problems), problems)

    def test_validate_pi_smoke_detects_cross_mismatch_with_pi_report(self):
        from qa.pi_readiness import check_readiness as check_pi
        from qa.pi_smoke import run_smoke

        pi_smoke = run_smoke(device_confirmed=False, which=lambda name: None)
        pi_report = check_pi(probe=READY_PI_PROBE, device_confirmed=True)
        problems = validate_pi_smoke(pi_smoke, pi_report=pi_report)
        self.assertTrue(any("pi smoke" in p for p in problems), problems)

    def test_validate_pi_smoke_detects_passed_diff_tamper(self):
        from qa.pi_smoke import run_smoke

        def _session(output_dir, bin_ids=None, session_id=None, runner=None, which=None):
            return {
                "session_id": "PI-SMOKE",
                "source": "mock",
                "capture_source": "pi-camera",
                "bins": [
                    {
                        "bin_id": "A-01-02",
                        "book_qty": 8,
                        "counted_qty": 5,
                        "diff": -3,
                        "photo": {"sha256": "f" * 64, "image_ref": "A-01-02.jpg"},
                    }
                ],
            }

        def _libcamera(name):
            return "/usr/bin/libcamera-still" if name == "libcamera-still" else None

        report = run_smoke(
            device_confirmed=True, which=_libcamera, session_fn=_session
        )
        self.assertEqual(validate_pi_smoke(report), [])
        report["diff"] = 99
        problems = validate_pi_smoke(report)
        self.assertTrue(any("diff" in p for p in problems), problems)


class DevpostIntegrationTests(unittest.TestCase):
    def test_real_root_includes_devpost_check_and_section(self):
        result = run_pre_submission_checks(ROOT, sam_env={}, pi_probe=MISSING_PI_PROBE)
        names = [c.name for c in result["checks"]]
        self.assertIn("devpost_consistent", names)
        by_name = {c.name: c for c in result["checks"]}
        self.assertTrue(by_name["devpost_consistent"].passed, by_name["devpost_consistent"].detail)
        self.assertIn("section_count=11", by_name["devpost_consistent"].detail)
        devpost = result["readiness"]["devpost"]
        self.assertEqual(devpost["section_count"], 11)
        self.assertEqual(devpost["blockers"], ["pi_real_capture_pending", "sam_real_call_pending"])
        self.assertFalse(devpost["submission_ready"])
        self.assertTrue(devpost["claims_audit_clean"])
        self.assertFalse(result["submission_ready"])

    def test_validate_devpost_text_accepts_valid_and_detects_tamper(self):
        text = _valid_devpost_text()
        self.assertEqual(validate_devpost_text(text), [])
        tampered = text.replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1)
        problems = validate_devpost_text(tampered)
        self.assertTrue(any("SUBMISSION_READY" in p for p in problems), problems)

    def test_validate_devpost_text_detects_missing_section(self):
        text = _valid_devpost_text().replace("## 기술 구성", "## 구성", 1)
        problems = validate_devpost_text(text)
        self.assertTrue(any("section" in p for p in problems), problems)

    def test_validate_devpost_report_detects_contradictions(self):
        report = build_devpost_report(ROOT)
        self.assertEqual(validate_devpost_report(report), [])
        report["submission_ready"] = True
        problems = validate_devpost_report(report)
        self.assertTrue(any("submission_ready" in p for p in problems), problems)
        report2 = build_devpost_report(ROOT)
        report2["blockers"] = ["sam_real_call_pending", "pi_real_capture_pending"]
        problems2 = validate_devpost_report(report2)
        self.assertTrue(any("blockers" in p for p in problems2), problems2)

    def test_minimal_root_tampered_devpost_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(root, "docs/devpost-submission.md",
                   _valid_devpost_text().replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1))
            result = run_pre_submission_checks(root, sam_env={}, pi_probe=MISSING_PI_PROBE)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["devpost_consistent"])
            self.assertFalse(result["mechanical_pass"])


class RunbookIntegrationTests(unittest.TestCase):
    def test_real_root_includes_runbook_check_and_section(self):
        result = run_pre_submission_checks(ROOT, sam_env={}, pi_probe=MISSING_PI_PROBE)
        names = [c.name for c in result["checks"]]
        self.assertIn("runbook_consistent", names)
        by_name = {c.name: c for c in result["checks"]}
        self.assertTrue(by_name["runbook_consistent"].passed, by_name["runbook_consistent"].detail)
        self.assertIn("section_count=7", by_name["runbook_consistent"].detail)
        self.assertIn("final_commands=8", by_name["runbook_consistent"].detail)
        runbook = result["readiness"]["runbook"]
        self.assertEqual(runbook["section_count"], 7)
        self.assertEqual(runbook["blockers"], ["pi_real_capture_pending", "sam_real_call_pending"])
        self.assertFalse(runbook["submission_ready"])
        self.assertTrue(runbook["claims_audit_clean"])
        self.assertEqual(runbook["final_command_count"], 8)
        self.assertFalse(result["submission_ready"])

    def test_validate_runbook_text_accepts_valid_and_detects_tamper(self):
        text = _valid_runbook_text()
        self.assertEqual(validate_runbook_text(text), [])
        tampered = text.replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1)
        problems = validate_runbook_text(tampered)
        self.assertTrue(any("SUBMISSION_READY" in p for p in problems), problems)

    def test_validate_runbook_text_detects_missing_section(self):
        text = _valid_runbook_text().replace("## 3. SAM 전환", "## 3. 전환", 1)
        problems = validate_runbook_text(text)
        self.assertTrue(any("section" in p for p in problems), problems)

    def test_validate_runbook_report_detects_contradictions(self):
        report = build_runbook_report(ROOT)
        self.assertEqual(validate_runbook_report(report), [])
        report["submission_ready"] = True
        problems = validate_runbook_report(report)
        self.assertTrue(any("submission_ready" in p for p in problems), problems)
        report2 = build_runbook_report(ROOT)
        report2["blockers"] = ["sam_real_call_pending", "pi_real_capture_pending"]
        problems2 = validate_runbook_report(report2)
        self.assertTrue(any("blockers" in p for p in problems2), problems2)

    def test_minimal_root_tampered_runbook_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(root, "docs/submission-runbook.md",
                   _valid_runbook_text().replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1))
            result = run_pre_submission_checks(root, sam_env={}, pi_probe=MISSING_PI_PROBE)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["runbook_consistent"])
            self.assertFalse(result["mechanical_pass"])


class StoryIntegrationTests(unittest.TestCase):
    def test_real_root_includes_story_check_and_section(self):
        result = run_pre_submission_checks(ROOT, sam_env={}, pi_probe=MISSING_PI_PROBE)
        names = [c.name for c in result["checks"]]
        self.assertIn("story_consistent", names)
        by_name = {c.name: c for c in result["checks"]}
        self.assertTrue(by_name["story_consistent"].passed, by_name["story_consistent"].detail)
        self.assertIn("section_count=7", by_name["story_consistent"].detail)
        story = result["readiness"]["story"]
        self.assertEqual(story["section_count"], 7)
        self.assertEqual(story["blockers"], ["pi_real_capture_pending", "sam_real_call_pending"])
        self.assertFalse(story["submission_ready"])
        self.assertTrue(story["claims_audit_clean"])
        self.assertFalse(result["submission_ready"])

    def test_validate_story_text_accepts_valid_and_detects_tamper(self):
        text = _valid_story_text()
        self.assertEqual(validate_story_text(text), [])
        tampered = text.replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1)
        problems = validate_story_text(tampered)
        self.assertTrue(any("SUBMISSION_READY" in p for p in problems), problems)

    def test_validate_story_text_detects_missing_section(self):
        text = _valid_story_text().replace("## 현재 상태", "## 상태", 1)
        problems = validate_story_text(text)
        self.assertTrue(any("section" in p for p in problems), problems)

    def test_validate_story_report_detects_contradictions(self):
        report = build_story_report(ROOT)
        self.assertEqual(validate_story_report(report), [])
        report["submission_ready"] = True
        problems = validate_story_report(report)
        self.assertTrue(any("submission_ready" in p for p in problems), problems)
        report2 = build_story_report(ROOT)
        report2["blockers"] = ["sam_real_call_pending", "pi_real_capture_pending"]
        problems2 = validate_story_report(report2)
        self.assertTrue(any("blockers" in p for p in problems2), problems2)

    def test_minimal_root_tampered_story_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(root, "docs/submission-story.md",
                   _valid_story_text().replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1))
            result = run_pre_submission_checks(root, sam_env={}, pi_probe=MISSING_PI_PROBE)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["story_consistent"])
            self.assertFalse(result["mechanical_pass"])


class EnSummaryIntegrationTests(unittest.TestCase):
    def test_real_root_includes_en_summary_check_and_section(self):
        result = run_pre_submission_checks(ROOT, sam_env={}, pi_probe=MISSING_PI_PROBE)
        names = [c.name for c in result["checks"]]
        self.assertIn("en_summary_consistent", names)
        by_name = {c.name: c for c in result["checks"]}
        self.assertTrue(by_name["en_summary_consistent"].passed, by_name["en_summary_consistent"].detail)
        self.assertIn("section_count=8", by_name["en_summary_consistent"].detail)
        en = result["readiness"]["en_summary"]
        self.assertEqual(en["section_count"], 8)
        self.assertEqual(en["blockers"], ["pi_real_capture_pending", "sam_real_call_pending"])
        self.assertFalse(en["submission_ready"])
        self.assertTrue(en["claims_audit_clean"])
        self.assertFalse(result["submission_ready"])

    def test_validate_en_summary_text_accepts_valid_and_detects_tamper(self):
        text = _valid_en_summary_text()
        self.assertEqual(validate_en_summary_text(text), [])
        tampered = text.replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1)
        problems = validate_en_summary_text(tampered)
        self.assertTrue(any("SUBMISSION_READY" in p for p in problems), problems)

    def test_validate_en_summary_text_detects_missing_section(self):
        text = _valid_en_summary_text().replace("## Current status", "## Status", 1)
        problems = validate_en_summary_text(text)
        self.assertTrue(any("section" in p for p in problems), problems)

    def test_validate_en_summary_report_detects_contradictions(self):
        report = build_en_summary_report(ROOT)
        self.assertEqual(validate_en_summary_report(report), [])
        report["submission_ready"] = True
        problems = validate_en_summary_report(report)
        self.assertTrue(any("submission_ready" in p for p in problems), problems)
        report2 = build_en_summary_report(ROOT)
        report2["blockers"] = ["sam_real_call_pending", "pi_real_capture_pending"]
        problems2 = validate_en_summary_report(report2)
        self.assertTrue(any("blockers" in p for p in problems2), problems2)

    def test_minimal_root_tampered_en_summary_fails_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_root(root)
            _write(root, "docs/submission-summary-en.md",
                   _valid_en_summary_text().replace("SUBMISSION_READY: false", "SUBMISSION_READY: true", 1))
            result = run_pre_submission_checks(root, sam_env={}, pi_probe=MISSING_PI_PROBE)
            by_name = {c.name: c.passed for c in result["checks"]}
            self.assertFalse(by_name["en_summary_consistent"])
            self.assertFalse(result["mechanical_pass"])


if __name__ == "__main__":
    unittest.main()
