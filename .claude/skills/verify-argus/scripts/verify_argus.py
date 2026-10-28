#!/usr/bin/env python3
"""Argus 검증 헬퍼.

사용자가 닿는 표면을 직접 구동해 검증한다: 웹 콘솔은 임시 포트 서버를
띄워 HTTP로, 단말 흐름은 CLI 서브프로세스로, 데모 영상 초안은 ffprobe
탐침으로 확인하고, 제출 전 전수 점검은 CLI 서브프로세스로 구동하며,
Pi 캡처 경계는 탐지·기대 실패·가짜 runner 성공으로 구동하고(Pi 실촬영
검증 전), Pi 촬영 세션은 CLI 기대 실패(카메라 부재)와 가짜 which/runner
주입 성공으로 구동하며(Pi 실촬영 검증 전), 응답 원문과 종료 판정을
증거 디렉터리에 남긴다.
서버는 이 스크립트가 띄운 것만 종료한다.

사용:
  python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor
  python3 .claude/skills/verify-argus/scripts/verify_argus.py \
      --feature <기능> --evidence-dir /tmp/argus-verify-evidence/<run-id>

기능: console-home(기본), terminal-simulator, session-list,
difference-report, demo-video-draft, photo-intake, pre-submission,
pi-capture, pi-session, all(전부, 기능별 하위 디렉터리).

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
            "pre-submission", "pi-capture", "pi-session")
EXPECTED_BLOCKER_IDS = ("pi_real_capture_pending", "sam_real_call_pending")
PHOTO_BIN_IDS = ("A-01-01", "A-01-02", "A-02-02",
                 "A-03-01", "B-01-02", "B-02-02")
EXPECTED_SIM_SUMMARY = {"counted_bins": 6, "matched": 4, "mismatched": 2,
                        "abs_diff_total": 6, "net_diff": 0}
PI_FAKE_CONTENT = b"fake-pi-jpeg"
PI_BIN_ID = "A-01-02"
PI_SESSION_FAKE_CONTENT = b"fake-pi-session-jpeg"
PI_SESSION_ID = "VERIFY-PI-SESSION-1"


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
    for needle in ("PRE_SUBMISSION: 6/6 mechanical passed", "BLOCKERS: 2",
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
        if report.get("passed") != 6:
            problems.append(f"passed 기대 6, 실제 {report.get('passed')}")
        if report.get("total") != 6:
            problems.append(f"total 기대 6, 실제 {report.get('total')}")
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
        if len(checks) != 6:
            problems.append(f"checks 기대 6, 실제 {len(checks)}")
        if not all(c.get("passed") is True for c in checks):
            problems.append("checks 중 passed가 True가 아닌 항목이 있다")
        honesty = report.get("honesty", [])
        if not any("모의" in line for line in honesty):
            problems.append("honesty에 '모의'를 포함한 줄 없음")
        if not any("데모 기준" in line for line in honesty):
            problems.append("honesty에 '데모 기준'을 포함한 줄 없음")
    summary = {"feature": "pre-submission",
               "mechanical_pass": report.get("mechanical_pass"),
               "passed": report.get("passed"), "total": report.get("total"),
               "blockers": blocker_ids,
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


DRIVERS = {"console-home": drive_console_home,
           "terminal-simulator": drive_terminal_simulator,
           "session-list": drive_session_list,
           "difference-report": drive_difference_report,
           "demo-video-draft": drive_demo_video,
           "photo-intake": drive_photo_intake,
           "pre-submission": drive_pre_submission,
           "pi-capture": drive_pi_capture,
           "pi-session": drive_pi_session}


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
