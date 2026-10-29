"""Argus 데모 영상 초안 렌더러.

Captions(CUTS)와 조립 매니페스트(SEGMENTS)를 이용해 컷별 슬라이드 PNG를
만들고 ffmpeg로 이어 붙여 180초 MP4 초안을 생성한다.

정직성 표기:
- 이 모듈이 만드는 파일은 영상 초안 조립본이며 최종 제출본이 아니다.
- 현재 동작은 모의 어댑터 기준이다(SAM 실호출 아님).
- Pi 실촬영 컷(컷 3)은 도착 후 실촬영으로 교체할 플레이스홀더다.
- 화면에 등장하는 수치는 전부 데모 기준이다.
- 폴백 렌더 변형(--fallback)은 컷 3을 파일 입력 폴백 데이터로 보여 주는 별도 파일이며, Pi 실촬영이 아니다. 기본 렌더는 무변경이다.
- 슬라이드 하단 데이터 패널은 terminal.simulator.run_simulation()이 만든 실제 리포트에서 가져오며 하드코딩 수치가 아니다. 단 그 리포트 자체는 모의 어댑터 기준이고 수치는 데모 기준이다.
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
FALLBACK_OUT = "demo/assets/argus-demo-fallback-draft.mp4"

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
PANEL_BG = (36, 42, 52)
PANEL_Y = 460
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


def build_data_panel_lines(cut_index, report=None, fallback_manifest=None) -> list[str]:
    """컷 번호에 맞는 데이터 패널 줄을 실제 시뮬레이션 리포트에서 만든다.

    리포트를 넘기지 않으면 함수 안에서 지연 import로 시뮬레이션을 한 번 돌린다.
    모듈 import 시점에는 시뮬레이션을 돌리지 않는다.
    """
    if report is None:
        from terminal.simulator import run_simulation

        report = run_simulation()
    from terminal.report import build_actions, impact_line

    verdict_labels = {"match": "일치", "short": "부족", "over": "초과"}

    # 플레이스홀더 컷에는 실데이터인 척하는 패널을 붙이지 않는다.
    # 단, 폴백 매니페스트가 명시적으로 주어진 경우에만 파일 입력 폴백 패널을 붙인다.
    if cut_index == 3:
        if fallback_manifest is None:
            return ["실촬영 데이터 없음 — Pi 도착 후 교체"]
        from demo.fallback import validate_fallback

        problems = validate_fallback(fallback_manifest)
        if problems:
            raise ValueError("폴백 매니페스트 검증 실패: " + "; ".join(problems))
        summary = fallback_manifest["summary"]
        target = next(
            b for b in fallback_manifest["bins"] if b["bin_id"] == "A-01-02"
        )
        sha8 = str(target["photo"]["sha256"])[:8]
        return [
            "파일 입력 폴백 — Pi 실촬영 아님 · 결정일 2026-11-02",
            f"세션 {fallback_manifest['session_id']} · capture_source=file · source=mock",
            (
                f"빈 {summary['counted_bins']} · 일치 {summary['matched']} · "
                f"불일치 {summary['mismatched']} · 절대 차이 {summary['abs_diff_total']} · "
                f"순차이 {summary['net_diff']:+d}"
            ),
            (
                f"A-01-02 장부 {target['book_qty']} → 실측 {target['counted_qty']} "
                f"(차이 {target['diff']:+d}) [부족] · 사진 sha256 {sha8}…"
            ),
        ]
    if cut_index not in (1, 2, 4, 5, 6, 7, 8, 9):
        return []

    def _summary_line() -> str:
        summary = report["summary"]
        pct = round(float(summary["match_rate"]) * 100, 1)
        return (
            f"빈 {summary['counted_bins']} · 일치 {summary['matched']} · "
            f"불일치 {summary['mismatched']} · 절대 차이 {summary['abs_diff_total']} · "
            f"일치율 {pct:.1f}%"
        )

    if cut_index in (1, 2, 4):
        return [_summary_line()]

    if cut_index == 5:
        return [
            f"{b['bin_id']} {b['item_code']} 장부 {b['book_qty']} → 실측 {b['counted_qty']} "
            f"[{verdict_labels.get(b['verdict'], b['verdict'])}]"
            for b in report["bins"]
        ]

    if cut_index == 6:
        return [
            f"{b['bin_id']} {b['item_code']} 장부 {b['book_qty']} → 실측 {b['counted_qty']} "
            f"(차이 {b['diff']:+d}) [{verdict_labels.get(b['verdict'], b['verdict'])}]"
            for b in report["bins"]
            if b["verdict"] != "match"
        ]

    if cut_index == 7:
        return [
            f"{a['priority']}. {a['bin_id']} "
            f"[{verdict_labels.get(a['verdict'], a['verdict'])}] "
            f"차이 {a['diff']:+d} — {a['action_hint']}"
            for a in build_actions(report)
        ]

    if cut_index == 8:
        summary = report["summary"]
        pct = round(float(summary["match_rate"]) * 100, 1)
        return [
            f"실사 완료 빈: {summary['counted_bins']}",
            f"일치 {summary['matched']} · 불일치 {summary['mismatched']} · 일치율 {pct:.1f}%",
            f"절대 차이 {summary['abs_diff_total']} · 순차이 {summary['net_diff']:+d}",
        ]

    if cut_index == 9:
        return [impact_line(report)]

    return []


def build_slide(cut, segment, out_path, report=None, fallback_manifest=None) -> Path:
    """컷 1개짜리 1280x720 슬라이드 PNG를 만든다."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    placeholder = bool(_field(segment, "placeholder", False))
    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_PLACEHOLDER if placeholder else BG_NORMAL)
    draw = ImageDraw.Draw(image)

    index = _field(cut, "index")
    if fallback_manifest is not None and index == 3:
        from demo.fallback import validate_fallback

        problems = validate_fallback(fallback_manifest)
        if problems:
            raise ValueError("폴백 매니페스트 검증 실패: " + "; ".join(problems))
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
        header_note = (
            "파일 입력 폴백 — Pi 실촬영 아님"
            if index == 3 and fallback_manifest is not None
            else "Pi 도착 후 실촬영으로 교체"
        )
        draw.text((60, 88), header_note, font=header_font, fill=FG_WARN)

    caption_lines = wrap_text(draw, caption, caption_font, VIDEO_WIDTH - 120)
    y = 190
    for line in caption_lines:
        draw.text((60, y), line, font=caption_font, fill=FG_MAIN)
        y += 72

    y += 36
    for line in wrap_text(draw, narration, body_font, VIDEO_WIDTH - 120):
        draw.text((60, y), line, font=body_font, fill=FG_SUB)
        y += 44

    lines = build_data_panel_lines(_field(cut, "index"), report=report, fallback_manifest=fallback_manifest)
    if lines:
        draw.rectangle([60, PANEL_Y, VIDEO_WIDTH - 60, 650], fill=PANEL_BG)
        panel_font = find_font(24)
        panel_y = PANEL_Y + 16
        for line in lines:
            for wrapped in wrap_text(draw, line, panel_font, VIDEO_WIDTH - 168):
                if panel_y > 640:
                    break
                draw.text((84, panel_y), wrapped, font=panel_font, fill=FG_MAIN)
                panel_y += 30
            if panel_y > 640:
                break

    draw.text((60, VIDEO_HEIGHT - 52), FOOTER_TEXT, font=footer_font, fill=FG_SUB)
    image.save(out_path)
    return out_path


def build_slides(workdir, report=None, fallback_manifest=None) -> list[Path]:
    """CUTS와 SEGMENTS를 index로 짝지어 슬라이드 9장을 만든다.

    리포트를 넘기지 않으면 시뮬레이션을 한 번만 돌려 9장이 같은 리포트를 공유한다.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    if report is None:
        from terminal.simulator import run_simulation

        report = run_simulation()
    segments_by_index = {_field(seg, "cut_index"): seg for seg in SEGMENTS}
    slides: list[Path] = []
    for cut in CUTS:
        index = _field(cut, "index")
        segment = segments_by_index[index]
        slides.append(
            build_slide(
                cut, segment, workdir / f"slide-{index:02d}.png",
                report=report, fallback_manifest=fallback_manifest,
            )
        )
    return slides


def _run_ffmpeg(args: list[str]) -> None:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "")[-800:]
        raise RuntimeError(f"ffmpeg 실패 (code={proc.returncode}): {tail}")


def render(out_path=DEFAULT_OUT, workdir=None, fallback=False) -> dict:
    """슬라이드를 컷별 세그먼트로 인코딩하고 concat으로 병합해 MP4를 만든다."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg를 찾을 수 없어 영상을 조립할 수 없습니다")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    own_tmp = workdir is None
    tmp = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="argus-render-"))
    tmp.mkdir(parents=True, exist_ok=True)
    try:
        from terminal.simulator import run_simulation

        report = run_simulation()
        fallback_manifest = None
        fallback_info = None
        if fallback:
            from demo.fallback import build_fallback_manifest

            fallback_manifest = build_fallback_manifest()
            fallback_info = {
                "cut_index": 3,
                "capture_source": "file",
                "source": "mock",
                "is_pi_real_capture": False,
                "decision_date": "2026-11-02",
                "session_id": fallback_manifest["session_id"],
            }
        slides = build_slides(tmp, report=report, fallback_manifest=fallback_manifest)
        data_panel_cuts = sorted(
            int(_field(c, "index"))
            for c in CUTS
            if build_data_panel_lines(
                _field(c, "index"), report=report, fallback_manifest=fallback_manifest
            )
        )
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
            "data_panel_cuts": data_panel_cuts,
            "fallback": fallback_info,
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
    parser.add_argument("--out", default=None)
    parser.add_argument("--fallback", action="store_true", help="컷 3을 파일 입력 폴백으로 렌더")
    args = parser.parse_args(argv)
    out = args.out or (FALLBACK_OUT if args.fallback else DEFAULT_OUT)
    result = render(out_path=out, fallback=args.fallback)
    if result.get("fallback"):
        fb = result["fallback"]
        print(
            f"폴백: 컷 {fb['cut_index']} · capture_source={fb['capture_source']} · "
            f"Pi 실촬영 아님 · 결정일 {fb['decision_date']}"
        )
    probed = probe_duration(result["out"])
    print(f"출력: {result['out']}")
    print(f"길이: {result['duration_seconds']}초 (ffprobe 실측: {probed})")
    print(f"세그먼트: {result['segment_count']}개")
    for line in result["honesty"]:
        print(f"정직성: {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
