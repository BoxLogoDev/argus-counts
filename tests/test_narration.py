"""demo.narration(데모 영상 나레이션 대본 자산) 테스트."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from demo.captions import CUTS
from demo.narration import (
    HONESTY,
    PACE_LIMIT_CPS,
    build_full_script,
    build_narration,
    build_narration_text,
    validate_narration,
    write_narration,
)


class TestBuildNarration(unittest.TestCase):
    def test_totals_and_honesty(self):
        narration = build_narration()
        self.assertEqual(narration["total_seconds"], 180)
        self.assertEqual(narration["cut_count"], 9)
        self.assertEqual(len(narration["segments"]), 9)
        self.assertEqual(narration["pace_limit_cps"], PACE_LIMIT_CPS)
        joined = " ".join(HONESTY)
        self.assertIn("음성 파일 아님", joined)
        self.assertIn("모의", joined)
        self.assertIn("데모 기준", joined)
        self.assertEqual(narration["honesty"], HONESTY)

    def test_segments_carry_narration_from_cuts(self):
        narration = build_narration()
        for seg, cut in zip(narration["segments"], CUTS):
            self.assertEqual(seg["index"], cut.index)
            self.assertEqual(seg["start"], cut.start)
            self.assertEqual(seg["end"], cut.end)
            self.assertEqual(seg["duration"], cut.end - cut.start)
            self.assertEqual(seg["narration"], cut.narration)
            self.assertEqual(seg["caption"], cut.caption)

    def test_chars_and_pace_calc(self):
        narration = build_narration()
        total = 0
        for seg, cut in zip(narration["segments"], CUTS):
            expected_chars = len(cut.narration.replace(" ", ""))
            self.assertEqual(seg["chars"], expected_chars)
            self.assertEqual(
                seg["chars_per_second"],
                round(expected_chars / (cut.end - cut.start), 2),
            )
            total += expected_chars
        self.assertEqual(narration["total_chars"], total)

    def test_no_pace_warnings_after_rebalance(self):
        # 구간 재조정(컷 1: 0-18, 컷 9: 170-180) 뒤에는 전 컷이 기준 이내다
        narration = build_narration()
        self.assertEqual(narration["pace_warnings"], [])
        for seg in narration["segments"]:
            self.assertLessEqual(seg["chars_per_second"], PACE_LIMIT_CPS)

    def test_validate_clean(self):
        self.assertEqual(validate_narration(build_narration()), [])


class TestValidateDetects(unittest.TestCase):
    def test_detects_gap(self):
        narration = copy.deepcopy(build_narration())
        narration["segments"][4]["start"] += 5
        narration["segments"][4]["duration"] -= 5
        problems = validate_narration(narration)
        self.assertTrue(
            any("이어지지" in p or "불연속" in p or "duration" in p for p in problems)
        )

    def test_detects_empty_narration(self):
        narration = copy.deepcopy(build_narration())
        narration["segments"][0]["narration"] = "  "
        problems = validate_narration(narration)
        self.assertTrue(any("narration" in p or "비어" in p for p in problems))


class TestScriptsAndWrite(unittest.TestCase):
    def test_full_script_joins_all_narrations(self):
        script = build_full_script()
        for cut in CUTS:
            self.assertIn(cut.narration, script)
        self.assertTrue(script.endswith("\n"))
        self.assertNotIn("컷 1", script)

    def test_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = write_narration(tmp)
            names = sorted(p.name for p in written)
            self.assertEqual(
                names, ["narration-full.txt", "narration.json", "narration.txt"]
            )
            data = json.loads(
                (Path(tmp) / "narration.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["cut_count"], 9)
            self.assertEqual(data["total_seconds"], 180)
            self.assertEqual(data["pace_warnings"], [])
            text = (Path(tmp) / "narration.txt").read_text(encoding="utf-8")
            self.assertIn("컷 1 [00:00-00:18]", text)
            self.assertIn("컷 9 [02:50-03:00]", text)
            self.assertEqual(build_narration_text(build_narration()), text)
            full = (Path(tmp) / "narration-full.txt").read_text(encoding="utf-8")
            self.assertEqual(build_full_script(build_narration()), full)


if __name__ == "__main__":
    unittest.main()
