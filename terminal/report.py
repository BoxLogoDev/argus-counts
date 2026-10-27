"""차이 리포트 완성 모듈.

시뮬레이터 리포트(terminal.simulator.run_simulation 결과 dict)를 받아
현장 작업자가 바로 쓸 수 있는 형태로 가공한다.

- build_actions: 불일치 빈을 |차이| 큰 순으로 정렬한 조치 우선순위 목록.
  각 항목에 판정별 조치 힌트를 붙인다.
- impact_line: 제출 서술에 넣을 영향 수치 한 줄. 모의(source="mock")
  기반이면 "데모 기준"을 반드시 앞에 붙여 실측으로 오해되지 않게 한다.
- format_text_report: 사람이 읽는 한국어 텍스트 리포트.
- build_report_payload: 콘솔·외부 연동용 구조화 payload(JSON).

표준 라이브러리만 쓴다. SAM/Model API 실호출은 여기서 하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .simulator import run_simulation

_VERDICT_LABEL = {"match": "일치", "short": "부족", "over": "초과"}

_ACTION_HINTS = {
    "short": "재촬영으로 재확인하고 입고·출고 기록을 대조하세요",
    "over": "오적재 여부를 확인하고 이동·반품 기록을 대조하세요",
}


def action_hint(verdict: str) -> str:
    """판정별 조치 힌트. 일치(match) 등 불일치가 아니면 빈 문자열."""
    return _ACTION_HINTS.get(verdict, "")


def build_actions(report: dict) -> list[dict]:
    """불일치 빈만 골라 조치 우선순위 목록을 만든다.

    정렬: |diff| 내림차순, 동률이면 bin_id 오름차순. priority는 1부터.
    """
    mismatched = [b for b in report["bins"] if b["verdict"] != "match"]
    mismatched.sort(key=lambda b: (-abs(b["diff"]), b["bin_id"]))
    return [
        {
            "priority": idx + 1,
            "bin_id": b["bin_id"],
            "item_code": b["item_code"],
            "verdict": b["verdict"],
            "diff": b["diff"],
            "abs_diff": abs(b["diff"]),
            "book_qty": b["book_qty"],
            "counted_qty": b["counted_qty"],
            "action_hint": action_hint(b["verdict"]),
        }
        for idx, b in enumerate(mismatched)
    ]


def impact_line(report: dict) -> str:
    """영향 수치 한 줄. 모의 기반이면 '데모 기준' 접두어를 붙인다."""
    summary = report["summary"]
    pct = round(float(summary["match_rate"]) * 100, 1)
    line = (
        f"빈 {summary['counted_bins']}개 중 불일치 {summary['mismatched']}건, "
        f"절대 차이 {summary['abs_diff_total']}개, 일치율 {pct:.1f}%"
    )
    if report["source"] == "mock":
        return f"데모 기준: {line}"
    return line


def _signed(value: int) -> str:
    return f"{value:+d}"


def format_text_report(report: dict) -> str:
    summary = report["summary"]
    pct = round(float(summary["match_rate"]) * 100, 1)
    source_label = "모의" if report["source"] == "mock" else "SAM 실호출"

    lines = [
        "Argus 차이 리포트",
        f"세션: {report['session_id']}",
        f"생성 시각: {report['generated_at']}",
        f"계수 출처: {source_label}",
        "",
        "요약 지표",
        f"- 실사 완료 빈: {summary['counted_bins']}",
        f"- 일치: {summary['matched']}",
        f"- 불일치: {summary['mismatched']}",
        f"- 일치율: {pct:.1f}%",
        f"- 절대 차이 합계: {summary['abs_diff_total']}",
        f"- 순차이: {_signed(summary['net_diff'])}",
        "",
        "조치 우선순위",
    ]

    actions = build_actions(report)
    if actions:
        for a in actions:
            label = _VERDICT_LABEL.get(a["verdict"], a["verdict"])
            lines.append(
                f"{a['priority']}. [{label}] {a['bin_id']} {a['item_code']} "
                f"장부 {a['book_qty']} → 실측 {a['counted_qty']} "
                f"(차이 {_signed(a['diff'])}) — {a['action_hint']}"
            )
    else:
        lines.append("차이 없음")

    lines += ["", "전체 빈"]
    for b in report["bins"]:
        label = _VERDICT_LABEL.get(b["verdict"], b["verdict"])
        lines.append(
            f"- {b['bin_id']} {b['item_code']} 장부 {b['book_qty']} "
            f"실측 {b['counted_qty']} 차이 {_signed(b['diff'])} [{label}]"
        )

    lines += ["", impact_line(report)]
    return "\n".join(lines) + "\n"


def build_report_payload(report: dict) -> dict:
    """구조화 payload. 콘솔·연동에서 그대로 JSON으로 내보낼 수 있다."""
    return {
        "session_id": report["session_id"],
        "generated_at": report["generated_at"],
        "source": report["source"],
        "summary": report["summary"],
        "actions": build_actions(report),
        "impact_line": impact_line(report),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus difference report")
    parser.add_argument("--json", action="store_true", help="payload를 JSON으로 출력")
    parser.add_argument("--out", default=None, help="출력 저장 경로")
    parser.add_argument("--session-id", default=None, help="세션 id")
    args = parser.parse_args(argv)

    report = run_simulation(session_id=args.session_id)
    if args.json:
        text = json.dumps(build_report_payload(report), ensure_ascii=False, indent=2) + "\n"
    else:
        text = format_text_report(report)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
