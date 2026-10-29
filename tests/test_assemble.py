"""demo.assemble(데모 영상 조립 매니페스트) 테스트."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from demo.assemble import (
    HONESTY,
    SEGMENTS,
    build_assembly,
    build_assembly_text,
    validate_assembly,
    write_assembly,
)
from demo.captions import CUTS
from demo.capture import CAPTURE_SPECS


class TestSegments(unittest.TestCase):
    def test_segments_match_cuts(self):
        self.assertEqual(len(SEGMENTS), 9)
        for seg, cut in zip(SEGMENTS, CUTS):
            self.assertEqual(seg.cut_index, cut.index)
            self.assertEqual(seg.start, cut.start)
            self.assertEqual(seg.end, cut.end)
            self.assertEqual(seg.duration, cut.end - cut.start)

    def test_only_pi_cut_is_placeholder(self):
        placeholders = [s.cut_index for s in SEGMENTS if s.placeholder]
        self.assertEqual(placeholders, [3])
        pi = SEGMENTS[2]
        self.assertEqual(pi.source_kind, "pi-placeholder")
        self.assertEqual(pi.source_ref, "pi-capture-pending")

    def test_capture_refs_exist_in_capture_specs(self):
        filenames = {spec.filename for spec in CAPTURE_SPECS}
        capture_segs = [s for s in SEGMENTS if s.source_kind == "capture"]
        self.assertEqual(len(capture_segs), 7)
        for seg in capture_segs:
            self.assertIn(seg.source_ref, filenames)
        for seg in SEGMENTS:
            self.assertTrue(seg.source_ref)


class TestBuildAssembly(unittest.TestCase):
    def test_totals_and_honesty(self):
        assembly = build_assembly()
        self.assertEqual(assembly["total_seconds"], 180)
        self.assertEqual(assembly["segment_count"], 9)
        self.assertEqual(len(assembly["segments"]), 9)
        joined = " ".join(HONESTY)
        self.assertIn("영상 파일 아님", joined)
        self.assertIn("모의", joined)
        self.assertIn("데모 기준", joined)
        self.assertEqual(assembly["honesty"], HONESTY)

    def test_segments_carry_captions_from_cuts(self):
        assembly = build_assembly()
        for seg, cut in zip(assembly["segments"], CUTS):
            self.assertEqual(seg["caption"], cut.caption)
            self.assertEqual(seg["narration"], cut.narration)
            self.assertEqual(seg["duration"], seg["end"] - seg["start"])

    def test_validate_clean(self):
        self.assertEqual(validate_assembly(build_assembly()), [])


class TestValidateDetects(unittest.TestCase):
    def test_detects_gap(self):
        assembly = copy.deepcopy(build_assembly())
        assembly["segments"][4]["start"] += 5
        assembly["segments"][4]["duration"] -= 5
        problems = validate_assembly(assembly)
        self.assertTrue(any("불연속" in p or "duration" in p for p in problems))

    def test_detects_wrong_placeholder(self):
        assembly = copy.deepcopy(build_assembly())
        assembly["segments"][0]["placeholder"] = True
        problems = validate_assembly(assembly)
        self.assertTrue(any("placeholder" in p for p in problems))


class TestFallbackRef(unittest.TestCase):
    def test_cut3_has_fallback_ref(self):
        assembly = build_assembly()
        seg3 = assembly["segments"][2]
        self.assertEqual(seg3["index"], 3)
        self.assertTrue(seg3["placeholder"])
        self.assertEqual(seg3["source_kind"], "pi-placeholder")
        fallback = seg3["fallback"]
        self.assertEqual(fallback["asset"], "demo/assets/fallback.json")
        self.assertEqual(fallback["cut_index"], 3)
        self.assertEqual(fallback["decision_date"], "2026-11-02")
        self.assertIs(fallback["is_pi_real_capture"], False)
        self.assertEqual(fallback["capture_source"], "file")
        self.assertEqual(fallback["replaces"], "pi-placeholder")
        joined = " ".join(HONESTY)
        self.assertIn("Pi 실촬영이 아닙니다", joined)

    def test_other_cuts_have_no_fallback(self):
        assembly = build_assembly()
        for seg in assembly["segments"]:
            if seg["index"] == 3:
                continue
            self.assertNotIn("fallback", seg)

    def test_validate_detects_missing_fallback(self):
        assembly = copy.deepcopy(build_assembly())
        del assembly["segments"][2]["fallback"]
        problems = validate_assembly(assembly)
        self.assertTrue(any("fallback" in p for p in problems))

    def test_validate_detects_fallback_tamper(self):
        assembly = copy.deepcopy(build_assembly())
        assembly["segments"][2]["fallback"]["is_pi_real_capture"] = True
        assembly["segments"][2]["fallback"]["decision_date"] = "2026-11-03"
        problems = validate_assembly(assembly)
        self.assertTrue(any("fallback" in p for p in problems))
        self.assertTrue(any("is_pi_real_capture" in p for p in problems))

    def test_validate_detects_fallback_on_other_cut_and_text(self):
        assembly = copy.deepcopy(build_assembly())
        assembly["segments"][0]["fallback"] = dict(assembly["segments"][2]["fallback"])
        problems = validate_assembly(assembly)
        self.assertTrue(any("fallback" in p for p in problems))
        text = build_assembly_text(build_assembly())
        self.assertIn("fallback: demo/assets/fallback.json", text)
        self.assertIn("결정일 2026-11-02", text)
        self.assertIn("Pi 실촬영 아님", text)


class TestWriteAssembly(unittest.TestCase):
    def test_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = write_assembly(tmp)
            names = sorted(p.name for p in written)
            self.assertEqual(names, ["assembly.json", "assembly.txt"])
            data = json.loads(
                (Path(tmp) / "assembly.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["segment_count"], 9)
            self.assertEqual(data["total_seconds"], 180)
            text = (Path(tmp) / "assembly.txt").read_text(encoding="utf-8")
            self.assertIn("컷 1 [00:00-00:18] simulator:terminal-simulator", text)
            self.assertIn("컷 3", text)
            self.assertIn("pi-capture-pending", text)
            built = build_assembly_text(build_assembly())
            self.assertEqual(built, text)


if __name__ == "__main__":
    unittest.main()
