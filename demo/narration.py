"""데모 영상 나레이션 대본 자산 생성.

docs/demo-script.md와 demo.captions의 CUTS(9개 컷)에 있는 나레이션 문장을
녹음·TTS 제작에 바로 쓸 수 있는 나레이션 대본 자산으로 확정한다.
실제 음성 파일이 아니라 대본 텍스트 자산이며 그 사실을 HONESTY에 명시한다.

실행: 프로젝트 루트에서 `python3 -m demo.narration` (기본 출력 demo/assets/)
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from demo.captions import CUTS

PACE_LIMIT_CPS = 4.0

HONESTY = ["나레이션 대본 (음성 파일 아님)", "모의 어댑터 동작 중", "Pi 실촬영 컷은 도착 후 교체", "수치는 데모 기준"]


def _mmss(seconds: int) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def build_narration() -> dict:
    segments = []
    for cut in CUTS:
        duration = cut.end - cut.start
        chars = len("".join(cut.narration.split()))
        segments.append(
            {
                "index": cut.index,
                "start": cut.start,
                "end": cut.end,
                "duration": duration,
                "caption": cut.caption,
                "narration": cut.narration,
                "chars": chars,
                "chars_per_second": round(chars / duration, 2) if duration else 0.0,
            }
        )
    return {
        "title": "Argus 데모 영상 나레이션 대본",
        "total_seconds": CUTS[-1].end if CUTS else 0,
        "cut_count": len(segments),
        "total_chars": sum(s["chars"] for s in segments),
        "pace_limit_cps": PACE_LIMIT_CPS,
        "honesty": list(HONESTY),
        "segments": segments,
        "pace_warnings": [s["index"] for s in segments if s["chars_per_second"] > PACE_LIMIT_CPS],
    }


def validate_narration(narration: dict) -> list[str]:
    problems: list[str] = []
    segments = narration.get("segments", [])
    if narration.get("cut_count") != len(segments):
        problems.append(f"cut_count({narration.get('cut_count')})와 segments 길이({len(segments)})가 다릅니다.")
    if narration.get("total_seconds") != 180:
        problems.append(f"total_seconds({narration.get('total_seconds')})가 180이 아닙니다.")
    for i, segment in enumerate(segments):
        start = segment.get("start")
        end = segment.get("end")
        if i > 0 and segments[i - 1].get("end") != start:
            problems.append(f"컷 {segment.get('index')}의 start가 이전 컷의 end와 이어지지 않습니다.")
        if start is not None and end is not None:
            if end <= start:
                problems.append(f"컷 {segment.get('index')}의 end가 start보다 크지 않습니다.")
            if segment.get("duration") != end - start:
                problems.append(f"컷 {segment.get('index')}의 duration이 end-start와 다릅니다.")
        if not segment.get("narration") or not str(segment.get("narration")).strip():
            problems.append(f"컷 {segment.get('index')}의 narration이 비어 있습니다.")
        if not segment.get("caption") or not str(segment.get("caption")).strip():
            problems.append(f"컷 {segment.get('index')}의 caption이 비어 있습니다.")
    if segments and segments[-1].get("end") != 180:
        problems.append(f"마지막 구간 종료({segments[-1].get('end')})가 180이 아닙니다.")
    return problems


def build_narration_text(narration=None) -> str:
    if narration is None:
        narration = build_narration()
    lines = [f"{narration['title']} (총 {narration['total_seconds']}초)"]
    for segment in narration["segments"]:
        lines.append(f"컷 {segment['index']} [{_mmss(segment['start'])}-{_mmss(segment['end'])}]")
        lines.append(f"  {segment['narration']}")
    return "\n".join(lines) + "\n"


def build_full_script(narration=None) -> str:
    if narration is None:
        narration = build_narration()
    return " ".join(segment["narration"] for segment in narration["segments"]) + "\n"


def write_narration(out_dir) -> list[Path]:
    narration = build_narration()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    targets = {
        "narration.json": json.dumps(narration, ensure_ascii=False, indent=2) + "\n",
        "narration.txt": build_narration_text(narration),
        "narration-full.txt": build_full_script(narration),
    }
    written: list[Path] = []
    for name, text in targets.items():
        path = out / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 데모 영상 나레이션 대본 생성")
    parser.add_argument("--out", default="demo/assets", help="출력 디렉터리")
    args = parser.parse_args(argv)
    for path in write_narration(args.out):
        print(path)
    narration = build_narration()
    problems = validate_narration(narration)
    if problems:
        for problem in problems:
            print(f"문제: {problem}")
        return 1
    print("검증 통과: 문제 없음")
    if narration["pace_warnings"]:
        print(f"속도 경고 컷: {narration['pace_warnings']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
