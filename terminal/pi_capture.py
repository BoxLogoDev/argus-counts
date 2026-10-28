"""Pi 카메라 캡처 경계.

Raspberry Pi의 libcamera-still / raspistill 명령으로 빈(bin) 사진을
찍는 입력 경계다. Pi 실촬영 검증 전이며, 이 모듈이 존재한다는 것만으로
실촬영이 성공했다고 보지 않는다.

카메라 명령이 없으면 PiCaptureError를 던진다. 가짜 파일이나 모의
결과로 조용히 대체하지 않는다 — 없는 촬영을 있는 것처럼 만들면
재고 대조가 거짓으로 통과하기 때문이다.

명령 실행(runner)과 명령 탐지(which)는 주입 가능하게 둬서, Pi가 없는
환경에서도 가짜 runner로 검증할 수 있게 한다. 모듈을 불러오거나
probe만으로는 어떤 명령도 실행하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .photo_intake import CaptureRecord, load_capture

CAPTURE_COMMAND_CANDIDATES = ("libcamera-still", "raspistill")
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080


class PiCaptureError(Exception):
    """Pi 캡처 실패. 명령 부재·실행 실패·산출 파일 문제를 이 예외로만 모은다."""


def probe_pi_camera(which=None) -> dict:
    """캡처 명령의 존재만 탐지한다. 명령을 실행하지는 않는다."""
    finder = which if which is not None else shutil.which
    command = None
    command_path = None
    for candidate in CAPTURE_COMMAND_CANDIDATES:
        found = finder(candidate)
        if found:
            command = candidate
            command_path = found
            break
    return {
        "available": command is not None,
        "command": command,
        "command_path": command_path,
        "candidates_checked": list(CAPTURE_COMMAND_CANDIDATES),
        "honesty": [
            "Pi 실촬영 검증 전입니다",
            "카메라 명령이 있어도 실제 촬영 성공을 뜻하지 않습니다",
        ],
    }


def build_capture_command(
    command: str,
    output_path,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> list[str]:
    out = str(output_path)
    if command == "libcamera-still":
        return [
            command, "-o", out,
            "--width", str(width), "--height", str(height),
            "-n", "--timeout", "1000",
        ]
    if command == "raspistill":
        return [
            command, "-o", out,
            "-w", str(width), "-h", str(height),
            "-n", "-t", "1000",
        ]
    raise PiCaptureError(f"지원하지 않는 캡처 명령입니다: {command}")


def capture_photo(
    bin_id: str,
    output_path,
    runner=None,
    which=None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> CaptureRecord:
    probe = probe_pi_camera(which=which)
    if not probe["available"]:
        raise PiCaptureError(
            "Pi 카메라 명령을 찾을 수 없습니다: "
            + ", ".join(CAPTURE_COMMAND_CANDIDATES)
        )
    argv = build_capture_command(
        probe["command"], output_path, width=width, height=height
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    run = runner if runner is not None else subprocess.run
    try:
        completed = run(argv, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        # 원본 예외 문구를 메시지에 복사하지 않는다.
        raise PiCaptureError(
            f"Pi 캡처 명령 실행 중 오류가 발생했습니다 (bin={bin_id})."
        ) from exc
    returncode = getattr(completed, "returncode", None)
    if returncode != 0:
        raise PiCaptureError(
            f"Pi 캡처 명령이 실패했습니다 (returncode={returncode}, bin={bin_id})."
        )
    try:
        return load_capture(bin_id, path)
    except (FileNotFoundError, ValueError) as exc:
        raise PiCaptureError(
            f"Pi 캡처 산출 파일을 검증할 수 없습니다 (bin={bin_id})."
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pi 카메라 캡처 경계")
    parser.add_argument("--probe", action="store_true", help="캡처 명령 존재만 탐지")
    parser.add_argument(
        "--capture",
        action="append",
        default=[],
        help="빈과 출력 경로. 형식: BIN=PATH (예: A-01-02=/tmp/a.jpg)",
    )
    args = parser.parse_args(argv)
    if args.probe and not args.capture:
        print(json.dumps(probe_pi_camera(), ensure_ascii=False, indent=2))
        return 0
    if not args.capture:
        parser.error("--probe 또는 --capture 중 하나가 필요합니다")
    captures = []
    try:
        for raw in args.capture:
            bin_id, sep, out_path = raw.partition("=")
            if not sep or not bin_id or not out_path:
                parser.error(f"invalid --capture format (expected BIN=PATH): {raw}")
            record = capture_photo(bin_id, out_path)
            captures.append(
                {
                    "bin_id": record.bin_id,
                    "image_ref": record.image_ref,
                    "size_bytes": record.size_bytes,
                    "sha256": record.sha256,
                    "suffix": record.suffix,
                }
            )
    except PiCaptureError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    payload = {
        "captures": captures,
        "capture_source": "pi-camera",
        "honesty": [
            "Pi 카메라 명령으로 캡처를 시도한 결과이며 Pi 실촬영 검증 전입니다"
        ],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
