import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from demo import render_video
from demo.assemble import SEGMENTS
from demo.captions import CUTS


class RenderVideoTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(render_video.VIDEO_WIDTH, 1280)
        self.assertEqual(render_video.VIDEO_HEIGHT, 720)
        self.assertEqual(render_video.FPS, 30)
        self.assertTrue(render_video.DEFAULT_OUT.endswith("argus-demo-draft.mp4"))

    def test_honesty_markers(self):
        joined = " ".join(render_video.HONESTY)
        self.assertIn("초안", joined)
        self.assertIn("모의", joined)
        self.assertIn("Pi", joined)
        self.assertIn("데모 기준", joined)

    def test_find_font_returns_font(self):
        font = render_video.find_font(30)
        self.assertIsNotNone(font)

    def test_wrap_text_wraps_long_line(self):
        image = Image.new("RGB", (render_video.VIDEO_WIDTH, render_video.VIDEO_HEIGHT))
        draw = ImageDraw.Draw(image)
        font = render_video.find_font(30)
        long_text = "창고 재고실사는 빈마다 세고 장부와 맞춰야 하는 작업입니다 " * 4
        lines = render_video.wrap_text(draw, long_text, font, 600)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(draw.textlength(line, font=font), 600)

    def test_wrap_text_keeps_short_line(self):
        image = Image.new("RGB", (200, 100))
        draw = ImageDraw.Draw(image)
        font = render_video.find_font(30)
        self.assertEqual(render_video.wrap_text(draw, "짧은 문장", font, 1000), ["짧은 문장"])

    def test_build_slides_creates_nine_pngs(self):
        with tempfile.TemporaryDirectory() as tmp:
            slides = render_video.build_slides(tmp)
            self.assertEqual(len(slides), 9)
            for slide in slides:
                self.assertTrue(Path(slide).exists())
                with Image.open(slide) as img:
                    self.assertEqual(img.size, (1280, 720))

    def test_placeholder_slide_background_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            slides = render_video.build_slides(tmp)
            with Image.open(slides[0]) as normal, Image.open(slides[2]) as placeholder:
                self.assertEqual(normal.getpixel((1200, 700)), render_video.BG_NORMAL)
                self.assertEqual(placeholder.getpixel((1200, 700)), render_video.BG_PLACEHOLDER)

    def test_cuts_and_segments_align(self):
        self.assertEqual(len(CUTS), len(SEGMENTS))
        total = 0
        for cut, segment in zip(CUTS, SEGMENTS):
            self.assertEqual(cut.index, segment.cut_index)
            self.assertEqual((cut.start, cut.end), (segment.start, segment.end))
            total += cut.end - cut.start
        self.assertEqual(total, 180)
        placeholders = [s for s in SEGMENTS if s.placeholder]
        self.assertEqual(len(placeholders), 1)
        self.assertEqual(placeholders[0].cut_index, 3)

    def test_data_panel_cut5_lists_all_bins(self):
        lines = render_video.build_data_panel_lines(5)
        self.assertEqual(len(lines), 6)
        joined = "\n".join(lines)
        self.assertIn("A-01-02", joined)
        self.assertIn("[부족]", joined)
        self.assertIn("[초과]", joined)

    def test_data_panel_cut6_only_mismatched(self):
        lines = render_video.build_data_panel_lines(6)
        self.assertEqual(len(lines), 2)
        self.assertIn("A-01-02", lines[0])
        self.assertIn("(차이 -3)", lines[0])
        self.assertIn("B-01-02", lines[1])
        self.assertIn("(차이 +3)", lines[1])

    def test_data_panel_cut7_actions_priority(self):
        lines = render_video.build_data_panel_lines(7)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("1. A-01-02"))
        self.assertIn("재촬영", lines[0])
        self.assertTrue(lines[1].startswith("2. B-01-02"))
        self.assertIn("오적재", lines[1])

    def test_data_panel_cut8_summary(self):
        lines = render_video.build_data_panel_lines(8)
        self.assertEqual(len(lines), 3)
        joined = "\n".join(lines)
        self.assertIn("실사 완료 빈: 6", joined)
        self.assertIn("66.7%", joined)
        self.assertIn("절대 차이 6", joined)

    def test_data_panel_cut9_impact_line(self):
        lines = render_video.build_data_panel_lines(9)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("데모 기준:"))
        self.assertIn("66.7%", lines[0])

    def test_data_panel_cut3_placeholder_honest(self):
        lines = render_video.build_data_panel_lines(3)
        self.assertEqual(lines, ["실촬영 데이터 없음 — Pi 도착 후 교체"])

    def test_data_panel_cut1_summary_oneliner(self):
        for index in (1, 2, 4):
            lines = render_video.build_data_panel_lines(index)
            self.assertEqual(len(lines), 1)
            self.assertIn("빈 6", lines[0])
            self.assertIn("일치율 66.7%", lines[0])
        self.assertEqual(render_video.build_data_panel_lines(99), [])

    def test_data_panel_reflects_custom_report(self):
        custom = {
            "session_id": "CUSTOM-1",
            "generated_at": "2026-10-28T00:00:00+00:00",
            "source": "mock",
            "bins": [
                {
                    "bin_id": "X-99",
                    "item_code": "ITEM-X",
                    "book_qty": 10,
                    "counted_qty": 7,
                    "diff": -3,
                    "verdict": "short",
                }
            ],
            "summary": {
                "counted_bins": 1,
                "matched": 0,
                "mismatched": 1,
                "match_rate": 0.0,
                "abs_diff_total": 3,
                "net_diff": -3,
            },
        }
        lines5 = render_video.build_data_panel_lines(5, report=custom)
        self.assertEqual(len(lines5), 1)
        self.assertIn("X-99", lines5[0])
        self.assertNotIn("A-01-02", "\n".join(lines5))
        lines1 = render_video.build_data_panel_lines(1, report=custom)
        self.assertIn("빈 1", lines1[0])
        self.assertIn("일치율 0.0%", lines1[0])

    def test_slide_panel_pixel(self):
        with tempfile.TemporaryDirectory() as tmp:
            slides = render_video.build_slides(tmp)
            with Image.open(slides[4]) as slide:
                self.assertEqual(slide.getpixel((65, 465)), render_video.PANEL_BG)
                self.assertEqual(slide.getpixel((1200, 700)), render_video.BG_NORMAL)

    def test_fallback_out_constant(self):
        self.assertTrue(
            render_video.FALLBACK_OUT.endswith("argus-demo-fallback-draft.mp4")
        )
        self.assertNotEqual(render_video.FALLBACK_OUT, render_video.DEFAULT_OUT)

    def test_data_panel_cut3_fallback_lines(self):
        from demo.fallback import build_fallback_manifest

        lines = render_video.build_data_panel_lines(
            3, fallback_manifest=build_fallback_manifest()
        )
        self.assertEqual(len(lines), 4)
        self.assertIn("파일 입력 폴백", lines[0])
        self.assertIn("Pi 실촬영 아님", lines[0])
        self.assertIn("2026-11-02", lines[0])
        self.assertIn("capture_source=file", lines[1])
        self.assertIn("source=mock", lines[1])
        self.assertIn("FALLBACK-FILE-INPUT", lines[1])

    def test_data_panel_cut3_fallback_summary_and_bin(self):
        from demo.fallback import build_fallback_manifest

        lines = render_video.build_data_panel_lines(
            3, fallback_manifest=build_fallback_manifest()
        )
        self.assertIn("빈 6", lines[2])
        self.assertIn("일치 4", lines[2])
        self.assertIn("불일치 2", lines[2])
        self.assertIn("A-01-02", lines[3])
        self.assertIn("장부 8", lines[3])
        self.assertIn("실측 5", lines[3])
        self.assertIn("sha256 106573c1", lines[3])

    def test_data_panel_cut3_fallback_invalid_real_capture_raises(self):
        from demo.fallback import build_fallback_manifest

        bad = dict(build_fallback_manifest())
        bad["is_pi_real_capture"] = True
        with self.assertRaises(ValueError):
            render_video.build_data_panel_lines(3, fallback_manifest=bad)

    def test_data_panel_cut3_fallback_invalid_source_raises(self):
        from demo.fallback import build_fallback_manifest

        bad = dict(build_fallback_manifest())
        bad["capture_source"] = "pi-camera"
        with self.assertRaises(ValueError):
            render_video.build_data_panel_lines(3, fallback_manifest=bad)

    def test_data_panel_fallback_other_cuts_unchanged(self):
        from demo.fallback import build_fallback_manifest

        manifest = build_fallback_manifest()
        self.assertEqual(
            len(render_video.build_data_panel_lines(5, fallback_manifest=manifest)), 6
        )
        self.assertEqual(
            render_video.build_data_panel_lines(3),
            ["실촬영 데이터 없음 — Pi 도착 후 교체"],
        )

    def test_build_slides_fallback_changes_only_cut3(self):
        from demo.fallback import build_fallback_manifest

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "base"
            fb = Path(tmp) / "fb"
            base_slides = render_video.build_slides(base)
            fb_slides = render_video.build_slides(
                fb, fallback_manifest=build_fallback_manifest()
            )
            self.assertEqual(base_slides[0].read_bytes(), fb_slides[0].read_bytes())
            self.assertNotEqual(base_slides[2].read_bytes(), fb_slides[2].read_bytes())
            with Image.open(fb_slides[2]) as slide:
                self.assertEqual(slide.getpixel((1200, 700)), render_video.BG_PLACEHOLDER)
                self.assertEqual(slide.getpixel((65, 465)), render_video.PANEL_BG)

    def test_render_fallback_default_is_false(self):
        import inspect

        sig = inspect.signature(render_video.render)
        self.assertIs(sig.parameters["fallback"].default, False)

    def test_render_fallback_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "fallback.mp4"
            result = render_video.render(out_path=out, fallback=True)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 0)
            fb = result["fallback"]
            self.assertEqual(fb["cut_index"], 3)
            self.assertEqual(fb["capture_source"], "file")
            self.assertEqual(fb["source"], "mock")
            self.assertIs(fb["is_pi_real_capture"], False)
            self.assertEqual(fb["decision_date"], "2026-11-02")
            self.assertIn(3, result["data_panel_cuts"])
            probed = render_video.probe_duration(out)
            self.assertIsNotNone(probed)
            self.assertGreater(probed, 179.0)
            self.assertLess(probed, 181.0)

    def test_probe_duration_missing_file_returns_none(self):
        self.assertIsNone(render_video.probe_duration("/nonexistent/nope.mp4"))


if __name__ == "__main__":
    unittest.main()
