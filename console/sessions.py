"""데모 세션 목록용 콘솔 뷰.

모든 리포트는 모의 데이터 기반이다. terminal.demo_sessions의 스펙으로
terminal.simulator.run_simulation을 실행해 만든다. 실제 회사 자료나
SAM/Model API 실호출은 쓰지 않는다.
"""
from __future__ import annotations

from terminal.demo_sessions import counted_qty_for, demo_session_specs
from terminal.simulator import run_simulation


def list_session_reports() -> list[dict]:
    return [
        run_simulation(
            session_id=spec["session_id"], counted_qty=spec["counted_qty"]
        )
        for spec in demo_session_specs()
    ]


def get_session_report(session_id: str) -> dict | None:
    counted_qty = counted_qty_for(session_id)
    if counted_qty is None:
        return None
    return run_simulation(session_id=session_id, counted_qty=counted_qty)


def build_session_list_view() -> dict:
    sessions = []
    for spec, report in zip(demo_session_specs(), list_session_reports()):
        summary = report["summary"]
        source = report["source"]
        sessions.append(
            {
                "session_id": report["session_id"],
                "label": spec["label"],
                "generated_at": report["generated_at"],
                "source": source,
                "is_mock": source == "mock",
                "counted_bins": summary["counted_bins"],
                "matched": summary["matched"],
                "mismatched": summary["mismatched"],
                "match_rate_pct": round(float(summary["match_rate"]) * 100, 1),
                "abs_diff_total": summary["abs_diff_total"],
                "net_diff": summary["net_diff"],
            }
        )
    return {
        "sessions": sessions,
        "total_sessions": len(sessions),
        "total_mismatched": sum(s["mismatched"] for s in sessions),
    }
