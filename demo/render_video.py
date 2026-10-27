"""Argus 데모 영상 초안 렌더러.

Captions(CUTS)와 조립 매니페스트(SEGMENTS)를 이용해 컷별 슬라이드 PNG를
만들고 ffmpeg로 이어 붙여 180초 MP4 초안을 생성한다.

정직성 표기:
- 이 모듈이 만드는 파일은 영상 초안 조립본이며 최종 제출본이 아니다.
- 현재 동작은 모의 어댑터 기준이다(SAM 실호출 아님).
- Pi 실촬영 컷(컷 3)은 도착 후 실촬영으로 교체할 플레이스홀더다.
- 화면에 등장하는 수치는 전부 데모 기준이다.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from demo.assemble import SEGMENTS
from demo.captions import CUTS

VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
FPS = 30
DEFAULT_OUT = "demo/assets/argus-demo-draft.mp4"

FONT_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)

HONESTY = [
    "영상 초안 조립본 (최종본 아님)",
    "모의 어댑터 동작 중",
    "Pi 실촬영 컷은 도착 후 교체",
    "수치는 데모 기준",
]

BG_NORMAL = (24, 28, 34)
BG_PLACEHOLDER = (74, 54, 28)
FG_MAIN = (238, 240, 244)
FG_SUB = (168, 176, 188)
FG_ACCENT = (120, 200, 255)
FG_WARN = (255, 196, 92)
FOOTER_TEXT = "모의 데이터 · 데모 기준"


def _field(obj, name, default=None):
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def find_font(size: int):
    """FONT_CANDIDATES 중 존재하는 첫 폰트를 로드한다. 없으면 기본 폰트."""
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    """픽셀 폭 기준으로 텍스트를 줄바꿈한다(공백 우선, 없으면 글자 단위)."""
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
                continue
            if current:
                lines.append(current)
                current = ""
            # 단어 하나가 max_width보다 길면 글자 단위로 쪼갠다.
            chunk = ""
            for ch in word:
                if draw.textlength(chunk + ch, font=font) <= max_width:
                    chunk += ch
                else:
                    if chunk:
                        lines.append(chunk)
                    chunk = ch
            current = chunk
        if current:
            lines.append(current)
    return lines


def build_slide(cut, segment, out_path) -> Path:
    """컷 1개짜리 1280x720 슬라이드 PNG를 만든다."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    placeholder = bool(_field(segment, "placeholder", False))
    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_PLACEHOLDER if placeholder else BG_NORMAL)
    draw = ImageDraw.Draw(image)

    index = _field(cut, "index")
    start = _field(cut, "start")
    end = _field(cut, "end")
    caption = _field(cut, "caption", "")
    narration = _field(cut, "narration", "")

    header_font = find_font(30)
    caption_font = find_font(54)
    body_font = find_font(30)
    footer_font = find_font(24)

    draw.text((60, 44), f"컷 {index} · {start}-{end}초", font=header_font, fill=FG_ACCENT)
    if placeholder:
        draw.text((60, 88), "Pi 도착 후 실촬영으로 교체", font=header_font, fill=FG_WARN)

    caption_lines = wrap_text(draw, caption, caption_font, VIDEO_WIDTH - 120)
    y = 190
    for line in caption_lines:
        draw.text((60, y), line, font=caption_font, fill=FG_MAIN)
        y += 72

    y += 36
    for line in wrap_text(draw, narration, body_font, VIDEO_WIDTH - 120):
        draw.text((60, y), line, font=body_font, fill=FG_SUB)
        y += 44

    draw.text((60, VIDEO_HEIGHT - 52), FOOTER_TEXT, font=footer_font, fill=FG_SUB)
    image.save(out_path)
    return out_path


def build_slides(workdir) -> list[Path]:
    """CUTS와 SEGMENTS를 index로 짝지어 슬라이드 9장을 만든다."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    segments_by_index = {_field(seg, "cut_index"): seg for seg in SEGMENTS}
    slides: list[Path] = []
    for cut in CUTS:
        index = _field(cut, "index")
        segment = segments_by_index[index]
        slides.append(build_slide(cut, segment, workdir / f"slide-{index:02d}.png"))
    return slides


def _run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "")[-800:]
        raise RuntimeError(f"ffmpeg 실패 (code={proc.returncode}): {tail}")


def render(out_path=DEFAULT_OUT, workdir=None) -> dict:
    """슬라이드를 컷별 세그먼트로 인코딩하고 concat으로 병합해 MP4를 만든다."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg를 찾을 수 없어 영상을 조립할 수 없습니다")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    own_tmp = workdir is None
    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="argus-render-"))
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        slides = build_slides(tmp)
        total_seconds = sum(int(_field(c, "end")) - int(_field(c, "start")) for c in CUTS)
        segment_paths: list[Path] = []
        for cut, slide in zip(CUTS, slides):
            duration = int(_field(cut, "end")) - int(_field(cut, "start"))
            seg_path = tmp / f"segment-{_field(cut, 'index'):02d}.mp4"
            _run_ffmpeg([
                "ffmpeg", "-y", "-loop", "1", "-t", str(duration), "-i", str(slide),
                "-f", "lavfi", "-t", str(duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(seg_path),
            ])
            segment_paths.append(seg_path)
        concat_list = tmp / "concat.txt"
        concat_list.write_text(
            "".join(f"file '{p.resolve()}'\n" for p in segment_paths), encoding="utf-8"
        )
        _run_ffmpeg([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c", "copy", str(out_path),
        ])
        result = {
            "out": str(out_path),
            "duration_seconds": total_seconds,
            "segment_count": len(segment_paths),
            "slides": [str(s) for s in slides],
            "honesty": list(HONESTY),
        }
        return result
    finally:
        if own_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def probe_duration(path) -> float | None:
    """ffprobe로 영상 길이를 초 단위로 읽는다. ffprobe가 없으면 None."""
    if shutil.which("ffprobe") is None:
        return None
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    try:
        return float(json.loads(proc.stdout)["format"]["duration"])
    except (ValueError, KeyError, TypeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 데모 영상 초안 조립")
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    result = render(out_path=args.out)
    probed = probe_duration(result["out"])
    print(f"출력: {result['out']}")
    print(f"길이: {result['duration_seconds']}초 (ffprobe 실측: {probed})")
    print(f"세그먼트: {result['segment_count']}개")
    for line in result["honesty"]:
        print(f"정직성: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
