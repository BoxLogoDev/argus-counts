#!/usr/bin/env python3
"""Argus 검증 헬퍼.

사용자가 닿는 표면을 직접 구동해 검증한다: 웹 콘솔은 임시 포트 서버를
띄워 HTTP로, 단말 흐름은 CLI 서브프로세스로, 데모 영상 초안은 ffprobe
탐침으로 확인하고, 제출 전 전수 점검은 CLI 서브프로세스로 구동하며,
Pi 캡처 경계는 탐지·기대 실패·가짜 runner 성공으로 구동하고(Pi 실촬영
검증 전), Pi 촬영 세션은 CLI 기대 실패(카메라 부재)와 가짜 which/runner
주입 성공으로 구동하며(Pi 실촬영 검증 전), SAM 실호출 준비 경계는
가짜 transport 주입으로만 구동하며 실제 API 호출은 하지 않는다
(SAM 실호출 검증 전). SAM 실호출 전환 준비 점검(sam-readiness)은
실제 API 호출 없이 CLI 서브프로세스와 프로세스 내 check_readiness로만
구동한다(준비 완료는 실호출 성공이 아님). 제출 런북(submission-runbook)은
파일 원문을 읽어 절 순서·블로커·최종 점검 명령을 대조하고 변조 탐지를
확인한다(제출 준비 완료가 아니다). Pi 실촬영 준비 점검(pi-readiness)은
실제 촬영 없이 CLI 서브프로세스와 프로세스 내 check_readiness로만
구동한다(준비 완료는 실촬영 성공이 아님). 콘솔 준비 상태(console-readiness)는
임시 포트 HTTP GET /api/readiness와 GET / 홈 패널, 프로세스 내
build_readiness 가짜 준비 완료로 구동한다(실제 API 호출·실제 촬영 없음,
준비 완료는 실호출·실촬영 성공이 아님). 응답 원문과 종료 판정을
증거 디렉터리에 남긴다.
서버는 이 스크립트가 띄운 것만 종료한다.

사용:
  python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor
  python3 .claude/skills/verify-argus/scripts/verify_argus.py \
      --feature <기능> --evidence-dir /tmp/argus-verify-evidence/<run-id>

기능: console-home(기본), terminal-simulator, session-list,
difference-report, demo-video-draft, photo-intake, pre-submission,
pi-capture, pi-session, sam-live, sam-readiness, submission-runbook,
pi-readiness, console-readiness, all(전부, 기능별 하위 디렉터리).

SAM 실호출은 하지 않는다. 자식 프로세스 환경에서도 SAM_API_BASE_URL과
SAM_API_KEY를 제거하고, 응답의 source가 mock이 아니면 실패로 처리한다.
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from console.server import create_handler  # noqa: E402

HOME_MARKERS = ("조치 우선순위", "모의 데이터", "66.7%")
SESSION_IDS = ("DEMO-20261027-A", "DEMO-20261027-B", "DEMO-20261026-A")
FEATURES = ("console-home", "terminal-simulator", "session-list",
            "difference-report", "demo-video-draft", "photo-intake",
            "pre-submission", "pi-capture", "pi-session", "sam-live",
            "sam-readiness", "submission-runbook", "pi-readiness",
            "console-readiness")
EXPECTED_BLOCKER_IDS = ("pi_real_capture_pending", "sam_real_call_pending")
PHOTO_BIN_IDS = ("A-01-01", "A-01-02", "A-02-02",
                 "A-03-01", "B-01-02", "B-02-02")
EXPECTED_SIM_SUMMARY = {"counted_bins": 6, "matched": 4, "mismatched": 2,
                        "abs_diff_total": 6, "net_diff": 0}
PI_FAKE_CONTENT = b"fake-pi-jpeg"
PI_BIN_ID = "A-01-02"
PI_SESSION_FAKE_CONTENT = b"fake-pi-session-jpeg"
PI_SESSION_ID = "VERIFY-PI-SESSION-1"
SAM_FAKE_URL = "https://example.invalid/sam"
SAM_FAKE_KEY = "test-key-not-real"
SAM_BIN_ID = "A-01-02"
SAM_FAKE_COUNT = 5
EXPECTED_READINESS_BLOCKER_IDS = ("sam_credit_not_confirmed",
                                  "sam_base_url_missing",
                                  "sam_api_key_missing")
SAM_READINESS_FAKE_URL = "https://sentinel-readiness.example.invalid/sam"
SAM_READINESS_FAKE_KEY_VALUE = "sentinel-readiness-key-not-real"
EXPECTED_PI_READINESS_BLOCKER_IDS = ("pi_device_arrival_not_confirmed",
                                     "pi_camera_command_missing")
PI_READINESS_READY_PROBE = {"available": True,
                            "command": "libcamera-still",
                            "command_path": "/usr/bin/libcamera-still",
                            "candidates_checked": ["libcamera-still",
                                                   "raspistill"],
                            "honesty": ["Pi 실촬영 검증 전입니다"]}
PI_READINESS_MISSING_PROBE = {"available": False, "command": None,
                              "command_path": None,
                              "candidates_checked": ["libcamera-still",
                                                     "raspistill"],
                              "honesty": ["Pi 실촬영 검증 전입니다"]}
EXPECTED_CONSOLE_SAM_BLOCKERS = ("sam_credit_not_confirmed",
                                 "sam_base_url_missing",
                                 "sam_api_key_missing")
EXPECTED_CONSOLE_PI_BLOCKERS = ("pi_device_arrival_not_confirmed",
                                "pi_camera_command_missing")
CONSOLE_READINESS_HOME_MARKERS = ("준비 상태", "SAM 실호출 준비: 준비 안 됨",
                                  "Pi 실촬영 준비: 준비 안 됨",
                                  "sam_credit_not_confirmed",
                                  "pi_camera_command_missing",
                                  "준비 완료는 실호출·실촬영 성공을 뜻하지 않는다")
CONSOLE_READINESS_FAKE_URL = "https://console-readiness.example.invalid/sam"
CONSOLE_READINESS_FAKE_KEY_VALUE = "sentinel-console-readiness-key-not-real"
CONSOLE_READINESS_FAKE_PROBE = {"available": True,
                                "command": "libcamera-still",
                                "candidates_checked": ["libcamera-still",
                                                       "raspistill"],
                                "honesty": ["Pi 실촬영 검증 전"]}
RUNBOOK_REL = "docs/submission-runbook.md"
RUNBOOK_SECTIONS = ("## 0. 현재 상태", "## 1. 크레딧 확인", "## 2. API 키",
                    "## 3. SAM 전환", "## 4. Pi 촬영", "## 5. 최종 점검",
                    "## 6. 제출")
RUNBOOK_FINAL_COMMANDS = ("python3 -m unittest discover -s tests",
                          "python3 -m qa", "python3 -m qa.standalone",
                          "python3 -m qa.claims_audit",
                          "python3 -m qa.pre_submission",
                          "verify_argus.py --doctor",
                          "verify_argus.py --feature all",
                          "python3 -m demo.render_video")
RUNBOOK_CREDIT_AT = "2026-10-29 09:30"
RUNBOOK_DEADLINE_KST = "2026-11-05 11:00"


def clean_env() -> dict:
    env = dict(os.environ)
    env.pop("SAM_API_BASE_URL", None)
    env.pop("SAM_API_KEY", None)
    return env


def fetch(port: int, path: str) -> tuple[int, str]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(f"http://127.0.0.1:{port}{path}", timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


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


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], cwd=ROOT, env=clean_env(),
                          capture_output=True, text=True, timeout=120)


def write_evidence(evidence: Path, lines: list[str], summary: dict,
                   files: dict[str, str]) -> None:
    evidence.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (evidence / name).write_text(text, encoding="utf-8")
    (evidence / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines.append(f"증거 저장: {evidence}")
    (evidence / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


class Ctx:
    """기능 구동 공용 맥락: 노트 누적과 임시 포트 서버 지연 기동."""

    def __init__(self) -> None:
        self.lines: list[str] = []
        self._server = None
        self.port: int | None = None

    def note(self, text: str) -> None:
        self.lines.append(text)
        print(text)

    def ensure_server(self) -> int:
        if self.port is None:
            server, thread, port = serve()
            self._server = (server, thread)
            self.port = port
            self.note(f"서버 기동: http://127.0.0.1:{port} (임시 포트, 이 실행이 띄운 서버)")
        return self.port

    def close(self) -> None:
        if self._server is not None:
            server, thread = self._server
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            self._server = None


def drive_console_home(ctx: Ctx, evidence: Path) -> dict:
    port = ctx.ensure_server()
    status, report_text = fetch(port, "/api/report")
    report = json.loads(report_text)
    ctx.note(f"GET /api/report -> {status}, source={report.get('source')}")
    problems = check_report(report)
    if status != 200:
        problems.append(f"/api/report 상태 {status}")
    status_home, home_text = fetch(port, "/")
    ctx.note(f"GET / -> {status_home}")
    markers_found = {m: (m in home_text) for m in HOME_MARKERS}
    for marker, found in markers_found.items():
        ctx.note(f"마커 {marker!r}: {'발견' if found else '없음'}")
    if status_home != 200:
        problems.append(f"/ 상태 {status_home}")
    missing = [m for m, ok in markers_found.items() if not ok]
    if missing:
        problems.append(f"홈 마커 누락 {missing}")
    summary = {"feature": "console-home", "home_status": status_home,
               "report_status": status, "markers_found": markers_found,
               "source": report.get("source"), "all_ok": not problems,
               "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"home.html": home_text, "api-report.json": report_text})
    return summary


def drive_terminal_simulator(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    result = run_cli(["-m", "terminal.simulator"])
    ctx.note(f"python3 -m terminal.simulator -> 종료코드 {result.returncode}")
    data: dict = {}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"stdout JSON 파싱 실패: {e}")
    if result.returncode != 0:
        problems.append(f"시뮬레이터 종료코드 {result.returncode}: {result.stderr[:200]}")
    if data:
        if data.get("source") != "mock":
            problems.append(f"source가 mock이 아니다: {data.get('source')}")
        summary = data.get("summary", {})
        for key, expected in EXPECTED_SIM_SUMMARY.items():
            if summary.get(key) != expected:
                problems.append(f"summary.{key} 기대 {expected}, 실제 {summary.get(key)}")
        if len(data.get("bins", [])) != 6:
            problems.append(f"bins 기대 6, 실제 {len(data.get('bins', []))}")
    out_path = evidence / "simulator.json"
    evidence.mkdir(parents=True, exist_ok=True)
    result2 = run_cli(["-m", "terminal.simulator", "--out", str(out_path)])
    ctx.note(f"python3 -m terminal.simulator --out -> 종료코드 {result2.returncode}")
    if result2.returncode != 0:
        problems.append(f"--out 종료코드 {result2.returncode}")
    elif out_path.is_file():
        saved = json.loads(out_path.read_text(encoding="utf-8"))
        if saved.get("summary") != data.get("summary"):
            problems.append("--out 파일의 summary가 stdout과 다르다")
    else:
        problems.append("--out 파일이 생성되지 않았다")
    summary = {"feature": "terminal-simulator", "source": data.get("source"),
               "sim_summary": data.get("summary"), "all_ok": not problems,
               "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"simulator-stdout.json": result.stdout})
    return summary


def drive_session_list(ctx: Ctx, evidence: Path) -> dict:
    port = ctx.ensure_server()
    problems: list[str] = []
    status, sessions_text = fetch(port, "/sessions")
    ctx.note(f"GET /sessions -> {status}")
    if status != 200:
        problems.append(f"/sessions 상태 {status}")
    for sid in SESSION_IDS:
        if sid not in sessions_text:
            problems.append(f"세션 목록에 {sid} 없음")
    if "모의 데이터" not in sessions_text:
        problems.append("세션 목록에 '모의 데이터' 표기 없음")
    status_j, sessions_json_text = fetch(port, "/api/sessions")
    ctx.note(f"GET /api/sessions -> {status_j}")
    data = json.loads(sessions_json_text) if status_j == 200 else {}
    if data.get("total_sessions") != 3:
        problems.append(f"total_sessions 기대 3, 실제 {data.get('total_sessions')}")
    if data.get("total_mismatched") != 5:
        problems.append(f"total_mismatched 기대 5, 실제 {data.get('total_mismatched')}")
    status_d, detail_text = fetch(port, "/sessions/DEMO-20261027-B")
    ctx.note(f"GET /sessions/DEMO-20261027-B -> {status_d}")
    if status_d != 200 or "100.0%" not in detail_text:
        problems.append(f"전부 일치 세션 상세 이상: 상태 {status_d}, 100.0% 포함 여부 {'100.0%' in detail_text}")
    status_dj, _ = fetch(port, "/api/sessions/DEMO-20261027-B")
    ctx.note(f"GET /api/sessions/DEMO-20261027-B -> {status_dj}")
    if status_dj != 200:
        problems.append(f"세션 상세 JSON 상태 {status_dj}")
    not_found: dict[str, int] = {}
    for path in ("/sessions/NOPE", "/api/sessions/NOPE"):
        code, _ = fetch(port, path)
        not_found[path] = code
        ctx.note(f"GET {path} -> {code} (404가 기대 동작)")
        if code != 404:
            problems.append(f"{path} 기대 404, 실제 {code}")
    summary = {"feature": "session-list", "sessions_status": status,
               "total_sessions": data.get("total_sessions"),
               "total_mismatched": data.get("total_mismatched"),
               "detail_status": status_d, "not_found": not_found,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"sessions.html": sessions_text,
                    "sessions.json": sessions_json_text,
                    "session-detail.html": detail_text})
    return summary


def drive_difference_report(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    result = run_cli(["-m", "terminal.report"])
    text = result.stdout
    ctx.note(f"python3 -m terminal.report -> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(f"리포트 종료코드 {result.returncode}")
    idx_a, idx_b = text.find("A-01-02"), text.find("B-01-02")
    if not (0 <= idx_a < idx_b):
        problems.append(f"조치 순서 이상: A-01-02 위치 {idx_a}, B-01-02 위치 {idx_b}")
    if "데모 기준" not in text:
        problems.append("텍스트 리포트에 '데모 기준' 영향 줄 없음")
    result_j = run_cli(["-m", "terminal.report", "--json"])
    payload: dict = {}
    try:
        payload = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    if len(payload.get("actions", [])) != 2:
        problems.append(f"actions 기대 2, 실제 {len(payload.get('actions', []))}")
    if "데모 기준" not in str(payload.get("impact_line", "")):
        problems.append("JSON impact_line에 '데모 기준' 없음")
    evidence.mkdir(parents=True, exist_ok=True)
    out_path = evidence / "report.txt"
    result_o = run_cli(["-m", "terminal.report", "--out", str(out_path)])
    ctx.note(f"python3 -m terminal.report --out -> 종료코드 {result_o.returncode}")
    if result_o.returncode != 0 or not out_path.is_file():
        problems.append("--out 파일이 생성되지 않았다")
    else:
        saved = out_path.read_text(encoding="utf-8")
        if not (0 <= saved.find("A-01-02") < saved.find("B-01-02")) or "데모 기준" not in saved:
            problems.append("--out 파일 내용이 stdout과 다르다")
    summary = {"feature": "difference-report",
               "actions": len(payload.get("actions", [])),
               "impact_line": payload.get("impact_line"),
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"report-stdout.txt": text, "report.json": result_j.stdout})
    return summary


def drive_demo_video(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    ctx.note("데모 영상 초안 탐침: 기존 MP4를 ffprobe로 확인한다(렌더 아님).")
    mp4 = ROOT / "demo" / "assets" / "argus-demo-draft.mp4"
    probe: dict = {"path": "demo/assets/argus-demo-draft.mp4",
                   "exists": mp4.is_file(),
                   "size": mp4.stat().st_size if mp4.is_file() else 0}
    if not mp4.is_file() or probe["size"] <= 0:
        problems.append("MP4 초안이 없거나 비어 있다")
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        problems.append("ffprobe가 없어 영상 길이를 구동 확인할 수 없다")
        probe["duration"] = None
    else:
        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(mp4)], capture_output=True, text=True, timeout=60)
        try:
            duration = float(result.stdout.strip())
        except ValueError:
            duration = -1.0
            problems.append(f"ffprobe duration 파싱 실패: {result.stdout[:100]}")
        probe["duration"] = duration
        ctx.note(f"ffprobe duration -> {duration}")
        if not (179.0 <= duration <= 181.0):
            problems.append(f"duration 기대 179~181초, 실제 {duration}")
    narration = json.loads((ROOT / "demo" / "assets" / "narration.json").read_text(encoding="utf-8"))
    if narration.get("pace_warnings") != []:
        problems.append(f"pace_warnings 기대 [], 실제 {narration.get('pace_warnings')}")
    assembly = json.loads((ROOT / "demo" / "assets" / "assembly.json").read_text(encoding="utf-8"))
    if assembly.get("total_seconds") != 180:
        problems.append(f"assembly total_seconds 기대 180, 실제 {assembly.get('total_seconds')}")
    probe["pace_warnings"] = narration.get("pace_warnings")
    probe["assembly_total_seconds"] = assembly.get("total_seconds")
    from demo.render_video import build_data_panel_lines
    from terminal.simulator import run_simulation

    report = run_simulation()
    panel: dict[str, list[str]] = {}
    for cut in range(1, 10):
        panel[str(cut)] = build_data_panel_lines(cut, report=report)
    all_bin_ids = ("A-01-01", "A-01-02", "A-02-02", "A-03-01", "B-01-02", "B-02-02")
    cut5 = panel["5"]
    if len(cut5) != 6:
        problems.append(f"컷 5 데이터 패널 기대 6줄, 실제 {len(cut5)}줄")
    missing5 = [bid for bid in all_bin_ids if bid not in "\n".join(cut5)]
    if missing5:
        problems.append(f"컷 5 데이터 패널에 빈 ID 누락 {missing5}")
    if any("장부" not in line or "→ 실측" not in line for line in cut5):
        problems.append("컷 5 데이터 패널 줄마다 '장부'와 '→ 실측'이 있어야 한다")
    cut6 = panel["6"]
    if len(cut6) != 2:
        problems.append(f"컷 6 데이터 패널 기대 2줄, 실제 {len(cut6)}줄")
    present6 = [bid for bid in all_bin_ids if bid in "\n".join(cut6)]
    if present6 != ["A-01-02", "B-01-02"]:
        problems.append(f"컷 6 데이터 패널 빈 ID 기대 ['A-01-02', 'B-01-02'], 실제 {present6}")
    cut7 = panel["7"]
    if len(cut7) != 2:
        problems.append(f"컷 7 데이터 패널 기대 2줄, 실제 {len(cut7)}줄")
    if not cut7 or "A-01-02" not in cut7[0]:
        problems.append("컷 7 데이터 패널 첫 줄에 A-01-02가 있어야 한다")
    cut8 = panel["8"]
    if len(cut8) != 3:
        problems.append(f"컷 8 데이터 패널 기대 3줄, 실제 {len(cut8)}줄")
    if "66.7%" not in "\n".join(cut8):
        problems.append("컷 8 데이터 패널에 '66.7%'가 있어야 한다")
    cut9 = panel["9"]
    if len(cut9) != 1:
        problems.append(f"컷 9 데이터 패널 기대 1줄, 실제 {len(cut9)}줄")
    if not any("데모 기준" in line for line in cut9):
        problems.append("컷 9 데이터 패널에 '데모 기준'이 있어야 한다")
    if panel["3"] != ["실촬영 데이터 없음 — Pi 도착 후 교체"]:
        problems.append(f"컷 3 데이터 패널 기대 ['실촬영 데이터 없음 — Pi 도착 후 교체'], 실제 {panel['3']}")
    cut1 = panel["1"]
    if len(cut1) != 1:
        problems.append(f"컷 1 데이터 패널 기대 1줄, 실제 {len(cut1)}줄")
    if not any("일치율 66.7%" in line for line in cut1):
        problems.append("컷 1 데이터 패널에 '일치율 66.7%'가 있어야 한다")
    custom_report = copy.deepcopy(report)
    custom_report["bins"][0]["counted_qty"] = 999
    custom_cut5 = build_data_panel_lines(5, report=custom_report)
    custom_counted_qty_reflected = bool(custom_cut5 and "실측 999" in custom_cut5[0])
    if not custom_counted_qty_reflected:
        problems.append("변조 리포트의 counted_qty 999가 컷 5 첫 줄 '실측 999'에 반영되지 않았다")
    data_panel_cuts = sorted(int(cut) for cut, lines in panel.items() if lines)
    ctx.note(f"데이터 패널 컷 -> {data_panel_cuts}, 변조 반영 {custom_counted_qty_reflected}")
    probe["data_panel_cuts"] = data_panel_cuts
    probe["data_panel"] = panel
    data_panel_payload = {"data_panel": panel, "panel": panel,
                          "data_panel_cuts": data_panel_cuts,
                          "custom_counted_qty_reflected": custom_counted_qty_reflected,
                          **panel}
    summary = {"feature": "demo-video-draft", "probe": probe,
               "data_panel_cuts": data_panel_cuts,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"video-probe.json": json.dumps(probe, ensure_ascii=False, indent=2) + "\n",
                    "data-panel.json": json.dumps(data_panel_payload, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_photo_intake(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    evidence.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        captures: dict[str, Path] = {}
        for bin_id in PHOTO_BIN_IDS:
            path = root / f"{bin_id}.jpg"
            path.write_bytes(f"fake-photo-{bin_id}".encode())
            captures[bin_id] = path
        args: list[str] = ["-m", "terminal.photo_intake"]
        for bin_id in PHOTO_BIN_IDS:
            args += ["--capture", f"{bin_id}={captures[bin_id]}"]
        result = run_cli([*args, "--session-id", "VERIFY-PHOTO-1"])
        ctx.note(f"python3 -m terminal.photo_intake (가짜 사진 6장) -> 종료코드 {result.returncode}")
        data: dict = {}
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            problems.append(f"stdout JSON 파싱 실패: {e}")
        if result.returncode != 0:
            problems.append(f"사진 입력 종료코드 {result.returncode}: {result.stderr[:200]}")
        if data:
            if data.get("source") != "mock":
                problems.append(f"source가 mock이 아니다: {data.get('source')}")
            if data.get("capture_source") != "file":
                problems.append(f"capture_source가 file이 아니다: {data.get('capture_source')}")
            if data.get("session_id") != "VERIFY-PHOTO-1":
                problems.append(f"session_id 기대 VERIFY-PHOTO-1, 실제 {data.get('session_id')}")
            if not any("Pi 실촬영이 아닙니다" in line
                       for line in data.get("honesty", [])):
                problems.append("honesty에 'Pi 실촬영이 아닙니다' 표기 없음")
            summary_data = data.get("summary", {})
            for key, expected in EXPECTED_SIM_SUMMARY.items():
                if summary_data.get(key) != expected:
                    problems.append(
                        f"summary.{key} 기대 {expected}, 실제 {summary_data.get(key)}")
            bins = data.get("bins", [])
            if len(bins) != 6:
                problems.append(f"bins 기대 6, 실제 {len(bins)}")
            by_bin = {b.get("bin_id"): b for b in bins}
            target = by_bin.get("A-01-02", {})
            if target.get("verdict") != "short":
                problems.append(f"A-01-02 verdict 기대 short, 실제 {target.get('verdict')}")
            if target.get("diff") != -3:
                problems.append(f"A-01-02 diff 기대 -3, 실제 {target.get('diff')}")
            photo = target.get("photo", {})
            expected_sha = hashlib.sha256(b"fake-photo-A-01-02").hexdigest()
            if photo.get("sha256") != expected_sha:
                problems.append("A-01-02 photo.sha256이 가짜 사진 바이트 해시와 다르다")
            if photo.get("image_ref") != "A-01-02.jpg":
                problems.append(f"A-01-02 photo.image_ref 기대 A-01-02.jpg, 실제 {photo.get('image_ref')}")
            over = by_bin.get("B-01-02", {})
            if over.get("verdict") != "over" or over.get("diff") != 3:
                problems.append(f"B-01-02 기대 over/+3, 실제 {over.get('verdict')}/{over.get('diff')}")
        out_path = evidence / "photo-intake.json"
        result2 = run_cli([*args, "--session-id", "VERIFY-PHOTO-1",
                           "--out", str(out_path)])
        ctx.note(f"python3 -m terminal.photo_intake --out -> 종료코드 {result2.returncode}")
        if result2.returncode != 0:
            problems.append(f"--out 종료코드 {result2.returncode}")
        elif out_path.is_file():
            saved = json.loads(out_path.read_text(encoding="utf-8"))
            if saved.get("summary") != data.get("summary"):
                problems.append("--out 파일의 summary가 stdout과 다르다")
            if saved.get("capture_source") != "file":
                problems.append("--out 파일의 capture_source가 file이 아니다")
        else:
            problems.append("--out 파일이 생성되지 않았다")
    summary = {"feature": "photo-intake", "source": data.get("source"),
               "capture_source": data.get("capture_source"),
               "intake_summary": data.get("summary"), "all_ok": not problems,
               "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"photo-intake-stdout.json": result.stdout})
    return summary


def drive_pre_submission(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    result = run_cli(["-m", "qa.pre_submission"])
    text = result.stdout
    ctx.note(f"python3 -m qa.pre_submission -> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(f"전수 점검 종료코드 {result.returncode}: {result.stderr[:200]}")
    for needle in ("PRE_SUBMISSION: 9/9 mechanical passed", "BLOCKERS: 2",
                   "SUBMISSION_READY: false", *EXPECTED_BLOCKER_IDS):
        if needle not in text:
            problems.append(f"전수 점검 텍스트에 {needle!r} 없음")
    result_j = run_cli(["-m", "qa.pre_submission", "--json"])
    ctx.note(f"python3 -m qa.pre_submission --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 0:
        problems.append(f"전수 점검 --json 종료코드 {result_j.returncode}: {result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocker_ids: list = []
    if report:
        if report.get("passed") != 9:
            problems.append(f"passed 기대 9, 실제 {report.get('passed')}")
        if report.get("total") != 9:
            problems.append(f"total 기대 9, 실제 {report.get('total')}")
        if report.get("mechanical_pass") is not True:
            problems.append(f"mechanical_pass 기대 True, 실제 {report.get('mechanical_pass')}")
        if report.get("submission_ready") is not False:
            problems.append(
                "심각한 문제: submission_ready가 false가 아니다"
                f" (실제 {report.get('submission_ready')})"
                " — 기계적 통과를 제출 가능으로 오인하면 안 된다")
        blocker_ids = [b["id"] for b in report.get("blockers", [])]
        if blocker_ids != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {blocker_ids}")
        checks = report.get("checks", [])
        if len(checks) != 9:
            problems.append(f"checks 기대 9, 실제 {len(checks)}")
        check_names = [c.get("name") for c in checks]
        if "console_readiness_consistent" not in check_names:
            problems.append("checks에 console_readiness_consistent 없음")
        if not all(c.get("passed") is True for c in checks):
            problems.append("checks 중 passed가 True가 아닌 항목이 있다")
        honesty = report.get("honesty", [])
        if not any("모의" in line for line in honesty):
            problems.append("honesty에 '모의'를 포함한 줄 없음")
        if not any("데모 기준" in line for line in honesty):
            problems.append("honesty에 '데모 기준'을 포함한 줄 없음")
        readiness = report.get("readiness", {}) or {}
        sam_r = readiness.get("sam") or {}
        pi_r = readiness.get("pi") or {}
        sam_rb = [b["id"] for b in sam_r.get("blockers", [])]
        pi_rb = [b["id"] for b in pi_r.get("blockers", [])]
        if sam_rb != ["sam_credit_not_confirmed", "sam_base_url_missing",
                      "sam_api_key_missing"]:
            problems.append(f"readiness sam blockers 기대 3종, 실제 {sam_rb}")
        if pi_rb != ["pi_device_arrival_not_confirmed",
                     "pi_camera_command_missing"]:
            problems.append(f"readiness pi blockers 기대 2종, 실제 {pi_rb}")
        if sam_r.get("ready_for_live_call") is not False:
            problems.append(
                f"readiness sam ready 기대 False, 실제 {sam_r.get('ready_for_live_call')}")
        if pi_r.get("ready_for_real_capture") is not False:
            problems.append(
                f"readiness pi ready 기대 False, 실제 {pi_r.get('ready_for_real_capture')}")
        console_r = readiness.get("console") or {}
        console_bc = console_r.get("blocker_count")
        console_overall = console_r.get("overall_ready")
        if console_bc != 5:
            problems.append(f"readiness console blocker_count 기대 5, 실제 {console_bc}")
        if console_r.get("sam_blockers") != sam_rb:
            problems.append(
                f"readiness console sam_blockers가 sam 블로커와 다르다: {console_r.get('sam_blockers')}")
        if console_r.get("pi_blockers") != pi_rb:
            problems.append(
                f"readiness console pi_blockers가 pi 블로커와 다르다: {console_r.get('pi_blockers')}")
        if console_overall is not False:
            problems.append(
                f"readiness console overall_ready 기대 False, 실제 {console_overall}")
    else:
        sam_rb, pi_rb = [], []
        console_bc, console_overall = None, None
    summary = {"feature": "pre-submission",
               "mechanical_pass": report.get("mechanical_pass"),
               "passed": report.get("passed"), "total": report.get("total"),
               "blockers": blocker_ids,
               "readiness_sam_blockers": sam_rb,
               "readiness_pi_blockers": pi_rb,
               "readiness_console_blocker_count": console_bc,
               "readiness_console_overall_ready": console_overall,
               "submission_ready": report.get("submission_ready"),
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"pre-submission-stdout.txt": text,
                    "pre-submission.json": result_j.stdout})
    return summary


def drive_pi_capture(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from terminal.pi_capture import (CAPTURE_COMMAND_CANDIDATES, PiCaptureError,
                                     build_capture_command, capture_photo,
                                     probe_pi_camera)

    result = run_cli(["-m", "terminal.pi_capture", "--probe"])
    ctx.note(f"python3 -m terminal.pi_capture --probe -> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(f"Pi probe 종료코드 {result.returncode}: {result.stderr[:200]}")
    probe_data: dict = {}
    try:
        probe_data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"probe stdout JSON 파싱 실패: {e}")
    available = probe_data.get("available")
    command = probe_data.get("command")
    if probe_data:
        if not isinstance(available, bool):
            problems.append(f"probe available이 bool이 아니다: {available!r}")
        if command is not None and command not in CAPTURE_COMMAND_CANDIDATES:
            problems.append(
                f"probe command 기대 None 또는 {list(CAPTURE_COMMAND_CANDIDATES)} 중 하나, 실제 {command!r}")
        if not any("Pi 실촬영 검증 전" in line
                   for line in probe_data.get("honesty", [])):
            problems.append("probe honesty에 'Pi 실촬영 검증 전' 표기 없음")
    ctx.note(f"Pi probe -> available={available}, command={command}")

    cli_capture_blocked: bool | None = None
    record = None
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if available is False:
            blocked_path = root / f"{PI_BIN_ID}.jpg"
            result_c = run_cli(["-m", "terminal.pi_capture", "--capture",
                                f"{PI_BIN_ID}={blocked_path}"])
            ctx.note(f"python3 -m terminal.pi_capture --capture (명령 부재) -> 종료코드 {result_c.returncode}")
            cli_capture_blocked = result_c.returncode != 0 and not blocked_path.exists()
            if result_c.returncode == 0:
                problems.append("카메라 명령 부재 환경에서 --capture 종료코드가 0이다")
            if blocked_path.exists():
                problems.append("카메라 명령 부재 환경에서 --capture 출력 파일이 생겼다")
        elif available is True:
            ctx.note("카메라 명령이 있는 환경이라 CLI --capture 기대 실패 검사는 건너뛴다.")

        fake_which = lambda name: f"/usr/bin/{name}" if name == "libcamera-still" else None  # noqa: E731

        def fake_runner(argv, **kwargs):
            Path(argv[argv.index("-o") + 1]).write_bytes(PI_FAKE_CONTENT)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        def failing_runner(argv, **kwargs):
            return SimpleNamespace(returncode=2, stdout="", stderr="sensitive-detail")

        fake_probe = probe_pi_camera(which=fake_which)
        if fake_probe.get("available") is not True or fake_probe.get("command") != "libcamera-still":
            problems.append(
                f"가짜 which probe 기대 available=True·command=libcamera-still, 실제 {fake_probe.get('available')}·{fake_probe.get('command')}")

        fake_path = root / "fake-pi.jpg"
        try:
            record = capture_photo(PI_BIN_ID, fake_path,
                                   runner=fake_runner, which=fake_which)
        except Exception as e:
            problems.append(f"가짜 runner capture_photo 실패: {type(e).__name__}: {e}")
        if record is not None:
            ctx.note(f"가짜 runner capture_photo -> sha256={record.sha256}, suffix={record.suffix}")
            expected_sha = hashlib.sha256(PI_FAKE_CONTENT).hexdigest()
            if record.sha256 != expected_sha:
                problems.append("가짜 캡처 sha256이 PI_FAKE_CONTENT 해시와 다르다")
            if record.suffix != ".jpg":
                problems.append(f"가짜 캡처 suffix 기대 .jpg, 실제 {record.suffix}")
            if record.bin_id != PI_BIN_ID:
                problems.append(f"가짜 캡처 bin_id 기대 {PI_BIN_ID}, 실제 {record.bin_id}")

        argv_shape = build_capture_command("libcamera-still", "/tmp/x.jpg")
        if not argv_shape or argv_shape[0] != "libcamera-still":
            problems.append(f"build_capture_command 첫 원소 기대 libcamera-still, 실제 {argv_shape[:1]}")
        elif "-o" not in argv_shape or argv_shape.index("-o") + 1 >= len(argv_shape) \
                or argv_shape[argv_shape.index("-o") + 1] != "/tmp/x.jpg":
            problems.append(f"build_capture_command -o 다음 기대 /tmp/x.jpg, 실제 {argv_shape}")

        try:
            capture_photo(PI_BIN_ID, root / "fake-pi-fail.jpg",
                          runner=failing_runner, which=fake_which)
            problems.append("returncode 2인 runner에서 PiCaptureError가 나지 않았다")
        except PiCaptureError as e:
            if "sensitive-detail" in str(e):
                problems.append("PiCaptureError 메시지에 runner stderr(sensitive-detail)가 포함됐다")

    fake_payload = {"bin_id": getattr(record, "bin_id", None),
                    "image_ref": getattr(record, "image_ref", None),
                    "size_bytes": getattr(record, "size_bytes", None),
                    "sha256": getattr(record, "sha256", None),
                    "suffix": getattr(record, "suffix", None)}
    summary = {"feature": "pi-capture", "probe_available": available,
               "probe_command": command,
               "cli_capture_blocked": cli_capture_blocked,
               "fake_capture_sha256": getattr(record, "sha256", None),
               "fake_capture_suffix": getattr(record, "suffix", None),
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"pi-capture-probe.json": result.stdout,
                    "pi-capture-fake.json": json.dumps(fake_payload, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_pi_session(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from terminal.pi_capture import PiCaptureError, probe_pi_camera
    from terminal.pi_session import run_pi_session

    probe = probe_pi_camera()
    available = probe.get("available")
    ctx.note(f"Pi probe -> available={available}, command={probe.get('command')}")
    if not isinstance(available, bool):
        problems.append(f"probe available이 bool이 아니다: {available!r}")

    cli_session_blocked: bool | None = None
    no_camera_blocked = False
    blocked_text = ""
    report: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fake_which = lambda name: f"/usr/bin/{name}" if name == "libcamera-still" else None  # noqa: E731

        def fake_runner(argv, **kwargs):
            Path(argv[argv.index("-o") + 1]).write_bytes(PI_SESSION_FAKE_CONTENT)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        if available is False:
            out_dir = root / "captures"
            result = run_cli(["-m", "terminal.pi_session", "--out-dir", str(out_dir)])
            ctx.note(
                f"python3 -m terminal.pi_session --out-dir (명령 부재) -> 종료코드 {result.returncode}")
            blocked_text = result.stderr
            cli_session_blocked = result.returncode != 0 and not out_dir.exists()
            if result.returncode != 1:
                problems.append(
                    f"카메라 명령 부재 환경에서 terminal.pi_session 종료코드 기대 1, 실제 {result.returncode}")
            if "Pi 카메라 명령을 찾을 수 없습니다" not in result.stderr:
                problems.append("terminal.pi_session stderr에 'Pi 카메라 명령을 찾을 수 없습니다' 없음")
            if out_dir.exists():
                problems.append("카메라 명령 부재 환경에서 terminal.pi_session 캡처 디렉터리가 생겼다")
        elif available is True:
            cli_session_blocked = None
            blocked_text = "카메라 명령이 있는 환경이라 CLI 기대 실패 검사는 건너뛰었습니다.\n"
            ctx.note("카메라 명령이 있는 환경이라 CLI --out-dir 기대 실패 검사는 건너뛴다.")
        else:
            blocked_text = "probe available이 bool이 아니라 CLI 기대 실패 검사는 건너뛰었습니다.\n"
            ctx.note("probe available이 bool이 아니라 CLI --out-dir 기대 실패 검사는 건너뛴다.")

        no_camera_dir = root / "no-camera"
        try:
            run_pi_session(no_camera_dir, which=lambda name: None, runner=fake_runner)
            problems.append("무카메라 which에서 run_pi_session이 PiCaptureError를 던지지 않았다")
            no_camera_blocked = False
        except PiCaptureError:
            no_camera_blocked = not no_camera_dir.exists()
            if no_camera_dir.exists():
                problems.append("무카메라 run_pi_session에서 캡처 디렉터리가 생겼다")
        except Exception as e:
            problems.append(f"무카메라 run_pi_session 예외가 PiCaptureError가 아니다: {type(e).__name__}: {e}")
            no_camera_blocked = False
        ctx.note(f"무카메라 run_pi_session 차단 -> {no_camera_blocked}")

        session_out_dir = root / "pi-session-captures"
        try:
            report = run_pi_session(session_out_dir, session_id=PI_SESSION_ID,
                                    runner=fake_runner, which=fake_which)
        except Exception as e:
            problems.append(f"가짜 which/runner run_pi_session 실패: {type(e).__name__}: {e}")
            report = {}
        if report:
            ctx.note(
                f"가짜 which/runner run_pi_session -> source={report.get('source')}, "
                f"capture_source={report.get('capture_source')}, summary={report.get('summary')}")
            if report.get("source") != "mock":
                problems.append(f"source가 mock이 아니다: {report.get('source')}")
            if report.get("capture_source") != "pi-camera":
                problems.append(f"capture_source가 pi-camera가 아니다: {report.get('capture_source')}")
            if report.get("session_id") != PI_SESSION_ID:
                problems.append(f"session_id 기대 {PI_SESSION_ID}, 실제 {report.get('session_id')}")
            summary_data = report.get("summary", {})
            for key, expected in EXPECTED_SIM_SUMMARY.items():
                if summary_data.get(key) != expected:
                    problems.append(
                        f"summary.{key} 기대 {expected}, 실제 {summary_data.get(key)}")
            bins = report.get("bins", [])
            if len(bins) != 6:
                problems.append(f"bins 기대 6, 실제 {len(bins)}")
            by_bin = {b.get("bin_id"): b for b in bins}
            target = by_bin.get("A-01-02", {})
            if target.get("verdict") != "short" or target.get("diff") != -3:
                problems.append(
                    f"A-01-02 기대 short/-3, 실제 {target.get('verdict')}/{target.get('diff')}")
            over = by_bin.get("B-01-02", {})
            if over.get("verdict") != "over" or over.get("diff") != 3:
                problems.append(
                    f"B-01-02 기대 over/+3, 실제 {over.get('verdict')}/{over.get('diff')}")
            probe_data = report.get("probe", {})
            if probe_data.get("available") is not True:
                problems.append(f"report probe.available 기대 True, 실제 {probe_data.get('available')}")
            if probe_data.get("command") != "libcamera-still":
                problems.append(f"report probe.command 기대 libcamera-still, 실제 {probe_data.get('command')}")
            if not any("Pi 실촬영 검증 전" in line for line in report.get("honesty", [])):
                problems.append("honesty에 'Pi 실촬영 검증 전' 표기 없음")
            expected_sha = hashlib.sha256(PI_SESSION_FAKE_CONTENT).hexdigest()
            for entry in bins:
                bin_id = entry.get("bin_id")
                photo = entry.get("photo", {})
                if photo.get("sha256") != expected_sha:
                    problems.append(f"{bin_id} photo.sha256이 가짜 세션 바이트 해시와 다르다")
                if photo.get("image_ref") != f"{bin_id}.jpg":
                    problems.append(
                        f"{bin_id} photo.image_ref 기대 {bin_id}.jpg, 실제 {photo.get('image_ref')}")
                if not (session_out_dir / f"{bin_id}.jpg").is_file():
                    problems.append(f"{bin_id} 캡처 파일이 임시 디렉터리에 존재하지 않는다")

    summary = {"feature": "pi-session", "source": report.get("source"),
               "capture_source": report.get("capture_source"),
               "session_summary": report.get("summary"),
               "probe_command": report.get("probe", {}).get("command"),
               "fake_capture_sha256": hashlib.sha256(PI_SESSION_FAKE_CONTENT).hexdigest(),
               "cli_session_blocked": cli_session_blocked,
               "no_camera_blocked": no_camera_blocked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"pi-session-report.json": json.dumps(report, ensure_ascii=False, indent=2),
                    "pi-session-blocked.txt": blocked_text})
    return summary


def drive_sam_live(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from terminal.sam_adapter import (LiveSamCounter, MockSamCounter,
                                      SamCountingError, build_counter,
                                      build_payload, parse_response)

    recorded: dict = {}

    def fake_transport(url, headers, body, timeout):
        recorded["url"] = url
        recorded["headers"] = dict(headers)
        recorded["body"] = body
        recorded["timeout"] = timeout
        return 200, {"counted_qty": SAM_FAKE_COUNT}

    result = None
    parsed_body: dict = {}
    try:
        counter = LiveSamCounter(SAM_FAKE_URL + "/", SAM_FAKE_KEY,
                                 transport=fake_transport)
        result = counter.count(SAM_BIN_ID, image_ref="photo-1.jpg")
    except Exception as e:
        problems.append(f"가짜 transport SAM count 실패: {type(e).__name__}: {e}")
    if result is not None:
        ctx.note(
            f"가짜 transport SAM count -> source={result.source}, "
            f"counted_qty={result.counted_qty}")
        if result.counted_qty != SAM_FAKE_COUNT:
            problems.append(
                f"counted_qty 기대 {SAM_FAKE_COUNT}, 실제 {result.counted_qty}")
        if result.source != "sam":
            problems.append(f"source 기대 sam, 실제 {result.source}")
    if recorded.get("url") != SAM_FAKE_URL:
        problems.append(
            f"기록된 url 기대 {SAM_FAKE_URL}, 실제 {recorded.get('url')}")
    headers = recorded.get("headers", {})
    if headers.get("Authorization") != "Bearer " + SAM_FAKE_KEY:
        problems.append("Authorization 헤더가 Bearer 키 형태가 아니다")
    body_bytes = recorded.get("body", b"")
    body_text = (body_bytes.decode("utf-8", "replace")
                 if isinstance(body_bytes, bytes) else str(body_bytes))
    try:
        parsed_body = json.loads(body_text) if body_text else {}
    except json.JSONDecodeError as e:
        problems.append(f"요청 body JSON 파싱 실패: {e}")
        parsed_body = {}
    if parsed_body.get("model") != "sam-3.1":
        problems.append(f"body model 기대 sam-3.1, 실제 {parsed_body.get('model')}")
    if parsed_body.get("bin_id") != SAM_BIN_ID:
        problems.append(f"body bin_id 기대 {SAM_BIN_ID}, 실제 {parsed_body.get('bin_id')}")
    if parsed_body.get("image_ref") != "photo-1.jpg":
        problems.append(
            f"body image_ref 기대 photo-1.jpg, 실제 {parsed_body.get('image_ref')}")
    if SAM_FAKE_KEY in body_text:
        problems.append("요청 body 원문에 API 키가 포함됐다")
    direct_payload = build_payload(SAM_BIN_ID, image_ref="photo-1.jpg")
    if direct_payload.get("model") != "sam-3.1" \
            or direct_payload.get("bin_id") != SAM_BIN_ID \
            or direct_payload.get("image_ref") != "photo-1.jpg":
        problems.append(f"build_payload 결과가 기대와 다르다: {direct_payload}")
    if SAM_FAKE_KEY in json.dumps(direct_payload):
        problems.append("build_payload 결과에 API 키가 포함됐다")

    for payload, expected in (({"counted_qty": 7}, 7),
                              ({"result": {"quantity": 4}}, 4),
                              ({"detections": [1, 2]}, 2)):
        try:
            actual = parse_response(payload)
        except Exception as e:
            problems.append(
                f"parse_response({payload}) 실패: {type(e).__name__}: {e}")
            continue
        if actual != expected:
            problems.append(
                f"parse_response({payload}) 기대 {expected}, 실제 {actual}")

    def http_fail_transport(url, headers, body, timeout):
        return 503, {"error": "unavailable"}

    http_error_blocked = False
    try:
        LiveSamCounter(SAM_FAKE_URL, SAM_FAKE_KEY,
                       transport=http_fail_transport).count(
                           SAM_BIN_ID, image_ref="photo-1.jpg")
        problems.append("HTTP 503에서 SamCountingError가 나지 않았다")
    except SamCountingError:
        http_error_blocked = True
    except Exception as e:
        problems.append(
            f"HTTP 503 예외가 SamCountingError가 아니다: {type(e).__name__}: {e}")
    ctx.note(f"HTTP 503 차단(모의 폴백 없음) -> {http_error_blocked}")

    def raising_transport(url, headers, body, timeout):
        raise OSError("sensitive-detail")

    transport_error_wrapped = False
    try:
        LiveSamCounter(SAM_FAKE_URL, SAM_FAKE_KEY,
                       transport=raising_transport).count(
                           SAM_BIN_ID, image_ref="photo-1.jpg")
        problems.append("전송 OSError에서 SamCountingError가 나지 않았다")
    except SamCountingError as e:
        message = str(e)
        if "sensitive-detail" in message:
            problems.append("SamCountingError 메시지에 원본 전송 상세가 포함됐다")
        elif SAM_FAKE_KEY in message:
            problems.append("SamCountingError 메시지에 API 키가 포함됐다")
        else:
            transport_error_wrapped = True
    except Exception as e:
        problems.append(
            f"전송 예외가 SamCountingError가 아니다: {type(e).__name__}: {e}")
    ctx.note(f"전송 예외 SamCountingError 감싸기 -> {transport_error_wrapped}")

    mock_selection_ok = False
    saved_env: dict[str, str] = {}
    for key in ("SAM_API_BASE_URL", "SAM_API_KEY"):
        if key in os.environ:
            saved_env[key] = os.environ.pop(key)
    try:
        selected = build_counter({SAM_BIN_ID: SAM_FAKE_COUNT})
        if not isinstance(selected, MockSamCounter):
            problems.append(
                f"환경변수 없는 build_counter 기대 MockSamCounter, "
                f"실제 {type(selected).__name__}")
        else:
            mock_result = selected.count(SAM_BIN_ID, image_ref="photo-1.jpg")
            if mock_result.source != "mock":
                problems.append(f"모의 선택 source 기대 mock, 실제 {mock_result.source}")
            elif mock_result.counted_qty != SAM_FAKE_COUNT:
                problems.append(
                    f"모의 선택 counted_qty 기대 {SAM_FAKE_COUNT}, "
                    f"실제 {mock_result.counted_qty}")
            else:
                mock_selection_ok = True
    except Exception as e:
        problems.append(f"모의 선택 확인 실패: {type(e).__name__}: {e}")
    finally:
        for key in ("SAM_API_BASE_URL", "SAM_API_KEY"):
            if key in saved_env:
                os.environ[key] = saved_env[key]
            else:
                os.environ.pop(key, None)
    ctx.note(f"환경변수 없는 모의 선택 -> {mock_selection_ok}")

    fake_payload = {"url": recorded.get("url"),
                    "model": parsed_body.get("model"),
                    "bin_id": parsed_body.get("bin_id"),
                    "counted_qty": getattr(result, "counted_qty", None),
                    "source": getattr(result, "source", None)}
    errors_payload = {"http_error_blocked": http_error_blocked,
                      "transport_error_wrapped": transport_error_wrapped,
                      "mock_selection_ok": mock_selection_ok}
    summary = {"feature": "sam-live",
               "source": getattr(result, "source", None),
               "counted_qty": getattr(result, "counted_qty", None),
               "fake_url": SAM_FAKE_URL,
               "http_error_blocked": http_error_blocked,
               "transport_error_wrapped": transport_error_wrapped,
               "mock_selection_ok": mock_selection_ok,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-live-fake.json": json.dumps(fake_payload, ensure_ascii=False, indent=2) + "\n",
                    "sam-live-errors.json": json.dumps(errors_payload, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_sam_readiness(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.sam_readiness import ENV_BASE_URL, ENV_KEY_VAR, check_readiness

    result = run_cli(["-m", "qa.sam_readiness"])
    ctx.note(f"python3 -m qa.sam_readiness -> 종료코드 {result.returncode}")
    if result.returncode != 1:
        problems.append(
            f"sam_readiness 기본 종료코드 기대 1, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("BLOCKERS: 3", "READY_FOR_LIVE_CALL: false"):
        if needle not in result.stdout:
            problems.append(f"sam_readiness 텍스트에 {needle!r} 없음")
    positions = [result.stdout.find(blocker_id)
                 for blocker_id in EXPECTED_READINESS_BLOCKER_IDS]
    if any(position < 0 for position in positions):
        problems.append(
            f"sam_readiness 텍스트에 블로커 id 누락: 위치 {positions}")
    elif positions != sorted(positions):
        problems.append(f"sam_readiness 블로커 id 순서 이상: 위치 {positions}")

    result_j = run_cli(["-m", "qa.sam_readiness", "--json"])
    ctx.note(f"python3 -m qa.sam_readiness --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 1:
        problems.append(
            f"sam_readiness --json 종료코드 기대 1, 실제 {result_j.returncode}: "
            f"{result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocked_blockers: list = []
    if report:
        if report.get("ready_for_live_call") is not False:
            problems.append(
                "ready_for_live_call 기대 False, 실제 "
                f"{report.get('ready_for_live_call')}")
        blocked_blockers = [b["id"] for b in report.get("blockers", [])]
        if blocked_blockers != list(EXPECTED_READINESS_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_READINESS_BLOCKER_IDS)}, "
                f"실제 {blocked_blockers}")
        for field in ("base_url_present", "api_key_present", "credit_confirmed"):
            if report.get(field) is not False:
                problems.append(f"{field} 기대 False, 실제 {report.get(field)}")
        if not any("호출하지 않는다" in line
                   for line in report.get("honesty", [])):
            problems.append("honesty에 '호출하지 않는다'를 포함한 줄 없음")

    fake_env = {ENV_BASE_URL: SAM_READINESS_FAKE_URL,
                ENV_KEY_VAR: SAM_READINESS_FAKE_KEY_VALUE}
    ready: dict = {}
    sentinel_leaked = False
    try:
        ready = check_readiness(env=fake_env, credit_confirmed=True)
    except Exception as e:
        problems.append(f"check_readiness 가짜 환경 실패: {type(e).__name__}: {e}")
    if ready:
        ctx.note(
            f"check_readiness 가짜 환경 -> ready_for_live_call="
            f"{ready.get('ready_for_live_call')}")
        if ready.get("ready_for_live_call") is not True:
            problems.append(
                "가짜 환경 ready_for_live_call 기대 True, 실제 "
                f"{ready.get('ready_for_live_call')}")
        if ready.get("blockers") != []:
            problems.append(f"가짜 환경 blockers 기대 [], 실제 {ready.get('blockers')}")
        if ready.get("would_select_live") is not True:
            problems.append(
                "가짜 환경 would_select_live 기대 True, 실제 "
                f"{ready.get('would_select_live')}")
        ready_dumped = json.dumps(ready, ensure_ascii=False)
        if SAM_READINESS_FAKE_KEY_VALUE in ready_dumped \
                or SAM_READINESS_FAKE_URL in ready_dumped:
            sentinel_leaked = True
            problems.append("check_readiness 결과에 가짜 키/URL 값이 포함됐다")

    credit_only_ids: list = []
    try:
        credit_only = check_readiness(env=fake_env, credit_confirmed=False)
        credit_only_ids = [b["id"] for b in credit_only.get("blockers", [])]
    except Exception as e:
        problems.append(
            f"check_readiness 크레딧 미확인 실패: {type(e).__name__}: {e}")
    ctx.note(f"check_readiness 크레딧 미확인 블로커 -> {credit_only_ids}")
    if credit_only_ids != ["sam_credit_not_confirmed"]:
        problems.append(
            f"크레딧 미확인 blockers 기대 ['sam_credit_not_confirmed'], "
            f"실제 {credit_only_ids}")

    cli_ready = subprocess.run(
        [sys.executable, "-m", "qa.sam_readiness",
         "--credit-confirmed", "--json"],
        cwd=ROOT,
        env={**clean_env(), ENV_BASE_URL: SAM_READINESS_FAKE_URL,
             ENV_KEY_VAR: SAM_READINESS_FAKE_KEY_VALUE},
        capture_output=True, text=True, timeout=120)
    ctx.note(
        "python3 -m qa.sam_readiness --credit-confirmed --json "
        f"(가짜 환경) -> 종료코드 {cli_ready.returncode}")
    if cli_ready.returncode != 0:
        problems.append(
            f"가짜 환경 CLI 종료코드 기대 0, 실제 {cli_ready.returncode}: "
            f"{cli_ready.stderr[:200]}")
    cli_ready_report: dict = {}
    try:
        cli_ready_report = json.loads(cli_ready.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"가짜 환경 CLI --json 파싱 실패: {e}")
    if cli_ready_report and cli_ready_report.get("ready_for_live_call") is not True:
        problems.append(
            "가짜 환경 CLI ready_for_live_call 기대 True, 실제 "
            f"{cli_ready_report.get('ready_for_live_call')}")
    if SAM_READINESS_FAKE_KEY_VALUE in cli_ready.stdout \
            or SAM_READINESS_FAKE_URL in cli_ready.stdout:
        sentinel_leaked = True
        problems.append("가짜 환경 CLI stdout에 가짜 키/URL 값이 포함됐다")
    ctx.note(f"가짜 키/URL 값 누출 -> {sentinel_leaked}")

    summary = {"feature": "sam-readiness",
               "blocked_blockers": blocked_blockers,
               "default_exit_code": result.returncode,
               "ready_with_fake_env": ready.get("ready_for_live_call") is True,
               "credit_only_blocker": credit_only_ids,
               "cli_ready_exit_code": cli_ready.returncode,
               "sentinel_leaked": sentinel_leaked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-readiness-blocked.json": result_j.stdout,
                    "sam-readiness-ready.json": json.dumps(
                        ready, ensure_ascii=False, indent=2) + "\n"})
    return summary


def validate_runbook_text(text: str) -> list[str]:
    problems: list[str] = []
    positions = [text.find(section) for section in RUNBOOK_SECTIONS]
    if any(position < 0 for position in positions):
        missing = [section for section, position
                   in zip(RUNBOOK_SECTIONS, positions) if position < 0]
        problems.append(f"런북 절 누락 {missing}")
    elif positions != sorted(positions):
        problems.append(f"런북 절 순서 이상: 위치 {positions}")
    blocker_positions = [text.find(blocker_id)
                         for blocker_id in EXPECTED_BLOCKER_IDS]
    if any(position < 0 for position in blocker_positions) \
            or blocker_positions != sorted(blocker_positions):
        problems.append(
            f"런북 블로커 id 누락 또는 순서 이상: 위치 {blocker_positions}, "
            f"기대 {list(EXPECTED_BLOCKER_IDS)}")
    if "SUBMISSION_READY: false" not in text \
            or "SUBMISSION_READY: true" in text:
        problems.append(
            "SUBMISSION_READY 표기 이상: SUBMISSION_READY: false가 없거나 "
            "SUBMISSION_READY: true가 있다")
    for needle in (RUNBOOK_CREDIT_AT, "--credit-confirmed", "Secure Vault",
                   "SAM_API_BASE_URL", "SAM_API_KEY"):
        if needle not in text:
            problems.append(f"런북에 {needle!r} 없음")
    for needle in ("모의", "검증 전", "미실시"):
        if needle not in text:
            problems.append(f"런북 정직성 표기 {needle!r} 없음")
    for command in RUNBOOK_FINAL_COMMANDS:
        if command not in text:
            problems.append(f"런북 최종 점검 명령 {command!r} 없음")
    for needle in ("2026-11-04 21:00", RUNBOOK_DEADLINE_KST,
                   "BoxLogoDev/argus-counts"):
        if needle not in text:
            problems.append(f"런북에 {needle!r} 없음")
    from qa.claims_audit import audit_text

    audit_problems = audit_text(RUNBOOK_REL, text)
    if audit_problems:
        problems.append(f"런북 주장 감사 문제 {audit_problems}")
    return problems


def drive_pi_readiness(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.pi_readiness import check_readiness

    result = run_cli(["-m", "qa.pi_readiness"])
    ctx.note(f"python3 -m qa.pi_readiness -> 종료코드 {result.returncode}")
    if result.returncode != 1:
        problems.append(
            f"pi_readiness 기본 종료코드 기대 1, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("BLOCKERS: 2", "READY_FOR_REAL_CAPTURE: false"):
        if needle not in result.stdout:
            problems.append(f"pi_readiness 텍스트에 {needle!r} 없음")
    positions = [result.stdout.find(blocker_id)
                 for blocker_id in EXPECTED_PI_READINESS_BLOCKER_IDS]
    if any(position < 0 for position in positions):
        problems.append(f"pi_readiness 텍스트에 블로커 id 누락: 위치 {positions}")
    elif positions != sorted(positions):
        problems.append(f"pi_readiness 블로커 id 순서 이상: 위치 {positions}")

    result_j = run_cli(["-m", "qa.pi_readiness", "--json"])
    ctx.note(f"python3 -m qa.pi_readiness --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 1:
        problems.append(
            f"pi_readiness --json 종료코드 기대 1, 실제 {result_j.returncode}: "
            f"{result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocked_blockers: list = []
    if report:
        if report.get("ready_for_real_capture") is not False:
            problems.append(
                "ready_for_real_capture 기대 False, 실제 "
                f"{report.get('ready_for_real_capture')}")
        blocked_blockers = [b["id"] for b in report.get("blockers", [])]
        if blocked_blockers != list(EXPECTED_PI_READINESS_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_PI_READINESS_BLOCKER_IDS)}, "
                f"실제 {blocked_blockers}")
        if report.get("device_confirmed") is not False:
            problems.append(
                f"device_confirmed 기대 False, 실제 {report.get('device_confirmed')}")
        if report.get("camera_available") is not False:
            problems.append(
                f"camera_available 기대 False, 실제 {report.get('camera_available')}")
        if report.get("camera_command") is not None:
            problems.append(
                f"camera_command 기대 None, 실제 {report.get('camera_command')}")
        if report.get("candidates_checked") != ["libcamera-still", "raspistill"]:
            problems.append(
                f"candidates_checked 이상: {report.get('candidates_checked')}")
        honesty = report.get("honesty", [])
        if not any("촬영을 하지 않는다" in line for line in honesty):
            problems.append("honesty에 '촬영을 하지 않는다'를 포함한 줄 없음")
        if not any("성공을 뜻하지 않는다" in line for line in honesty):
            problems.append("honesty에 '성공을 뜻하지 않는다'를 포함한 줄 없음")

    ready: dict = {}
    try:
        ready = check_readiness(probe=PI_READINESS_READY_PROBE,
                                device_confirmed=True)
    except Exception as e:
        problems.append(f"check_readiness 가짜 probe 실패: {type(e).__name__}: {e}")
    if ready:
        ctx.note(
            f"check_readiness 가짜 probe -> ready_for_real_capture="
            f"{ready.get('ready_for_real_capture')}")
        if ready.get("ready_for_real_capture") is not True:
            problems.append(
                "가짜 probe ready_for_real_capture 기대 True, 실제 "
                f"{ready.get('ready_for_real_capture')}")
        if ready.get("blockers") != []:
            problems.append(f"가짜 probe blockers 기대 [], 실제 {ready.get('blockers')}")

    device_only_ids: list = []
    try:
        device_only = check_readiness(probe=PI_READINESS_READY_PROBE,
                                      device_confirmed=False)
        device_only_ids = [b["id"] for b in device_only.get("blockers", [])]
    except Exception as e:
        problems.append(f"check_readiness 장치만 차단 실패: {type(e).__name__}: {e}")
    ctx.note(f"check_readiness 장치만 차단 블로커 -> {device_only_ids}")
    if device_only_ids != ["pi_device_arrival_not_confirmed"]:
        problems.append(
            f"장치만 차단 blockers 기대 ['pi_device_arrival_not_confirmed'], "
            f"실제 {device_only_ids}")

    camera_only_ids: list = []
    try:
        camera_only = check_readiness(probe=PI_READINESS_MISSING_PROBE,
                                      device_confirmed=True)
        camera_only_ids = [b["id"] for b in camera_only.get("blockers", [])]
    except Exception as e:
        problems.append(f"check_readiness 카메라만 차단 실패: {type(e).__name__}: {e}")
    ctx.note(f"check_readiness 카메라만 차단 블로커 -> {camera_only_ids}")
    if camera_only_ids != ["pi_camera_command_missing"]:
        problems.append(
            f"카메라만 차단 blockers 기대 ['pi_camera_command_missing'], "
            f"실제 {camera_only_ids}")

    which_command = None
    try:
        injected = check_readiness(
            device_confirmed=True,
            which=lambda name: "/usr/bin/raspistill" if name == "raspistill" else None)
        which_command = injected.get("camera_command")
        if injected.get("camera_available") is not True \
                or injected.get("ready_for_real_capture") is not True:
            problems.append(f"which 주입 결과 이상: {injected}")
    except Exception as e:
        problems.append(f"check_readiness which 주입 실패: {type(e).__name__}: {e}")
    ctx.note(f"which 주입 카메라 명령 -> {which_command}")
    if which_command != "raspistill":
        problems.append(f"which 주입 command 기대 'raspistill', 실제 {which_command}")

    cli_device = run_cli(["-m", "qa.pi_readiness", "--device-confirmed", "--json"])
    ctx.note(
        "python3 -m qa.pi_readiness --device-confirmed --json -> "
        f"종료코드 {cli_device.returncode}")
    if cli_device.returncode != 1:
        problems.append(
            f"장치 확인 CLI 종료코드 기대 1, 실제 {cli_device.returncode}: "
            f"{cli_device.stderr[:200]}")
    cli_device_blockers: list = []
    try:
        cli_device_report = json.loads(cli_device.stdout)
        cli_device_blockers = [b["id"] for b in cli_device_report.get("blockers", [])]
    except json.JSONDecodeError as e:
        problems.append(f"장치 확인 CLI --json 파싱 실패: {e}")
    if cli_device_blockers != ["pi_camera_command_missing"]:
        problems.append(
            f"장치 확인 CLI blockers 기대 ['pi_camera_command_missing'], "
            f"실제 {cli_device_blockers}")

    summary = {"feature": "pi-readiness",
               "blocked_blockers": blocked_blockers,
               "default_exit_code": result.returncode,
               "ready_with_fake_probe": ready.get("ready_for_real_capture") is True,
               "device_only_blocker": device_only_ids,
               "camera_only_blocker": camera_only_ids,
               "which_injected_command": which_command,
               "cli_device_confirmed_exit_code": cli_device.returncode,
               "cli_device_confirmed_blockers": cli_device_blockers,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"pi-readiness-blocked.json": result_j.stdout,
                    "pi-readiness-ready.json": json.dumps(
                        ready, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_submission_runbook(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    runbook_path = ROOT / RUNBOOK_REL
    if runbook_path.is_file():
        text = runbook_path.read_text(encoding="utf-8")
        problems = validate_runbook_text(text)
    else:
        text = ""
        problems.append(f"제출 런북 파일이 없다: {RUNBOOK_REL}")
    ctx.note(f"제출 런북 읽기 -> {RUNBOOK_REL}, {len(text)}자")
    tampered = text.replace("SUBMISSION_READY: false",
                            "SUBMISSION_READY: true", 1)
    tamper_problems = validate_runbook_text(tampered) if text else []
    tamper_detected = bool(tamper_problems)
    ctx.note(f"런북 변조 탐지 -> {tamper_detected}")
    if not tamper_detected:
        problems.append(
            "변조 탐지 실패: SUBMISSION_READY를 true로 바꾼 텍스트에서 "
            "문제를 찾지 못했다")
    result = run_cli(["-m", "qa.pre_submission", "--json"])
    ctx.note(
        f"python3 -m qa.pre_submission --json -> 종료코드 {result.returncode}")
    pre_blockers: list = []
    report: dict = {}
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"qa.pre_submission --json 파싱 실패: {e}")
    if report:
        pre_blockers = [b.get("id") if isinstance(b, dict) else b
                        for b in report.get("blockers", [])]
        if pre_blockers != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"pre_submission blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, "
                f"실제 {pre_blockers}")
        if report.get("submission_ready") is not False:
            problems.append(
                "pre_submission submission_ready 기대 False, 실제 "
                f"{report.get('submission_ready')}")
    claims_audit_clean = False
    if text:
        from qa.claims_audit import audit_text

        claims_audit_clean = audit_text(RUNBOOK_REL, text) == []
    ctx.note(f"런북 주장 감사 깨끗함 -> {claims_audit_clean}")
    extracted = {"sections": list(RUNBOOK_SECTIONS),
                 "blockers": list(EXPECTED_BLOCKER_IDS),
                 "submission_ready": False,
                 "credit_check_at": RUNBOOK_CREDIT_AT,
                 "deadline_kst": RUNBOOK_DEADLINE_KST,
                 "final_check_commands": list(RUNBOOK_FINAL_COMMANDS)}
    summary = {"feature": "submission-runbook",
               "sections": list(RUNBOOK_SECTIONS),
               "section_count": len(RUNBOOK_SECTIONS),
               "blockers": list(EXPECTED_BLOCKER_IDS),
               "submission_ready": False,
               "credit_check_at": RUNBOOK_CREDIT_AT,
               "deadline_kst": RUNBOOK_DEADLINE_KST,
               "final_check_command_count": len(RUNBOOK_FINAL_COMMANDS),
               "claims_audit_clean": claims_audit_clean,
               "tamper_detected": tamper_detected,
               "pre_submission_blockers": pre_blockers,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"submission-runbook.json": json.dumps(
                       extracted, ensure_ascii=False, indent=2) + "\n",
                    "submission-runbook.md": text})
    return summary


def drive_console_readiness(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from console.readiness import build_readiness
    from qa.sam_readiness import ENV_BASE_URL, ENV_KEY_VAR

    port = ctx.ensure_server()
    status, readiness_text = fetch(port, "/api/readiness")
    ctx.note(f"GET /api/readiness -> {status}")
    if status != 200:
        problems.append(f"/api/readiness 상태 {status}")
    readiness: dict = {}
    try:
        readiness = json.loads(readiness_text)
    except json.JSONDecodeError as e:
        problems.append(f"/api/readiness JSON 파싱 실패: {e}")
    sam_blockers = readiness.get("sam_blockers", []) if readiness else []
    pi_blockers = readiness.get("pi_blockers", []) if readiness else []
    blocker_count = readiness.get("blocker_count") if readiness else None
    if readiness:
        if sam_blockers != list(EXPECTED_CONSOLE_SAM_BLOCKERS):
            problems.append(
                f"sam_blockers 기대 {list(EXPECTED_CONSOLE_SAM_BLOCKERS)}, "
                f"실제 {sam_blockers}")
        if pi_blockers != list(EXPECTED_CONSOLE_PI_BLOCKERS):
            problems.append(
                f"pi_blockers 기대 {list(EXPECTED_CONSOLE_PI_BLOCKERS)}, "
                f"실제 {pi_blockers}")
        if blocker_count != 5:
            problems.append(f"blocker_count 기대 5, 실제 {blocker_count}")
        if readiness.get("sam_ready") is not False:
            problems.append(
                f"sam_ready 기대 False, 실제 {readiness.get('sam_ready')}")
        if readiness.get("pi_ready") is not False:
            problems.append(
                f"pi_ready 기대 False, 실제 {readiness.get('pi_ready')}")
        if readiness.get("overall_ready") is not False:
            problems.append(
                "overall_ready 기대 False, 실제 "
                f"{readiness.get('overall_ready')}")
        sam = readiness.get("sam") or {}
        pi = readiness.get("pi") or {}
        if sam.get("ready_for_live_call") is not False:
            problems.append(
                "sam.ready_for_live_call 기대 False, 실제 "
                f"{sam.get('ready_for_live_call')}")
        if pi.get("ready_for_real_capture") is not False:
            problems.append(
                "pi.ready_for_real_capture 기대 False, 실제 "
                f"{pi.get('ready_for_real_capture')}")
        honesty = readiness.get("honesty", [])
        for needle in ("준비 완료는 실호출·실촬영 성공을 뜻하지 않는다",
                       "실제 API를 호출하지 않는다", "실제 촬영을 하지 않는다"):
            if not any(needle in line for line in honesty):
                problems.append(f"honesty에 {needle!r} 없음")

    home_status, home_text = fetch(port, "/")
    ctx.note(f"GET / -> {home_status}")
    if home_status != 200:
        problems.append(f"/ 상태 {home_status}")
    home_markers = {m: (m in home_text) for m in CONSOLE_READINESS_HOME_MARKERS}
    for marker, found in home_markers.items():
        ctx.note(f"홈 준비 상태 마커 {marker!r}: {'발견' if found else '없음'}")
    missing = [m for m, ok in home_markers.items() if not ok]
    if missing:
        problems.append(f"홈 준비 상태 마커 누락 {missing}")
    try:
        order = [home_text.index("실사 세션 정보"),
                 home_text.index("준비 상태"), home_text.index("차이 목록")]
        if order != sorted(order):
            problems.append(f"홈 준비 상태 섹션 순서 이상: {order}")
    except ValueError as e:
        problems.append(f"홈 섹션 순서 확인 실패: {e}")

    fake_env = {ENV_BASE_URL: CONSOLE_READINESS_FAKE_URL,
                ENV_KEY_VAR: CONSOLE_READINESS_FAKE_KEY_VALUE}
    fake_ready = build_readiness(
        env=fake_env, sam_credit_confirmed=True,
        pi_probe=dict(CONSOLE_READINESS_FAKE_PROBE), pi_device_confirmed=True)
    ctx.note(
        f"build_readiness 가짜 준비 완료 -> overall_ready={fake_ready.get('overall_ready')}")
    if fake_ready.get("overall_ready") is not True:
        problems.append(
            f"가짜 준비 완료 overall_ready 기대 True, 실제 {fake_ready.get('overall_ready')}")
    if fake_ready.get("sam_blockers") != [] or fake_ready.get("pi_blockers") != []:
        problems.append(
            f"가짜 준비 완료 블로커 기대 [], 실제 {fake_ready.get('sam_blockers')}/"
            f"{fake_ready.get('pi_blockers')}")
    if fake_ready.get("blocker_count") != 0:
        problems.append(
            f"가짜 준비 완료 blocker_count 기대 0, 실제 {fake_ready.get('blocker_count')}")

    sam_only = build_readiness(env=fake_env, sam_credit_confirmed=True)
    if sam_only.get("sam_ready") is not True or sam_only.get("pi_ready") is not False \
            or sam_only.get("overall_ready") is not False:
        problems.append(f"SAM만 준비 완료 분리 이상: {sam_only}")
    pi_only = build_readiness(
        env={}, pi_probe=dict(CONSOLE_READINESS_FAKE_PROBE),
        pi_device_confirmed=True)
    if pi_only.get("pi_ready") is not True or pi_only.get("sam_ready") is not False \
            or pi_only.get("overall_ready") is not False:
        problems.append(f"Pi만 준비 완료 분리 이상: {pi_only}")

    dumped = json.dumps(fake_ready, ensure_ascii=False)
    sentinel_leaked = (CONSOLE_READINESS_FAKE_KEY_VALUE in dumped
                       or CONSOLE_READINESS_FAKE_URL in dumped)
    ctx.note(f"가짜 준비 완료 증거 값 누출 -> {sentinel_leaked}")
    if sentinel_leaked:
        problems.append("가짜 환경변수 값이 build_readiness 결과에 새어 나왔다")

    summary = {"feature": "console-readiness",
               "readiness_status": status, "home_status": home_status,
               "sam_blockers": sam_blockers, "pi_blockers": pi_blockers,
               "blocker_count": blocker_count,
               "sam_ready": readiness.get("sam_ready") if readiness else None,
               "pi_ready": readiness.get("pi_ready") if readiness else None,
               "overall_ready": readiness.get("overall_ready") if readiness else None,
               "home_markers": home_markers,
               "fake_overall_ready": fake_ready.get("overall_ready") is True,
               "fake_sam_only_overall": sam_only.get("overall_ready") is True,
               "fake_pi_only_overall": pi_only.get("overall_ready") is True,
               "sentinel_leaked": sentinel_leaked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"console-readiness.json": readiness_text,
                    "console-readiness-ready.json": json.dumps(
                        fake_ready, ensure_ascii=False, indent=2) + "\n",
                    "console-readiness-home.html": home_text})
    return summary


DRIVERS = {"console-home": drive_console_home,
           "terminal-simulator": drive_terminal_simulator,
           "session-list": drive_session_list,
           "difference-report": drive_difference_report,
           "demo-video-draft": drive_demo_video,
           "photo-intake": drive_photo_intake,
           "pre-submission": drive_pre_submission,
           "pi-capture": drive_pi_capture,
           "pi-session": drive_pi_session,
           "sam-live": drive_sam_live,
           "sam-readiness": drive_sam_readiness,
           "submission-runbook": drive_submission_runbook,
           "pi-readiness": drive_pi_readiness,
           "console-readiness": drive_console_readiness}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Argus verification helper")
    parser.add_argument("--doctor", action="store_true",
                        help="구동 가능 여부만 빠르게 확인한다")
    parser.add_argument("--feature", default="console-home",
                        choices=[*FEATURES, "all"],
                        help="검증할 기능 이름 (기본 console-home)")
    parser.add_argument("--evidence-dir", default="/tmp/argus-verify-evidence/manual-run",
                        help="증거를 남길 디렉터리")
    args = parser.parse_args(argv)

    if os.environ.get("SAM_API_KEY"):
        print("경고: SAM_API_KEY가 설정돼 있다. 검증은 source=mock일 때만 통과하고 자식 환경에서는 제거한다.")

    ctx = Ctx()
    try:
        if args.doctor:
            port = ctx.ensure_server()
            status, report_text = fetch(port, "/api/report")
            report = json.loads(report_text)
            ctx.note(f"GET /api/report -> {status}, source={report.get('source')}")
            problems = check_report(report)
            if status != 200:
                problems.append(f"/api/report 상태 {status}")
            if problems:
                for problem in problems:
                    ctx.note(f"FAIL: {problem}")
                ctx.note("DOCTOR: FAIL")
                return 1
            ctx.note("DOCTOR: PASS (python·import·임시 서버·source=mock 확인)")
            return 0

        evidence_root = Path(args.evidence_dir)
        if args.feature == "all":
            results: dict[str, dict] = {}
            for name in FEATURES:
                sub_ctx = Ctx()
                try:
                    results[name] = DRIVERS[name](sub_ctx, evidence_root / name)
                finally:
                    sub_ctx.close()
            problems = [f"{name}: {p}" for name, r in results.items() for p in r["problems"]]
            summary = {"feature": "all",
                       "features": {name: r["all_ok"] for name, r in results.items()},
                       "all_ok": not problems, "problems": problems}
            evidence_root.mkdir(parents=True, exist_ok=True)
            (evidence_root / "summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (evidence_root / "transcript.txt").write_text(
                "\n".join(f"{name}: all_ok={r['all_ok']}" for name, r in results.items()) + "\n",
                encoding="utf-8")
        else:
            summary = DRIVERS[args.feature](ctx, evidence_root)

        if summary["all_ok"]:
            print("VERIFY: PASS")
            return 0
        for problem in summary["problems"]:
            print(f"FAIL: {problem}")
        print("VERIFY: FAIL")
        return 1
    finally:
        ctx.close()


if __name__ == "__main__":
    raise SystemExit(main())
