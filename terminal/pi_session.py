"""Pi 촬영 세션 오케스트레이션.

Pi 카메라 캡처 경계(terminal/pi_capture.py)와 파일 기반 사진 입력
(terminal/photo_intake.py)을 이어, 한 번의 호출로 촬영부터 계수,
대조, 리포트까지 수행한다. Pi 실촬영 검증 전이며, 이 모듈이
존재한다는 것만으로 실촬영이 성공했다고 보지 않는다.

카메라 명령이 없으면 실패한다. 가짜 파일이나 모의 결과로 조용히
대체하지 않는다. 없는 촬영을 있는 것처럼 만들면 재고 대조가
거짓으로 통과하기 때문이다.

명령 실행(runner)과 명령 탐지(which)는 주입 가능하게 둬서, Pi가 없는
환경에서도 가짜 runner로 검증할 수 있게 한다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .demo_data import demo_bin_ids
from .photo_intake import run_photo_intake
from .pi_capture import PiCaptureError, capture_photo, probe_pi_camera


def capture_filename(bin_id: str) -> str:
    return f"{bin_id}.jpg"


def run_pi_session(
    output_dir,
    bin_ids=None,
    session_id=None,
    runner=None,
    which=None,
    counted_qty=None,
) -> dict:
    if bin_ids is None:
        bin_ids = demo_bin_ids()
    bin_ids = sorted(bin_ids)
    if not bin_ids:
        raise ValueError("bin_ids must not be empty")
    probe = probe_pi_camera(which=which)
    if not probe["available"]:
        raise PiCaptureError(
            "Pi 카메라 명령을 찾을 수 없습니다: "
            + ", ".join(probe["candidates_checked"])
        )
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    captures = {}
    for bin_id in bin_ids:
        path = output_path / capture_filename(bin_id)
        capture_photo(bin_id, path, runner=runner, which=which)
        captures[bin_id] = path
    report = run_photo_intake(
        captures, session_id=session_id, counted_qty=counted_qty
    )
    result = dict(report)
    result["capture_source"] = "pi-camera"
    result["probe"] = {
        "available": probe["available"],
        "command": probe["command"],
        "candidates_checked": probe["candidates_checked"],
    }
    result["honesty"] = [
        "Pi 카메라 명령으로 캡처를 시도한 세션이며 Pi 실촬영 검증 전입니다",
        "계수는 모의 어댑터 결과일 수 있으며 source 필드로 구분합니다",
    ]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pi 촬영 세션 오케스트레이션")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--bin", action="append", dest="bins", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    try:
        result = run_pi_session(
            args.out_dir, bin_ids=args.bins, session_id=args.session_id
        )
    except PiCaptureError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text, file=sys.stdout)
    if args.out is not None:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
