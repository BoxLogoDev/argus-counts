"""qa.pre_submission 제출 전 전수 점검 하네스 테스트."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qa.pre_submission import (
    BLOCKERS,
    build_report,
    format_text_report,
    run_pre_submission_checks,
)

ROOT = Path(__file__).resolve().parent.parent


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_bytes(root: Path, rel: str, data: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


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


if __name__ == "__main__":
    unittest.main()
