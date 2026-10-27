"""데모 영상 조립 매니페스트 생성.

자막 자산(demo.captions의 CUTS)과 캡처 자산(demo.capture의 CAPTURE_SPECS)을
컷별로 묶은 편집 결정 목록을 만든다. 실제 영상 파일이 아니라 조립
매니페스트이며, 그 사실을 HONESTY 목록에 명시한다.

실행: 프로젝트 루트에서 `python3 -m demo.assemble` (기본 출력 demo/assets/)
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from demo.captions import CUTS
from demo.capture import CAPTURE_SPECS


@dataclass(frozen=True)
class AssemblySegment:
    cut_index: int
    start: int
    end: int
    source_kind: str
    source_ref: str
    placeholder: bool

    @property
    def duration(self) -> int:
        return self.end - self.start


SEGMENTS: tuple[AssemblySegment, ...] = (
    AssemblySegment(1, 0, 8, "simulator", "terminal-simulator", False),
    AssemblySegment(2, 8, 30, "capture", "console-sessions.html", False),
    AssemblySegment(3, 30, 50, "pi-placeholder", "pi-capture-pending", True),
    AssemblySegment(4, 50, 75, "capture", "api-report.json", False),
    AssemblySegment(5, 75, 105, "capture", "console-home.html", False),
    AssemblySegment(6, 105, 130, "capture", "console-home.html", False),
    AssemblySegment(7, 130, 155, "capture", "console-home.html", False),
    AssemblySegment(8, 155, 175, "capture", "api-report.json", False),
    AssemblySegment(9, 175, 180, "capture", "console-home.html", False),
)

HONESTY = [
    "조립 매니페스트 (영상 파일 아님)",
    "모의 어댑터 동작 중",
    "Pi 실촬영 컷은 도착 후 교체",
    "수치는 데모 기준",
]


def build_assembly() -> dict:
    cut_by_index = {cut.index: cut for cut in CUTS}
    segments = []
    for seg in SEGMENTS:
        cut = cut_by_index[seg.cut_index]
        segments.append(
            {
                "index": seg.cut_index,
                "start": seg.start,
                "end": seg.end,
                "duration": seg.duration,
                "caption": cut.caption,
                "narration": cut.narration,
                "source_kind": seg.source_kind,
                "source_ref": seg.source_ref,
                "placeholder": seg.placeholder,
            }
        )
    return {
        "title": "Argus 데모 영상 조립 매니페스트",
        "total_seconds": SEGMENTS[-1].end if SEGMENTS else 0,
        "segment_count": len(SEGMENTS),
        "honesty": list(HONESTY),
        "segments": segments,
    }


def validate_assembly(assembly: dict) -> list[str]:
    problems: list[str] = []
    segments = assembly.get("segments", [])
    if assembly.get("segment_count") != len(segments):
        problems.append(
            f"세그먼트 수 불일치: {assembly.get('segment_count')} != {len(segments)}"
        )
    if assembly.get("total_seconds") != 180:
        problems.append(
            f"총 길이 불일치: {assembly.get('total_seconds')} != 180"
        )
    capture_filenames = {spec.filename for spec in CAPTURE_SPECS}
    prev_end = 0
    for seg in segments:
        index = seg.get("index")
        start = seg.get("start")
        end = seg.get("end")
        if start != prev_end:
            problems.append(
                f"컷 {index}: 구간 불연속 start {start} != 이전 end {prev_end}"
            )
        if start is not None and end is not None:
            if end <= start:
                problems.append(f"컷 {index}: 구간 순서 오류 {start}..{end}")
            if seg.get("duration") != end - start:
                problems.append(
                    f"컷 {index}: duration 불일치 {seg.get('duration')} != {end - start}"
                )
            prev_end = end
        caption = seg.get("caption")
        if not caption or not str(caption).strip():
            problems.append(f"컷 {index}: 자막이 비어 있다")
        if bool(seg.get("placeholder")) != (index == 3):
            problems.append(
                f"컷 {index}: placeholder는 컷 3만 True여야 한다"
            )
        source_ref = seg.get("source_ref")
        if not source_ref or not str(source_ref).strip():
            problems.append(f"컷 {index}: source_ref가 비어 있다")
        elif seg.get("source_kind") == "capture" and source_ref not in capture_filenames:
            problems.append(
                f"컷 {index}: capture source_ref가 CAPTURE_SPECS에 없다: {source_ref}"
            )
    if segments and prev_end != 180:
        problems.append(f"마지막 구간 종료 불일치: {prev_end} != 180")
    return problems


def _mmss(seconds: int) -> str:
    seconds = int(seconds)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def build_assembly_text(assembly: dict) -> str:
    lines = [f"{assembly.get('title')} (총 {assembly.get('total_seconds')}초)"]
    for seg in assembly.get("segments", []):
        lines.append(
            f"컷 {seg.get('index')} "
            f"[{_mmss(seg.get('start', 0))}-{_mmss(seg.get('end', 0))}] "
            f"{seg.get('source_kind')}:{seg.get('source_ref')}"
        )
        lines.append(f"  {seg.get('caption', '')}")
    return "\n".join(lines) + "\n"


def write_assembly(out_dir) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    assembly = build_assembly()
    json_path = out / "assembly.json"
    json_path.write_text(
        json.dumps(assembly, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    text_path = out / "assembly.txt"
    text_path.write_text(build_assembly_text(assembly), encoding="utf-8")
    return [json_path, text_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 데모 영상 조립 매니페스트 생성")
    parser.add_argument("--out", default="demo/assets", help="출력 디렉터리")
    args = parser.parse_args(argv)
    for path in write_assembly(args.out):
        print(path)
    problems = validate_assembly(build_assembly())
    for problem in problems:
        print(f"문제: {problem}")
    if not problems:
        print("검증 통과: 문제 없음")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
