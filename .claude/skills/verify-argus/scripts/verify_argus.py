#!/usr/bin/env python3
"""Argus 검증 헬퍼.

사용자가 닿는 표면을 직접 구동해 검증한다: 웹 콘솔은 임시 포트 서버를
띄워 HTTP로, 단말 흐름은 CLI 서브프로세스로, 데모 영상 초안은 ffprobe
탐침으로 확인하고, 제출 전 전수 점검은 CLI 서브프로세스로 구동하며,
응답 원문과 종료 판정을 증거 디렉터리에 남긴다.
서버는 이 스크립트가 띄운 것만 종료한다.

사용:
  python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor
  python3 .claude/skills/verify-argus/scripts/verify_argus.py \
      --feature <기능> --evidence-dir /tmp/argus-verify-evidence/<run-id>

기능: console-home(기본), terminal-simulator, session-list,
difference-report, demo-video-draft, photo-intake, pre-submission,
all(전부, 기능별 하위 디렉터리).

SAM 실호출은 하지 않는다. 자식 프로세스 환경에서도 SAM_API_BASE_URL과
SAM_API_KEY를 제거하고, 응답의 source가 mock이 아니면 실패로 처리한다.
표준 라이브러리만 사용한다.
"""
from __future__ import annotations

import argparse
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

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from console.server import create_handler  # noqa: E402

HOME_MARKERS = ("조치 우선순위", "모의 데이터", "66.7%")
SESSION_IDS = ("DEMO-20261027-A", "DEMO-20261027-B", "DEMO-20261026-A")
FEATURES = ("console-home", "terminal-simulator", "session-list",
            "difference-report", "demo-video-draft", "photo-intake",
            "pre-submission")
EXPECTED_BLOCKER_IDS = ("pi_real_capture_pending", "sam_real_call_pending")
PHOTO_BIN_IDS = ("A-01-01", "A-01-02", "A-02-02",
                 "A-03-01", "B-01-02", "B-02-02")
EXPECTED_SIM_SUMMARY = {"counted_bins": 6, "matched": 4, "mismatched": 2,
                        "abs_diff_total": 6, "net_diff": 0}


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
    summary = {"feature": "demo-video-draft", "probe": probe,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"video-probe.json": json.dumps(probe, ensure_ascii=False, indent=2) + "\n"})
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


DRIVERS = {"console-home": drive_console_home,
           "terminal-simulator": drive_terminal_simulator,
           "session-list": drive_session_list,
           "difference-report": drive_difference_report,
           "demo-video-draft": drive_demo_video,
           "photo-intake": drive_photo_intake,
           "pre-submission": drive_pre_submission}


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
