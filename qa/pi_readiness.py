"""Pi 실촬영 준비 점검 하네스.

실촬영을 시작하기 전에 필요한 두 가지 — Pi 장치 도착의 외부 확인,
이 환경에 Pi 카메라 명령(libcamera-still/raspistill) 존재 —
가 갖춰졌는지만 점검한다.
이 하네스는 실제 촬영을 하지 않는다.
카메라 명령을 실행하지 않는다(probe는 존재 탐지만 한다).
장치 도착은 이 하네스가 확인할 수 없어 외부 확인 플래그로만 받는다.
준비 완료(ready_for_real_capture=True)는 Pi 실촬영 성공을 뜻하지 않는다.
실제 촬영 성공은 장치와 카메라가 갖춰진 뒤 별도로 확인해야 한다.

실행: 프로젝트 루트에서 `python3 -m qa.pi_readiness`
`--device-confirmed`는 Pi 장치 도착을 외부에서 확인했음을 알리는 플래그다.
이 하네스 자체는 장치 도착을 확인할 수 없어, 플래그가 없으면 블로커로 남긴다.
`--json`을 주면 같은 내용을 JSON으로 출력한다.
준비 완료이면 종료코드 0, 아니면 1이다.
"""
from __future__ import annotations

import json
import sys

from terminal.pi_capture import probe_pi_camera

_BLOCKER_DETAILS = {
    "pi_device_arrival_not_confirmed": "장치 도착이 외부에서 확인되지 않았습니다",
    "pi_camera_command_missing": "Pi 카메라 명령(libcamera-still, raspistill)을 찾을 수 없습니다 — 이 환경에서는 실촬영을 시작할 수 없습니다",
}

# 결정적 순서: 장치 도착 확인 → 카메라 명령
_BLOCKER_ORDER = (
    "pi_device_arrival_not_confirmed",
    "pi_camera_command_missing",
)

HONESTY = [
    "실제 촬영을 하지 않는다",
    "카메라 명령을 실행하지 않고 존재만 탐지한다",
    "준비 완료는 Pi 실촬영 성공을 뜻하지 않는다",
]


def check_readiness(
    probe: dict | None = None, device_confirmed: bool = False, which=None
) -> dict:
    """준비 상태를 점검한다. probe가 없으면 명령 존재만 탐지한다."""
    if probe is None:
        probe = probe_pi_camera(which=which)
    device = bool(device_confirmed)
    camera_available = bool(probe["available"])

    conditions = {
        "pi_device_arrival_not_confirmed": not device,
        "pi_camera_command_missing": not camera_available,
    }
    blockers = [
        {"id": blocker_id, "detail": _BLOCKER_DETAILS[blocker_id]}
        for blocker_id in _BLOCKER_ORDER
        if conditions[blocker_id]
    ]
    return {
        "device_confirmed": device,
        "camera_available": camera_available,
        "camera_command": probe.get("command"),
        "candidates_checked": list(probe["candidates_checked"]),
        "ready_for_real_capture": device and camera_available,
        "blockers": blockers,
        "honesty": list(HONESTY),
    }


def build_report(
    probe: dict | None = None, device_confirmed: bool = False, which=None
) -> dict:
    """check_readiness 결과를 JSON 직렬화 가능한 dict로 반환한다."""
    return check_readiness(probe=probe, device_confirmed=device_confirmed, which=which)


def format_text_report(report: dict) -> str:
    lines: list[str] = []
    device_mark = "PASS" if report["device_confirmed"] else "FAIL"
    lines.append(f"[{device_mark}] device_confirmed — {report['device_confirmed']}")
    lines.append(
        f"[{'PASS' if report['camera_available'] else 'FAIL'}] "
        f"pi_camera_command: {report['camera_command'] or 'missing'}"
    )
    lines.append(f"BLOCKERS: {len(report['blockers'])}")
    for blocker in report["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    ready = "true" if report["ready_for_real_capture"] else "false"
    lines.append(f"READY_FOR_REAL_CAPTURE: {ready}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    report = build_report(device_confirmed="--device-confirmed" in argv)
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    return 0 if report["ready_for_real_capture"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
