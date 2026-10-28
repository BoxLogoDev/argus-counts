"""SAM 3.1 실호출 전환 준비 점검 하네스.

실호출을 시작하기 전에 필요한 세 가지 — Model API 크레딧 입금 확인,
SAM_API_BASE_URL 존재, SAM_API_KEY 존재 — 가 갖춰졌는지만 점검한다.
이 하네스는 실제 API를 호출하지 않는다. 네트워크를 전혀 쓰지 않으며,
환경변수 값은 반환·출력하지 않고 존재 여부(bool)만 확인한다.
준비 완료(ready_for_live_call=True)는 실호출 성공을 뜻하지 않는다.
실제 호출 성공은 크레딧 입금과 키 발급 뒤 별도로 확인해야 한다.

실행: 프로젝트 루트에서 `python3 -m qa.sam_readiness`
`--credit-confirmed`는 크레딧 입금을 외부에서 확인했음을 알리는 플래그다.
이 하네스 자체는 입금을 확인할 수 없어, 플래그가 없으면 블로커로 남긴다.
`--json`을 주면 같은 내용을 JSON으로 출력한다.
준비 완료이면 종료코드 0, 아니면 1이다.
"""
from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping

ENV_BASE_URL = "SAM_API_BASE_URL"
ENV_KEY_VAR = "SAM_" + "API_KEY"

_BLOCKER_DETAILS = {
    "sam_credit_not_confirmed": "SAM 크레딧 입금이 확인되지 않았습니다. 입금 확인 전 호출은 카드로 청구될 수 있습니다",
    "sam_base_url_missing": "SAM_API_BASE_URL 환경변수가 설정되지 않았습니다",
    "sam_api_key_missing": "SAM_API_KEY 환경변수가 설정되지 않았습니다. 키는 보안 경로로만 받아야 합니다",
}

# 결정적 순서: 크레딧 → base_url → api_key
_BLOCKER_ORDER = (
    "sam_credit_not_confirmed",
    "sam_base_url_missing",
    "sam_api_key_missing",
)

HONESTY = [
    "실제 API를 호출하지 않는다",
    "환경변수 값은 확인하지 않고 존재 여부만 확인한다",
    "준비 완료는 실호출 성공을 뜻하지 않는다",
]


def check_readiness(
    env: Mapping[str, str] | None = None, credit_confirmed: bool = False
) -> dict:
    """준비 상태를 점검한다. env 값은 결과 어디에도 넣지 않는다."""
    env = os.environ if env is None else env
    base_url_present = bool(env.get(ENV_BASE_URL))
    api_key_present = bool(env.get(ENV_KEY_VAR))
    credit = bool(credit_confirmed)

    conditions = {
        "sam_credit_not_confirmed": not credit,
        "sam_base_url_missing": not base_url_present,
        "sam_api_key_missing": not api_key_present,
    }
    blockers = [
        {"id": blocker_id, "detail": _BLOCKER_DETAILS[blocker_id]}
        for blocker_id in _BLOCKER_ORDER
        if conditions[blocker_id]
    ]
    would_select_live = base_url_present and api_key_present
    return {
        "base_url_present": base_url_present,
        "api_key_present": api_key_present,
        "credit_confirmed": credit,
        "would_select_live": would_select_live,
        "ready_for_live_call": credit and would_select_live,
        "blockers": blockers,
        "honesty": list(HONESTY),
    }


def build_report(
    env: Mapping[str, str] | None = None, credit_confirmed: bool = False
) -> dict:
    """check_readiness 결과를 JSON 직렬화 가능한 dict로 반환한다."""
    return check_readiness(env=env, credit_confirmed=credit_confirmed)


def format_text_report(report: dict) -> str:
    lines: list[str] = []
    credit_mark = "PASS" if report["credit_confirmed"] else "FAIL"
    lines.append(f"[{credit_mark}] credit_confirmed — {report['credit_confirmed']}")
    lines.append(
        f"[{'PASS' if report['base_url_present'] else 'FAIL'}] "
        f"{ENV_BASE_URL}: {'present' if report['base_url_present'] else 'missing'}"
    )
    lines.append(
        f"[{'PASS' if report['api_key_present'] else 'FAIL'}] "
        f"{ENV_KEY_VAR}: {'present' if report['api_key_present'] else 'missing'}"
    )
    lines.append(f"BLOCKERS: {len(report['blockers'])}")
    for blocker in report["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    ready = "true" if report["ready_for_live_call"] else "false"
    lines.append(f"READY_FOR_LIVE_CALL: {ready}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    report = build_report(credit_confirmed="--credit-confirmed" in argv)
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    return 0 if report["ready_for_live_call"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
