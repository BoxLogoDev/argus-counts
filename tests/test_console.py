"""콘솔 뷰, 렌더러, 서버 단위 테스트.

기준 케이스는 데모 빈 6개 시나리오: 일치 4 · 부족 1 · 초과 1.
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

from console.render import render_html
from console.server import create_handler
from console.view import build_view
from terminal.simulator import run_simulation


def run_mock_view():
    with mock.patch.dict(os.environ, {}, clear=True):
        return build_view(run_simulation(session_id="SIM-TEST"))


class BuildViewTest(unittest.TestCase):
    def setUp(self):
        self.view = run_mock_view()

    def test_metrics(self):
        metrics = self.view["metrics"]
        self.assertEqual(metrics["counted_bins"], 6)
        self.assertEqual(metrics["matched"], 4)
        self.assertEqual(metrics["mismatched"], 2)
        self.assertEqual(metrics["match_rate_pct"], 66.7)
        self.assertEqual(metrics["abs_diff_total"], 6)
        self.assertEqual(metrics["net_diff"], 0)

    def test_mock_source(self):
        self.assertTrue(self.view["is_mock"])
        self.assertEqual(self.view["source_label"], "모의")

    def test_differences(self):
        differences = self.view["differences"]
        self.assertEqual(
            [bin_["bin_id"] for bin_ in differences], ["A-01-02", "B-01-02"]
        )
        self.assertEqual(
            [bin_["verdict_label"] for bin_ in differences], ["부족", "초과"]
        )

    def test_all_bins_have_verdict_label(self):
        self.assertEqual(len(self.view["bins"]), 6)
        for bin_ in self.view["bins"]:
            self.assertIn("verdict_label", bin_)
            self.assertTrue(bin_["verdict_label"])


class RenderHtmlTest(unittest.TestCase):
    def setUp(self):
        self.html = render_html(run_mock_view())

    def test_mock_html_contents(self):
        for text in (
            "Argus 콘솔",
            "모의 데이터",
            "A-01-02",
            "B-01-02",
            "66.7%",
            "(데모)",
        ):
            self.assertIn(text, self.html)

    def test_sam_source_has_no_mock_badge(self):
        fake_report = {
            "session_id": "SIM-SAM",
            "generated_at": "2026-10-27T00:00:00+00:00",
            "source": "sam",
            "bins": [
                {
                    "bin_id": "A-01-01",
                    "item_code": "ITM-001",
                    "book_qty": 10,
                    "counted_qty": 10,
                    "diff": 0,
                    "verdict": "match",
                }
            ],
            "summary": {
                "counted_bins": 1,
                "matched": 1,
                "mismatched": 0,
                "match_rate": 1.0,
                "abs_diff_total": 0,
                "net_diff": 0,
            },
        }
        view = build_view(fake_report)
        self.assertFalse(view["is_mock"])
        self.assertEqual(view["source_label"], "SAM 실호출")
        self.assertNotIn("모의 데이터", render_html(view))


class ConsoleServerTest(unittest.TestCase):
    def setUp(self):
        self._env = mock.patch.dict(os.environ, {}, clear=True)
        self._env.start()
        self.addCleanup(self._env.stop)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler())
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.thread.start()
        port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{port}"

    def test_root_returns_html(self):
        with urllib.request.urlopen(self.base_url + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.headers["Content-Type"])
            body = response.read().decode("utf-8")
        self.assertIn("Argus 콘솔", body)
        self.assertIn("A-01-02", body)

    def test_api_report_returns_json(self):
        with urllib.request.urlopen(self.base_url + "/api/report") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(
                "application/json", response.headers["Content-Type"]
            )
            data = json.loads(response.read().decode("utf-8"))
        self.assertTrue(data["session_id"])
        self.assertEqual(data["summary"]["matched"], 4)

    def test_unknown_path_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.base_url + "/nope")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
