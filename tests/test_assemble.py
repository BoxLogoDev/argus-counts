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
            self.assertIn("컷 1 [00:00-00:08] simulator:terminal-simulator", text)
            self.assertIn("컷 3", text)
            self.assertIn("pi-capture-pending", text)
            built = build_assembly_text(build_assembly())
            self.assertEqual(built, text)


if __name__ == "__main__":
    unittest.main()
