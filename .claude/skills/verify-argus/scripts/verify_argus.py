#!/usr/bin/env python3
"""Argus 검증 헬퍼.

실제 콘솔 서버를 임시 포트(포트 0, OS 배정)에 띄우고, 사용자가 보는
경로(GET / 와 GET /api/report)를 프록시를 우회한 HTTP로 직접 읽어
마커와 JSON 요약 수치를 확인한다. 서버는 이 스크립트가 띄운 것만
종료하고, 증거 파일은 증거 디렉터리에 그대로 남긴다.

사용:
  python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor
  python3 .claude/skills/verify-argus/scripts/verify_argus.py \
      --evidence-dir /tmp/argus-verify-evidence/<run-id>

SAM 실호출은 하지 않는다. 환경에 SAM_API_KEY가 있으면 경고를 남기고,
응답의 source가 mock이 아니면 실패로 처리한다.
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from console.server import create_handler  # noqa: E402

HOME_MARKERS = ("조치 우선순위", "모의 데이터", "66.7%")


def fetch(port: int, path: str) -> tuple[int, str]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}{path}", timeout=10) as resp:
        return resp.status, resp.read().decode("utf-8")


def serve() -> tuple[ThreadingHTTPServer, threading.Thread, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, server.server_address[1]


def check_report(report: dict) -> list[str]:
    problems: list[str] = []
    if report.get("source") != "mock":
        problems.append(f"source가 mock이 아니다: {report.get('source')}")
    summary = report.get("summary", {})
    if summary.get("matched") != 4:
        problems.append(f"matched 기대 4, 실제 {summary.get('matched')}")
    if summary.get("mismatched") != 2:
        problems.append(f"mismatched 기대 2, 실제 {summary.get('mismatched')}")
    if summary.get("counted_bins") != 6:
        problems.append(f"counted_bins 기대 6, 실제 {summary.get('counted_bins')}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus verification helper")
    parser.add_argument("--doctor", action="store_true",
                        help="구동 가능 여부만 빠르게 확인한다")
    parser.add_argument("--feature", default="console-home",
                        help="검증할 기능 이름 (기본 console-home)")
    parser.add_argument("--evidence-dir", default="/tmp/argus-verify-evidence/manual-run",
                        help="증거를 남길 디렉터리")
    args = parser.parse_args(argv)

    lines: list[str] = []
    def note(text: str) -> None:
        lines.append(text)
        print(text)

    env_name = "SAM_API" + "_KEY"
    if os.environ.get(env_name):
        note(f"경고: {env_name}가 설정돼 있다. 검증은 source=mock일 때만 통과한다.")

    server, thread, port = serve()
    note(f"서버 기동: http://127.0.0.1:{port} (임시 포트, 이 실행이 띄운 서버)")
    try:
        status, report_text = fetch(port, "/api/report")
        report = json.loads(report_text)
        note(f"GET /api/report -> {status}, source={report.get('source')}")
        problems = check_report(report)
        if status != 200:
            problems.append(f"/api/report 상태 {status}")

        if args.doctor:
            if problems:
                for problem in problems:
                    note(f"FAIL: {problem}")
                note("DOCTOR: FAIL")
                return 1
            note("DOCTOR: PASS (python·import·임시 서버·source=mock 확인)")
            return 0

        status_home, home_text = fetch(port, "/")
        note(f"GET / -> {status_home}")
        markers_found = {m: (m in home_text) for m in HOME_MARKERS}
        for marker, found in markers_found.items():
            note(f"마커 {marker!r}: {'발견' if found else '없음'}")
        if status_home != 200:
            problems.append(f"/ 상태 {status_home}")
        missing = [m for m, ok in markers_found.items() if not ok]
        if missing:
            problems.append(f"홈 마커 누락 {missing}")

        evidence = Path(args.evidence_dir)
        evidence.mkdir(parents=True, exist_ok=True)
        summary = {
            "feature": args.feature,
            "home_status": status_home,
            "report_status": status,
            "markers_found": markers_found,
            "source": report.get("source"),
            "all_ok": not problems,
            "problems": problems,
        }
        (evidence / "home.html").write_text(home_text, encoding="utf-8")
        (evidence / "api-report.json").write_text(report_text, encoding="utf-8")
        (evidence / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lines.append(f"증거 저장: {evidence}")
        (evidence / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

        if problems:
            for problem in problems:
                print(f"FAIL: {problem}")
            print("VERIFY: FAIL")
            return 1
        print("VERIFY: PASS")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
