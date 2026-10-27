"""콘솔 화면 캡처 자산 생성.

데모 영상 제작용으로 실제 콘솔 서버 응답을 그대로 파일로 저장하고
매니페스트(JSON)를 만든다. PNG 스크린샷이 아니라 서버가 반환한
HTML/JSON 원문 캡처이며, 매니페스트에도 그렇게 표기한다.

실행: 프로젝트 루트에서 `python3 -m demo.capture`
(기본 출력 demo/assets/captures/)
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import json
import threading
import urllib.request
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path

from console.server import create_handler


@dataclass(frozen=True)
class CaptureSpec:
    name: str
    path: str
    filename: str
    kind: str
    markers: tuple[str, ...]
    cut_ref: str
    purpose: str


CAPTURE_SPECS: tuple[CaptureSpec, ...] = (
    CaptureSpec(
        name="console-home",
        path="/",
        filename="console-home.html",
        kind="html",
        markers=("조치 우선순위", "모의 데이터", "66.7%"),
        cut_ref="컷 5~7 (대조·차이·조치)",
        purpose="최신 세션 상세 — 요약 지표·차이 목록·조치 우선순위 화면",
    ),
    CaptureSpec(
        name="console-sessions",
        path="/sessions",
        filename="console-sessions.html",
        kind="html",
        markers=("DEMO-20261027-A", "DEMO-20261026-A", "모의 데이터"),
        cut_ref="컷 2 (문제·세션 목록)",
        purpose="데모 세션 3개 목록 화면",
    ),
    CaptureSpec(
        name="console-session-detail",
        path="/sessions/DEMO-20261027-B",
        filename="console-session-detail.html",
        kind="html",
        markers=("DEMO-20261027-B", "100.0%"),
        cut_ref="컷 5 (대조 — 전부 일치 세션)",
        purpose="전부 일치 세션 상세 화면",
    ),
    CaptureSpec(
        name="api-report",
        path="/api/report",
        filename="api-report.json",
        kind="json",
        markers=('"source": "mock"',),
        cut_ref="컷 4·8 (SAM 계수·리포트)",
        purpose="시뮬레이션 리포트 JSON 원문 (source=mock 표기 확인용)",
    ),
)

HONESTY = [
    "서버 응답 원문 캡처 (PNG 스크린샷 아님)",
    "모의 어댑터 동작 중",
    "수치는 데모 기준",
]


def fetch_captures(
    specs: tuple[CaptureSpec, ...] = CAPTURE_SPECS,
) -> list[tuple[CaptureSpec, int, str]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    # 로컬 서버 전용 오프너: 전역 urlopen의 프록시 캐시 상태를 건드리지 않고,
    # 환경 프록시를 거치지 않게 명시적으로 비운다.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    results: list[tuple[CaptureSpec, int, str]] = []
    try:
        for spec in specs:
            url = f"http://127.0.0.1:{port}{spec.path}"
            with opener.open(url, timeout=10) as resp:
                text = resp.read().decode("utf-8")
                results.append((spec, resp.status, text))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return results


def build_manifest(
    results: list[tuple[CaptureSpec, int, str]],
) -> dict:
    captures = []
    for spec, status, text in results:
        markers_found = {m: (m in text) for m in spec.markers}
        captures.append(
            {
                "name": spec.name,
                "path": spec.path,
                "file": spec.filename,
                "kind": spec.kind,
                "status": status,
                "bytes": len(text.encode("utf-8")),
                "markers_found": markers_found,
                "all_markers_found": all(markers_found.values()),
                "cut_ref": spec.cut_ref,
                "purpose": spec.purpose,
            }
        )
    return {
        "title": "Argus 콘솔 캡처 매니페스트",
        "capture_count": len(captures),
        "all_ok": all(
            c["status"] == 200 and c["all_markers_found"] for c in captures
        ),
        "honesty": list(HONESTY),
        "captures": captures,
    }


def capture_assets(out_dir) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = fetch_captures()
    files: list[str] = []
    for spec, _status, text in results:
        path = out / spec.filename
        path.write_text(text, encoding="utf-8")
        files.append(str(path))
    manifest = build_manifest(results)
    manifest["files"] = files
    manifest_path = out / "capture-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest["files"] = files + [str(manifest_path)]
    return manifest


def validate_manifest(manifest: dict) -> list[str]:
    problems: list[str] = []
    if manifest.get("capture_count") != len(CAPTURE_SPECS):
        problems.append(
            f"캡처 수 불일치: {manifest.get('capture_count')} != {len(CAPTURE_SPECS)}"
        )
    for capture in manifest.get("captures", []):
        if capture.get("status") != 200:
            problems.append(
                f"{capture.get('name')}: HTTP 상태 {capture.get('status')}"
            )
        if not capture.get("all_markers_found"):
            missing = [
                m for m, ok in capture.get("markers_found", {}).items() if not ok
            ]
            problems.append(
                f"{capture.get('name')}: 마커 누락 {missing}"
            )
    if not manifest.get("all_ok") and not problems:
        problems.append("매니페스트 all_ok가 거짓이다")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus 콘솔 캡처 자산 생성")
    parser.add_argument(
        "--out", default="demo/assets/captures", help="출력 디렉터리"
    )
    args = parser.parse_args(argv)
    manifest = capture_assets(args.out)
    for capture in manifest["captures"]:
        print(f"{capture['name']}: {capture['status']} {capture['file']}")
    problems = validate_manifest(manifest)
    for problem in problems:
        print(f"문제: {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
