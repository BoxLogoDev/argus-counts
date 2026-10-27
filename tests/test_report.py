"""terminal.report 테스트: 조치 우선순위·영향 수치·텍스트 리포트·CLI."""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from terminal.report import (
    action_hint,
    build_actions,
    build_report_payload,
    format_text_report,
    impact_line,
    main,
)
from terminal.simulator import run_simulation


def _custom_report(bins, source="mock"):
    matched = sum(1 for b in bins if b["verdict"] == "match")
    return {
        "session_id": "T-1",
        "generated_at": "2026-10-27T00:00:00+00:00",
        "source": source,
        "bins": bins,
        "summary": {
            "counted_bins": len(bins),
            "matched": matched,
            "mismatched": len(bins) - matched,
            "match_rate": matched / len(bins) if bins else 0.0,
            "abs_diff_total": sum(abs(b["diff"]) for b in bins),
            "net_diff": sum(b["diff"] for b in bins),
        },
    }


class BuildActionsTest(unittest.TestCase):
    def setUp(self):
        self.report = run_simulation(session_id="TEST-REPORT")

    def test_demo_actions_exact(self):
        actions = build_actions(self.report)
        self.assertEqual(len(actions), 2)
        first, second = actions
        # |diff| 동률(3)이라 bin_id 오름차순: A-01-02가 1순위
        self.assertEqual(first["bin_id"], "A-01-02")
        self.assertEqual(first["priority"], 1)
        self.assertEqual(first["verdict"], "short")
        self.assertEqual(first["diff"], -3)
        self.assertEqual(first["abs_diff"], 3)
        self.assertEqual(first["book_qty"], 8)
        self.assertEqual(first["counted_qty"], 5)
        self.assertEqual(second["bin_id"], "B-01-02")
        self.assertEqual(second["priority"], 2)
        self.assertEqual(second["diff"], 3)

    def test_sorted_by_abs_diff_desc(self):
        report = _custom_report(
            [
                {"bin_id": "X-1", "item_code": "I-1", "book_qty": 10,
                 "counted_qty": 7, "diff": -3, "verdict": "short"},
                {"bin_id": "X-2", "item_code": "I-2", "book_qty": 10,
                 "counted_qty": 15, "diff": 5, "verdict": "over"},
                {"bin_id": "X-3", "item_code": "I-3", "book_qty": 4,
                 "counted_qty": 4, "diff": 0, "verdict": "match"},
            ]
        )
        actions = build_actions(report)
        self.assertEqual([a["bin_id"] for a in actions], ["X-2", "X-1"])

    def test_no_differences(self):
        report = _custom_report(
            [{"bin_id": "X-1", "item_code": "I-1", "book_qty": 4,
              "counted_qty": 4, "diff": 0, "verdict": "match"}]
        )
        self.assertEqual(build_actions(report), [])
        self.assertIn("차이 없음", format_text_report(report))


class HintAndImpactTest(unittest.TestCase):
    def test_action_hints(self):
        self.assertIn("재촬영", action_hint("short"))
        self.assertIn("오적재", action_hint("over"))
        self.assertEqual(action_hint("match"), "")

    def test_impact_line_mock_marked_demo(self):
        line = impact_line(run_simulation(session_id="TEST-IMPACT"))
        self.assertTrue(line.startswith("데모 기준"))
        self.assertIn("불일치 2건", line)
        self.assertIn("절대 차이 6개", line)
        self.assertIn("66.7%", line)

    def test_impact_line_sam_has_no_demo_prefix(self):
        report = run_simulation(session_id="TEST-IMPACT-SAM")
        report = {**report, "source": "sam"}
        line = impact_line(report)
        self.assertNotIn("데모 기준", line)
        self.assertIn("불일치 2건", line)


class FormatAndPayloadTest(unittest.TestCase):
    def setUp(self):
        self.report = run_simulation(session_id="TEST-FMT")

    def test_format_text_report(self):
        text = format_text_report(self.report)
        self.assertIn("Argus 차이 리포트", text)
        self.assertIn("모의", text)
        self.assertIn("조치 우선순위", text)
        self.assertIn("A-01-02", text)
        self.assertIn("B-01-02", text)
        self.assertIn(impact_line(self.report), text)

    def test_payload_shape(self):
        payload = build_report_payload(self.report)
        self.assertEqual(payload["session_id"], "TEST-FMT")
        self.assertEqual(payload["source"], "mock")
        self.assertEqual(len(payload["actions"]), 2)
        self.assertEqual(payload["impact_line"], impact_line(self.report))
        self.assertEqual(payload["summary"]["abs_diff_total"], 6)


class CliTest(unittest.TestCase):
    def test_main_json(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--json", "--session-id", "TEST-CLI"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(len(payload["actions"]), 2)
        self.assertEqual(payload["session_id"], "TEST-CLI")

    def test_main_text(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main(["--session-id", "TEST-CLI-TXT"])
        self.assertEqual(rc, 0)
        self.assertIn("Argus 차이 리포트", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
