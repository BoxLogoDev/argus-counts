"""단말 시뮬레이터 단위 테스트.

기준 케이스는 데모 빈 6개 시나리오: 일치 4 · 부족 1 · 초과 1.
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)

from terminal.simulator import main, run_simulation


class RunSimulationTest(unittest.TestCase):
    def setUp(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.report = run_simulation(session_id="SIM-TEST")

    def test_session_id(self):
        self.assertEqual(self.report["session_id"], "SIM-TEST")

    def test_six_bins(self):
        self.assertEqual(len(self.report["bins"]), 6)

    def test_summary(self):
        summary = self.report["summary"]
        self.assertEqual(summary["counted_bins"], 6)
        self.assertEqual(summary["matched"], 4)
        self.assertEqual(summary["mismatched"], 2)
        self.assertAlmostEqual(summary["match_rate"], 4 / 6)
        self.assertEqual(summary["abs_diff_total"], 6)
        self.assertEqual(summary["net_diff"], 0)

    def test_shortage_bin(self):
        comp = next(b for b in self.report["bins"] if b["bin_id"] == "A-01-02")
        self.assertEqual(comp["verdict"], "short")
        self.assertEqual(comp["diff"], -3)

    def test_overage_bin(self):
        comp = next(b for b in self.report["bins"] if b["bin_id"] == "B-01-02")
        self.assertEqual(comp["verdict"], "over")
        self.assertEqual(comp["diff"], 3)

    def test_json_serializable(self):
        loaded = json.loads(json.dumps(self.report, ensure_ascii=False))
        self.assertEqual(loaded["session_id"], "SIM-TEST")
        self.assertEqual(loaded["summary"]["matched"], 4)


class CliOutTest(unittest.TestCase):
    def test_out_writes_readable_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "report.json")
            with mock.patch.dict(os.environ, {}, clear=True):
                result = main(["--out", path, "--session-id", "SIM-CLI"])
            self.assertEqual(result, 0)
            with open(path, encoding="utf-8") as fh:
                loaded = json.load(fh)
        self.assertEqual(loaded["session_id"], "SIM-CLI")
        self.assertEqual(len(loaded["bins"]), 6)
        self.assertEqual(loaded["summary"]["matched"], 4)


if __name__ == "__main__":
    unittest.main()
