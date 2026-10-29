"""콘솔 준비 상태 뷰 모델.

SAM 실호출 준비(qa.sam_readiness)와 Pi 실촬영 준비(qa.pi_readiness)를
한 dict로 묶는다. 실제 API 호출·실제 촬영을 하지 않으며, 준비 완료는
실호출·실촬영 성공을 뜻하지 않는다.
"""
from __future__ import annotations

from qa import pi_readiness, sam_readiness

HONESTY = [
    "실제 API를 호출하지 않는다",
    "실제 촬영을 하지 않는다",
    "준비 완료는 실호출·실촬영 성공을 뜻하지 않는다",
]


def build_readiness(
    env=None,
    sam_credit_confirmed=False,
    pi_device_confirmed=False,
    pi_probe=None,
    pi_which=None,
) -> dict:
    sam = sam_readiness.check_readiness(
        env=env, credit_confirmed=sam_credit_confirmed
    )
    pi = pi_readiness.check_readiness(
        probe=pi_probe, device_confirmed=pi_device_confirmed, which=pi_which
    )
    sam_blockers = [blocker["id"] for blocker in sam["blockers"]]
    pi_blockers = [blocker["id"] for blocker in pi["blockers"]]
    sam_ready = sam["ready_for_live_call"]
    pi_ready = pi["ready_for_real_capture"]
    return {
        "sam": sam,
        "pi": pi,
        "sam_blockers": sam_blockers,
        "pi_blockers": pi_blockers,
        "blocker_count": len(sam_blockers) + len(pi_blockers),
        "sam_ready": sam_ready,
        "pi_ready": pi_ready,
        "overall_ready": sam_ready and pi_ready,
        "honesty": list(HONESTY),
    }


def build_readiness_payload(
    env=None,
    sam_credit_confirmed=False,
    pi_device_confirmed=False,
    pi_probe=None,
    pi_which=None,
) -> dict:
    return build_readiness(
        env=env,
        sam_credit_confirmed=sam_credit_confirmed,
        pi_device_confirmed=pi_device_confirmed,
        pi_probe=pi_probe,
        pi_which=pi_which,
    )
