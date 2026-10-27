"""demo 패키지(데모 영상 자막·샷 리스트 자산) 테스트."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from demo.captions import (
    CUTS,
    build_shot_list,
    build_srt,
    build_vtt,
    format_srt_timestamp,
    format_vtt_timestamp,
    write_assets,
)


class TestCuts(unittest.TestCase):
    def test_nine_cuts_total_180_seconds(self):
        self.assertEqual(len(CUTS), 9)
        self.assertEqual(CUTS[0].start, 0)
        self.assertEqual(CUTS[-1].end, 180)

    def test_cuts_are_contiguous_and_ordered(self):
        for prev, cur in zip(CUTS, CUTS[1:]):
            self.assertEqual(prev.end, cur.start)
            self.assertLess(cur.start, cur.end)
        self.assertEqual([c.index for c in CUTS], list(range(1, 10)))

    def test_honesty_markers_in_cuts(self):
        all_text = " ".join(c.caption + c.narration + c.screen for c in CUTS)
        self.assertIn("모의", all_text)
        self.assertIn("데모 기준", all_text)
        # Pi 컷은 도착 후 교체 플레이스홀더 취지를 담아야 한다
        pi_cut = CUTS[2]
        self.assertIn("Pi", pi_cut.screen + pi_cut.narration + pi_cut.caption)


class TestTimestamps(unittest.TestCase):
    def test_srt_timestamp(self):
        self.assertEqual(format_srt_timestamp(0), "00:00:00,000")
        self.assertEqual(format_srt_timestamp(75), "00:01:15,000")
        self.assertEqual(format_srt_timestamp(180), "00:03:00,000")

    def test_vtt_timestamp(self):
        self.assertEqual(format_vtt_timestamp(0), "00:00:00.000")
        self.assertEqual(format_vtt_timestamp(130), "00:02:10.000")


class TestBuilders(unittest.TestCase):
    def test_srt_structure(self):
        srt = build_srt()
        blocks = [b for b in srt.strip().split("\n\n") if b.strip()]
        self.assertEqual(len(blocks), 9)
        self.assertTrue(blocks[0].startswith("1\n00:00:00,000 --> 00:00:08,000"))
        self.assertIn("Argus", blocks[0])
        self.assertIn("00:02:55,000 --> 00:03:00,000", blocks[-1])

    def test_vtt_structure(self):
        vtt = build_vtt()
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:50.000 --> 00:01:15.000", vtt)

    def test_shot_list(self):
        shot = build_shot_list()
        self.assertEqual(shot["total_seconds"], 180)
        self.assertEqual(shot["cut_count"], 9)
        self.assertEqual(len(shot["cuts"]), 9)
        joined = json.dumps(shot, ensure_ascii=False)
        self.assertIn("모의", joined)
        self.assertIn("데모 기준", joined)

    def test_write_assets_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "assets"
            written = write_assets(out)
            names = sorted(p.name for p in written)
            self.assertEqual(names, ["captions.srt", "captions.vtt", "shot-list.json"])
            for p in written:
                self.assertTrue(p.is_file())
            data = json.loads((out / "shot-list.json").read_text(encoding="utf-8"))
            self.assertEqual(data["cut_count"], 9)
            self.assertTrue((out / "captions.srt").read_text(encoding="utf-8").startswith("1\n"))


if __name__ == "__main__":
    unittest.main()
