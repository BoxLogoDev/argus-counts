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

    def test_probe_duration_missing_file_returns_none(self):
        self.assertIsNone(render_video.probe_duration("/nonexistent/nope.mp4"))


if __name__ == "__main__":
    unittest.main()
