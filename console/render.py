"""콘솔 뷰 모델을 외부 리소스 없는 단일 HTML 문서로 렌더링한다."""
from __future__ import annotations

import html

_CSS = """
body { font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; background: #f5f5f4; }
h1 { font-size: 1.5rem; }
h2 { font-size: 1.1rem; margin-top: 2rem; }
.badge { display: inline-block; margin-left: .5rem; padding: .2rem .6rem;
  background: #b42318; color: #fff; font-size: .85rem; font-weight: 700; border-radius: 4px; }
.cards { display: flex; gap: 1rem; flex-wrap: wrap; }
.card { background: #fff; border: 1px solid #d6d3d1; border-radius: 6px;
  padding: 1rem; min-width: 8rem; }
.card .label { font-size: .85rem; color: #57534e; }
.card .value { font-size: 1.5rem; font-weight: 700; }
table { border-collapse: collapse; background: #fff; }
th, td { border: 1px solid #d6d3d1; padding: .4rem .8rem; text-align: right; }
th { background: #e7e5e4; }
td:first-child, td:nth-child(2), td:last-child { text-align: left; }
.verdict-short { color: #b42318; font-weight: 700; }
.verdict-over { color: #b54708; font-weight: 700; }
.meta { color: #44403c; }
.note { margin-top: 2rem; color: #57534e; }
"""


def _signed(value) -> str:
    if isinstance(value, int):
        return f"{value:+d}"
    return f"{value:+g}"


def _row(bin_: dict) -> str:
    verdict = html.escape(str(bin_["verdict"]))
    return (
        "<tr>"
        f"<td>{html.escape(str(bin_['bin_id']))}</td>"
        f"<td>{html.escape(str(bin_['item_code']))}</td>"
        f"<td>{html.escape(str(bin_['book_qty']))}</td>"
        f"<td>{html.escape(str(bin_['counted_qty']))}</td>"
        f"<td>{html.escape(_signed(bin_['diff']))}</td>"
        f'<td class="verdict-{verdict}">{html.escape(str(bin_["verdict_label"]))}</td>'
        "</tr>"
    )


def _table(rows: list[dict]) -> str:
    header = (
        "<tr><th>빈</th><th>품목 코드</th><th>장부</th>"
        "<th>실측</th><th>차이</th><th>판정</th></tr>"
    )
    body = "".join(_row(row) for row in rows)
    return f"<table>{header}{body}</table>"


def _action_row(action: dict) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(action['priority']))}</td>"
        f"<td>{html.escape(str(action['bin_id']))}</td>"
        f"<td>{html.escape(str(action['item_code']))}</td>"
        f"<td>{html.escape(str(action['verdict_label']))}</td>"
        f"<td>{html.escape(_signed(action['diff']))}</td>"
        f"<td>{html.escape(str(action['action_hint']))}</td>"
        "</tr>"
    )


def _actions_table(actions: list[dict]) -> str:
    header = (
        "<tr><th>우선순위</th><th>빈</th><th>품목 코드</th>"
        "<th>판정</th><th>차이</th><th>조치 힌트</th></tr>"
    )
    body = "".join(_action_row(action) for action in actions)
    return f"<table>{header}{body}</table>"


def _card(label: str, value: str) -> str:
    return (
        f'<div class="card"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div></div>'
    )


_HONESTY_LINE = "준비 완료는 실호출·실촬영 성공을 뜻하지 않는다"


def _blocker_ids(readiness: dict, key: str, nested: dict) -> list[str]:
    ids = readiness.get(key)
    if ids is None:
        ids = [
            str(blocker.get("id", ""))
            for blocker in (nested.get("blockers") or [])
            if isinstance(blocker, dict)
        ]
    return [str(blocker_id) for blocker_id in (ids or [])]


def _blocker_line(blockers: list[str]) -> str:
    if blockers:
        return ", ".join(blockers)
    return "블로커 없음"


def _readiness_section(readiness: dict) -> str:
    sam = readiness.get("sam") or {}
    pi = readiness.get("pi") or {}
    sam_ready = readiness.get("sam_ready", sam.get("ready_for_live_call", False))
    pi_ready = readiness.get(
        "pi_ready", pi.get("ready_for_real_capture", False)
    )
    sam_blockers = _blocker_ids(readiness, "sam_blockers", sam)
    pi_blockers = _blocker_ids(readiness, "pi_blockers", pi)
    honesty = [str(item) for item in (readiness.get("honesty") or [])]
    if _HONESTY_LINE not in honesty:
        honesty.append(_HONESTY_LINE)
    honesty_html = "".join(
        f'<p class="meta">{html.escape(item)}</p>' for item in honesty
    )
    sam_line = "SAM 실호출 준비: " + ("준비 완료" if sam_ready else "준비 안 됨")
    pi_line = "Pi 실촬영 준비: " + ("준비 완료" if pi_ready else "준비 안 됨")
    return (
        "<section>\n"
        "<h2>준비 상태</h2>\n"
        f'<p class="meta">{html.escape(sam_line)}</p>\n'
        f'<p class="meta">{html.escape(pi_line)}</p>\n'
        f'<p class="meta">SAM 블로커: '
        f"{html.escape(_blocker_line(sam_blockers))}</p>\n"
        f'<p class="meta">Pi 블로커: '
        f"{html.escape(_blocker_line(pi_blockers))}</p>\n"
        f"{honesty_html}"
        "</section>\n"
    )


def render_html(view: dict) -> str:
    metrics = view["metrics"]
    badge = '<span class="badge">모의 데이터</span>' if view["is_mock"] else ""

    cards = "".join(
        [
            _card("실사 완료 빈", str(metrics["counted_bins"])),
            _card("일치", str(metrics["matched"])),
            _card("불일치", str(metrics["mismatched"])),
            _card("일치율", f"{metrics['match_rate_pct']:.1f}%"),
            _card("절대 차이 합계", str(metrics["abs_diff_total"])),
        ]
    )

    if view["differences"]:
        differences_html = _table(view["differences"])
    else:
        differences_html = "<p>차이 없음</p>"

    actions = view.get("actions") or []
    if actions:
        actions_html = _actions_table(actions)
    else:
        actions_html = "<p>차이 없음</p>"

    impact_html = (
        f'<p class="meta">{html.escape(str(view.get("impact_line", "")))}</p>'
    )

    readiness_html = _readiness_section(view.get("readiness") or {})

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Argus 콘솔 — 재고 실사</title>
<style>{_CSS}</style>
</head>
<body>
<header>
<h1>Argus 콘솔 — 재고 실사{badge}</h1>
</header>
<section>
<h2>요약 지표</h2>
<div class="cards">{cards}</div>
</section>
<section>
<h2>실사 세션 정보</h2>
<p class="meta">세션: {html.escape(str(view["session_id"]))}</p>
<p class="meta">생성 시각: {html.escape(str(view["generated_at"]))}</p>
<p class="meta">계수 출처: {html.escape(str(view["source_label"]))}</p>
</section>
{readiness_html}<section>
<h2>차이 목록</h2>
{differences_html}
</section>
<section>
<h2>조치 우선순위</h2>
{actions_html}
{impact_html}
</section>
<section>
<h2>전체 빈</h2>
{_table(view["bins"])}
</section>
<p class="note">MES · MW 모듈은 통합 관제판 골격만 표시합니다 (데모)</p>
<p class="note"><a href="/sessions">실사 세션 목록 보기</a></p>
</body>
</html>
"""


def _session_row(session: dict) -> str:
    sid = html.escape(str(session["session_id"]))
    return (
        "<tr>"
        f'<td><a href="/sessions/{sid}">{sid}</a></td>'
        f"<td>{html.escape(str(session['label']))}</td>"
        f"<td>{html.escape(str(session['counted_bins']))}</td>"
        f"<td>{html.escape(str(session['matched']))}</td>"
        f"<td>{html.escape(str(session['mismatched']))}</td>"
        f"<td>{html.escape(str(session['match_rate_pct']))}%</td>"
        f"<td>{html.escape(str(session['abs_diff_total']))}</td>"
        "</tr>"
    )


def render_sessions_html(list_view: dict) -> str:
    sessions = list_view.get("sessions") or []
    if sessions:
        header = (
            "<tr><th>세션</th><th>이름</th><th>실사 빈</th>"
            "<th>일치</th><th>불일치</th><th>일치율</th><th>절대 차이</th></tr>"
        )
        body = "".join(_session_row(s) for s in sessions)
        table_html = f"<table>{header}{body}</table>"
    else:
        table_html = "<p>세션 없음</p>"
    any_mock = any(s.get("is_mock") for s in sessions)
    badge = '<span class="badge">모의 데이터</span>' if any_mock else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>Argus 콘솔 — 실사 세션 목록</title>
<style>{_CSS}</style>
</head>
<body>
<header>
<h1>Argus 콘솔 — 실사 세션 목록{badge}</h1>
</header>
<section>
<p class="meta">전체 세션: {html.escape(str(list_view.get("total_sessions", 0)))}</p>
<p class="meta">전체 불일치: {html.escape(str(list_view.get("total_mismatched", 0)))}</p>
{table_html}
</section>
<p class="note"><a href="/">최신 세션 상세로 돌아가기</a></p>
</body>
</html>
"""
