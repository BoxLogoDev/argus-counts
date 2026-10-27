"""시뮬레이터 리포트를 콘솔 화면용 뷰 모델로 바꾼다."""
from __future__ import annotations

from terminal.report import build_actions, impact_line


def _verdict_label(verdict: str) -> str:
    if verdict == "match":
        return "일치"
    if verdict == "short":
        return "부족"
    return "초과"


def build_view(report: dict) -> dict:
    summary = report["summary"]
    match_rate = float(summary["match_rate"])

    bins = [
        {**bin_, "verdict_label": _verdict_label(bin_["verdict"])}
        for bin_ in report["bins"]
    ]
    differences = [bin_ for bin_ in bins if bin_["verdict"] != "match"]
    actions = [
        {**action, "verdict_label": _verdict_label(action["verdict"])}
        for action in build_actions(report)
    ]

    source = report["source"]
    is_mock = source == "mock"

    return {
        "session_id": report["session_id"],
        "generated_at": report["generated_at"],
        "source": source,
        "is_mock": is_mock,
        "source_label": "모의" if is_mock else "SAM 실호출",
        "metrics": {
            "counted_bins": summary["counted_bins"],
            "matched": summary["matched"],
            "mismatched": summary["mismatched"],
            "match_rate": match_rate,
            "match_rate_pct": round(match_rate * 100, 1),
            "abs_diff_total": summary["abs_diff_total"],
            "net_diff": summary["net_diff"],
        },
        "differences": differences,
        "bins": bins,
        "actions": actions,
        "impact_line": impact_line(report),
    }
