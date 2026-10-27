"""QA 기준값 대조 하네스.

데모 시나리오의 기준값을 이 파일에 리터럴로 고정해 두고, 실제 실행
결과(단말 시뮬레이터 리포트와 콘솔 뷰 모델)를 그 기준과 대조한다.
기준값을 terminal/demo_data에서 가져와 복사하지 않는 것이 핵심이다:
소스 데이터나 대조 엔진이 드리프트하면 하네스가 실패로 잡아내야 한다.

기준 시나리오: 데모 빈 6개 — 일치 4, 부족 1(A-01-02, 장부 8 → 실측 5),
초과 1(B-01-02, 장부 6 → 실측 9). 절대 차이 합계 6, 순차이 0, 일치율 4/6.

실행: 프로젝트 루트에서 `python3 -m qa`
전부 통과하면 종료코드 0, 하나라도 실패하면 1.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

from console.view import build_view
from terminal.simulator import run_simulation

# --- 기준값 (단일 출처: 이 리터럴들) ---

EXPECTED_BOOK_QTY = {
    "A-01-01": 12,
    "A-01-02": 8,
    "A-02-02": 15,
    "A-03-01": 18,
    "B-01-02": 6,
    "B-02-02": 10,
}

EXPECTED_COUNTED_QTY = {
    "A-01-01": 12,
    "A-01-02": 5,
    "A-02-02": 15,
    "A-03-01": 18,
    "B-01-02": 9,
    "B-02-02": 10,
}

EXPECTED_VERDICTS = {
    "A-01-01": "match",
    "A-01-02": "short",
    "A-02-02": "match",
    "A-03-01": "match",
    "B-01-02": "over",
    "B-02-02": "match",
}

EXPECTED_DIFFS = {
    "A-01-01": 0,
    "A-01-02": -3,
    "A-02-02": 0,
    "A-03-01": 0,
    "B-01-02": 3,
    "B-02-02": 0,
}

EXPECTED_SHORTAGE_BINS = ["A-01-02"]
EXPECTED_OVERAGE_BINS = ["B-01-02"]

EXPECTED_SUMMARY = {
    "counted_bins": 6,
    "matched": 4,
    "mismatched": 2,
    "match_rate": 4 / 6,
    "abs_diff_total": 6,
    "net_diff": 0,
}

EXPECTED_MATCH_RATE_PCT = 66.7


@dataclass(frozen=True)
class QACheck:
    name: str
    passed: bool
    detail: str


def _per_bin_mismatches(bins: dict, field: str, expected: dict) -> list[str]:
    out = []
    for bin_id, want in expected.items():
        if bin_id not in bins:
            out.append(f"{bin_id}: missing")
        elif bins[bin_id][field] != want:
            out.append(f"{bin_id}: {field}={bins[bin_id][field]} expected={want}")
    return out


def run_checks() -> list[QACheck]:
    """기준값 대조 체크를 전부 실행해 결과 목록을 돌려준다.

    개별 체크에서 예외가 나도 그 체크만 실패로 기록하고 계속 진행한다.
    """
    checks: list[QACheck] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append(QACheck(name=name, passed=bool(passed), detail=str(detail)))

    try:
        report = run_simulation(session_id="QA-FIXED")
    except Exception as exc:  # 시뮬레이션 자체가 깨지면 나머지는 판정 불가
        add("simulation_runs", False, f"run_simulation raised: {exc!r}")
        return checks
    add("simulation_runs", True, f"session_id={report['session_id']}")

    bins = {b["bin_id"]: b for b in report["bins"]}

    add(
        "bin_set_matches",
        set(bins) == set(EXPECTED_BOOK_QTY),
        f"bins={sorted(bins)}",
    )

    for name, field, expected in (
        ("book_qty_per_bin", "book_qty", EXPECTED_BOOK_QTY),
        ("counted_qty_per_bin", "counted_qty", EXPECTED_COUNTED_QTY),
        ("verdict_per_bin", "verdict", EXPECTED_VERDICTS),
        ("diff_per_bin", "diff", EXPECTED_DIFFS),
    ):
        mismatches = _per_bin_mismatches(bins, field, expected)
        add(
            name,
            not mismatches,
            "; ".join(mismatches) if mismatches else "all 6 bins match",
        )

    shortage = [b["bin_id"] for b in report["bins"] if b["verdict"] == "short"]
    overage = [b["bin_id"] for b in report["bins"] if b["verdict"] == "over"]
    add(
        "shortage_bins_exact",
        shortage == EXPECTED_SHORTAGE_BINS,
        f"shortage={shortage}",
    )
    add(
        "overage_bins_exact",
        overage == EXPECTED_OVERAGE_BINS,
        f"overage={overage}",
    )

    summary = report["summary"]
    for key, want in EXPECTED_SUMMARY.items():
        got = summary.get(key)
        if isinstance(want, float):
            ok = got is not None and abs(float(got) - want) < 1e-9
        else:
            ok = got == want
        add(f"summary_{key}", ok, f"{key}={got} expected={want}")

    add(
        "source_is_mock",
        report["source"] == "mock",
        f"source={report['source']} (모의 결과임을 명시 검증)",
    )

    try:
        view = build_view(report)
        metrics = view["metrics"]
        metric_keys = (
            "counted_bins",
            "matched",
            "mismatched",
            "abs_diff_total",
            "net_diff",
        )
        off = [
            f"{k}: view={metrics[k]} summary={summary[k]}"
            for k in metric_keys
            if metrics[k] != summary[k]
        ]
        if abs(metrics["match_rate"] - summary["match_rate"]) >= 1e-9:
            off.append(
                f"match_rate: view={metrics['match_rate']} "
                f"summary={summary['match_rate']}"
            )
        if metrics["match_rate_pct"] != EXPECTED_MATCH_RATE_PCT:
            off.append(
                f"match_rate_pct={metrics['match_rate_pct']} "
                f"expected={EXPECTED_MATCH_RATE_PCT}"
            )
        add(
            "console_metrics_match",
            not off,
            "; ".join(off) if off else "view metrics == report summary",
        )

        diff_bins = sorted(b["bin_id"] for b in view["differences"])
        want_diff_bins = sorted(EXPECTED_SHORTAGE_BINS + EXPECTED_OVERAGE_BINS)
        add(
            "console_differences_match",
            diff_bins == want_diff_bins,
            f"differences={diff_bins}",
        )
    except Exception as exc:
        add("console_metrics_match", False, f"build_view raised: {exc!r}")
        add("console_differences_match", False, "build_view failed")

    return checks


def main(argv: list[str] | None = None) -> int:
    checks = run_checks()
    passed = 0
    for check in checks:
        mark = "PASS" if check.passed else "FAIL"
        if check.passed:
            passed += 1
        sys.stdout.write(f"[{mark}] {check.name} — {check.detail}\n")
    sys.stdout.write(f"QA: {passed}/{len(checks)} passed\n")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
