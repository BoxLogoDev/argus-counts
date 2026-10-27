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


def _card(label: str, value: str) -> str:
    return (
        f'<div class="card"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div></div>'
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
<section>
<h2>차이 목록</h2>
{differences_html}
</section>
<section>
<h2>전체 빈</h2>
{_table(view["bins"])}
</section>
<p class="note">MES · MW 모듈은 통합 관제판 골격만 표시합니다 (데모)</p>
</body>
</html>
"""
