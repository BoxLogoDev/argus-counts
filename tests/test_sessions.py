"""다중 세션 목록 단위 테스트.

데모 세션 3개 기준: DEMO-20261027-A(일치4·불일치2·절대차이6),
DEMO-20261027-B(전부 일치), DEMO-20261026-A(일치3·불일치3·절대차이7).
환경변수를 비워 항상 모의 어댑터로 결정적으로 돌린다.
"""
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)

from console.render import render_sessions_html
from console.server import create_handler
from console.sessions import (
    build_session_list_view,
    get_session_report,
    list_session_reports,
)
from terminal.demo_sessions import counted_qty_for, demo_session_specs
from terminal.simulator import run_simulation


def _mock_env():
    return mock.patch.dict(os.environ, {}, clear=True)


class DemoSessionsTest(unittest.TestCase):
    def test_specs_order_and_ids(self):
        specs = demo_session_specs()
        self.assertEqual(
            [s["session_id"] for s in specs],
            ["DEMO-20261027-A", "DEMO-20261027-B", "DEMO-20261026-A"],
        )
        for spec in specs:
            self.assertTrue(spec["label"])
            self.assertEqual(len(spec["counted_qty"]), 6)

    def test_counted_qty_for(self):
        self.assertEqual(counted_qty_for("DEMO-20261027-A")["A-01-02"], 5)
        self.assertEqual(counted_qty_for("DEMO-20261027-B")["A-01-02"], 8)
        self.assertEqual(counted_qty_for("DEMO-20261026-A")["B-02-02"], 7)
        self.assertIsNone(counted_qty_for("NOPE"))

    def test_specs_are_copies(self):
        specs = demo_session_specs()
        specs[0]["counted_qty"]["A-01-01"] = 999
        self.assertEqual(counted_qty_for("DEMO-20261027-A")["A-01-01"], 12)


class SimulatorOverrideTest(unittest.TestCase):
    def test_override_all_match(self):
        with _mock_env():
            report = run_simulation(
                session_id="DEMO-20261027-B",
                counted_qty=counted_qty_for("DEMO-20261027-B"),
            )
        self.assertEqual(report["summary"]["matched"], 6)
        self.assertEqual(report["summary"]["mismatched"], 0)
        self.assertEqual(report["summary"]["abs_diff_total"], 0)

    def test_default_unchanged(self):
        with _mock_env():
            report = run_simulation(session_id="SIM-DEFAULT")
        self.assertEqual(report["summary"]["matched"], 4)
        self.assertEqual(report["summary"]["abs_diff_total"], 6)


class SessionListViewTest(unittest.TestCase):
    def setUp(self):
        with _mock_env():
            self.view = build_session_list_view()
            self.reports = list_session_reports()

    def test_totals(self):
        self.assertEqual(self.view["total_sessions"], 3)
        # 불일치 합계: 2 + 0 + 3
        self.assertEqual(self.view["total_mismatched"], 5)

    def test_session_summaries(self):
        by_id = {s["session_id"]: s for s in self.view["sessions"]}
        a = by_id["DEMO-20261027-A"]
        self.assertEqual((a["matched"], a["mismatched"], a["abs_diff_total"]), (4, 2, 6))
        self.assertEqual(a["match_rate_pct"], 66.7)
        self.assertTrue(a["is_mock"])
        b = by_id["DEMO-20261027-B"]
        self.assertEqual((b["matched"], b["mismatched"], b["match_rate_pct"]), (6, 0, 100.0))
        c = by_id["DEMO-20261026-A"]
        self.assertEqual((c["matched"], c["mismatched"], c["abs_diff_total"], c["net_diff"]), (3, 3, 7, -3))

    def test_get_session_report(self):
        with _mock_env():
            report = get_session_report("DEMO-20261026-A")
        self.assertIsNotNone(report)
        self.assertEqual(report["session_id"], "DEMO-20261026-A")
        self.assertEqual(report["summary"]["mismatched"], 3)
        self.assertIsNone(get_session_report("NOPE"))

    def test_render_sessions_html(self):
        html_out = render_sessions_html(self.view)
        for text in ("실사 세션 목록", "DEMO-20261027-A", "DEMO-20261026-A", "모의 데이터"):
            self.assertIn(text, html_out)


class SessionServerTest(unittest.TestCase):
    def setUp(self):
        self._env = _mock_env()
        self._env.start()
        self.addCleanup(self._env.stop)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler())
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def test_sessions_html(self):
        with urllib.request.urlopen(self.base_url + "/sessions") as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode("utf-8")
        self.assertIn("실사 세션 목록", body)
        self.assertIn("DEMO-20261027-B", body)

    def test_api_sessions(self):
        with urllib.request.urlopen(self.base_url + "/api/sessions") as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(data["total_sessions"], 3)
        self.assertEqual(len(data["sessions"]), 3)

    def test_api_session_detail_and_404(self):
        with urllib.request.urlopen(self.base_url + "/api/sessions/DEMO-20261027-A") as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.assertEqual(data["summary"]["matched"], 4)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.base_url + "/api/sessions/NOPE")
        self.assertEqual(ctx.exception.code, 404)

    def test_session_detail_html_and_404(self):
        with urllib.request.urlopen(self.base_url + "/sessions/DEMO-20261027-B") as resp:
            body = resp.read().decode("utf-8")
        self.assertIn("DEMO-20261027-B", body)
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.base_url + "/sessions/NOPE")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
