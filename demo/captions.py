"""데모 영상 자막·샷 리스트 자산 생성.

docs/demo-script.md의 3분 컷 표(9개 컷)를 구조화 데이터로 고정하고,
영상 제작에 바로 쓰는 자막 파일(SRT·VTT)과 샷 리스트(JSON)를 만든다.
나레이션 문장은 유지하고 나레이션 속도 경고 해소를 위해 컷 구간만 재조정한다.

실행: 프로젝트 루트에서 `python3 -m demo.captions` (기본 출력 demo/assets/)
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Cut:
    index: int
    start: int  # 초
    end: int  # 초
    screen: str
    narration: str
    caption: str


CUTS: tuple[Cut, ...] = (
    Cut(
        1, 0, 18,
        "단말 실동작 화면으로 바로 시작한다. 시뮬레이터 콘솔 화면과 Argus 제목을 보여준다. 제목 바로 아래에 기존과 신규 구분 한 줄을 띄운다.",
        "Argus는 창고 재고실사 코파일럿입니다. 기존 도구는 SAM 3.1과 Model API입니다. 이 저장소의 코드는 해커톤 기간에 새로 만들었습니다.",
        "Argus. 창고 재고실사 코파일럿",
    ),
    Cut(
        2, 18, 30,
        "빈 목록과 실사 문제를 보여주는 시뮬레이터 화면. 빈 6개 데모 세션을 연다.",
        "실사는 빈마다 세고 장부와 맞춰야 합니다. 사람이 세면 시간과 오차가 함께 늘어납니다.",
        "문제. 세는 시간과 오차",
    ),
    Cut(
        3, 30, 50,
        "Pi 실촬영 컷 자리. 지금은 빈 촬영 단계의 시뮬레이터 화면을 보여준다. 화면 한쪽에 플레이스홀더 문구를 띄운다.",
        "첫 단계는 촬영입니다. 이 컷은 Pi 도착 후 실촬영으로 교체합니다. 지금은 시뮬레이터로 흐름을 보여줍니다.",
        "1. 촬영. Pi 도착 후 교체",
    ),
    Cut(
        4, 50, 75,
        "SAM 계수 단계 화면. 계수 출처가 모의로 표기된 부분을 확대한다. 환경변수 전환 구조를 짧게 보여준다.",
        "두 번째는 SAM 계수입니다. 데모 계수는 모의 어댑터 기준입니다. 실호출은 단일 빈 스모크로 검증했습니다.",
        "2. SAM 계수. 현재 모의(mock)",
    ),
    Cut(
        5, 75, 105,
        "장부 대조 화면. 빈별 장부 수량과 실측 수량과 판정을 보여준다.",
        "세 번째는 장부 대조입니다. 일치와 부족과 초과로 판정합니다. 데모 기준 빈 6개 중 일치 4건과 불일치 2건입니다.",
        "3. 장부 대조. 일치 4와 불일치 2",
    ),
    Cut(
        6, 105, 130,
        "차이 목록 화면. A-01-02 부족과 B-01-02 초과를 보여준다.",
        "차이 목록입니다. A-01-02는 장부 8에서 실측 5로 부족입니다. B-01-02는 장부 6에서 실측 9로 초과입니다.",
        "차이 목록. 부족 1과 초과 1",
    ),
    Cut(
        7, 130, 155,
        "조치 우선순위 화면. 절대 차이 큰 순 정렬과 조치 힌트를 보여준다.",
        "리포트는 절대 차이 큰 순으로 조치 순서를 정합니다. 부족이면 재촬영과 입출고 기록 대조를 안내합니다. 초과이면 오적재 확인을 안내합니다.",
        "조치 우선순위. 절대 차이 큰 순",
    ),
    Cut(
        8, 155, 170,
        "텍스트 리포트와 콘솔 요약 지표 화면. QA 하네스와 테스트 수치를 짧게 보여준다.",
        "마지막은 차이 리포트입니다. QA 하네스 17개 체크와 단위 테스트 431개로 기준값을 지킵니다.",
        "리포트. QA 17개와 테스트 431개",
    ),
    Cut(
        9, 170, 180,
        "영향 한 줄 화면. 모의 표기와 함께 보여준다.",
        "데모 기준 빈 6개 중 불일치 2건과 절대 차이 6개와 일치율 66.7%를 한 번에 정리합니다.",
        "데모 기준. 불일치 2건과 일치율 66.7%",
    ),
)

HONESTY = [
    "모의 어댑터 동작 중",
    "Pi 실촬영 컷은 도착 후 교체",
    "수치는 데모 기준",
]


def _hms(seconds: int) -> tuple[int, int, int]:
    return seconds // 3600, (seconds % 3600) // 60, seconds % 60


def format_srt_timestamp(seconds: int) -> str:
    h, m, s = _hms(int(seconds))
    return f"{h:02d}:{m:02d}:{s:02d},000"


def format_vtt_timestamp(seconds: int) -> str:
    h, m, s = _hms(int(seconds))
    return f"{h:02d}:{m:02d}:{s:02d}.000"


def build_srt(cuts: tuple[Cut, ...] = CUTS) -> str:
    blocks = []
    for cut in cuts:
        blocks.append(
            f"{cut.index}\n"
            f"{format_srt_timestamp(cut.start)} --> {format_srt_timestamp(cut.end)}\n"
            f"{cut.caption}"
        )
    return "\n\n".join(blocks) + "\n"


def build_vtt(cuts: tuple[Cut, ...] = CUTS) -> str:
    blocks = ["WEBVTT"]
    for cut in cuts:
        blocks.append(
            f"{format_vtt_timestamp(cut.start)} --> {format_vtt_timestamp(cut.end)}\n"
            f"{cut.caption}"
        )
    return "\n\n".join(blocks) + "\n"


def build_shot_list(cuts: tuple[Cut, ...] = CUTS) -> dict:
    return {
        "title": "Argus 데모 영상 샷 리스트",
        "total_seconds": cuts[-1].end if cuts else 0,
        "cut_count": len(cuts),
        "honesty": list(HONESTY),
        "cuts": [
            {
                "index": c.index,
                "start": c.start,
                "end": c.end,
                "screen": c.screen,
                "narration": c.narration,
                "caption": c.caption,
            }
            for c in cuts
        ],
    }


def write_assets(out_dir) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    targets = {
        "captions.srt": build_srt(),
        "captions.vtt": build_vtt(),
        "shot-list.json": json.dumps(build_shot_list(), ensure_ascii=False, indent=2) + "\n",
    }
    written: list[Path] = []
    for name, text in targets.items():
        path = out / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 데모 영상 자산 생성")
    parser.add_argument("--out", default="demo/assets", help="출력 디렉터리")
    args = parser.parse_args(argv)
    for path in write_assets(args.out):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
