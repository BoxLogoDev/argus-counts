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
준비 완료는 실호출·실촬영 성공이 아님). SAM 단일 빈 스모크(sam-smoke)는
실제 API 호출 없이 CLI 기본 차단과 프로세스 내 가짜 counter 주입으로만
구동한다(차단 시 counter를 부르지 않으며, 성공해도 전체 세션 성공이 아님).
Pi 단일 빈 스모크(pi-smoke)는 실제 촬영 없이 CLI 기본 차단과 프로세스 내
가짜 session 주입으로만 구동한다(차단 시 session을 부르지 않으며,
성공해도 전체 세션 성공이나 Pi 실촬영 검증 완료가 아님).
SAM 전체 세션(sam-session)은 qa.sam_session 전체 세션 하네스를 실제
API 호출 없이 CLI 기본 차단과 프로세스 내 가짜 counter 주입으로만
구동한다(차단 시 counter를 부르지 않으며, 가짜 성공은 데모 기준 수량의
대조 검증일 뿐 Pi 실촬영이 아니고 빈별 정확도 검증도 아니다).
Pi 전체 세션(pi-session-full)은 qa.pi_session 전체 촬영 세션 하네스를 실제
촬영 없이 CLI 기본 차단과 프로세스 내 가짜 session 주입으로만
구동한다(차단 시 session을 부르지 않으며, 가짜 성공은 데모 기준 수량의
대조 검증일 뿐 Pi 실촬영 검증 완료가 아니다).
제출 문안 패키지(devpost-submission)는 파일 원문을 읽어 절 순서·데모
수치·블로커를 대조하고 변조 탐지를 확인한다(제출 준비 완료가 아니다).
파일 입력 폴백(file-fallback)은 demo.fallback CLI를 임시 출력 디렉터리로
구동해 컷 3 폴백 자산(파일 입력·모의 계수)을 대조하고 변조 탐지를
확인한다(Pi 실촬영이 아니다).
제출물 인벤토리(submission-inventory)는 qa.submission_inventory CLI와
프로세스 내 build_inventory·validate_inventory·write_inventory로만
구동한다(파일 존재·크기·SHA-256 대조만 하며 실제로 제출하지 않는다.
인벤토리가 온전해도 제출 가능을 뜻하지 않는다).
Pi 폴백 결정(fallback-decision)은 qa.fallback_decision CLI와
프로세스 내 evaluate_decision·build_decision·validate_decision으로만
구동한다(실제 촬영 없음, 결정일 2026-11-02 전에는 폴백을 확정하지
않으며, 폴백 채택은 Pi 실촬영 검증 완료를 뜻하지 않는다).
제출 마감 점검(deadline)은 qa.deadline CLI와
프로세스 내 evaluate_deadline·build_deadline·validate_deadline으로만
구동한다(실제로 제출하지 않으며, 마감 전이어도 제출 준비 완료를
뜻하지 않고, 남은 시간은 제공된 기준 시각으로만 계산한다).
제출 패키지 최종 묶음(final-package)은 qa.final_package CLI와
프로세스 내 evaluate_final_package·build_final_package·
validate_final_package으로만 구동한다(실제로 제출하지 않으며,
패키지 준비 상태는 제출 완료를 뜻하지 않고, Pi 실촬영 검증 전이다).
SAM 빈별 서로 다른 사진 세션(sam-per-bin)은 qa.sam_per_bin 하네스를 실제
API 호출 없이 CLI 기본 차단과 프로세스 내 가짜 counter 주입으로만
구동한다(차단·사진 누락·중복 사진 시 counter를 부르지 않으며, 가짜 성공은
호출자가 제공한 가상 사진 잘라내기의 대조 검증일 뿐 실제 빈 촬영이나
Pi 실촬영이 아니고 빈별 정확도 검증도 아니다).
SAM 실호출 증거 검증(sam-live-evidence)은 qa.sam_live_evidence 하네스를
실제 API 호출 없이 CLI 파일 구동과 프로세스 내 validate_evidence·
build_report·validate_report으로만 구동한다(합성한 유효 증거의 내부
정합·해시 서로 다름·요약 재계산·변조 탐지만 확인하며, 증거 검증 통과는
실제 빈 촬영이나 Pi 실촬영, 제출 준비 완료를 뜻하지 않는다).
SAM 전체 세션 실호출 증거 검증(sam-session-evidence)은
qa.sam_session_evidence 하네스를 실제 API 호출 없이 CLI 파일 구동과
프로세스 내 validate_evidence·build_report·validate_report으로만
구동한다(합성한 유효 증거의 내부 정합·image_hashes 서로 다름·요약
재계산·변조 탐지만 확인하며, 증거 검증 통과는 실제 빈 촬영이나
Pi 실촬영, 제출 준비 완료를 뜻하지 않는다).
SAM 파일 입력 경로 실호출 증거 검증(sam-photo-evidence)은
qa.sam_photo_evidence 하네스를 실제 API 호출 없이 CLI 파일 구동과
프로세스 내 validate_evidence·build_report·validate_report으로만
구동한다(합성한 유효 증거의 내부 정합·bins photo SHA-256 서로 다름·
요약 재계산·변조 탐지만 확인하며, 증거 검증 통과는 실제 빈 촬영이나
Pi 실촬영, 제출 준비 완료를 뜻하지 않는다).
데모 영상 제출 후보 선택(video-selection)은 qa.video_selection 하네스를
CLI 날짜 구동과 프로세스 내 evaluate_selection·build_selection·
validate_selection으로만 구동한다(실제로 제출하지 않으며 선택은 제출
준비 완료를 뜻하지 않는다. 폴백 영상은 Pi 실촬영이 아니고, Pi 준비
완료만으로 기본 영상이 실촬영본이 되지는 않는다).
제출 패키지 내보내기(package-export)는 qa.package_export CLI와
프로세스 내 build_export·validate_export으로만 구동한다(제출물 18개를
임시 staging 디렉터리로 복사·해시 재대조만 하며 실제로 제출하지 않는다.
내보내기가 온전해도 제출 가능을 뜻하지 않고, Pi 실촬영 검증 전이다).
재검증 증거는 같은 드라이버가 깨끗한 staging을 새로 만들어 CLI
--verify-dir(텍스트·--json)와 프로세스 내 verify_export_dir로 다시
대조한다(읽기 전용·복사본 변조 탐지·매니페스트 없음 종료코드 2·
인자 충돌 종료코드 2 포함, 실제로 제출하지 않는다).
제출 패키지 영속 아카이브(package-archive)는 qa.package_archive CLI와
프로세스 내 build_archive·build_archive_verify·validate_archive으로만
구동한다(제출물 18개를 영속 디렉터리로 복사·재검증하고 최종 묶음 수치와
교차 대조한 아카이브 보고만 확인하며 실제로 제출하지 않는다.
아카이브가 archived여도 제출 준비 완료를 뜻하지 않고, Pi 실촬영 검증
전이며 수치는 데모 기준이다). 재검증은 매니페스트만 읽어 읽기 전용으로
다시 대조하고, 복사본 변조와 매니페스트 없음을 탐지한다.
응답 원문과 종료 판정을 증거 디렉터리에 남긴다.
서버는 이 스크립트가 띄운 것만 종료한다.

사용:
  python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor
  python3 .claude/skills/verify-argus/scripts/verify_argus.py \
      --feature <기능> --evidence-dir /tmp/argus-verify-evidence/<run-id>

기능: console-home(기본), terminal-simulator, session-list,
difference-report, demo-video-draft, photo-intake, pre-submission,
pi-capture, pi-session, sam-live, sam-readiness, submission-runbook,
pi-readiness, console-readiness, sam-smoke, pi-smoke, devpost-submission,
file-fallback, sam-session, pi-session-full, submission-inventory,
fallback-decision, deadline, final-package, package-export,
sam-per-bin, sam-live-evidence, sam-session-evidence,
video-selection, package-archive, sam-photo-evidence,
all(전부, 기능별 하위 디렉터리).

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
            "console-readiness", "sam-smoke", "pi-smoke",
            "devpost-submission", "file-fallback", "sam-session",
            "pi-session-full", "submission-inventory",
            "fallback-decision", "deadline", "final-package",
            "package-export", "sam-per-bin", "sam-live-evidence",
            "sam-session-evidence", "video-selection", "package-archive",
            "sam-photo-evidence")
EXPECTED_BLOCKER_IDS = ("pi_real_capture_pending",)
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
SAM_SMOKE_FAKE_URL = "https://sentinel-smoke.example.invalid/sam"
SAM_SMOKE_FAKE_KEY_VALUE = "sentinel-smoke-key-not-real"
SAM_SMOKE_BIN_ID = "A-01-02"
SAM_SMOKE_FAKE_COUNT = 5
SAM_SMOKE_BOOK_QTY = 8
SAM_SESSION_FAKE_URL = "https://sentinel-session.example.invalid/sam"
SAM_SESSION_FAKE_KEY_VALUE = "sentinel-session-key-not-real"
SAM_SESSION_ID = "VERIFY-SAM-SESSION-1"
SAM_SESSION_SENTINEL = "sentinel-session-not-real"
SAM_PERBIN_FAKE_URL = "https://sentinel-perbin.example.invalid/sam"
SAM_PERBIN_FAKE_KEY_VALUE = "sentinel-perbin-key-not-real"
SAM_PERBIN_SESSION_ID = "VERIFY-SAM-PERBIN-1"
SAM_PERBIN_SENTINEL = "sentinel-perbin-not-real"
SAM_EVIDENCE_SESSION_ID = "VERIFY-SAM-EVIDENCE-1"
SAM_EVIDENCE_COUNTED = {"A-01-01": 9, "A-01-02": 3, "A-02-02": 7,
                        "A-03-01": 5, "B-01-02": 6, "B-02-02": 11}
SAM_SESSION_EVIDENCE_SESSION_ID = "VERIFY-SAM-SESSION-EVIDENCE-1"
SAM_SESSION_EVIDENCE_COUNTED = {"A-01-01": 9, "A-01-02": 3, "A-02-02": 7,
                                "A-03-01": 5, "B-01-02": 6, "B-02-02": 11}
SAM_PHOTO_EVIDENCE_SESSION_ID = "VERIFY-SAM-PHOTO-EVIDENCE-1"
SAM_PHOTO_EVIDENCE_COUNTED = {"A-01-01": 9, "A-01-02": 3, "A-02-02": 7,
                              "A-03-01": 5, "B-01-02": 6, "B-02-02": 11}
VIDEO_SELECTION_PENDING_DATE = "2026-11-01"
VIDEO_SELECTION_DUE_DATE = "2026-11-02"
VIDEO_SELECTION_READY_DATE = "2026-11-03"
VIDEO_SELECTION_PRIMARY_SIZE = 1000000
VIDEO_SELECTION_FALLBACK_SIZE = 1050000
PI_SMOKE_BIN_ID = "A-01-02"
PI_SMOKE_FAKE_COUNT = 5
PI_SMOKE_BOOK_QTY = 8
PI_SMOKE_FAKE_CONTENT = b"fake-pi-smoke-jpeg"
PI_SMOKE_FAKE_SHA = "f" * 64
PI_SMOKE_SENTINEL = "sentinel-pi-smoke-not-real"
PI_FULL_SESSION_ID = "VERIFY-PI-FULL-1"
PI_FULL_FAKE_CONTENT = b"fake-pi-full-session-jpeg"
PI_FULL_FAKE_SHA = "f" * 64
PI_FULL_SENTINEL = "sentinel-pi-full-not-real"
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
RUNBOOK_FALLBACK_MARKERS = ("2026-11-02",
                            "python3 -m qa.fallback_decision",
                            "python3 -m qa.video_selection",
                            "demo/assets/argus-demo-fallback-draft.mp4",
                            "파일 입력 폴백은 Pi 실촬영이 아니며")
DEVPOST_REL = "docs/devpost-submission.md"
DEVPOST_SECTIONS = ("## 프로젝트 이름", "## 한 줄 소개", "## 소개",
                    "## 동작 방식", "## Meta AI 도구 활용", "## 기술 구성",
                    "## 데모 데이터", "## 해커톤 기간 중 신규 제작",
                    "## 데모 영상", "## 현재 블로커와 제출 상태",
                    "## 제출 전 교체할 항목")
DEVPOST_DEMO_MARKERS = ("데모 기준: 빈 6개 중 일치 4건, 불일치 2건",
                        "데모 기준: 절대 차이 6개, 순차이 0, 일치율 66.7%",
                        "실제 창고 성과가 아니다")
DEVPOST_HONESTY_MARKERS = ("모의 어댑터가 동작 중이지만 SAM 3.1 실호출은 전체 세션으로 검증했다(같은 가상 사진 재사용, 빈별 정확도 아님)",
                           "빈별 실호출은 2026-10-31 커넥터 브리지로 통과했다(가상 사진의 서로 다른 잘라내기 6장, 실제 빈 촬영 아님)",
                           "파일 입력 경로 실호출은 2026-11-02 커넥터 브리지로 통과했다(가상 사진의 서로 다른 잘라내기 6장, 파일 기반 입력이며 Pi 실촬영 아님)",
                           "가짜 transport", "Secure Vault", "가안",
                           "컷 3은 Pi 실촬영 교체 예정인 플레이스홀더")
DEVPOST_FALLBACK_MARKERS = ("fallback_due", "2026-11-02",
                            "demo/assets/argus-demo-fallback-draft.mp4",
                            "폴백 렌더의 컷 3은 파일 입력 폴백 데이터",
                            "파일 입력 폴백은 Pi 실촬영이 아니며 검증 전")
DEVPOST_SELECTED_VIDEO = "demo/assets/argus-demo-fallback-draft.mp4"
DEVPOST_REPO_URL = "https://github.com/BoxLogoDev/argus-counts"
DEVPOST_DEADLINE_ET = "2026-11-04 21:00 ET"
DEVPOST_DEADLINE_KST = "2026-11-05 11:00 KST"
FALLBACK_CUT_INDEX = 3
FALLBACK_DECISION_DATE = "2026-11-02"
FALLBACK_SESSION_ID = "FALLBACK-FILE-INPUT"
FALLBACK_EXPECTED_SUMMARY = {"counted_bins": 6, "matched": 4,
                             "mismatched": 2, "abs_diff_total": 6,
                             "net_diff": 0}
FALLBACK_HONESTY_MARKERS = ("Pi 실촬영이 아닙니다", "Pi 실촬영 검증 전",
                            "이 폴백 실행에서는 SAM 실호출을 하지 않았다", "데모 기준")
ASSEMBLY_FALLBACK_ASSET = "demo/assets/fallback.json"
ASSEMBLY_FALLBACK_CUT_INDEX = 3
ASSEMBLY_FALLBACK_DECISION_DATE = "2026-11-02"
ASSEMBLY_FALLBACK_EXPECTED = {"asset": ASSEMBLY_FALLBACK_ASSET,
                              "cut_index": ASSEMBLY_FALLBACK_CUT_INDEX,
                              "decision_date": ASSEMBLY_FALLBACK_DECISION_DATE,
                              "is_pi_real_capture": False,
                              "capture_source": "file",
                              "replaces": "pi-placeholder"}
INVENTORY_TOTAL_FILES = 18
INVENTORY_REPO_URL = "https://github.com/BoxLogoDev/argus-counts"
FALLBACK_DECISION_DATE = "2026-11-02"
FALLBACK_DECISION_PENDING_DATE = "2026-10-30"
FALLBACK_DECISION_ASSET = "demo/assets/fallback.json"
FALLBACK_DECISION_RENDER = "demo/assets/argus-demo-fallback-draft.mp4"
FALLBACK_RENDER_REL = "demo/assets/argus-demo-fallback-draft.mp4"
DEADLINE_BEFORE_NOW = "2026-10-31T01:50:00+09:00"
DEADLINE_BEFORE_REMAINING = 465000
DEADLINE_DUE_SOON_NOW = "2026-11-04T12:00:00+09:00"
DEADLINE_OVERDUE_NOW = "2026-11-05T11:00:00+09:00"
FINAL_PACKAGE_NOW = "2026-10-31T04:50:00+09:00"
FINAL_PACKAGE_DATE = "2026-10-31"
FINAL_PACKAGE_REMAINING = 454200
FINAL_PACKAGE_TARGET = "2026-11-03"
FINAL_PACKAGE_DUE_DATE = "2026-11-02"
FINAL_PACKAGE_PRIMARY_VIDEO = "demo/assets/argus-demo-draft.mp4"
FINAL_PACKAGE_FALLBACK_VIDEO = "demo/assets/argus-demo-fallback-draft.mp4"
FALLBACK_RENDER_CUT_INDEX = 3
FALLBACK_RENDER_DECISION_DATE = "2026-11-02"


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
    # 조립 폴백 참조: 컷 3에만 파일 입력 폴백 후보가 있어야 한다(Pi 실촬영 아님).
    from demo.assemble import (build_assembly, build_assembly_text,
                               build_fallback_ref, validate_assembly)

    if build_fallback_ref() != ASSEMBLY_FALLBACK_EXPECTED:
        problems.append(
            f"build_fallback_ref 기대 {ASSEMBLY_FALLBACK_EXPECTED}, "
            f"실제 {build_fallback_ref()}")
    segments = assembly.get("segments", [])
    cut3_segments = [s for s in segments if s.get("index") == ASSEMBLY_FALLBACK_CUT_INDEX]
    assembly_fallback = cut3_segments[0].get("fallback") if cut3_segments else None
    if assembly_fallback != ASSEMBLY_FALLBACK_EXPECTED:
        problems.append(
            f"assembly 컷 3 fallback 기대 {ASSEMBLY_FALLBACK_EXPECTED}, "
            f"실제 {assembly_fallback}")
    other_fallback = [s.get("index") for s in segments
                      if s.get("index") != ASSEMBLY_FALLBACK_CUT_INDEX
                      and "fallback" in s]
    if other_fallback:
        problems.append(f"컷 3 외 fallback 참조가 있는 컷 {other_fallback}")
    built_assembly = build_assembly()
    built_problems = validate_assembly(built_assembly)
    if built_problems:
        problems.append(f"build_assembly validate_assembly 문제: {built_problems}")
    tampered_assembly = copy.deepcopy(built_assembly)
    tampered_assembly["segments"][2]["fallback"]["is_pi_real_capture"] = True
    assembly_fallback_tamper_detected = any(
        "fallback" in p for p in validate_assembly(tampered_assembly))
    if not assembly_fallback_tamper_detected:
        problems.append("컷 3 fallback is_pi_real_capture 변조를 탐지하지 못했다")
    missing_assembly = copy.deepcopy(built_assembly)
    del missing_assembly["segments"][2]["fallback"]
    assembly_fallback_missing_detected = any(
        "fallback" in p for p in validate_assembly(missing_assembly))
    if not assembly_fallback_missing_detected:
        problems.append("컷 3 fallback 누락을 탐지하지 못했다")
    assembly_text = build_assembly_text(built_assembly)
    if f"fallback: {ASSEMBLY_FALLBACK_ASSET}" not in assembly_text:
        problems.append("조립 텍스트에 fallback 자산 표기가 없다")
    if "Pi 실촬영 아님" not in assembly_text:
        problems.append("조립 텍스트에 'Pi 실촬영 아님' 표기가 없다")
    ctx.note(
        f"조립 폴백 참조 -> 컷 {ASSEMBLY_FALLBACK_CUT_INDEX} "
        f"fallback={assembly_fallback}, "
        f"변조 탐지 {assembly_fallback_tamper_detected}, "
        f"누락 탐지 {assembly_fallback_missing_detected}")
    probe["assembly_fallback"] = assembly_fallback
    assembly_fallback_payload = {
        "fallback": assembly_fallback,
        "expected": ASSEMBLY_FALLBACK_EXPECTED,
        "cut_index": ASSEMBLY_FALLBACK_CUT_INDEX,
        "decision_date": ASSEMBLY_FALLBACK_DECISION_DATE,
        "is_pi_real_capture": (assembly_fallback or {}).get("is_pi_real_capture"),
        "capture_source": (assembly_fallback or {}).get("capture_source"),
        "tamper_detected": assembly_fallback_tamper_detected,
        "missing_detected": assembly_fallback_missing_detected,
        "honesty": ["컷 3 폴백은 파일 입력이며 Pi 실촬영이 아닙니다",
                    "Pi 실촬영 아님"]}
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
    # 폴백 렌더 변형: 별도 MP4를 ffprobe로 탐침하고(렌더 아님) 컷 3 폴백 패널을 대조한다.
    fb_mp4 = ROOT / FALLBACK_RENDER_REL
    fb_probe: dict = {"path": FALLBACK_RENDER_REL,
                      "exists": fb_mp4.is_file(),
                      "size": fb_mp4.stat().st_size if fb_mp4.is_file() else 0}
    if not fb_mp4.is_file() or fb_probe["size"] <= 0:
        problems.append("폴백 MP4가 없거나 비어 있다")
    fb_duration = None
    if ffprobe is not None and fb_mp4.is_file():
        fb_result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(fb_mp4)], capture_output=True, text=True, timeout=60)
        try:
            fb_duration = float(fb_result.stdout.strip())
        except ValueError:
            fb_duration = -1.0
            problems.append(f"폴백 ffprobe duration 파싱 실패: {fb_result.stdout[:100]}")
        if not (179.0 <= fb_duration <= 181.0):
            problems.append(f"폴백 duration 기대 179~181초, 실제 {fb_duration}")
    fb_probe["duration"] = fb_duration
    ctx.note(f"폴백 ffprobe duration -> {fb_duration}")
    from demo.fallback import build_fallback_manifest

    fb_manifest = build_fallback_manifest()
    fb_panel = build_data_panel_lines(
        FALLBACK_RENDER_CUT_INDEX, report=report, fallback_manifest=fb_manifest)
    if len(fb_panel) != 4:
        problems.append(f"컷 3 폴백 패널 기대 4줄, 실제 {len(fb_panel)}줄")
    if fb_panel:
        if "파일 입력 폴백 — Pi 실촬영 아님" not in fb_panel[0] or FALLBACK_RENDER_DECISION_DATE not in fb_panel[0]:
            problems.append(f"컷 3 폴백 패널 1줄 표기 이상: {fb_panel[0]}")
        if "capture_source=file" not in fb_panel[1] or "source=mock" not in fb_panel[1]:
            problems.append(f"컷 3 폴백 패널 2줄 표기 이상: {fb_panel[1]}")
        if len(fb_panel) > 3:
            fb_target = next(b for b in fb_manifest["bins"] if b["bin_id"] == "A-01-02")
            fb_sha8 = str(fb_target["photo"]["sha256"])[:8]
            if "A-01-02" not in fb_panel[3] or fb_sha8 not in fb_panel[3]:
                problems.append(f"컷 3 폴백 패널 4줄에 A-01-02·sha256 앞 8자 없음: {fb_panel[3]}")
    fb_cut5 = build_data_panel_lines(5, report=report, fallback_manifest=fb_manifest)
    if len(fb_cut5) != 6:
        problems.append(f"폴백 매니페스트를 줘도 컷 5 패널은 6줄이어야 한다, 실제 {len(fb_cut5)}줄")
    fb_tampered = copy.deepcopy(fb_manifest)
    fb_tampered["is_pi_real_capture"] = True
    fallback_render_tamper_detected = False
    try:
        build_data_panel_lines(
            FALLBACK_RENDER_CUT_INDEX, report=report, fallback_manifest=fb_tampered)
    except ValueError:
        fallback_render_tamper_detected = True
    if not fallback_render_tamper_detected:
        problems.append("컷 3 폴백 is_pi_real_capture 변조를 탐지하지 못했다")
    ctx.note(
        f"폴백 렌더 -> exists {fb_probe['exists']}, size {fb_probe['size']}, "
        f"duration {fb_duration}, 패널 {len(fb_panel)}줄, 변조 탐지 {fallback_render_tamper_detected}")
    probe["fallback_render"] = fb_probe
    fallback_render_payload = {
        "path": FALLBACK_RENDER_REL, "exists": fb_probe["exists"],
        "size": fb_probe["size"], "duration": fb_duration,
        "panel": fb_panel, "panel_count": len(fb_panel),
        "cut_index": FALLBACK_RENDER_CUT_INDEX,
        "decision_date": FALLBACK_RENDER_DECISION_DATE,
        "capture_source": "file", "source": "mock",
        "is_pi_real_capture": False,
        "session_id": fb_manifest.get("session_id"),
        "tamper_detected": fallback_render_tamper_detected,
        "honesty": ["폴백 렌더는 파일 입력이며 Pi 실촬영이 아닙니다",
                    "Pi 실촬영 아님"]}
    summary = {"feature": "demo-video-draft", "probe": probe,
               "data_panel_cuts": data_panel_cuts,
               "assembly_fallback_cut_index": (assembly_fallback or {}).get("cut_index"),
               "assembly_fallback_capture_source": (assembly_fallback or {}).get("capture_source"),
               "assembly_fallback_is_pi_real_capture": (assembly_fallback or {}).get("is_pi_real_capture"),
               "assembly_fallback_decision_date": (assembly_fallback or {}).get("decision_date"),
               "assembly_fallback_tamper_detected": assembly_fallback_tamper_detected,
               "assembly_fallback_missing_detected": assembly_fallback_missing_detected,
               "fallback_render_exists": fb_probe["exists"],
               "fallback_render_size": fb_probe["size"],
               "fallback_render_duration": fb_duration,
               "fallback_render_panel_count": len(fb_panel),
               "fallback_render_tamper_detected": fallback_render_tamper_detected,
               "fallback_render_capture_source": "file",
               "fallback_render_is_pi_real_capture": False,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"video-probe.json": json.dumps(probe, ensure_ascii=False, indent=2) + "\n",
                    "data-panel.json": json.dumps(data_panel_payload, ensure_ascii=False, indent=2) + "\n",
                    "assembly-fallback.json": json.dumps(assembly_fallback_payload, ensure_ascii=False, indent=2) + "\n",
                    "fallback-render.json": json.dumps(fallback_render_payload, ensure_ascii=False, indent=2) + "\n"})
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
    for needle in ("PRE_SUBMISSION: 31/31 mechanical passed", "BLOCKERS: 1",
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
        if report.get("passed") != 31:
            problems.append(f"passed 기대 31, 실제 {report.get('passed')}")
        if report.get("total") != 31:
            problems.append(f"total 기대 31, 실제 {report.get('total')}")
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
        if len(checks) != 31:
            problems.append(f"checks 기대 31, 실제 {len(checks)}")
        check_names = [c.get("name") for c in checks]
        if "console_readiness_consistent" not in check_names:
            problems.append("checks에 console_readiness_consistent 없음")
        if "sam_smoke_consistent" not in check_names:
            problems.append("checks에 sam_smoke_consistent 없음")
        if "sam_session_consistent" not in check_names:
            problems.append("checks에 sam_session_consistent 없음")
        if "sam_photo_evidence_consistent" not in check_names:
            problems.append("checks에 sam_photo_evidence_consistent 없음")
        if "sam_per_bin_consistent" not in check_names:
            problems.append("checks에 sam_per_bin_consistent 없음")
        if "sam_live_evidence_consistent" not in check_names:
            problems.append("checks에 sam_live_evidence_consistent 없음")
        if "sam_session_evidence_consistent" not in check_names:
            problems.append("checks에 sam_session_evidence_consistent 없음")
        if "pi_smoke_consistent" not in check_names:
            problems.append("checks에 pi_smoke_consistent 없음")
        if "pi_session_consistent" not in check_names:
            problems.append("checks에 pi_session_consistent 없음")
        if "devpost_consistent" not in check_names:
            problems.append("checks에 devpost_consistent 없음")
        if "runbook_consistent" not in check_names:
            problems.append("checks에 runbook_consistent 없음")
        if "story_consistent" not in check_names:
            problems.append("checks에 story_consistent 없음")
        if "en_summary_consistent" not in check_names:
            problems.append("checks에 en_summary_consistent 없음")
        if "demo_script_consistent" not in check_names:
            problems.append("checks에 demo_script_consistent 없음")
        if "readme_consistent" not in check_names:
            problems.append("checks에 readme_consistent 없음")
        if "fallback_consistent" not in check_names:
            problems.append("checks에 fallback_consistent 없음")
        if "submission_inventory_consistent" not in check_names:
            problems.append("checks에 submission_inventory_consistent 없음")
        if "fallback_decision_consistent" not in check_names:
            problems.append("checks에 fallback_decision_consistent 없음")
        if "video_selection_consistent" not in check_names:
            problems.append("checks에 video_selection_consistent 없음")
        if "deadline_consistent" not in check_names:
            problems.append("checks에 deadline_consistent 없음")
        if "final_package_consistent" not in check_names:
            problems.append("checks에 final_package_consistent 없음")
        if "package_export_consistent" not in check_names:
            problems.append("checks에 package_export_consistent 없음")
        if "package_archive_consistent" not in check_names:
            problems.append("checks에 package_archive_consistent 없음")
        video_check = next((c for c in checks if c.get("name") == "video_draft_present"), {})
        video_fallback_cut = 3 if "fallback_render_cut=3" in str(video_check.get("detail") or "") else None
        if video_fallback_cut != 3:
            problems.append(
                f"video_draft_present detail에 fallback_render_cut=3 없음: {video_check.get('detail')}")
        demo_check = next((c for c in checks if c.get("name") == "demo_assets_consistent"), {})
        demo_fallback_cut = 3 if "assembly_fallback_cut=3" in str(demo_check.get("detail") or "") else None
        if demo_fallback_cut != 3:
            problems.append(
                f"demo_assets_consistent detail에 assembly_fallback_cut=3 없음: {demo_check.get('detail')}")
        else:
            demo_fallback_cut = 3
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
        smoke_r = readiness.get("smoke") or {}
        smoke_status = smoke_r.get("status")
        smoke_rb = [b["id"] for b in smoke_r.get("blockers", [])]
        if smoke_status != "blocked":
            problems.append(f"readiness smoke status 기대 blocked, 실제 {smoke_status}")
        if smoke_r.get("attempted") is not False:
            problems.append(
                f"readiness smoke attempted 기대 False, 실제 {smoke_r.get('attempted')}")
        if smoke_rb != sam_rb:
            problems.append(
                f"readiness smoke blockers가 sam 블로커와 다르다: {smoke_rb}")
        session_r = readiness.get("sam_session") or {}
        session_status = session_r.get("status")
        session_rb = [b["id"] for b in session_r.get("blockers", [])]
        if session_status != "blocked":
            problems.append(f"readiness sam_session status 기대 blocked, 실제 {session_status}")
        if session_r.get("attempted") is not False:
            problems.append(
                f"readiness sam_session attempted 기대 False, 실제 {session_r.get('attempted')}")
        if session_rb != sam_rb:
            problems.append(
                f"readiness sam_session blockers가 sam 블로커와 다르다: {session_rb}")
        if session_r.get("source") is not None:
            problems.append(f"readiness sam_session source 기대 None, 실제 {session_r.get('source')}")
        if session_r.get("summary") is not None:
            problems.append(f"readiness sam_session summary 기대 None, 실제 {session_r.get('summary')}")
        perbin_r = readiness.get("sam_per_bin") or {}
        perbin_status = perbin_r.get("status")
        perbin_rb = [b["id"] for b in perbin_r.get("blockers", [])]
        perbin_distinct = perbin_r.get("distinct_image_count")
        perbin_attempted = perbin_r.get("attempted")
        perbin_source = perbin_r.get("source")
        perbin_summary = perbin_r.get("summary")
        perbin_error_type = perbin_r.get("error_type")
        _perbin_bins = perbin_r.get("bins")
        perbin_bins_count = len(_perbin_bins) if isinstance(_perbin_bins, list) else None
        perbin_ready = perbin_r.get("ready_for_live_call")
        perbin_session_id = perbin_r.get("session_id")
        if perbin_status != "blocked":
            problems.append(f"readiness sam_per_bin status 기대 blocked, 실제 {perbin_status}")
        if perbin_r.get("attempted") is not False:
            problems.append(
                f"readiness sam_per_bin attempted 기대 False, 실제 {perbin_r.get('attempted')}")
        if perbin_attempted != session_r.get("attempted"):
            problems.append(
                f"readiness sam_per_bin attempted가 sam_session attempted와 다르다: {perbin_attempted} != {session_r.get('attempted')}")
        if perbin_attempted != smoke_r.get("attempted"):
            problems.append(
                f"readiness sam_per_bin attempted가 sam_smoke attempted와 다르다: {perbin_attempted} != {smoke_r.get('attempted')}")
        if perbin_rb != sam_rb:
            problems.append(
                f"readiness sam_per_bin blockers가 sam 블로커와 다르다: {perbin_rb}")
        if perbin_r.get("source") is not None:
            problems.append(f"readiness sam_per_bin source 기대 None, 실제 {perbin_r.get('source')}")
        if perbin_source != session_r.get("source"):
            problems.append(
                f"readiness sam_per_bin source가 sam_session source와 다르다: {perbin_source} != {session_r.get('source')}")
        if perbin_r.get("summary") is not None:
            problems.append(f"readiness sam_per_bin summary 기대 None, 실제 {perbin_r.get('summary')}")
        if perbin_summary != session_r.get("summary"):
            problems.append(
                f"readiness sam_per_bin summary가 sam_session summary와 다르다: {perbin_summary} != {session_r.get('summary')}")
        if perbin_distinct != 0:
            problems.append(
                f"readiness sam_per_bin distinct_image_count 기대 0, 실제 {perbin_distinct}")
        if perbin_error_type is not None:
            problems.append(f"readiness sam_per_bin error_type 기대 None, 실제 {perbin_error_type}")
        if perbin_bins_count != 0:
            problems.append(
                f"readiness sam_per_bin bins 개수 기대 0, 실제 {perbin_bins_count}")
        if perbin_bins_count != perbin_distinct:
            problems.append(
                f"readiness sam_per_bin bins 개수가 distinct_image_count와 다르다: {perbin_bins_count} != {perbin_distinct}")
        if perbin_ready is not False:
            problems.append(
                f"readiness sam_per_bin ready_for_live_call 기대 False, 실제 {perbin_ready}")
        if perbin_ready != sam_r.get("ready_for_live_call"):
            problems.append(
                f"readiness sam_per_bin ready_for_live_call가 sam ready와 다르다: {perbin_ready} != {sam_r.get('ready_for_live_call')}")
        if perbin_session_id != "PRE-SUBMISSION-SAM-PERBIN":
            problems.append(
                f"readiness sam_per_bin session_id 기대 PRE-SUBMISSION-SAM-PERBIN, 실제 {perbin_session_id}")
        sle_r = readiness.get("sam_live_evidence") or {}
        sle_valid = sle_r.get("valid")
        sle_source = sle_r.get("source")
        sle_distinct = sle_r.get("distinct_image_count")
        sle_session = sle_r.get("session_id")
        sle_tamper = sle_r.get("tamper_detected")
        sle_ready = sle_r.get("submission_ready")
        _sle_summary = sle_r.get("summary") or {}
        if sle_valid is not True:
            problems.append(f"readiness sam_live_evidence valid 기대 True, 실제 {sle_valid}")
        if sle_source != "sam":
            problems.append(f"readiness sam_live_evidence source 기대 sam, 실제 {sle_source}")
        if sle_distinct != 6:
            problems.append(f"readiness sam_live_evidence distinct 기대 6, 실제 {sle_distinct}")
        if sle_session != "PRE-SUBMISSION-SAM-EVIDENCE":
            problems.append(f"readiness sam_live_evidence session 기대 PRE-SUBMISSION-SAM-EVIDENCE, 실제 {sle_session}")
        if sle_tamper is not True:
            problems.append(f"readiness sam_live_evidence tamper_detected 기대 True, 실제 {sle_tamper}")
        if sle_ready is not False:
            problems.append(f"readiness sam_live_evidence submission_ready 기대 False, 실제 {sle_ready}")
        if _sle_summary.get("matched") != 1 or _sle_summary.get("mismatched") != 5 or _sle_summary.get("abs_diff_total") != 30 or _sle_summary.get("net_diff") != -28:
            problems.append(f"readiness sam_live_evidence summary 기대 matched1/mismatched5/abs30/net-28, 실제 {_sle_summary}")
        sse_r = readiness.get("sam_session_evidence") or {}
        sse_valid = sse_r.get("valid")
        sse_source = sse_r.get("source")
        sse_distinct = sse_r.get("distinct_image_count")
        sse_session = sse_r.get("session_id")
        sse_tamper = sse_r.get("tamper_detected")
        sse_ready = sse_r.get("submission_ready")
        _sse_summary = sse_r.get("summary") or {}
        if sse_valid is not True:
            problems.append(f"readiness sam_session_evidence valid 기대 True, 실제 {sse_valid}")
        if sse_source != "sam":
            problems.append(f"readiness sam_session_evidence source 기대 sam, 실제 {sse_source}")
        if sse_distinct != 6:
            problems.append(f"readiness sam_session_evidence distinct 기대 6, 실제 {sse_distinct}")
        if sse_session != "PRE-SUBMISSION-SAM-SESSION-EVIDENCE":
            problems.append(f"readiness sam_session_evidence session 기대 PRE-SUBMISSION-SAM-SESSION-EVIDENCE, 실제 {sse_session}")
        if sse_tamper is not True:
            problems.append(f"readiness sam_session_evidence tamper_detected 기대 True, 실제 {sse_tamper}")
        if sse_ready is not False:
            problems.append(f"readiness sam_session_evidence submission_ready 기대 False, 실제 {sse_ready}")
        if _sse_summary.get("matched") != 1 or _sse_summary.get("mismatched") != 5 or _sse_summary.get("abs_diff_total") != 30 or _sse_summary.get("net_diff") != -28:
            problems.append(f"readiness sam_session_evidence summary 기대 matched1/mismatched5/abs30/net-28, 실제 {_sse_summary}")
        spe_r = readiness.get("sam_photo_evidence") or {}
        spe_valid = spe_r.get("valid")
        spe_source = spe_r.get("source")
        spe_capture = spe_r.get("capture_source")
        spe_distinct = spe_r.get("distinct_image_count")
        spe_session = spe_r.get("session_id")
        spe_tamper = spe_r.get("tamper_detected")
        spe_ready = spe_r.get("submission_ready")
        _spe_summary = spe_r.get("summary") or {}
        if spe_valid is not True:
            problems.append(f"readiness sam_photo_evidence valid 기대 True, 실제 {spe_valid}")
        if spe_source != "sam":
            problems.append(f"readiness sam_photo_evidence source 기대 sam, 실제 {spe_source}")
        if spe_capture != "file":
            problems.append(f"readiness sam_photo_evidence capture_source 기대 file, 실제 {spe_capture}")
        if spe_distinct != 6:
            problems.append(f"readiness sam_photo_evidence distinct 기대 6, 실제 {spe_distinct}")
        if spe_session != "PRE-SUBMISSION-SAM-PHOTO-EVIDENCE":
            problems.append(f"readiness sam_photo_evidence session 기대 PRE-SUBMISSION-SAM-PHOTO-EVIDENCE, 실제 {spe_session}")
        if spe_tamper is not True:
            problems.append(f"readiness sam_photo_evidence tamper_detected 기대 True, 실제 {spe_tamper}")
        if spe_ready is not False:
            problems.append(f"readiness sam_photo_evidence submission_ready 기대 False, 실제 {spe_ready}")
        if _spe_summary.get("matched") != 1 or _spe_summary.get("mismatched") != 5 or _spe_summary.get("abs_diff_total") != 30 or _spe_summary.get("net_diff") != -28:
            problems.append(f"readiness sam_photo_evidence summary 기대 matched1/mismatched5/abs30/net-28, 실제 {_spe_summary}")
        pi_smoke_r = readiness.get("pi_smoke") or {}
        pi_smoke_status = pi_smoke_r.get("status")
        pi_smoke_rb = [b["id"] for b in pi_smoke_r.get("blockers", [])]
        if pi_smoke_status != "blocked":
            problems.append(f"readiness pi_smoke status 기대 blocked, 실제 {pi_smoke_status}")
        if pi_smoke_r.get("attempted") is not False:
            problems.append(
                f"readiness pi_smoke attempted 기대 False, 실제 {pi_smoke_r.get('attempted')}")
        if pi_smoke_rb != pi_rb:
            problems.append(
                f"readiness pi_smoke blockers가 pi 블로커와 다르다: {pi_smoke_rb}")
        pi_session_r = readiness.get("pi_session") or {}
        pi_session_status = pi_session_r.get("status")
        pi_session_rb = [b["id"] for b in pi_session_r.get("blockers", [])]
        if pi_session_status != "blocked":
            problems.append(f"readiness pi_session status 기대 blocked, 실제 {pi_session_status}")
        if pi_session_r.get("attempted") is not False:
            problems.append(
                f"readiness pi_session attempted 기대 False, 실제 {pi_session_r.get('attempted')}")
        if pi_session_rb != pi_rb:
            problems.append(
                f"readiness pi_session blockers가 pi 블로커와 다르다: {pi_session_rb}")
        if pi_session_r.get("source") is not None:
            problems.append(f"readiness pi_session source 기대 None, 실제 {pi_session_r.get('source')}")
        if pi_session_r.get("summary") is not None:
            problems.append(f"readiness pi_session summary 기대 None, 실제 {pi_session_r.get('summary')}")
        devpost_r = readiness.get("devpost") or {}
        devpost_sc = devpost_r.get("section_count")
        devpost_rb = devpost_r.get("blockers")
        devpost_fb = devpost_r.get("fallback_selected")
        devpost_sv = devpost_r.get("selected_video")
        if devpost_sc != 11:
            problems.append(f"readiness devpost section_count 기대 11, 실제 {devpost_sc}")
        if devpost_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"readiness devpost blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {devpost_rb}")
        if devpost_r.get("submission_ready") is not False:
            problems.append(
                f"readiness devpost submission_ready 기대 False, 실제 {devpost_r.get('submission_ready')}")
        if devpost_r.get("claims_audit_clean") is not True:
            problems.append("readiness devpost claims_audit_clean 기대 True")
        if devpost_r.get("fallback_selected") is not True:
            problems.append(
                f"readiness devpost fallback_selected 기대 True, 실제 {devpost_r.get('fallback_selected')}")
        if devpost_r.get("selected_video") != FALLBACK_DECISION_RENDER:
            problems.append(
                f"readiness devpost selected_video 기대 {FALLBACK_DECISION_RENDER}, 실제 {devpost_r.get('selected_video')}")
        runbook_r = readiness.get("runbook") or {}
        runbook_sc = runbook_r.get("section_count")
        runbook_rb = runbook_r.get("blockers")
        runbook_fc = runbook_r.get("final_command_count")
        if runbook_sc != 7:
            problems.append(f"readiness runbook section_count 기대 7, 실제 {runbook_sc}")
        if runbook_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"readiness runbook blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {runbook_rb}")
        if runbook_r.get("submission_ready") is not False:
            problems.append(
                f"readiness runbook submission_ready 기대 False, 실제 {runbook_r.get('submission_ready')}")
        if runbook_r.get("claims_audit_clean") is not True:
            problems.append("readiness runbook claims_audit_clean 기대 True")
        if runbook_fc != 8:
            problems.append(f"readiness runbook final_command_count 기대 8, 실제 {runbook_fc}")
        runbook_fb = runbook_r.get("fallback_branch_present")
        if runbook_fb is not True:
            problems.append(
                f"readiness runbook fallback_branch_present 기대 True, 실제 {runbook_fb}")
        story_r = readiness.get("story") or {}
        story_sc = story_r.get("section_count")
        story_rb = story_r.get("blockers")
        if story_sc != 7:
            problems.append(f"readiness story section_count 기대 7, 실제 {story_sc}")
        if story_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"readiness story blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {story_rb}")
        if story_r.get("submission_ready") is not False:
            problems.append(
                f"readiness story submission_ready 기대 False, 실제 {story_r.get('submission_ready')}")
        if story_r.get("claims_audit_clean") is not True:
            problems.append("readiness story claims_audit_clean 기대 True")
        en_r = readiness.get("en_summary") or {}
        en_sc = en_r.get("section_count")
        en_rb = en_r.get("blockers")
        if en_sc != 8:
            problems.append(f"readiness en_summary section_count 기대 8, 실제 {en_sc}")
        if en_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"readiness en_summary blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {en_rb}")
        if en_r.get("submission_ready") is not False:
            problems.append(
                f"readiness en_summary submission_ready 기대 False, 실제 {en_r.get('submission_ready')}")
        if en_r.get("claims_audit_clean") is not True:
            problems.append("readiness en_summary claims_audit_clean 기대 True")
        ds_r = readiness.get("demo_script") or {}
        ds_sc = ds_r.get("section_count")
        ds_rb = ds_r.get("blockers")
        if ds_sc != 3:
            problems.append(f"readiness demo_script section_count 기대 3, 실제 {ds_sc}")
        if ds_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"readiness demo_script blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {ds_rb}")
        if ds_r.get("submission_ready") is not False:
            problems.append(
                f"readiness demo_script submission_ready 기대 False, 실제 {ds_r.get('submission_ready')}")
        if ds_r.get("claims_audit_clean") is not True:
            problems.append("readiness demo_script claims_audit_clean 기대 True")
        rd_r = readiness.get("readme") or {}
        rd_sc = rd_r.get("section_count")
        rd_rb = rd_r.get("blockers")
        if rd_sc != 5:
            problems.append(f"readiness readme section_count 기대 5, 실제 {rd_sc}")
        if rd_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"readiness readme blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {rd_rb}")
        if rd_r.get("submission_ready") is not False:
            problems.append(
                f"readiness readme submission_ready 기대 False, 실제 {rd_r.get('submission_ready')}")
        if rd_r.get("claims_audit_clean") is not True:
            problems.append("readiness readme claims_audit_clean 기대 True")
        fb_r = readiness.get("fallback") or {}
        fb_cut = fb_r.get("cut_index")
        fb_source = fb_r.get("source")
        if fb_cut != 3:
            problems.append(f"readiness fallback cut_index 기대 3, 실제 {fb_cut}")
        if fb_r.get("capture_source") != "file":
            problems.append(f"readiness fallback capture_source 기대 file, 실제 {fb_r.get('capture_source')}")
        if fb_source != "mock":
            problems.append(f"readiness fallback source 기대 mock, 실제 {fb_source}")
        if fb_r.get("is_pi_real_capture") is not False:
            problems.append(f"readiness fallback is_pi_real_capture 기대 False, 실제 {fb_r.get('is_pi_real_capture')}")
        if fb_r.get("blockers") != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"readiness fallback blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {fb_r.get('blockers')}")
        if fb_r.get("submission_ready") is not False:
            problems.append(f"readiness fallback submission_ready 기대 False, 실제 {fb_r.get('submission_ready')}")
        fd_r = readiness.get("fallback_decision") or {}
        fd_status = fd_r.get("status")
        fd_pi_rb = fd_r.get("pi_blockers")
        fd_adopted = fd_r.get("fallback_adopted")
        fd_dd = fd_r.get("decision_date")
        if fd_pi_rb != pi_rb:
            problems.append(f"readiness fallback_decision pi_blockers가 pi 블로커와 다르다: {fd_pi_rb}")
        if fd_r.get("pi_ready") is not False:
            problems.append(f"readiness fallback_decision pi_ready 기대 False, 실제 {fd_r.get('pi_ready')}")
        if fd_r.get("is_pi_real_capture") is not False:
            problems.append(f"readiness fallback_decision is_pi_real_capture 기대 False, 실제 {fd_r.get('is_pi_real_capture')}")
        if fd_dd != "2026-11-02":
            problems.append(f"readiness fallback_decision decision_date 기대 2026-11-02, 실제 {fd_dd}")
        if (fd_status, fd_adopted) not in (("pending", False), ("fallback_due", True), ("pi_ready", False)):
            problems.append(f"readiness fallback_decision status/adopted 쌍이 어긋난다: {fd_status}/{fd_adopted}")
        if fd_r.get("fallback_asset") != "demo/assets/fallback.json":
            problems.append(f"readiness fallback_decision fallback_asset 기대 demo/assets/fallback.json, 실제 {fd_r.get('fallback_asset')}")
        vs_r = readiness.get("video_selection") or {}
        vs_status = vs_r.get("fallback_status")
        vs_selected = vs_r.get("selected_video")
        vs_reason = vs_r.get("selection_reason")
        vs_selected_size = vs_r.get("selected_size")
        vs_submission_ready = vs_r.get("submission_ready")
        if vs_status != fd_status:
            problems.append(f"readiness video_selection fallback_status가 fallback_decision status와 다르다: {vs_status} != {fd_status}")
        if vs_r.get("fallback_adopted") != fd_adopted:
            problems.append(f"readiness video_selection fallback_adopted가 fallback_decision과 다르다: {vs_r.get('fallback_adopted')} != {fd_adopted}")
        if vs_r.get("pi_blockers") != pi_rb:
            problems.append(f"readiness video_selection pi_blockers가 pi 블로커와 다르다: {vs_r.get('pi_blockers')}")
        if vs_r.get("pi_ready") is not False:
            problems.append(f"readiness video_selection pi_ready 기대 False, 실제 {vs_r.get('pi_ready')}")
        if vs_selected not in ("demo/assets/argus-demo-draft.mp4", "demo/assets/argus-demo-fallback-draft.mp4"):
            problems.append(f"readiness video_selection selected_video 기대 두 후보 중 하나, 실제 {vs_selected}")
        if (vs_status, vs_reason) not in (("pending", "pending_default"), ("fallback_due", "fallback_due"), ("pi_ready", "pi_ready")):
            problems.append(f"readiness video_selection status/reason 쌍이 어긋난다: {vs_status}/{vs_reason}")
        if not isinstance(vs_selected_size, int) or isinstance(vs_selected_size, bool) or vs_selected_size <= 0:
            problems.append(f"readiness video_selection selected_size 기대 양의 int, 실제 {vs_selected_size}")
        if vs_r.get("problems") != []:
            problems.append(f"readiness video_selection problems 기대 [], 실제 {vs_r.get('problems')}")
        if vs_submission_ready is not False:
            problems.append(f"readiness video_selection submission_ready 기대 False, 실제 {vs_submission_ready}")
        dl_r = readiness.get("deadline") or {}
        dl_status = dl_r.get("status")
        dl_rb = dl_r.get("blockers")
        dl_kst = dl_r.get("deadline_kst")
        dl_remaining = dl_r.get("remaining_seconds")
        if dl_status not in ("before_deadline", "due_soon", "overdue"):
            problems.append(f"readiness deadline status 기대 상태값 중 하나, 실제 {dl_status}")
        if dl_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"readiness deadline blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {dl_rb}")
        if dl_kst != "2026-11-05T11:00:00+09:00":
            problems.append(f"readiness deadline deadline_kst 기대 2026-11-05T11:00:00+09:00, 실제 {dl_kst}")
        if dl_r.get("submission_ready") is not False:
            problems.append(f"readiness deadline submission_ready 기대 False, 실제 {dl_r.get('submission_ready')}")
        if not isinstance(dl_remaining, int) or isinstance(dl_remaining, bool) or dl_remaining <= 0:
            problems.append(f"readiness deadline remaining_seconds 기대 양의 int, 실제 {dl_remaining}")
        fp_r = readiness.get("final_package") or {}
        fp_status = fp_r.get("status")
        fp_rb = fp_r.get("blockers")
        fp_inv_present = fp_r.get("inventory_present")
        fp_inv_total = fp_r.get("inventory_total")
        fp_deadline_status = fp_r.get("deadline_status")
        fp_remaining = fp_r.get("remaining_seconds")
        fp_fallback_status = fp_r.get("fallback_status")
        fp_submission_ready = fp_r.get("submission_ready")
        fp_export_copied = fp_r.get("export_copied")
        fp_export_total = fp_r.get("export_total")
        fp_export_missing = fp_r.get("export_missing")
        fp_export_total_bytes = fp_r.get("export_total_bytes")
        fp_export_verify_verified = fp_r.get("export_verify_verified")
        fp_export_verify_copied = fp_r.get("export_verify_copied_files")
        fp_export_verify_bytes = fp_r.get("export_verify_total_bytes")
        fp_selected_video = fp_r.get("selected_video")
        fp_selection_reason = fp_r.get("selection_reason")
        fp_selected_size = fp_r.get("selected_size")
        _inv_raw = readiness.get("submission_inventory") or {}
        if fp_inv_present != _inv_raw.get("present_files"):
            problems.append(f"readiness final_package inventory_present가 submission_inventory present_files와 다르다: {fp_inv_present} != {_inv_raw.get('present_files')}")
        if fp_inv_total != _inv_raw.get("total_files"):
            problems.append(f"readiness final_package inventory_total가 submission_inventory total_files와 다르다: {fp_inv_total} != {_inv_raw.get('total_files')}")
        if fp_status != "blocked":
            problems.append(f"readiness final_package status 기대 blocked, 실제 {fp_status}")
        if fp_r.get("inventory_present") != 18:
            problems.append(f"readiness final_package inventory_present 기대 18, 실제 {fp_r.get('inventory_present')}")
        if fp_r.get("inventory_total") != 18:
            problems.append(f"readiness final_package inventory_total 기대 18, 실제 {fp_r.get('inventory_total')}")
        if fp_r.get("deadline_status") != dl_status:
            problems.append(f"readiness final_package deadline_status가 deadline status와 다르다: {fp_r.get('deadline_status')} != {dl_status}")
        if not isinstance(fp_remaining, int) or isinstance(fp_remaining, bool) or fp_remaining <= 0:
            problems.append(f"readiness final_package remaining_seconds 기대 양의 int, 실제 {fp_remaining}")
        elif fp_remaining != dl_remaining:
            problems.append(f"readiness final_package remaining_seconds가 deadline remaining_seconds와 다르다: {fp_remaining} != {dl_remaining}")
        if fp_r.get("fallback_status") != fd_status:
            problems.append(f"readiness final_package fallback_status가 fallback_decision status와 다르다: {fp_r.get('fallback_status')} != {fd_status}")
        if fp_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"readiness final_package blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {fp_rb}")
        if fp_r.get("submission_ready") is not False:
            problems.append(f"readiness final_package submission_ready 기대 False, 실제 {fp_r.get('submission_ready')}")
        if fp_export_copied != 18:
            problems.append(f"readiness final_package export_copied 기대 18, 실제 {fp_export_copied}")
        if fp_export_copied != _inv_raw.get("present_files"):
            problems.append(f"readiness final_package export_copied가 submission_inventory present_files와 다르다: {fp_export_copied} != {_inv_raw.get('present_files')}")
        if fp_export_total != 18:
            problems.append(f"readiness final_package export_total 기대 18, 실제 {fp_export_total}")
        if fp_export_total != _inv_raw.get("total_files"):
            problems.append(f"readiness final_package export_total가 submission_inventory total_files와 다르다: {fp_export_total} != {_inv_raw.get('total_files')}")
        if fp_export_missing != []:
            problems.append(f"readiness final_package export_missing 기대 [], 실제 {fp_export_missing}")
        if fp_export_missing != _inv_raw.get("missing"):
            problems.append(f"readiness final_package export_missing가 submission_inventory missing와 다르다: {fp_export_missing} != {_inv_raw.get('missing')}")
        if not isinstance(fp_export_total_bytes, int) or isinstance(fp_export_total_bytes, bool) or fp_export_total_bytes <= 0:
            problems.append(f"readiness final_package export_total_bytes 기대 양의 int, 실제 {fp_export_total_bytes}")
        if fp_export_total_bytes != _inv_raw.get("total_bytes"):
            problems.append(f"readiness final_package export_total_bytes가 submission_inventory total_bytes와 다르다: {fp_export_total_bytes} != {_inv_raw.get('total_bytes')}")
        if fp_export_verify_verified is not True:
            problems.append(f"readiness final_package export_verify_verified 기대 True, 실제 {fp_export_verify_verified}")
        if fp_export_verify_copied != 18:
            problems.append(f"readiness final_package export_verify_copied_files 기대 18, 실제 {fp_export_verify_copied}")
        if fp_export_verify_copied != fp_export_copied:
            problems.append(f"readiness final_package export_verify_copied_files가 export_copied와 다르다: {fp_export_verify_copied} != {fp_export_copied}")
        if not isinstance(fp_export_verify_bytes, int) or isinstance(fp_export_verify_bytes, bool) or fp_export_verify_bytes <= 0:
            problems.append(f"readiness final_package export_verify_total_bytes 기대 양의 int, 실제 {fp_export_verify_bytes}")
        if fp_export_verify_bytes != fp_export_total_bytes:
            problems.append(f"readiness final_package export_verify_total_bytes가 export_total_bytes와 다르다: {fp_export_verify_bytes} != {fp_export_total_bytes}")
        if fp_selected_video not in ("demo/assets/argus-demo-draft.mp4", "demo/assets/argus-demo-fallback-draft.mp4"):
            problems.append(f"readiness final_package selected_video 기대 두 후보 중 하나, 실제 {fp_selected_video}")
        if fp_selected_video != vs_selected:
            problems.append(f"readiness final_package selected_video가 video_selection selected_video와 다르다: {fp_selected_video} != {vs_selected}")
        if fp_selection_reason != vs_reason:
            problems.append(f"readiness final_package selection_reason가 video_selection selection_reason과 다르다: {fp_selection_reason} != {vs_reason}")
        if not isinstance(fp_selected_size, int) or isinstance(fp_selected_size, bool) or fp_selected_size <= 0:
            problems.append(f"readiness final_package selected_size 기대 양의 int, 실제 {fp_selected_size}")
        if fp_selected_size != vs_selected_size:
            problems.append(f"readiness final_package selected_size가 video_selection selected_size와 다르다: {fp_selected_size} != {vs_selected_size}")
        if (fp_fallback_status, fp_selection_reason, fp_selected_video) not in (("pending", "pending_default", "demo/assets/argus-demo-draft.mp4"), ("fallback_due", "fallback_due", "demo/assets/argus-demo-fallback-draft.mp4"), ("pi_ready", "pi_ready", "demo/assets/argus-demo-draft.mp4")):
            problems.append(f"readiness final_package fallback_status/selection_reason/selected_video 쌍이 어긋난다: {fp_fallback_status}/{fp_selection_reason}/{fp_selected_video}")
        pkg_r = readiness.get("package_export") or {}
        pkg_total = pkg_r.get("total_files")
        pkg_copied = pkg_r.get("copied_files")
        pkg_rb = pkg_r.get("blockers")
        pkg_missing = pkg_r.get("missing")
        pkg_total_bytes = pkg_r.get("total_bytes")
        pkg_submission_ready = pkg_r.get("submission_ready")
        pkg_verify_verified = pkg_r.get("verify_verified")
        pkg_verify_copied = pkg_r.get("verify_copied_files")
        pkg_verify_bytes = pkg_r.get("verify_total_bytes")
        if pkg_total != 18:
            problems.append(f"readiness package_export total_files 기대 18, 실제 {pkg_total}")
        if pkg_copied != (_inv_raw.get("present_files")):
            problems.append(f"readiness package_export copied_files가 submission_inventory present_files와 다르다: {pkg_copied} != {_inv_raw.get('present_files')}")
        if pkg_missing != []:
            problems.append(f"readiness package_export missing 기대 [], 실제 {pkg_missing}")
        if pkg_missing != _inv_raw.get("missing"):
            problems.append(f"readiness package_export missing가 submission_inventory missing와 다르다: {pkg_missing} != {_inv_raw.get('missing')}")
        if pkg_total_bytes != _inv_raw.get("total_bytes"):
            problems.append(f"readiness package_export total_bytes가 submission_inventory total_bytes와 다르다: {pkg_total_bytes} != {_inv_raw.get('total_bytes')}")
        if pkg_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"readiness package_export blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {pkg_rb}")
        if pkg_submission_ready is not False:
            problems.append(f"readiness package_export submission_ready 기대 False, 실제 {pkg_submission_ready}")
        if pkg_verify_verified is not True:
            problems.append(f"readiness package_export verify_verified 기대 True, 실제 {pkg_verify_verified}")
        if isinstance(pkg_verify_copied, bool) or not isinstance(pkg_verify_copied, int):
            problems.append(f"readiness package_export verify_copied_files 기대 int, 실제 {pkg_verify_copied}")
        elif pkg_verify_copied != pkg_copied:
            problems.append(f"readiness package_export verify_copied_files가 copied_files와 다르다: {pkg_verify_copied} != {pkg_copied}")
        elif pkg_verify_copied != _inv_raw.get("present_files"):
            problems.append(f"readiness package_export verify_copied_files가 submission_inventory present_files와 다르다: {pkg_verify_copied} != {_inv_raw.get('present_files')}")
        if isinstance(pkg_verify_bytes, bool) or not isinstance(pkg_verify_bytes, int):
            problems.append(f"readiness package_export verify_total_bytes 기대 int, 실제 {pkg_verify_bytes}")
        elif pkg_verify_bytes != pkg_total_bytes:
            problems.append(f"readiness package_export verify_total_bytes가 total_bytes와 다르다: {pkg_verify_bytes} != {pkg_total_bytes}")
        elif pkg_verify_bytes != _inv_raw.get("total_bytes"):
            problems.append(f"readiness package_export verify_total_bytes가 submission_inventory total_bytes와 다르다: {pkg_verify_bytes} != {_inv_raw.get('total_bytes')}")
        if fp_export_missing != pkg_missing:
            problems.append(f"readiness final_package export_missing가 package_export missing와 다르다: {fp_export_missing} != {pkg_missing}")
        if fp_export_total_bytes != pkg_total_bytes:
            problems.append(f"readiness final_package export_total_bytes가 package_export total_bytes와 다르다: {fp_export_total_bytes} != {pkg_total_bytes}")
        if fp_export_verify_verified != pkg_verify_verified:
            problems.append(f"readiness final_package export_verify_verified가 package_export verify_verified와 다르다: {fp_export_verify_verified} != {pkg_verify_verified}")
        if fp_export_verify_copied != pkg_verify_copied:
            problems.append(f"readiness final_package export_verify_copied_files가 package_export verify_copied_files와 다르다: {fp_export_verify_copied} != {pkg_verify_copied}")
        if fp_export_verify_copied != pkg_copied:
            problems.append(f"readiness final_package export_verify_copied_files가 package_export copied_files와 다르다: {fp_export_verify_copied} != {pkg_copied}")
        if fp_export_verify_bytes != pkg_verify_bytes:
            problems.append(f"readiness final_package export_verify_total_bytes가 package_export verify_total_bytes와 다르다: {fp_export_verify_bytes} != {pkg_verify_bytes}")
        if fp_export_verify_bytes != pkg_total_bytes:
            problems.append(f"readiness final_package export_verify_total_bytes가 package_export total_bytes와 다르다: {fp_export_verify_bytes} != {pkg_total_bytes}")
        arch_r = readiness.get("package_archive") or {}
        arch_status = arch_r.get("status")
        arch_copied = arch_r.get("copied")
        arch_total = arch_r.get("total")
        arch_missing = arch_r.get("missing")
        arch_total_bytes = arch_r.get("total_bytes")
        arch_verify_verified = arch_r.get("verify_verified")
        arch_archive_verified = arch_r.get("archive_verified")
        arch_selected_video = arch_r.get("selected_video")
        arch_selected_size = arch_r.get("selected_size")
        arch_selected_sha256 = arch_r.get("selected_sha256")
        arch_rb = arch_r.get("blockers")
        arch_submission_ready = arch_r.get("submission_ready")
        if arch_status != "archived":
            problems.append(f"readiness package_archive status 기대 archived, 실제 {arch_status}")
        if arch_copied != 18:
            problems.append(f"readiness package_archive copied 기대 18, 실제 {arch_copied}")
        if arch_total != 18:
            problems.append(f"readiness package_archive total 기대 18, 실제 {arch_total}")
        if arch_missing != []:
            problems.append(f"readiness package_archive missing 기대 [], 실제 {arch_missing}")
        if arch_total_bytes != pkg_total_bytes:
            problems.append(f"readiness package_archive total_bytes가 package_export total_bytes와 다르다: {arch_total_bytes} != {pkg_total_bytes}")
        if arch_verify_verified is not True:
            problems.append(f"readiness package_archive verify_verified 기대 True, 실제 {arch_verify_verified}")
        if arch_archive_verified is not True:
            problems.append(f"readiness package_archive archive_verified 기대 True, 실제 {arch_archive_verified}")
        if arch_selected_video != fp_selected_video:
            problems.append(f"readiness package_archive selected_video가 final_package selected_video와 다르다: {arch_selected_video} != {fp_selected_video}")
        if arch_selected_size != fp_selected_size:
            problems.append(f"readiness package_archive selected_size가 final_package selected_size와 다르다: {arch_selected_size} != {fp_selected_size}")
        if not (isinstance(arch_selected_sha256, str) and len(arch_selected_sha256) == 64 and all(c in "0123456789abcdef" for c in arch_selected_sha256)):
            problems.append(f"readiness package_archive selected_sha256 기대 64자 hex, 실제 {arch_selected_sha256}")
        if arch_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"readiness package_archive blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {arch_rb}")
        if arch_submission_ready is not False:
            problems.append(f"readiness package_archive submission_ready 기대 False, 실제 {arch_submission_ready}")
        inv_r = readiness.get("submission_inventory") or {}
        inv_total = inv_r.get("total_files")
        inv_present = inv_r.get("present_files")
        inv_rb = inv_r.get("blockers")
        if inv_total != 18:
            problems.append(f"readiness submission_inventory total_files 기대 18, 실제 {inv_total}")
        if inv_present != 18:
            problems.append(f"readiness submission_inventory present_files 기대 18, 실제 {inv_present}")
        if inv_r.get("missing") != []:
            problems.append(f"readiness submission_inventory missing 기대 [], 실제 {inv_r.get('missing')}")
        if inv_rb != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"readiness submission_inventory blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {inv_rb}")
        if inv_r.get("submission_ready") is not False:
            problems.append(f"readiness submission_inventory submission_ready 기대 False, 실제 {inv_r.get('submission_ready')}")
    else:
        sam_rb, pi_rb = [], []
        console_bc, console_overall = None, None
        smoke_status, smoke_rb = None, []
        session_status, session_rb = None, []
        perbin_status, perbin_rb, perbin_distinct = None, [], None
        perbin_attempted, perbin_source, perbin_summary = None, None, None
        perbin_error_type, perbin_bins_count = None, None
        perbin_ready, perbin_session_id = None, None
        sle_valid, sle_source, sle_distinct = None, None, None
        sle_session, sle_tamper, sle_ready = None, None, None
        sse_valid, sse_source, sse_distinct = None, None, None
        sse_session, sse_tamper, sse_ready = None, None, None
        spe_valid, spe_source, spe_capture, spe_distinct = None, None, None, None
        spe_session, spe_tamper, spe_ready = None, None, None
        pi_smoke_status, pi_smoke_rb = None, []
        pi_session_status, pi_session_rb = None, []
        devpost_sc, devpost_rb = None, []
        devpost_fb, devpost_sv = None, None
        runbook_sc, runbook_rb, runbook_fc = None, [], None
        story_sc, story_rb = None, []
        en_sc, en_rb = None, []
        ds_sc, ds_rb = None, []
        rd_sc, rd_rb = None, []
        fb_cut, fb_source = None, None
        inv_total, inv_present, inv_rb = None, None, []
        fd_status, fd_pi_rb, fd_adopted, fd_dd = None, [], None, None
        vs_status, vs_selected, vs_reason = None, None, None
        vs_selected_size, vs_submission_ready = None, None
        dl_status, dl_rb, dl_kst = None, [], None
        dl_remaining = None
        fp_status, fp_rb = None, []
        fp_inv_present, fp_inv_total = None, None
        fp_deadline_status, fp_fallback_status = None, None
        fp_remaining = None
        fp_submission_ready = None
        fp_export_copied, fp_export_total = None, None
        fp_export_missing, fp_export_total_bytes = None, None
        fp_export_verify_verified, fp_export_verify_copied = None, None
        fp_export_verify_bytes = None
        fp_selected_video, fp_selection_reason, fp_selected_size = None, None, None
        pkg_total, pkg_copied, pkg_rb = None, None, []
        pkg_missing, pkg_total_bytes, pkg_submission_ready = None, None, None
        pkg_verify_verified, pkg_verify_copied, pkg_verify_bytes = None, None, None
        arch_status, arch_copied, arch_total = None, None, None
        arch_missing, arch_total_bytes = None, None
        arch_verify_verified, arch_archive_verified = None, None
        arch_selected_video, arch_selected_size = None, None
        arch_selected_sha256 = None
        arch_rb, arch_submission_ready = [], None
        demo_fallback_cut = None
        video_fallback_cut = None
    summary = {"feature": "pre-submission",
               "mechanical_pass": report.get("mechanical_pass"),
               "passed": report.get("passed"), "total": report.get("total"),
               "blockers": blocker_ids,
               "readiness_sam_blockers": sam_rb,
               "readiness_pi_blockers": pi_rb,
               "readiness_console_blocker_count": console_bc,
               "readiness_console_overall_ready": console_overall,
               "readiness_smoke_status": smoke_status,
               "readiness_smoke_blockers": smoke_rb,
               "readiness_sam_session_status": session_status,
               "readiness_sam_session_blockers": session_rb,
               "readiness_sam_per_bin_status": perbin_status,
               "readiness_sam_per_bin_blockers": perbin_rb,
               "readiness_sam_per_bin_distinct_image_count": perbin_distinct,
               "readiness_sam_per_bin_attempted": perbin_attempted,
               "readiness_sam_per_bin_source": perbin_source,
               "readiness_sam_per_bin_summary": perbin_summary,
               "readiness_sam_per_bin_error_type": perbin_error_type,
               "readiness_sam_per_bin_bins_count": perbin_bins_count,
               "readiness_sam_per_bin_ready_for_live_call": perbin_ready,
               "readiness_sam_per_bin_session_id": perbin_session_id,
               "readiness_sam_live_evidence_valid": sle_valid,
               "readiness_sam_live_evidence_source": sle_source,
               "readiness_sam_live_evidence_distinct_image_count": sle_distinct,
               "readiness_sam_live_evidence_session_id": sle_session,
               "readiness_sam_live_evidence_tamper_detected": sle_tamper,
               "readiness_sam_live_evidence_submission_ready": sle_ready,
               "readiness_sam_session_evidence_valid": sse_valid,
               "readiness_sam_session_evidence_source": sse_source,
               "readiness_sam_session_evidence_distinct_image_count": sse_distinct,
               "readiness_sam_session_evidence_session_id": sse_session,
               "readiness_sam_session_evidence_tamper_detected": sse_tamper,
               "readiness_sam_session_evidence_submission_ready": sse_ready,
               "readiness_sam_photo_evidence_valid": spe_valid,
               "readiness_sam_photo_evidence_source": spe_source,
               "readiness_sam_photo_evidence_capture_source": spe_capture,
               "readiness_sam_photo_evidence_distinct_image_count": spe_distinct,
               "readiness_sam_photo_evidence_session_id": spe_session,
               "readiness_sam_photo_evidence_tamper_detected": spe_tamper,
               "readiness_sam_photo_evidence_submission_ready": spe_ready,
               "readiness_pi_smoke_status": pi_smoke_status,
               "readiness_pi_smoke_blockers": pi_smoke_rb,
               "readiness_pi_session_status": pi_session_status,
               "readiness_pi_session_blockers": pi_session_rb,
               "readiness_devpost_section_count": devpost_sc,
               "readiness_devpost_blockers": devpost_rb,
               "readiness_devpost_fallback_selected": devpost_fb,
               "readiness_devpost_selected_video": devpost_sv,
               "readiness_runbook_section_count": runbook_sc,
               "readiness_runbook_blockers": runbook_rb,
               "readiness_runbook_final_command_count": runbook_fc,
               "readiness_runbook_fallback_branch_present": runbook_fb,
               "readiness_story_section_count": story_sc,
               "readiness_story_blockers": story_rb,
               "readiness_en_summary_section_count": en_sc,
               "readiness_en_summary_blockers": en_rb,
               "readiness_demo_script_section_count": ds_sc,
               "readiness_demo_script_blockers": ds_rb,
               "readiness_readme_section_count": rd_sc,
               "readiness_readme_blockers": rd_rb,
               "readiness_fallback_cut_index": fb_cut,
               "readiness_inventory_total_files": inv_total,
               "readiness_inventory_present_files": inv_present,
               "readiness_inventory_blockers": inv_rb,
               "readiness_fallback_source": fb_source,
               "readiness_fallback_decision_status": fd_status,
               "readiness_fallback_decision_pi_blockers": fd_pi_rb,
               "readiness_fallback_decision_adopted": fd_adopted,
               "readiness_fallback_decision_date": fd_dd,
               "readiness_final_package_status": fp_status,
               "readiness_final_package_blockers": fp_rb,
               "readiness_final_package_inventory_present": fp_inv_present,
               "readiness_final_package_inventory_total": fp_inv_total,
               "readiness_final_package_deadline_status": fp_deadline_status,
               "readiness_final_package_remaining_seconds": fp_remaining,
               "readiness_final_package_fallback_status": fp_fallback_status,
               "readiness_final_package_submission_ready": fp_submission_ready,
               "readiness_final_package_export_copied": fp_export_copied,
               "readiness_final_package_export_total": fp_export_total,
               "readiness_final_package_export_missing": fp_export_missing,
               "readiness_final_package_export_total_bytes": fp_export_total_bytes,
               "readiness_final_package_export_verify_verified": fp_export_verify_verified,
               "readiness_final_package_export_verify_copied_files": fp_export_verify_copied,
               "readiness_final_package_export_verify_total_bytes": fp_export_verify_bytes,
               "readiness_final_package_selected_video": fp_selected_video,
               "readiness_final_package_selection_reason": fp_selection_reason,
               "readiness_final_package_selected_size": fp_selected_size,
               "readiness_package_export_total_files": pkg_total,
               "readiness_package_export_copied_files": pkg_copied,
               "readiness_package_export_blockers": pkg_rb,
               "readiness_package_export_missing": pkg_missing,
               "readiness_package_export_total_bytes": pkg_total_bytes,
               "readiness_package_export_submission_ready": pkg_submission_ready,
               "readiness_package_export_verify_verified": pkg_verify_verified,
               "readiness_package_export_verify_copied_files": pkg_verify_copied,
               "readiness_package_export_verify_total_bytes": pkg_verify_bytes,
               "readiness_package_archive_status": arch_status,
               "readiness_package_archive_copied": arch_copied,
               "readiness_package_archive_total": arch_total,
               "readiness_package_archive_missing": arch_missing,
               "readiness_package_archive_total_bytes": arch_total_bytes,
               "readiness_package_archive_verify_verified": arch_verify_verified,
               "readiness_package_archive_archive_verified": arch_archive_verified,
               "readiness_package_archive_selected_video": arch_selected_video,
               "readiness_package_archive_selected_size": arch_selected_size,
               "readiness_package_archive_selected_sha256": arch_selected_sha256,
               "readiness_package_archive_blockers": arch_rb,
               "readiness_package_archive_submission_ready": arch_submission_ready,
               "readiness_video_selection_status": vs_status,
               "readiness_video_selection_selected_video": vs_selected,
               "readiness_video_selection_reason": vs_reason,
               "readiness_video_selection_selected_size": vs_selected_size,
               "readiness_video_selection_submission_ready": vs_submission_ready,
               "readiness_deadline_status": dl_status,
               "readiness_deadline_blockers": dl_rb,
               "readiness_deadline_kst": dl_kst,
               "readiness_deadline_remaining_seconds": dl_remaining,
               "demo_assembly_fallback_cut": demo_fallback_cut,
               "video_fallback_render_cut": video_fallback_cut,
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
    body_content = []
    body_input = parsed_body.get("input")
    if isinstance(body_input, list) and body_input:
        body_content = body_input[0].get("content") or []
    body_text_part = next((c for c in body_content
                           if isinstance(c, dict) and c.get("type") == "input_text"),
                          {})
    body_image_part = next((c for c in body_content
                            if isinstance(c, dict) and c.get("type") == "input_image"),
                           {})
    if body_text_part.get("text") != "cardboard box":
        problems.append(
            f"body input_text 기대 cardboard box, 실제 {body_text_part.get('text')}")
    if body_image_part.get("image_url") != "photo-1.jpg":
        problems.append(
            f"body image_url 기대 photo-1.jpg, 실제 {body_image_part.get('image_url')}")
    if SAM_FAKE_KEY in body_text:
        problems.append("요청 body 원문에 API 키가 포함됐다")
    direct_payload = build_payload(SAM_BIN_ID, image_ref="photo-1.jpg")
    direct_content = (direct_payload.get("input") or [{}])[0].get("content") or []
    direct_image = next((c for c in direct_content
                         if isinstance(c, dict) and c.get("type") == "input_image"),
                        {})
    if direct_payload.get("model") != "sam-3.1" \
            or direct_image.get("image_url") != "photo-1.jpg":
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
                    "input_text": body_text_part.get("text"),
                    "image_url": body_image_part.get("image_url"),
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
    for needle in ("모의", "검증 전", "단일 빈 스모크"):
        if needle not in text:
            problems.append(f"런북 정직성 표기 {needle!r} 없음")
    for command in RUNBOOK_FINAL_COMMANDS:
        if command not in text:
            problems.append(f"런북 최종 점검 명령 {command!r} 없음")
    for needle in RUNBOOK_FALLBACK_MARKERS:
        if needle not in text:
            problems.append(f"런북 폴백 분기 표기 {needle!r} 없음")
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
    fallback_branch_present = bool(text) and all(
        marker in text for marker in RUNBOOK_FALLBACK_MARKERS)
    ctx.note(f"런북 폴백 분기 존재 -> {fallback_branch_present}")
    extracted = {"sections": list(RUNBOOK_SECTIONS),
                 "blockers": list(EXPECTED_BLOCKER_IDS),
                 "submission_ready": False,
                 "credit_check_at": RUNBOOK_CREDIT_AT,
                 "deadline_kst": RUNBOOK_DEADLINE_KST,
                 "final_check_commands": list(RUNBOOK_FINAL_COMMANDS),
                 "fallback_markers": list(RUNBOOK_FALLBACK_MARKERS),
                 "fallback_branch_present": fallback_branch_present}
    summary = {"feature": "submission-runbook",
               "sections": list(RUNBOOK_SECTIONS),
               "section_count": len(RUNBOOK_SECTIONS),
               "blockers": list(EXPECTED_BLOCKER_IDS),
               "submission_ready": False,
               "credit_check_at": RUNBOOK_CREDIT_AT,
               "deadline_kst": RUNBOOK_DEADLINE_KST,
               "final_check_command_count": len(RUNBOOK_FINAL_COMMANDS),
               "fallback_branch_present": fallback_branch_present,
               "fallback_decision_date": "2026-11-02",
               "claims_audit_clean": claims_audit_clean,
               "tamper_detected": tamper_detected,
               "pre_submission_blockers": pre_blockers,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"submission-runbook.json": json.dumps(
                       extracted, ensure_ascii=False, indent=2) + "\n",
                    "submission-runbook.md": text})
    return summary


def validate_devpost_text(text: str) -> list[str]:
    problems: list[str] = []
    positions = [text.find(section) for section in DEVPOST_SECTIONS]
    if any(position < 0 for position in positions):
        missing = [section for section, position
                   in zip(DEVPOST_SECTIONS, positions) if position < 0]
        problems.append(f"문안 절 누락 {missing}")
    elif positions != sorted(positions):
        problems.append(f"문안 절 순서 이상: 위치 {positions}")
    blocker_positions = [text.find(blocker_id)
                         for blocker_id in EXPECTED_BLOCKER_IDS]
    if any(position < 0 for position in blocker_positions) \
            or blocker_positions != sorted(blocker_positions):
        problems.append(
            f"문안 블로커 id 누락 또는 순서 이상: 위치 {blocker_positions}, "
            f"기대 {list(EXPECTED_BLOCKER_IDS)}")
    if "SUBMISSION_READY: false" not in text \
            or "SUBMISSION_READY: true" in text:
        problems.append(
            "SUBMISSION_READY 표기 이상: SUBMISSION_READY: false가 없거나 "
            "SUBMISSION_READY: true가 있다")
    for needle in DEVPOST_DEMO_MARKERS:
        if needle not in text:
            problems.append(f"문안 데모 수치 표기 {needle!r} 없음")
    for needle in DEVPOST_HONESTY_MARKERS:
        if needle not in text:
            problems.append(f"문안 정직성 표기 {needle!r} 없음")
    for needle in DEVPOST_FALLBACK_MARKERS:
        if needle not in text:
            problems.append(f"문안 폴백 표기 {needle!r} 없음")
    for needle in (DEVPOST_REPO_URL, DEVPOST_DEADLINE_ET, DEVPOST_DEADLINE_KST):
        if needle not in text:
            problems.append(f"문안에 {needle!r} 없음")
    from qa.claims_audit import audit_text

    audit_problems = audit_text(DEVPOST_REL, text)
    if audit_problems:
        problems.append(f"문안 주장 감사 문제 {audit_problems}")
    return problems


def drive_devpost_submission(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    devpost_path = ROOT / DEVPOST_REL
    if devpost_path.is_file():
        text = devpost_path.read_text(encoding="utf-8")
        problems = validate_devpost_text(text)
    else:
        text = ""
        problems.append(f"제출 문안 파일이 없다: {DEVPOST_REL}")
    ctx.note(f"제출 문안 읽기 -> {DEVPOST_REL}, {len(text)}자")
    tampered = text.replace("SUBMISSION_READY: false",
                            "SUBMISSION_READY: true", 1)
    tamper_problems = validate_devpost_text(tampered) if text else []
    tamper_detected = bool(tamper_problems)
    ctx.note(f"문안 변조 탐지 -> {tamper_detected}")
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

        claims_audit_clean = audit_text(DEVPOST_REL, text) == []
    ctx.note(f"문안 주장 감사 깨끗함 -> {claims_audit_clean}")
    fallback_selected = bool(text) and all(
        needle in text for needle in DEVPOST_FALLBACK_MARKERS)
    if text and not fallback_selected:
        problems.append("문안 폴백 채택 표기가 온전하지 않다")
    extracted = {"sections": list(DEVPOST_SECTIONS),
                 "blockers": list(EXPECTED_BLOCKER_IDS),
                 "submission_ready": False,
                 "demo_markers": list(DEVPOST_DEMO_MARKERS),
                 "fallback_markers": list(DEVPOST_FALLBACK_MARKERS),
                 "fallback_selected": fallback_selected,
                 "selected_video": (
                     DEVPOST_SELECTED_VIDEO if fallback_selected else None),
                 "deadline_et": DEVPOST_DEADLINE_ET,
                 "deadline_kst": DEVPOST_DEADLINE_KST,
                 "repo_url": DEVPOST_REPO_URL}
    summary = {"feature": "devpost-submission",
               "sections": list(DEVPOST_SECTIONS),
               "section_count": len(DEVPOST_SECTIONS),
               "blockers": list(EXPECTED_BLOCKER_IDS),
               "submission_ready": False,
               "demo_markers": list(DEVPOST_DEMO_MARKERS),
               "fallback_markers": list(DEVPOST_FALLBACK_MARKERS),
               "fallback_selected": fallback_selected,
               "selected_video": (
                   DEVPOST_SELECTED_VIDEO if fallback_selected else None),
               "deadline_et": DEVPOST_DEADLINE_ET,
               "deadline_kst": DEVPOST_DEADLINE_KST,
               "repo_url": DEVPOST_REPO_URL,
               "claims_audit_clean": claims_audit_clean,
               "tamper_detected": tamper_detected,
               "pre_submission_blockers": pre_blockers,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"devpost-submission.json": json.dumps(
                       extracted, ensure_ascii=False, indent=2) + "\n",
                    "devpost-submission.md": text})
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


def drive_sam_smoke(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.sam_readiness import ENV_BASE_URL, ENV_KEY_VAR
    from qa.sam_smoke import run_smoke
    from terminal.models import CountResult
    from terminal.sam_adapter import SamCountingError

    class _FakeCounter:
        def __init__(self) -> None:
            self.calls: list = []

        def count(self, bin_id: str, image_ref: str | None = None):
            self.calls.append((bin_id, image_ref))
            return CountResult(bin_id, SAM_SMOKE_FAKE_COUNT, source="sam")

    class _MockCounter:
        def __init__(self) -> None:
            self.calls: list = []

        def count(self, bin_id: str, image_ref: str | None = None):
            self.calls.append((bin_id, image_ref))
            return CountResult(bin_id, SAM_SMOKE_FAKE_COUNT, source="mock")

    class _RaisingCounter:
        def count(self, bin_id: str, image_ref: str | None = None):
            raise SamCountingError("fake smoke failure")

    result = run_cli(["-m", "qa.sam_smoke"])
    ctx.note(f"python3 -m qa.sam_smoke -> 종료코드 {result.returncode}")
    if result.returncode != 1:
        problems.append(
            f"sam_smoke 기본 종료코드 기대 1, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("STATUS: blocked", "ATTEMPTED: false", "BLOCKERS: 3",
                   "SMOKE_PASSED: false"):
        if needle not in result.stdout:
            problems.append(f"sam_smoke 텍스트에 {needle!r} 없음")
    positions = [result.stdout.find(blocker_id)
                 for blocker_id in EXPECTED_READINESS_BLOCKER_IDS]
    if any(position < 0 for position in positions):
        problems.append(f"sam_smoke 텍스트에 블로커 id 누락: 위치 {positions}")
    elif positions != sorted(positions):
        problems.append(f"sam_smoke 블로커 id 순서 이상: 위치 {positions}")

    result_j = run_cli(["-m", "qa.sam_smoke", "--json"])
    ctx.note(f"python3 -m qa.sam_smoke --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 1:
        problems.append(
            f"sam_smoke --json 종료코드 기대 1, 실제 {result_j.returncode}: "
            f"{result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocked_blockers: list = []
    if report:
        if report.get("status") != "blocked":
            problems.append(
                f"status 기대 blocked, 실제 {report.get('status')}")
        if report.get("attempted") is not False:
            problems.append(
                f"attempted 기대 False, 실제 {report.get('attempted')}")
        if report.get("ready_for_live_call") is not False:
            problems.append(
                "ready_for_live_call 기대 False, 실제 "
                f"{report.get('ready_for_live_call')}")
        blocked_blockers = [b["id"] for b in report.get("blockers", [])]
        if blocked_blockers != list(EXPECTED_READINESS_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_READINESS_BLOCKER_IDS)}, "
                f"실제 {blocked_blockers}")
        if report.get("counted_qty") is not None:
            problems.append(
                f"counted_qty 기대 None, 실제 {report.get('counted_qty')}")
        if report.get("source") is not None:
            problems.append(f"source 기대 None, 실제 {report.get('source')}")
        if not any("호출하지 않는다" in line
                   for line in report.get("honesty", [])):
            problems.append("honesty에 '호출하지 않는다'를 포함한 줄 없음")
        if not any("대체하지 않는다" in line
                   for line in report.get("honesty", [])):
            problems.append("honesty에 '대체하지 않는다'를 포함한 줄 없음")

    fake_env = {ENV_BASE_URL: SAM_SMOKE_FAKE_URL,
                ENV_KEY_VAR: SAM_SMOKE_FAKE_KEY_VALUE}
    fake_counter = _FakeCounter()
    passed = run_smoke(env=fake_env, credit_confirmed=True,
                       counter=fake_counter)
    ctx.note(
        f"run_smoke 가짜 counter -> status={passed.get('status')}, "
        f"counted_qty={passed.get('counted_qty')}, diff={passed.get('diff')}")
    if passed.get("status") != "passed":
        problems.append(
            f"가짜 counter status 기대 passed, 실제 {passed.get('status')}")
    if passed.get("attempted") is not True:
        problems.append(
            f"가짜 counter attempted 기대 True, 실제 {passed.get('attempted')}")
    if passed.get("source") != "sam":
        problems.append(
            f"가짜 counter source 기대 sam, 실제 {passed.get('source')}")
    if passed.get("counted_qty") != SAM_SMOKE_FAKE_COUNT:
        problems.append(
            f"counted_qty 기대 {SAM_SMOKE_FAKE_COUNT}, "
            f"실제 {passed.get('counted_qty')}")
    if passed.get("book_qty") != SAM_SMOKE_BOOK_QTY:
        problems.append(
            f"book_qty 기대 {SAM_SMOKE_BOOK_QTY}, 실제 {passed.get('book_qty')}")
    if passed.get("diff") != SAM_SMOKE_FAKE_COUNT - SAM_SMOKE_BOOK_QTY:
        problems.append(
            f"diff 기대 {SAM_SMOKE_FAKE_COUNT - SAM_SMOKE_BOOK_QTY}, "
            f"실제 {passed.get('diff')}")
    if fake_counter.calls != [(SAM_SMOKE_BIN_ID, None)]:
        problems.append(
            f"가짜 counter 호출 기대 [('A-01-02', None)], 실제 {fake_counter.calls}")

    blocked_counter = _FakeCounter()
    blocked_inproc = run_smoke(env={}, credit_confirmed=False,
                               counter=blocked_counter)
    ctx.note(
        f"run_smoke 차단 -> status={blocked_inproc.get('status')}, "
        f"counter 호출 {len(blocked_counter.calls)}건")
    if blocked_inproc.get("status") != "blocked":
        problems.append(
            "차단 시 status 기대 blocked, 실제 "
            f"{blocked_inproc.get('status')}")
    if blocked_inproc.get("attempted") is not False:
        problems.append(
            "차단 시 attempted 기대 False, 실제 "
            f"{blocked_inproc.get('attempted')}")
    if blocked_counter.calls != []:
        problems.append(
            f"차단 시 counter를 부르면 안 된다: 호출 {blocked_counter.calls}")

    mock_report = run_smoke(env=fake_env, credit_confirmed=True,
                            counter=_MockCounter())
    ctx.note(
        f"run_smoke 모의 source -> status={mock_report.get('status')}, "
        f"error_type={mock_report.get('error_type')}")
    if mock_report.get("status") != "failed":
        problems.append(
            f"모의 source status 기대 failed, 실제 {mock_report.get('status')}")
    if mock_report.get("error_type") != "unexpected_source":
        problems.append(
            "모의 source error_type 기대 unexpected_source, 실제 "
            f"{mock_report.get('error_type')}")

    error_report = run_smoke(env=fake_env, credit_confirmed=True,
                             counter=_RaisingCounter())
    ctx.note(
        f"run_smoke SamCountingError -> status={error_report.get('status')}, "
        f"error_type={error_report.get('error_type')}")
    if error_report.get("status") != "failed":
        problems.append(
            f"오류 시 status 기대 failed, 실제 {error_report.get('status')}")
    if error_report.get("error_type") != "SamCountingError":
        problems.append(
            "오류 시 error_type 기대 SamCountingError, 실제 "
            f"{error_report.get('error_type')}")
    if error_report.get("counted_qty") is not None:
        problems.append(
            "오류 시 counted_qty 기대 None(모의로 대체하지 않는다), 실제 "
            f"{error_report.get('counted_qty')}")

    unknown_counter = _FakeCounter()
    unknown = run_smoke(env=fake_env, credit_confirmed=True, bin_id="Z-99-99",
                        counter=unknown_counter)
    ctx.note(
        f"run_smoke 알 수 없는 빈 -> status={unknown.get('status')}, "
        f"error_type={unknown.get('error_type')}")
    if unknown.get("status") != "failed":
        problems.append(
            f"알 수 없는 빈 status 기대 failed, 실제 {unknown.get('status')}")
    if unknown.get("error_type") != "unknown_bin":
        problems.append(
            "알 수 없는 빈 error_type 기대 unknown_bin, 실제 "
            f"{unknown.get('error_type')}")
    if unknown.get("attempted") is not False:
        problems.append(
            f"알 수 없는 빈 attempted 기대 False, 실제 {unknown.get('attempted')}")
    if unknown_counter.calls != []:
        problems.append(
            f"알 수 없는 빈에서 counter를 부르면 안 된다: 호출 {unknown_counter.calls}")

    dumped = "".join(
        json.dumps(item, ensure_ascii=False)
        for item in (passed, blocked_inproc, mock_report, error_report,
                     unknown, report)) + result.stdout + result_j.stdout
    sentinel_leaked = (SAM_SMOKE_FAKE_KEY_VALUE in dumped
                       or SAM_SMOKE_FAKE_URL in dumped)
    ctx.note(f"가짜 키/URL 값 누출 -> {sentinel_leaked}")
    if sentinel_leaked:
        problems.append("가짜 환경변수 값이 sam_smoke 보고나 CLI 출력에 새어 나왔다")

    summary = {"feature": "sam-smoke",
               "blocked_blockers": blocked_blockers,
               "default_exit_code": result.returncode,
               "fake_passed": passed.get("status") == "passed",
               "counted_qty": passed.get("counted_qty"),
               "book_qty": passed.get("book_qty"),
               "diff": passed.get("diff"),
               "blocked_counter_calls": len(blocked_counter.calls),
               "mock_source_blocked":
                   mock_report.get("error_type") == "unexpected_source",
               "sam_error_blocked":
                   error_report.get("error_type") == "SamCountingError",
               "unknown_bin_blocked":
                   unknown.get("error_type") == "unknown_bin",
               "sentinel_leaked": sentinel_leaked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-smoke-blocked.json": result_j.stdout,
                    "sam-smoke-passed.json": json.dumps(
                        passed, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_pi_smoke(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.pi_smoke import run_smoke
    from terminal.pi_capture import PiCaptureError

    def _libcamera(name):
        return "/usr/bin/libcamera-still" if name == "libcamera-still" else None

    def _no_command(name):
        return None

    class FakeSession:
        def __init__(self, result=None) -> None:
            self.calls: list = []
            if result is None:
                result = {"session_id": "PI-SMOKE", "source": "mock",
                          "capture_source": "pi-camera",
                          "bins": [{"bin_id": PI_SMOKE_BIN_ID,
                                    "book_qty": 8, "counted_qty": 5, "diff": -3,
                                    "photo": {"sha256": PI_SMOKE_FAKE_SHA,
                                              "image_ref": "A-01-02.jpg"}}]}
            self.result = result

        def __call__(self, output_dir, bin_ids=None, session_id=None,
                     runner=None, which=None):
            self.calls.append({"output_dir": output_dir, "bin_ids": bin_ids,
                               "session_id": session_id, "runner": runner,
                               "which": which})
            return copy.deepcopy(self.result)

    class _PiErrorSession:
        def __call__(self, output_dir, bin_ids=None, session_id=None,
                     runner=None, which=None):
            raise PiCaptureError("fake pi smoke failure")

    class _BoomSession:
        def __call__(self, output_dir, bin_ids=None, session_id=None,
                     runner=None, which=None):
            raise RuntimeError(f"boom {PI_SMOKE_SENTINEL}")

    result = run_cli(["-m", "qa.pi_smoke"])
    ctx.note(f"python3 -m qa.pi_smoke -> 종료코드 {result.returncode}")
    if result.returncode != 1:
        problems.append(
            f"pi_smoke 기본 종료코드 기대 1, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("STATUS: blocked", "ATTEMPTED: false", "BLOCKERS: 2",
                   "SMOKE_PASSED: false"):
        if needle not in result.stdout:
            problems.append(f"pi_smoke 텍스트에 {needle!r} 없음")
    positions = [result.stdout.find(blocker_id)
                 for blocker_id in EXPECTED_PI_READINESS_BLOCKER_IDS]
    if any(position < 0 for position in positions):
        problems.append(f"pi_smoke 텍스트에 블로커 id 누락: 위치 {positions}")
    elif positions != sorted(positions):
        problems.append(f"pi_smoke 블로커 id 순서 이상: 위치 {positions}")

    result_j = run_cli(["-m", "qa.pi_smoke", "--json"])
    ctx.note(f"python3 -m qa.pi_smoke --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 1:
        problems.append(
            f"pi_smoke --json 종료코드 기대 1, 실제 {result_j.returncode}: "
            f"{result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocked_blockers: list = []
    if report:
        if report.get("status") != "blocked":
            problems.append(
                f"status 기대 blocked, 실제 {report.get('status')}")
        if report.get("attempted") is not False:
            problems.append(
                f"attempted 기대 False, 실제 {report.get('attempted')}")
        if report.get("ready_for_real_capture") is not False:
            problems.append(
                "ready_for_real_capture 기대 False, 실제 "
                f"{report.get('ready_for_real_capture')}")
        blocked_blockers = [b["id"] for b in report.get("blockers", [])]
        if blocked_blockers != list(EXPECTED_PI_READINESS_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_PI_READINESS_BLOCKER_IDS)}, "
                f"실제 {blocked_blockers}")
        if report.get("counted_qty") is not None:
            problems.append(
                f"counted_qty 기대 None, 실제 {report.get('counted_qty')}")
        if report.get("source") is not None:
            problems.append(f"source 기대 None, 실제 {report.get('source')}")
        if report.get("capture_source") is not None:
            problems.append(
                f"capture_source 기대 None, 실제 {report.get('capture_source')}")
        if not any("촬영하지 않는다" in line
                   for line in report.get("honesty", [])):
            problems.append("honesty에 '촬영하지 않는다'를 포함한 줄 없음")
        if not any("대체하지 않는다" in line
                   for line in report.get("honesty", [])):
            problems.append("honesty에 '대체하지 않는다'를 포함한 줄 없음")

    cli_device = run_cli(["-m", "qa.pi_smoke", "--device-confirmed", "--json"])
    ctx.note(
        "python3 -m qa.pi_smoke --device-confirmed --json -> "
        f"종료코드 {cli_device.returncode}")
    if cli_device.returncode != 1:
        problems.append(
            f"장치 확인 CLI 종료코드 기대 1, 실제 {cli_device.returncode}: "
            f"{cli_device.stderr[:200]}")
    device_confirmed_blockers: list = []
    try:
        cli_device_report = json.loads(cli_device.stdout)
        device_confirmed_blockers = [
            b["id"] for b in cli_device_report.get("blockers", [])]
    except json.JSONDecodeError as e:
        problems.append(f"장치 확인 CLI --json 파싱 실패: {e}")
    if device_confirmed_blockers != ["pi_camera_command_missing"]:
        problems.append(
            f"장치 확인 CLI blockers 기대 ['pi_camera_command_missing'], "
            f"실제 {device_confirmed_blockers}")

    passed: dict = {}
    blocked_inproc: dict = {}
    real: dict = {}
    wrong_source: dict = {}
    error_report: dict = {}
    boom: dict = {}
    unknown: dict = {}
    fake_session = FakeSession()
    blocked_session = FakeSession()
    unknown_session = FakeSession()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        passed = run_smoke(output_dir=root / "c", device_confirmed=True,
                           which=_libcamera, session_fn=fake_session)
        ctx.note(
            f"run_smoke 가짜 session -> status={passed.get('status')}, "
            f"counted_qty={passed.get('counted_qty')}, diff={passed.get('diff')}")
        if passed.get("status") != "passed":
            problems.append(
                f"가짜 session status 기대 passed, 실제 {passed.get('status')}")
        if passed.get("attempted") is not True:
            problems.append(
                f"가짜 session attempted 기대 True, 실제 {passed.get('attempted')}")
        if passed.get("ready_for_real_capture") is not True:
            problems.append(
                "가짜 session ready_for_real_capture 기대 True, 실제 "
                f"{passed.get('ready_for_real_capture')}")
        if passed.get("source") != "mock":
            problems.append(
                f"가짜 session source 기대 mock, 실제 {passed.get('source')}")
        if passed.get("capture_source") != "pi-camera":
            problems.append(
                "가짜 session capture_source 기대 pi-camera, 실제 "
                f"{passed.get('capture_source')}")
        if passed.get("counted_qty") != PI_SMOKE_FAKE_COUNT:
            problems.append(
                f"counted_qty 기대 {PI_SMOKE_FAKE_COUNT}, "
                f"실제 {passed.get('counted_qty')}")
        if passed.get("book_qty") != PI_SMOKE_BOOK_QTY:
            problems.append(
                f"book_qty 기대 {PI_SMOKE_BOOK_QTY}, 실제 {passed.get('book_qty')}")
        if passed.get("diff") != PI_SMOKE_FAKE_COUNT - PI_SMOKE_BOOK_QTY:
            problems.append(
                f"diff 기대 {PI_SMOKE_FAKE_COUNT - PI_SMOKE_BOOK_QTY}, "
                f"실제 {passed.get('diff')}")
        if passed.get("photo_sha256") != PI_SMOKE_FAKE_SHA:
            problems.append(
                f"photo_sha256 기대 {PI_SMOKE_FAKE_SHA}, "
                f"실제 {passed.get('photo_sha256')}")
        if passed.get("photo_image_ref") != "A-01-02.jpg":
            problems.append(
                "photo_image_ref 기대 A-01-02.jpg, 실제 "
                f"{passed.get('photo_image_ref')}")
        if passed.get("session_id") != "PI-SMOKE":
            problems.append(
                f"session_id 기대 PI-SMOKE, 실제 {passed.get('session_id')}")
        if len(fake_session.calls) != 1:
            problems.append(
                f"가짜 session 호출 기대 1회, 실제 {len(fake_session.calls)}회")
        elif fake_session.calls[0].get("bin_ids") != [PI_SMOKE_BIN_ID] \
                or fake_session.calls[0].get("session_id") != "PI-SMOKE":
            problems.append(
                f"가짜 session 호출 인자 이상: {fake_session.calls[0]}")

        blocked_dir = root / "blocked"
        blocked_inproc = run_smoke(output_dir=blocked_dir,
                                   device_confirmed=False, which=_no_command,
                                   session_fn=blocked_session)
        ctx.note(
            f"run_smoke 차단 -> status={blocked_inproc.get('status')}, "
            f"session 호출 {len(blocked_session.calls)}건")
        if blocked_inproc.get("status") != "blocked":
            problems.append(
                "차단 시 status 기대 blocked, 실제 "
                f"{blocked_inproc.get('status')}")
        if blocked_inproc.get("attempted") is not False:
            problems.append(
                "차단 시 attempted 기대 False, 실제 "
                f"{blocked_inproc.get('attempted')}")
        if blocked_session.calls != []:
            problems.append(
                f"차단 시 session을 부르면 안 된다: 호출 {blocked_session.calls}")
        if blocked_dir.exists():
            problems.append("차단 시 output_dir이 생기면 안 된다")

        def fake_runner(argv, capture_output=True, text=True, timeout=30):
            Path(argv[argv.index("-o") + 1]).write_bytes(PI_SMOKE_FAKE_CONTENT)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        out_dir = root / "captures"
        real = run_smoke(output_dir=out_dir, device_confirmed=True,
                         which=_libcamera, runner=fake_runner)
        ctx.note(
            f"run_smoke 실제 pi_session+가짜 runner -> status={real.get('status')}, "
            f"counted_qty={real.get('counted_qty')}, diff={real.get('diff')}")
        if real.get("status") != "passed":
            problems.append(
                "실제 pi_session+가짜 runner status 기대 passed, 실제 "
                f"{real.get('status')}")
        if real.get("counted_qty") != PI_SMOKE_FAKE_COUNT:
            problems.append(
                f"실제 pi_session counted_qty 기대 {PI_SMOKE_FAKE_COUNT}, "
                f"실제 {real.get('counted_qty')}")
        if real.get("diff") != PI_SMOKE_FAKE_COUNT - PI_SMOKE_BOOK_QTY:
            problems.append(
                f"실제 pi_session diff 기대 "
                f"{PI_SMOKE_FAKE_COUNT - PI_SMOKE_BOOK_QTY}, 실제 {real.get('diff')}")
        expected_sha = hashlib.sha256(PI_SMOKE_FAKE_CONTENT).hexdigest()
        if real.get("photo_sha256") != expected_sha:
            problems.append(
                f"실제 pi_session photo_sha256 기대 {expected_sha}, "
                f"실제 {real.get('photo_sha256')}")
        if not (out_dir / "A-01-02.jpg").is_file():
            problems.append("실제 pi_session 캡처 파일 A-01-02.jpg 가 없다")

        wrong_result = copy.deepcopy(FakeSession().result)
        wrong_result["capture_source"] = "file"
        wrong_source = run_smoke(output_dir=root / "wrong",
                                 device_confirmed=True, which=_libcamera,
                                 session_fn=FakeSession(result=wrong_result))
        ctx.note(
            f"run_smoke capture_source file -> status={wrong_source.get('status')}, "
            f"error_type={wrong_source.get('error_type')}")
        if wrong_source.get("status") != "failed":
            problems.append(
                "capture_source file status 기대 failed, 실제 "
                f"{wrong_source.get('status')}")
        if wrong_source.get("error_type") != "unexpected_capture_source":
            problems.append(
                "capture_source file error_type 기대 unexpected_capture_source, "
                f"실제 {wrong_source.get('error_type')}")

        error_report = run_smoke(output_dir=root / "error",
                                 device_confirmed=True, which=_libcamera,
                                 session_fn=_PiErrorSession())
        ctx.note(
            f"run_smoke PiCaptureError -> status={error_report.get('status')}, "
            f"error_type={error_report.get('error_type')}")
        if error_report.get("status") != "failed":
            problems.append(
                f"오류 시 status 기대 failed, 실제 {error_report.get('status')}")
        if error_report.get("error_type") != "PiCaptureError":
            problems.append(
                "오류 시 error_type 기대 PiCaptureError, 실제 "
                f"{error_report.get('error_type')}")
        if error_report.get("counted_qty") is not None:
            problems.append(
                "오류 시 counted_qty 기대 None(대체하지 않는다), 실제 "
                f"{error_report.get('counted_qty')}")

        boom = run_smoke(output_dir=root / "boom", device_confirmed=True,
                         which=_libcamera, session_fn=_BoomSession())
        ctx.note(
            f"run_smoke RuntimeError -> status={boom.get('status')}, "
            f"error_type={boom.get('error_type')}")
        if boom.get("status") != "failed":
            problems.append(
                f"일반 예외 시 status 기대 failed, 실제 {boom.get('status')}")
        if boom.get("error_type") != "RuntimeError":
            problems.append(
                "일반 예외 시 error_type 기대 RuntimeError, 실제 "
                f"{boom.get('error_type')}")

        unknown = run_smoke(output_dir=root / "unknown", device_confirmed=True,
                            which=_libcamera, bin_id="Z-99-99",
                            session_fn=unknown_session)
        ctx.note(
            f"run_smoke 알 수 없는 빈 -> status={unknown.get('status')}, "
            f"error_type={unknown.get('error_type')}")
        if unknown.get("status") != "failed":
            problems.append(
                f"알 수 없는 빈 status 기대 failed, 실제 {unknown.get('status')}")
        if unknown.get("error_type") != "unknown_bin":
            problems.append(
                "알 수 없는 빈 error_type 기대 unknown_bin, 실제 "
                f"{unknown.get('error_type')}")
        if unknown.get("attempted") is not False:
            problems.append(
                f"알 수 없는 빈 attempted 기대 False, 실제 {unknown.get('attempted')}")
        if unknown_session.calls != []:
            problems.append(
                f"알 수 없는 빈에서 session을 부르면 안 된다: 호출 {unknown_session.calls}")

    dumped = "".join(
        json.dumps(item, ensure_ascii=False)
        for item in (passed, blocked_inproc, real, wrong_source, error_report,
                     boom, unknown, report)) + result.stdout + result_j.stdout
    sentinel_leaked = PI_SMOKE_SENTINEL in dumped
    ctx.note(f"예외 원본 문자열 누출 -> {sentinel_leaked}")
    if sentinel_leaked:
        problems.append("일반 예외 원본 문자열이 pi_smoke 보고나 CLI 출력에 새어 나왔다")

    summary = {"feature": "pi-smoke",
               "blocked_blockers": blocked_blockers,
               "default_exit_code": result.returncode,
               "device_confirmed_blockers": device_confirmed_blockers,
               "fake_passed": passed.get("status") == "passed",
               "counted_qty": passed.get("counted_qty"),
               "book_qty": passed.get("book_qty"),
               "diff": passed.get("diff"),
               "blocked_session_calls": len(blocked_session.calls),
               "real_session_passed": real.get("status") == "passed",
               "fake_capture_sha256":
                   hashlib.sha256(PI_SMOKE_FAKE_CONTENT).hexdigest(),
               "unexpected_capture_source_blocked":
                   wrong_source.get("error_type") == "unexpected_capture_source",
               "pi_capture_error_blocked":
                   error_report.get("error_type") == "PiCaptureError",
               "unknown_bin_blocked":
                   unknown.get("error_type") == "unknown_bin",
               "sentinel_leaked": sentinel_leaked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"pi-smoke-blocked.json": result_j.stdout,
                    "pi-smoke-passed.json": json.dumps(
                        passed, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_sam_session(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.sam_readiness import ENV_BASE_URL, ENV_KEY_VAR
    from qa.sam_session import run_sam_session
    from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids
    from terminal.models import CountResult
    from terminal.sam_adapter import SamCountingError

    class _FakeCounter:
        def __init__(self, counts=None) -> None:
            self.calls: list = []
            self.counts = dict(counts) if counts is not None else dict(DEMO_COUNTED_QTY)

        def count(self, bin_id: str, image_ref: str | None = None):
            self.calls.append((bin_id, image_ref))
            return CountResult(bin_id, self.counts[bin_id], source="sam")

    class _MockCounter:
        def count(self, bin_id: str, image_ref: str | None = None):
            return CountResult(bin_id, 5, source="mock")

    class _RaisingCounter:
        def count(self, bin_id: str, image_ref: str | None = None):
            raise SamCountingError("fake session failure")

    class _LeakyCounter:
        def count(self, bin_id: str, image_ref: str | None = None):
            raise RuntimeError(f"boom {SAM_SESSION_SENTINEL}")

    result = run_cli(["-m", "qa.sam_session"])
    ctx.note(f"python3 -m qa.sam_session -> 종료코드 {result.returncode}")
    if result.returncode != 1:
        problems.append(
            f"sam_session 기본 종료코드 기대 1, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("STATUS: blocked", "ATTEMPTED: false", "BLOCKERS: 3",
                   "SESSION_PASSED: false"):
        if needle not in result.stdout:
            problems.append(f"sam_session 텍스트에 {needle!r} 없음")
    positions = [result.stdout.find(blocker_id)
                 for blocker_id in EXPECTED_READINESS_BLOCKER_IDS]
    if any(position < 0 for position in positions):
        problems.append(f"sam_session 텍스트에 블로커 id 누락: 위치 {positions}")
    elif positions != sorted(positions):
        problems.append(f"sam_session 블로커 id 순서 이상: 위치 {positions}")

    result_j = run_cli(["-m", "qa.sam_session", "--json"])
    ctx.note(f"python3 -m qa.sam_session --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 1:
        problems.append(
            f"sam_session --json 종료코드 기대 1, 실제 {result_j.returncode}: "
            f"{result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocked_blockers: list = []
    if report:
        if report.get("status") != "blocked":
            problems.append(f"status 기대 blocked, 실제 {report.get('status')}")
        if report.get("attempted") is not False:
            problems.append(f"attempted 기대 False, 실제 {report.get('attempted')}")
        if report.get("ready_for_live_call") is not False:
            problems.append(
                "ready_for_live_call 기대 False, 실제 "
                f"{report.get('ready_for_live_call')}")
        blocked_blockers = [b["id"] for b in report.get("blockers", [])]
        if blocked_blockers != list(EXPECTED_READINESS_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_READINESS_BLOCKER_IDS)}, "
                f"실제 {blocked_blockers}")
        if report.get("source") is not None:
            problems.append(f"source 기대 None, 실제 {report.get('source')}")
        if report.get("bins") != []:
            problems.append(f"bins 기대 [], 실제 {report.get('bins')}")
        if report.get("summary") is not None:
            problems.append(f"summary 기대 None, 실제 {report.get('summary')}")
        joined = " ".join(str(x) for x in report.get("honesty", []))
        for marker in ("호출하지 않는다", "대체하지 않는다", "Pi 실촬영이 아니며"):
            if marker not in joined:
                problems.append(f"honesty에 {marker!r} 없음")

    fake_env = {ENV_BASE_URL: SAM_SESSION_FAKE_URL,
                ENV_KEY_VAR: SAM_SESSION_FAKE_KEY_VALUE}
    fake_counter = _FakeCounter()
    passed = run_sam_session(env=fake_env, credit_confirmed=True,
                             counter=fake_counter, session_id=SAM_SESSION_ID,
                             image_ref="verify-photo.jpg")
    ctx.note(
        f"run_sam_session 가짜 counter -> status={passed.get('status')}, "
        f"summary={passed.get('summary')}")
    if passed.get("status") != "passed":
        problems.append(f"가짜 counter status 기대 passed, 실제 {passed.get('status')}")
    if passed.get("attempted") is not True:
        problems.append(f"가짜 counter attempted 기대 True, 실제 {passed.get('attempted')}")
    if passed.get("source") != "sam":
        problems.append(f"가짜 counter source 기대 sam, 실제 {passed.get('source')}")
    if passed.get("session_id") != SAM_SESSION_ID:
        problems.append(
            f"session_id 기대 {SAM_SESSION_ID}, 실제 {passed.get('session_id')}")
    expected_calls = [(bin_id, "verify-photo.jpg") for bin_id in demo_bin_ids()]
    if fake_counter.calls != expected_calls:
        problems.append(f"가짜 counter 호출 기대 {expected_calls}, 실제 {fake_counter.calls}")
    bins = passed.get("bins") or []
    if len(bins) != 6:
        problems.append(f"bins 기대 6개, 실제 {len(bins)}개")
    by_bin = {b.get("bin_id"): b for b in bins}
    a0102 = by_bin.get("A-01-02") or {}
    for key, expected in (("book_qty", 8), ("counted_qty", 5), ("diff", -3)):
        if a0102.get(key) != expected:
            problems.append(f"A-01-02 {key} 기대 {expected}, 실제 {a0102.get(key)}")
    if a0102.get("verdict") != "short":
        problems.append(f"A-01-02 verdict 기대 short, 실제 {a0102.get('verdict')}")
    b0102 = by_bin.get("B-01-02") or {}
    if b0102.get("diff") != 3 or b0102.get("verdict") != "over":
        problems.append(f"B-01-02 기대 diff 3/over, 실제 {b0102}")
    summary_map = passed.get("summary") or {}
    for key, expected in (("counted_bins", 6), ("matched", 4), ("mismatched", 2),
                          ("abs_diff_total", 6), ("net_diff", 0)):
        if summary_map.get(key) != expected:
            problems.append(f"summary.{key} 기대 {expected}, 실제 {summary_map.get(key)}")

    blocked_counter = _FakeCounter()
    blocked_inproc = run_sam_session(env={}, credit_confirmed=False,
                                     counter=blocked_counter)
    ctx.note(
        f"run_sam_session 차단 -> status={blocked_inproc.get('status')}, "
        f"counter 호출 {len(blocked_counter.calls)}건")
    if blocked_inproc.get("status") != "blocked":
        problems.append(f"차단 시 status 기대 blocked, 실제 {blocked_inproc.get('status')}")
    if blocked_counter.calls != []:
        problems.append(f"차단 시 counter를 부르면 안 된다: 호출 {blocked_counter.calls}")

    uniform_counter = _FakeCounter(counts={b: 14 for b in demo_bin_ids()})
    uniform = run_sam_session(env=fake_env, credit_confirmed=True,
                              counter=uniform_counter)
    ctx.note(f"run_sam_session 균일 14 -> summary={uniform.get('summary')}")
    uniform_summary = uniform.get("summary") or {}
    for key, expected in (("matched", 0), ("mismatched", 6),
                          ("abs_diff_total", 25), ("net_diff", 15)):
        if uniform_summary.get(key) != expected:
            problems.append(
                f"균일 14 summary.{key} 기대 {expected}, 실제 {uniform_summary.get(key)}")

    mock_report = run_sam_session(env=fake_env, credit_confirmed=True,
                                  counter=_MockCounter())
    ctx.note(
        f"run_sam_session 모의 source -> status={mock_report.get('status')}, "
        f"error_type={mock_report.get('error_type')}")
    if mock_report.get("status") != "failed" \
            or mock_report.get("error_type") != "unexpected_source":
        problems.append(f"모의 source 차단 이상: {mock_report.get('status')}/{mock_report.get('error_type')}")
    if mock_report.get("summary") is not None:
        problems.append("모의 source 실패 시 summary는 None이어야 한다")

    error_report = run_sam_session(env=fake_env, credit_confirmed=True,
                                   counter=_RaisingCounter())
    ctx.note(
        f"run_sam_session SamCountingError -> status={error_report.get('status')}, "
        f"error_type={error_report.get('error_type')}")
    if error_report.get("status") != "failed" \
            or error_report.get("error_type") != "SamCountingError":
        problems.append(f"오류 차단 이상: {error_report.get('status')}/{error_report.get('error_type')}")

    leaky_report = run_sam_session(env=fake_env, credit_confirmed=True,
                                   counter=_LeakyCounter())
    ctx.note(
        f"run_sam_session RuntimeError -> status={leaky_report.get('status')}, "
        f"error_type={leaky_report.get('error_type')}")
    if leaky_report.get("status") != "failed" \
            or leaky_report.get("error_type") != "RuntimeError":
        problems.append(f"일반 예외 차단 이상: {leaky_report.get('status')}/{leaky_report.get('error_type')}")

    dumped = "".join(
        json.dumps(item, ensure_ascii=False)
        for item in (passed, blocked_inproc, uniform, mock_report,
                     error_report, leaky_report, report)) \
        + result.stdout + result_j.stdout
    sentinel_leaked = (SAM_SESSION_FAKE_KEY_VALUE in dumped
                       or SAM_SESSION_FAKE_URL in dumped
                       or SAM_SESSION_SENTINEL in dumped)
    ctx.note(f"가짜 키/URL/예외 원본 누출 -> {sentinel_leaked}")
    if sentinel_leaked:
        problems.append("가짜 환경변수 값이나 예외 원본이 sam_session 보고나 CLI 출력에 새어 나왔다")

    summary = {"feature": "sam-session",
               "blocked_blockers": blocked_blockers,
               "default_exit_code": result.returncode,
               "fake_passed": passed.get("status") == "passed",
               "session_id": passed.get("session_id"),
               "matched": summary_map.get("matched"),
               "mismatched": summary_map.get("mismatched"),
               "abs_diff_total": summary_map.get("abs_diff_total"),
               "net_diff": summary_map.get("net_diff"),
               "blocked_counter_calls": len(blocked_counter.calls),
               "uniform_mismatched": uniform_summary.get("mismatched"),
               "mock_source_blocked":
                   mock_report.get("error_type") == "unexpected_source",
               "sam_error_blocked":
                   error_report.get("error_type") == "SamCountingError",
               "sentinel_leaked": sentinel_leaked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-session-blocked.json": result_j.stdout,
                    "sam-session-passed.json": json.dumps(
                        passed, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_sam_per_bin(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.sam_per_bin import run_sam_per_bin
    from qa.sam_readiness import ENV_BASE_URL, ENV_KEY_VAR
    from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids
    from terminal.models import CountResult
    from terminal.sam_adapter import SamCountingError

    class _FakeCounter:
        def __init__(self, counts=None) -> None:
            self.calls: list = []
            self.counts = dict(counts) if counts is not None else dict(DEMO_COUNTED_QTY)

        def count(self, bin_id: str, image_ref: str | None = None):
            self.calls.append((bin_id, image_ref))
            return CountResult(bin_id, self.counts[bin_id], source="sam")

    class _MockCounter:
        def __init__(self) -> None:
            self.calls: list = []

        def count(self, bin_id: str, image_ref: str | None = None):
            self.calls.append((bin_id, image_ref))
            return CountResult(bin_id, 5, source="mock")

    class _RaisingCounter:
        def count(self, bin_id: str, image_ref: str | None = None):
            raise SamCountingError("fake per-bin failure")

    class _LeakyCounter:
        def count(self, bin_id: str, image_ref: str | None = None):
            raise RuntimeError(f"boom {SAM_PERBIN_SENTINEL}")

    result = run_cli(["-m", "qa.sam_per_bin"])
    ctx.note(f"python3 -m qa.sam_per_bin -> 종료코드 {result.returncode}")
    if result.returncode != 1:
        problems.append(f"sam_per_bin 기본 종료코드 기대 1, 실제 {result.returncode}: {result.stderr[:200]}")
    for needle in ("STATUS: blocked", "ATTEMPTED: false", "DISTINCT_IMAGES: 0", "BLOCKERS: 3", "SESSION_PASSED: false"):
        if needle not in result.stdout:
            problems.append(f"sam_per_bin 텍스트에 {needle!r} 없음")
    positions = [result.stdout.find(b) for b in EXPECTED_READINESS_BLOCKER_IDS]
    if any(x < 0 for x in positions):
        problems.append(f"sam_per_bin 텍스트에 블로커 id 누락: 위치 {positions}")
    elif positions != sorted(positions):
        problems.append(f"sam_per_bin 블로커 id 순서 이상: 위치 {positions}")

    result_j = run_cli(["-m", "qa.sam_per_bin", "--json"])
    ctx.note(f"python3 -m qa.sam_per_bin --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 1:
        problems.append(f"sam_per_bin --json 종료코드 기대 1, 실제 {result_j.returncode}: {result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocked_blockers: list = []
    if report:
        if report.get("status") != "blocked":
            problems.append(f"status 기대 blocked, 실제 {report.get('status')}")
        if report.get("attempted") is not False:
            problems.append(f"attempted 기대 False, 실제 {report.get('attempted')}")
        if report.get("ready_for_live_call") is not False:
            problems.append(f"ready_for_live_call 기대 False, 실제 {report.get('ready_for_live_call')}")
        blocked_blockers = [b["id"] for b in report.get("blockers", [])]
        if blocked_blockers != list(EXPECTED_READINESS_BLOCKER_IDS):
            problems.append(f"blockers 기대 {list(EXPECTED_READINESS_BLOCKER_IDS)}, 실제 {blocked_blockers}")
        if report.get("source") is not None:
            problems.append(f"source 기대 None, 실제 {report.get('source')}")
        if report.get("distinct_image_count") != 0:
            problems.append(f"distinct_image_count 기대 0, 실제 {report.get('distinct_image_count')}")
        if report.get("bins") != []:
            problems.append(f"bins 기대 [], 실제 {report.get('bins')}")
        if report.get("summary") is not None:
            problems.append(f"summary 기대 None, 실제 {report.get('summary')}")
        joined = " ".join(str(x) for x in report.get("honesty", []))
        for marker in ("서로 다른 사진", "Pi 실촬영이 아니다", "호출하지 않는다"):
            if marker not in joined:
                problems.append(f"honesty에 {marker!r} 없음")

    fake_env = {ENV_BASE_URL: SAM_PERBIN_FAKE_URL, ENV_KEY_VAR: SAM_PERBIN_FAKE_KEY_VALUE}
    passed: dict = {}
    duplicate_report: dict = {}
    missing_report: dict = {}
    mock_report: dict = {}
    error_report: dict = {}
    leaky_report: dict = {}
    blocked_inproc: dict = {}
    fake_counter = _FakeCounter()
    dup_counter = _FakeCounter()
    miss_counter = _FakeCounter()
    blocked_counter = _FakeCounter()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        refs: dict[str, str] = {}
        expected_hashes: dict[str, str] = {}
        for bin_id in demo_bin_ids():
            data = f"fake-per-bin-photo-{bin_id}".encode()
            path = root / f"{bin_id}.jpg"
            path.write_bytes(data)
            refs[bin_id] = str(path)
            expected_hashes[bin_id] = hashlib.sha256(data).hexdigest()
        passed = run_sam_per_bin(env=fake_env, credit_confirmed=True, image_refs=refs, counter=fake_counter, session_id=SAM_PERBIN_SESSION_ID)
        ctx.note(f"run_sam_per_bin 가짜 counter -> status={passed.get('status')}, summary={passed.get('summary')}")
        if passed.get("status") != "passed":
            problems.append(f"가짜 counter status 기대 passed, 실제 {passed.get('status')}")
        if passed.get("source") != "sam":
            problems.append(f"가짜 counter source 기대 sam, 실제 {passed.get('source')}")
        if passed.get("distinct_image_count") != 6:
            problems.append(f"distinct_image_count 기대 6, 실제 {passed.get('distinct_image_count')}")
        if passed.get("session_id") != SAM_PERBIN_SESSION_ID:
            problems.append(f"session_id 기대 {SAM_PERBIN_SESSION_ID}, 실제 {passed.get('session_id')}")
        expected_calls = [(b, refs[b]) for b in demo_bin_ids()]
        if fake_counter.calls != expected_calls:
            problems.append(f"가짜 counter 호출 기대 {expected_calls}, 실제 {fake_counter.calls}")
        bins = passed.get("bins") or []
        if len(bins) != 6:
            problems.append(f"bins 기대 6개, 실제 {len(bins)}개")
        by_bin = {b.get("bin_id"): b for b in bins}
        for bin_id in demo_bin_ids():
            if (by_bin.get(bin_id) or {}).get("image_sha256") != expected_hashes[bin_id]:
                problems.append(f"{bin_id} image_sha256 기대 {expected_hashes[bin_id]}, 실제 {(by_bin.get(bin_id) or {}).get('image_sha256')}")
        a0102 = by_bin.get("A-01-02") or {}
        for key, expected in (("book_qty", 8), ("counted_qty", 5), ("diff", -3)):
            if a0102.get(key) != expected:
                problems.append(f"A-01-02 {key} 기대 {expected}, 실제 {a0102.get(key)}")
        if a0102.get("verdict") != "short":
            problems.append(f"A-01-02 verdict 기대 short, 실제 {a0102.get('verdict')}")
        b0102 = by_bin.get("B-01-02") or {}
        if b0102.get("diff") != 3 or b0102.get("verdict") != "over":
            problems.append(f"B-01-02 기대 diff 3/over, 실제 {b0102}")
        summary_map = passed.get("summary") or {}
        for key, expected in (("counted_bins", 6), ("matched", 4), ("mismatched", 2), ("abs_diff_total", 6), ("net_diff", 0)):
            if summary_map.get(key) != expected:
                problems.append(f"summary.{key} 기대 {expected}, 실제 {summary_map.get(key)}")

        dup_refs = dict(refs)
        dup_refs["B-01-02"] = refs["A-01-02"]
        duplicate_report = run_sam_per_bin(env=fake_env, credit_confirmed=True, image_refs=dup_refs, counter=dup_counter)
        ctx.note(f"run_sam_per_bin 중복 사진 -> status={duplicate_report.get('status')}, error_type={duplicate_report.get('error_type')}, calls={len(dup_counter.calls)}")
        if duplicate_report.get("status") != "failed" or duplicate_report.get("error_type") != "duplicate_image":
            problems.append(f"중복 사진 차단 이상: {duplicate_report.get('status')}/{duplicate_report.get('error_type')}")
        if dup_counter.calls != []:
            problems.append(f"중복 사진 시 counter를 부르면 안 된다: {dup_counter.calls}")
        if duplicate_report.get("attempted") is not False:
            problems.append(f"중복 사진 attempted 기대 False, 실제 {duplicate_report.get('attempted')}")

        miss_refs = dict(refs)
        del miss_refs["B-02-02"]
        missing_report = run_sam_per_bin(env=fake_env, credit_confirmed=True, image_refs=miss_refs, counter=miss_counter)
        ctx.note(f"run_sam_per_bin 사진 누락 -> status={missing_report.get('status')}, error_type={missing_report.get('error_type')}")
        if missing_report.get("status") != "failed" or missing_report.get("error_type") != "missing_image":
            problems.append(f"사진 누락 차단 이상: {missing_report.get('status')}/{missing_report.get('error_type')}")
        if miss_counter.calls != []:
            problems.append(f"사진 누락 시 counter를 부르면 안 된다: {miss_counter.calls}")

        blocked_inproc = run_sam_per_bin(env={}, credit_confirmed=False, image_refs=refs, counter=blocked_counter)
        ctx.note(f"run_sam_per_bin 차단 -> status={blocked_inproc.get('status')}, counter 호출 {len(blocked_counter.calls)}건")
        if blocked_inproc.get("status") != "blocked":
            problems.append(f"차단 시 status 기대 blocked, 실제 {blocked_inproc.get('status')}")
        if blocked_counter.calls != []:
            problems.append(f"차단 시 counter를 부르면 안 된다: 호출 {blocked_counter.calls}")

        mock_report = run_sam_per_bin(env=fake_env, credit_confirmed=True, image_refs=refs, counter=_MockCounter())
        ctx.note(f"run_sam_per_bin 모의 source -> status={mock_report.get('status')}, error_type={mock_report.get('error_type')}")
        if mock_report.get("status") != "failed" or mock_report.get("error_type") != "unexpected_source":
            problems.append(f"모의 source 차단 이상: {mock_report.get('status')}/{mock_report.get('error_type')}")
        if mock_report.get("summary") is not None:
            problems.append("모의 source 실패 시 summary는 None이어야 한다")

        error_report = run_sam_per_bin(env=fake_env, credit_confirmed=True, image_refs=refs, counter=_RaisingCounter())
        ctx.note(f"run_sam_per_bin SamCountingError -> status={error_report.get('status')}, error_type={error_report.get('error_type')}")
        if error_report.get("status") != "failed" or error_report.get("error_type") != "SamCountingError":
            problems.append(f"오류 차단 이상: {error_report.get('status')}/{error_report.get('error_type')}")

        leaky_report = run_sam_per_bin(env=fake_env, credit_confirmed=True, image_refs=refs, counter=_LeakyCounter())
        ctx.note(f"run_sam_per_bin RuntimeError -> status={leaky_report.get('status')}, error_type={leaky_report.get('error_type')}")
        if leaky_report.get("status") != "failed" or leaky_report.get("error_type") != "RuntimeError":
            problems.append(f"일반 예외 차단 이상: {leaky_report.get('status')}/{leaky_report.get('error_type')}")

    summary_map = passed.get("summary") or {}
    dumped = "".join(json.dumps(item, ensure_ascii=False) for item in (passed, blocked_inproc, duplicate_report, missing_report, mock_report, error_report, leaky_report, report)) + result.stdout + result_j.stdout
    sentinel_leaked = (SAM_PERBIN_FAKE_KEY_VALUE in dumped or SAM_PERBIN_FAKE_URL in dumped or SAM_PERBIN_SENTINEL in dumped)
    ctx.note(f"가짜 키/URL/예외 원본 누출 -> {sentinel_leaked}")
    if sentinel_leaked:
        problems.append("가짜 환경변수 값이나 예외 원본이 sam_per_bin 보고나 CLI 출력에 새어 나왔다")

    summary = {"feature": "sam-per-bin",
               "blocked_blockers": blocked_blockers,
               "default_exit_code": result.returncode,
               "fake_passed": passed.get("status") == "passed",
               "session_id": passed.get("session_id"),
               "distinct_image_count": passed.get("distinct_image_count"),
               "matched": summary_map.get("matched"),
               "mismatched": summary_map.get("mismatched"),
               "abs_diff_total": summary_map.get("abs_diff_total"),
               "net_diff": summary_map.get("net_diff"),
               "blocked_counter_calls": len(blocked_counter.calls),
               "duplicate_blocked": duplicate_report.get("error_type") == "duplicate_image",
               "missing_blocked": missing_report.get("error_type") == "missing_image",
               "mock_source_blocked": mock_report.get("error_type") == "unexpected_source",
               "sam_error_blocked": error_report.get("error_type") == "SamCountingError",
               "sentinel_leaked": sentinel_leaked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-per-bin-blocked.json": result_j.stdout,
                    "sam-per-bin-passed.json": json.dumps(passed, ensure_ascii=False, indent=2) + "\n"})
    return summary

def drive_pi_session_full(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.pi_session import run_pi_full_session
    from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids, demo_ledger
    from terminal.pi_capture import PiCaptureError

    def _libcamera(name):
        return "/usr/bin/libcamera-still" if name == "libcamera-still" else None

    def _no_command(name):
        return None

    def _ok_runner(argv, capture_output=True, text=True, timeout=30):
        Path(argv[argv.index("-o") + 1]).write_bytes(PI_FULL_FAKE_CONTENT)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def _passed_result() -> dict:
        ledger = demo_ledger()
        bins = []
        for bin_id in demo_bin_ids():
            counted = DEMO_COUNTED_QTY[bin_id]
            book = ledger[bin_id].book_qty
            diff = counted - book
            verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
            bins.append({"bin_id": bin_id, "book_qty": book, "counted_qty": counted,
                         "diff": diff, "verdict": verdict,
                         "photo": {"sha256": PI_FULL_FAKE_SHA,
                                   "image_ref": f"{bin_id}.jpg"}})
        return {"session_id": PI_FULL_SESSION_ID, "source": "mock",
                "capture_source": "pi-camera", "bins": bins,
                "summary": {"counted_bins": 6, "matched": 4, "mismatched": 2,
                            "match_rate": 4 / 6, "abs_diff_total": 6, "net_diff": 0}}

    class FakeSession:
        def __init__(self, result=None) -> None:
            self.calls: list = []
            self.result = result if result is not None else _passed_result()

        def __call__(self, output_dir, bin_ids=None, session_id=None,
                     runner=None, which=None):
            self.calls.append({"output_dir": output_dir, "bin_ids": bin_ids,
                               "session_id": session_id})
            return copy.deepcopy(self.result)

    class _PiErrorSession:
        def __call__(self, output_dir, bin_ids=None, session_id=None,
                     runner=None, which=None):
            raise PiCaptureError("fake pi full failure")

    class _BoomSession:
        def __call__(self, output_dir, bin_ids=None, session_id=None,
                     runner=None, which=None):
            raise RuntimeError(f"boom {PI_FULL_SENTINEL}")

    result = run_cli(["-m", "qa.pi_session"])
    ctx.note(f"python3 -m qa.pi_session -> 종료코드 {result.returncode}")
    if result.returncode != 1:
        problems.append(
            f"pi_session 기본 종료코드 기대 1, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("STATUS: blocked", "ATTEMPTED: false", "BLOCKERS: 2",
                   "SESSION_PASSED: false"):
        if needle not in result.stdout:
            problems.append(f"pi_session 텍스트에 {needle!r} 없음")
    positions = [result.stdout.find(blocker_id)
                 for blocker_id in EXPECTED_PI_READINESS_BLOCKER_IDS]
    if any(position < 0 for position in positions):
        problems.append(f"pi_session 텍스트에 블로커 id 누락: 위치 {positions}")
    elif positions != sorted(positions):
        problems.append(f"pi_session 블로커 id 순서 이상: 위치 {positions}")

    result_j = run_cli(["-m", "qa.pi_session", "--json"])
    ctx.note(f"python3 -m qa.pi_session --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 1:
        problems.append(
            f"pi_session --json 종료코드 기대 1, 실제 {result_j.returncode}: "
            f"{result_j.stderr[:200]}")
    report: dict = {}
    try:
        report = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocked_blockers: list = []
    if report:
        if report.get("status") != "blocked":
            problems.append(f"status 기대 blocked, 실제 {report.get('status')}")
        if report.get("attempted") is not False:
            problems.append(f"attempted 기대 False, 실제 {report.get('attempted')}")
        if report.get("ready_for_real_capture") is not False:
            problems.append(
                "ready_for_real_capture 기대 False, 실제 "
                f"{report.get('ready_for_real_capture')}")
        blocked_blockers = [b["id"] for b in report.get("blockers", [])]
        if blocked_blockers != list(EXPECTED_PI_READINESS_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_PI_READINESS_BLOCKER_IDS)}, "
                f"실제 {blocked_blockers}")
        if report.get("source") is not None:
            problems.append(f"source 기대 None, 실제 {report.get('source')}")
        if report.get("capture_source") is not None:
            problems.append(
                f"capture_source 기대 None, 실제 {report.get('capture_source')}")
        if report.get("bins") != []:
            problems.append(f"bins 기대 [], 실제 {report.get('bins')}")
        if report.get("summary") is not None:
            problems.append(f"summary 기대 None, 실제 {report.get('summary')}")
        joined = " ".join(str(x) for x in report.get("honesty", []))
        for marker in ("촬영하지 않는다", "대체하지 않는다", "검증 완료를 뜻하지 않는다"):
            if marker not in joined:
                problems.append(f"honesty에 {marker!r} 없음")

    cli_device = run_cli(["-m", "qa.pi_session", "--device-confirmed", "--json"])
    ctx.note(
        "python3 -m qa.pi_session --device-confirmed --json -> "
        f"종료코드 {cli_device.returncode}")
    if cli_device.returncode != 1:
        problems.append(
            f"장치 확인 CLI 종료코드 기대 1, 실제 {cli_device.returncode}: "
            f"{cli_device.stderr[:200]}")
    device_confirmed_blockers: list = []
    try:
        device_report = json.loads(cli_device.stdout)
        device_confirmed_blockers = [b["id"] for b in device_report.get("blockers", [])]
    except json.JSONDecodeError as e:
        problems.append(f"장치 확인 CLI --json 파싱 실패: {e}")
    if device_confirmed_blockers != ["pi_camera_command_missing"]:
        problems.append(
            "장치 확인 CLI blockers 기대 ['pi_camera_command_missing'], "
            f"실제 {device_confirmed_blockers}")

    passed: dict = {}
    blocked_inproc: dict = {}
    real: dict = {}
    wrong_source: dict = {}
    error_report: dict = {}
    boom: dict = {}
    real_files_ok = False
    fake_session = FakeSession()
    blocked_session = FakeSession()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        passed = run_pi_full_session(
            output_dir=root / "c", device_confirmed=True, which=_libcamera,
            session_fn=fake_session, session_id=PI_FULL_SESSION_ID)
        ctx.note(
            f"run_pi_full_session 가짜 session -> status={passed.get('status')}, "
            f"summary={passed.get('summary')}")
        if passed.get("status") != "passed":
            problems.append(f"가짜 session status 기대 passed, 실제 {passed.get('status')}")
        if passed.get("attempted") is not True:
            problems.append(f"가짜 session attempted 기대 True, 실제 {passed.get('attempted')}")
        if passed.get("ready_for_real_capture") is not True:
            problems.append(
                "가짜 session ready_for_real_capture 기대 True, 실제 "
                f"{passed.get('ready_for_real_capture')}")
        if passed.get("source") != "mock":
            problems.append(f"가짜 session source 기대 mock, 실제 {passed.get('source')}")
        if passed.get("capture_source") != "pi-camera":
            problems.append(
                "가짜 session capture_source 기대 pi-camera, 실제 "
                f"{passed.get('capture_source')}")
        if passed.get("session_id") != PI_FULL_SESSION_ID:
            problems.append(
                f"session_id 기대 {PI_FULL_SESSION_ID}, 실제 {passed.get('session_id')}")
        if len(fake_session.calls) != 1:
            problems.append(f"가짜 session 호출 기대 1회, 실제 {len(fake_session.calls)}회")
        elif fake_session.calls[0].get("bin_ids") != demo_bin_ids() \
                or fake_session.calls[0].get("session_id") != PI_FULL_SESSION_ID:
            problems.append(f"가짜 session 호출 인자 이상: {fake_session.calls[0]}")
        bins = passed.get("bins") or []
        if len(bins) != 6:
            problems.append(f"bins 기대 6개, 실제 {len(bins)}개")
        by_bin = {b.get("bin_id"): b for b in bins}
        a0102 = by_bin.get("A-01-02") or {}
        for key, expected in (("book_qty", 8), ("counted_qty", 5), ("diff", -3),
                              ("photo_sha256", PI_FULL_FAKE_SHA),
                              ("photo_image_ref", "A-01-02.jpg")):
            if a0102.get(key) != expected:
                problems.append(f"A-01-02 {key} 기대 {expected}, 실제 {a0102.get(key)}")
        if a0102.get("verdict") != "short":
            problems.append(f"A-01-02 verdict 기대 short, 실제 {a0102.get('verdict')}")
        b0102 = by_bin.get("B-01-02") or {}
        if b0102.get("diff") != 3 or b0102.get("verdict") != "over":
            problems.append(f"B-01-02 기대 diff 3/over, 실제 {b0102}")
        summary_map = passed.get("summary") or {}
        for key, expected in (("counted_bins", 6), ("matched", 4), ("mismatched", 2),
                              ("abs_diff_total", 6), ("net_diff", 0)):
            if summary_map.get(key) != expected:
                problems.append(f"summary.{key} 기대 {expected}, 실제 {summary_map.get(key)}")

        blocked_inproc = run_pi_full_session(
            output_dir=root / "blocked", device_confirmed=False, which=_no_command,
            session_fn=blocked_session)
        ctx.note(
            f"run_pi_full_session 차단 -> status={blocked_inproc.get('status')}, "
            f"session 호출 {len(blocked_session.calls)}건")
        if blocked_inproc.get("status") != "blocked":
            problems.append(f"차단 시 status 기대 blocked, 실제 {blocked_inproc.get('status')}")
        if blocked_session.calls != []:
            problems.append(f"차단 시 session을 부르면 안 된다: 호출 {blocked_session.calls}")

        out_dir = root / "captures"
        real = run_pi_full_session(
            output_dir=out_dir, device_confirmed=True, which=_libcamera,
            runner=_ok_runner, session_id="PI-FULL-REAL")
        ctx.note(
            f"run_pi_full_session 실제 pi_session+가짜 runner -> "
            f"status={real.get('status')}, summary={real.get('summary')}")
        if real.get("status") != "passed":
            problems.append(
                f"실제 pi_session+가짜 runner status 기대 passed, 실제 {real.get('status')}")
        expected_sha = hashlib.sha256(PI_FULL_FAKE_CONTENT).hexdigest()
        for entry in real.get("bins") or []:
            if entry.get("photo_sha256") != expected_sha:
                problems.append(
                    f"실제 pi_session {entry.get('bin_id')} photo_sha256 기대 "
                    f"{expected_sha}, 실제 {entry.get('photo_sha256')}")
        real_files_ok = all((out_dir / f"{bin_id}.jpg").is_file()
                            for bin_id in demo_bin_ids())
        if not real_files_ok:
            problems.append("실제 pi_session 캡처 파일이 빈별로 모두 있지 않다")
        if (real.get("summary") or {}).get("matched") != 4:
            problems.append(
                f"실제 pi_session matched 기대 4, 실제 {(real.get('summary') or {}).get('matched')}")

        wrong_result = _passed_result()
        wrong_result["capture_source"] = "file"
        wrong_source = run_pi_full_session(
            output_dir=root / "wrong", device_confirmed=True, which=_libcamera,
            session_fn=FakeSession(result=wrong_result))
        ctx.note(
            f"run_pi_full_session capture_source file -> status={wrong_source.get('status')}, "
            f"error_type={wrong_source.get('error_type')}")
        if wrong_source.get("status") != "failed" \
                or wrong_source.get("error_type") != "unexpected_capture_source":
            problems.append(
                f"capture_source 차단 이상: {wrong_source.get('status')}/{wrong_source.get('error_type')}")
        if wrong_source.get("summary") is not None:
            problems.append("capture_source 실패 시 summary는 None이어야 한다")

        error_report = run_pi_full_session(
            output_dir=root / "error", device_confirmed=True, which=_libcamera,
            session_fn=_PiErrorSession())
        ctx.note(
            f"run_pi_full_session PiCaptureError -> status={error_report.get('status')}, "
            f"error_type={error_report.get('error_type')}")
        if error_report.get("status") != "failed" \
                or error_report.get("error_type") != "PiCaptureError":
            problems.append(
                f"오류 차단 이상: {error_report.get('status')}/{error_report.get('error_type')}")

        boom = run_pi_full_session(
            output_dir=root / "boom", device_confirmed=True, which=_libcamera,
            session_fn=_BoomSession())
        ctx.note(
            f"run_pi_full_session RuntimeError -> status={boom.get('status')}, "
            f"error_type={boom.get('error_type')}")
        if boom.get("status") != "failed" \
                or boom.get("error_type") != "RuntimeError":
            problems.append(
                f"일반 예외 차단 이상: {boom.get('status')}/{boom.get('error_type')}")

    dumped = "".join(
        json.dumps(item, ensure_ascii=False)
        for item in (passed, blocked_inproc, real, wrong_source, error_report,
                     boom, report)) + result.stdout + result_j.stdout + cli_device.stdout
    sentinel_leaked = PI_FULL_SENTINEL in dumped
    ctx.note(f"예외 원본 문자열 누출 -> {sentinel_leaked}")
    if sentinel_leaked:
        problems.append("일반 예외 원본 문자열이 pi_session 보고나 CLI 출력에 새어 나왔다")

    summary = {"feature": "pi-session-full",
               "blocked_blockers": blocked_blockers,
               "default_exit_code": result.returncode,
               "device_confirmed_blockers": device_confirmed_blockers,
               "fake_passed": passed.get("status") == "passed",
               "session_id": passed.get("session_id"),
               "matched": (passed.get("summary") or {}).get("matched"),
               "mismatched": (passed.get("summary") or {}).get("mismatched"),
               "abs_diff_total": (passed.get("summary") or {}).get("abs_diff_total"),
               "net_diff": (passed.get("summary") or {}).get("net_diff"),
               "blocked_session_calls": len(blocked_session.calls),
               "real_session_passed": real.get("status") == "passed",
               "real_files_ok": real_files_ok,
               "fake_capture_sha256": hashlib.sha256(PI_FULL_FAKE_CONTENT).hexdigest(),
               "unexpected_capture_source_blocked":
                   wrong_source.get("error_type") == "unexpected_capture_source",
               "pi_capture_error_blocked":
                   error_report.get("error_type") == "PiCaptureError",
               "sentinel_leaked": sentinel_leaked,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"pi-full-session-blocked.json": result_j.stdout,
                    "pi-full-session-passed.json": json.dumps(
                        passed, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_file_fallback(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from demo.fallback import (build_fallback_manifest, fake_photo_bytes,
                               validate_fallback)

    manifest: dict = {}
    fallback_text = ""
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "assets"
        result = subprocess.run(
            [sys.executable, "-m", "demo.fallback", "--out", str(out_dir)],
            cwd=ROOT, env=clean_env(), capture_output=True, text=True,
            timeout=120)
        ctx.note(
            f"python3 -m demo.fallback --out <tmp> -> 종료코드 {result.returncode}")
        if result.returncode != 0:
            problems.append(
                f"demo.fallback CLI 종료코드 기대 0, 실제 {result.returncode}: "
                f"{result.stderr[:200]}")
        if "검증 통과" not in result.stdout:
            problems.append("demo.fallback CLI stdout에 '검증 통과' 없음")
        json_path = out_dir / "fallback.json"
        txt_path = out_dir / "fallback.txt"
        if json_path.is_file():
            try:
                manifest = json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                problems.append(f"fallback.json 파싱 실패: {e}")
        else:
            problems.append("CLI가 fallback.json을 만들지 않았다")
        if txt_path.is_file():
            fallback_text = txt_path.read_text(encoding="utf-8")
        else:
            problems.append("CLI가 fallback.txt를 만들지 않았다")

    validate_problems: list[str] = []
    if manifest:
        validate_problems = validate_fallback(manifest)
        ctx.note(f"validate_fallback(CLI manifest) -> 문제 {len(validate_problems)}건")
        if validate_problems:
            problems.append(f"validate_fallback 문제: {validate_problems}")
        if manifest.get("cut_index") != FALLBACK_CUT_INDEX:
            problems.append(
                f"cut_index 기대 {FALLBACK_CUT_INDEX}, 실제 {manifest.get('cut_index')}")
        if manifest.get("replaces") != "pi-placeholder":
            problems.append(
                f"replaces 기대 pi-placeholder, 실제 {manifest.get('replaces')}")
        if manifest.get("decision_date") != FALLBACK_DECISION_DATE:
            problems.append(
                f"decision_date 기대 {FALLBACK_DECISION_DATE}, "
                f"실제 {manifest.get('decision_date')}")
        if manifest.get("is_pi_real_capture") is not False:
            problems.append(
                "is_pi_real_capture 기대 False, 실제 "
                f"{manifest.get('is_pi_real_capture')}")
        if manifest.get("capture_source") != "file":
            problems.append(
                f"capture_source 기대 file, 실제 {manifest.get('capture_source')}")
        if manifest.get("source") != "mock":
            problems.append(f"source 기대 mock, 실제 {manifest.get('source')}")
        if manifest.get("session_id") != FALLBACK_SESSION_ID:
            problems.append(
                f"session_id 기대 {FALLBACK_SESSION_ID}, "
                f"실제 {manifest.get('session_id')}")
        summary_map = manifest.get("summary") or {}
        for key, expected in FALLBACK_EXPECTED_SUMMARY.items():
            if summary_map.get(key) != expected:
                problems.append(
                    f"summary.{key} 기대 {expected}, 실제 {summary_map.get(key)}")
        bins = manifest.get("bins") or []
        if len(bins) != 6:
            problems.append(f"bins 기대 6개, 실제 {len(bins)}개")
        for entry in bins:
            bin_id = entry.get("bin_id")
            expected_sha = hashlib.sha256(fake_photo_bytes(str(bin_id))).hexdigest()
            photo = entry.get("photo") or {}
            if photo.get("sha256") != expected_sha:
                problems.append(
                    f"bin {bin_id} photo sha256 기대 {expected_sha}, "
                    f"실제 {photo.get('sha256')}")
        by_bin = {b.get("bin_id"): b for b in bins}
        a0102 = by_bin.get("A-01-02") or {}
        if a0102.get("verdict") != "short":
            problems.append(f"A-01-02 verdict 기대 short, 실제 {a0102.get('verdict')}")
        if a0102.get("diff") != -3:
            problems.append(f"A-01-02 diff 기대 -3, 실제 {a0102.get('diff')}")
        if a0102.get("book_qty") != 8:
            problems.append(f"A-01-02 book_qty 기대 8, 실제 {a0102.get('book_qty')}")
        if a0102.get("counted_qty") != 5:
            problems.append(
                f"A-01-02 counted_qty 기대 5, 실제 {a0102.get('counted_qty')}")
        joined_honesty = " ".join(
            str(line) for line in manifest.get("honesty", []))
        for marker in FALLBACK_HONESTY_MARKERS:
            if marker not in joined_honesty:
                problems.append(f"honesty에 {marker!r} 없음")
        built = build_fallback_manifest()
        if built.get("summary") != manifest.get("summary"):
            problems.append("build_fallback_manifest summary가 CLI manifest와 다르다")
        if built.get("session_id") != manifest.get("session_id"):
            problems.append("build_fallback_manifest session_id가 CLI manifest와 다르다")
    if fallback_text:
        if "파일 입력 폴백" not in fallback_text:
            problems.append("fallback.txt에 '파일 입력 폴백' 없음")
        if "데모 기준" not in fallback_text:
            problems.append("fallback.txt에 '데모 기준' 없음")
        if "Pi 실촬영이 아닙니다" not in fallback_text:
            problems.append("fallback.txt에 'Pi 실촬영이 아닙니다' 없음")

    asset_valid = False
    asset_path = ROOT / "demo" / "assets" / "fallback.json"
    if asset_path.is_file():
        try:
            asset = json.loads(asset_path.read_text(encoding="utf-8"))
            asset_problems = validate_fallback(asset)
            asset_summary = asset.get("summary") or {}
            asset_valid = asset_problems == [] \
                and all(asset_summary.get(key) == expected
                        for key, expected in FALLBACK_EXPECTED_SUMMARY.items())
            ctx.note(f"저장소 자산 fallback.json 유효 -> {asset_valid}")
            if not asset_valid:
                problems.append(f"저장소 자산 fallback.json 문제: {asset_problems}")
        except json.JSONDecodeError as e:
            problems.append(f"저장소 자산 fallback.json 파싱 실패: {e}")
    else:
        problems.append("저장소 자산 demo/assets/fallback.json이 없다")

    tamper_detected = False
    capture_tamper_detected = False
    if manifest:
        tampered = copy.deepcopy(manifest)
        tampered["is_pi_real_capture"] = True
        tamper_detected = bool(validate_fallback(tampered))
        tampered2 = copy.deepcopy(manifest)
        tampered2["capture_source"] = "pi-camera"
        capture_tamper_detected = bool(validate_fallback(tampered2))
    ctx.note(f"폴백 변조 탐지 -> 실촬영 변조 {tamper_detected}, "
             f"capture_source 변조 {capture_tamper_detected}")
    if not tamper_detected:
        problems.append("변조 탐지 실패: is_pi_real_capture를 True로 바꿔도 문제를 찾지 못했다")
    if not capture_tamper_detected:
        problems.append("변조 탐지 실패: capture_source를 pi-camera로 바꿔도 문제를 찾지 못했다")

    summary = {"feature": "file-fallback",
               "cut_index": manifest.get("cut_index"),
               "decision_date": manifest.get("decision_date"),
               "is_pi_real_capture": manifest.get("is_pi_real_capture"),
               "capture_source": manifest.get("capture_source"),
               "source": manifest.get("source"),
               "session_id": manifest.get("session_id"),
               "manifest_summary": manifest.get("summary"),
               "validate_problems": validate_problems,
               "tamper_detected": tamper_detected,
               "capture_source_tamper_detected": capture_tamper_detected,
               "asset_valid": asset_valid,
               "fake_photo_sha256": hashlib.sha256(
                   fake_photo_bytes("A-01-02")).hexdigest(),
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"fallback.json": json.dumps(
                       manifest, ensure_ascii=False, indent=2) + "\n",
                    "fallback.txt": fallback_text})
    return summary


def drive_submission_inventory(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.submission_inventory import (build_inventory, validate_inventory,
                                          write_inventory)

    result = run_cli(["-m", "qa.submission_inventory"])
    ctx.note(f"python3 -m qa.submission_inventory -> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(
            f"submission_inventory 기본 종료코드 기대 0, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("제출물 18/18개 존재", "BLOCKERS: 1",
                   "pi_real_capture_pending", "SUBMISSION_READY: false",
                   "실제로 제출하지 않는다", "Pi 실촬영 검증 전"):
        if needle not in result.stdout:
            problems.append(f"submission_inventory 텍스트에 {needle!r} 없음")

    result_j = run_cli(["-m", "qa.submission_inventory", "--json"])
    ctx.note(
        f"python3 -m qa.submission_inventory --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 0:
        problems.append(
            f"submission_inventory --json 종료코드 기대 0, 실제 {result_j.returncode}: "
            f"{result_j.stderr[:200]}")
    inventory: dict = {}
    try:
        inventory = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"--json 파싱 실패: {e}")
    blocker_ids: list = []
    if inventory:
        if inventory.get("total_files") != INVENTORY_TOTAL_FILES:
            problems.append(
                f"total_files 기대 {INVENTORY_TOTAL_FILES}, 실제 {inventory.get('total_files')}")
        if inventory.get("present_files") != INVENTORY_TOTAL_FILES:
            problems.append(
                f"present_files 기대 {INVENTORY_TOTAL_FILES}, 실제 {inventory.get('present_files')}")
        if inventory.get("missing") != []:
            problems.append(f"missing 기대 [], 실제 {inventory.get('missing')}")
        blocker_ids = [b.get("id") for b in inventory.get("blockers", [])]
        if blocker_ids != list(EXPECTED_BLOCKER_IDS):
            problems.append(
                f"blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {blocker_ids}")
        if inventory.get("submission_ready") is not False:
            problems.append(
                f"submission_ready 기대 False, 실제 {inventory.get('submission_ready')}")
        if inventory.get("repo_url") != INVENTORY_REPO_URL:
            problems.append(
                f"repo_url 기대 {INVENTORY_REPO_URL}, 실제 {inventory.get('repo_url')}")
        if "2026-11-05 11:00 KST" not in str(inventory.get("deadline")):
            problems.append(f"deadline에 KST 마감 없음: {inventory.get('deadline')}")
        entries = inventory.get("deliverables") or []
        if len(entries) != INVENTORY_TOTAL_FILES:
            problems.append(f"deliverables 기대 18개, 실제 {len(entries)}개")
        categories = [e.get("category") for e in entries]
        for category, expected in (("document", 6), ("video", 2), ("demo_asset", 10)):
            if categories.count(category) != expected:
                problems.append(
                    f"category {category} 기대 {expected}, 실제 {categories.count(category)}")
        total_bytes = 0
        for entry in entries:
            rel = entry.get("path")
            path = ROOT / str(rel)
            if not path.is_file():
                problems.append(f"제출물 파일 없음: {rel}")
                continue
            data = path.read_bytes()
            total_bytes += len(data)
            if entry.get("exists") is not True:
                problems.append(f"{rel}: exists 기대 True, 실제 {entry.get('exists')}")
            if entry.get("size_bytes") != len(data):
                problems.append(
                    f"{rel}: size_bytes 기대 {len(data)}, 실제 {entry.get('size_bytes')}")
            expected_sha = hashlib.sha256(data).hexdigest()
            if entry.get("sha256") != expected_sha:
                problems.append(f"{rel}: sha256이 실제 파일 해시와 다르다")
        if inventory.get("total_bytes") != total_bytes:
            problems.append(
                f"total_bytes 기대 {total_bytes}, 실제 {inventory.get('total_bytes')}")
        joined = " ".join(str(x) for x in inventory.get("honesty", []))
        for marker in ("실제로 제출하지 않는다", "Pi 실촬영 검증 전", "데모 기준",
                       "제출 가능을 뜻하지 않는다"):
            if marker not in joined:
                problems.append(f"honesty에 {marker!r} 없음")

    built = build_inventory(ROOT)
    validate_problems = validate_inventory(built, ROOT)
    ctx.note(f"validate_inventory(build_inventory) -> 문제 {len(validate_problems)}건")
    if validate_problems:
        problems.append(f"validate_inventory 문제: {validate_problems}")
    if built.get("total_files") != INVENTORY_TOTAL_FILES \
            or built.get("present_files") != INVENTORY_TOTAL_FILES:
        problems.append(f"build_inventory 총수 이상: {built.get('total_files')}/{built.get('present_files')}")

    tamper_detected = False
    totals_tamper_detected = False
    ready_tamper_detected = False
    if built:
        tampered = copy.deepcopy(built)
        tampered["deliverables"][0]["sha256"] = "0" * 64
        tamper_problems = validate_inventory(tampered, ROOT)
        tamper_detected = any("README.md" in p and "sha256" in p
                              for p in tamper_problems)
        tampered2 = copy.deepcopy(built)
        tampered2["total_bytes"] = int(tampered2.get("total_bytes") or 0) + 1
        totals_tamper_detected = any("total_bytes" in p
                                     for p in validate_inventory(tampered2, ROOT))
        tampered3 = copy.deepcopy(built)
        tampered3["submission_ready"] = True
        tampered3["blockers"] = []
        ready_problems = validate_inventory(tampered3, ROOT)
        ready_tamper_detected = any("submission_ready" in p for p in ready_problems) \
            and any("blocker" in p for p in ready_problems)
    ctx.note(f"인벤토리 변조 탐지 -> sha {tamper_detected}, 합계 {totals_tamper_detected}, "
             f"ready {ready_tamper_detected}")
    if not tamper_detected:
        problems.append("변조 탐지 실패: sha256을 바꿔도 문제를 찾지 못했다")
    if not totals_tamper_detected:
        problems.append("변조 탐지 실패: total_bytes를 바꿔도 문제를 찾지 못했다")
    if not ready_tamper_detected:
        problems.append("변조 탐지 실패: submission_ready/blockers를 바꿔도 문제를 찾지 못했다")

    empty_missing_count = None
    with tempfile.TemporaryDirectory() as tmp:
        empty = build_inventory(Path(tmp))
        empty_missing_count = len(empty.get("missing") or [])
        ctx.note(f"빈 루트 인벤토리 -> present {empty.get('present_files')}, "
                 f"missing {empty_missing_count}")
        if empty.get("present_files") != 0 or empty_missing_count != INVENTORY_TOTAL_FILES:
            problems.append(f"빈 루트 기대 present 0/missing 18, 실제 {empty}")
        if validate_inventory(empty, Path(tmp)) != []:
            problems.append("빈 루트의 정직한 누락 인벤토리가 검증에서 모순으로 잡혔다")

    write_roundtrip_ok = False
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "inventory"
        written = write_inventory(out_dir, ROOT)
        names = sorted(p.name for p in written)
        if names != ["submission-inventory.json", "submission-inventory.txt"]:
            problems.append(f"write_inventory 산출 이름 이상: {names}")
        else:
            try:
                data = json.loads(
                    (out_dir / "submission-inventory.json").read_text(encoding="utf-8"))
                text = (out_dir / "submission-inventory.txt").read_text(encoding="utf-8")
                write_roundtrip_ok = validate_inventory(data, ROOT) == [] \
                    and data.get("total_files") == INVENTORY_TOTAL_FILES \
                    and "SUBMISSION_READY: false" in text \
                    and "pi_real_capture_pending" in text
            except (OSError, json.JSONDecodeError) as e:
                problems.append(f"write_inventory 왕복 실패: {e}")
    ctx.note(f"write_inventory 왕복 -> {write_roundtrip_ok}")
    if not write_roundtrip_ok:
        problems.append("write_inventory 왕복 검증이 통과하지 않았다")

    # 최종 묶음 교차 대조: 같은 제출물의 qa.final_package 보고와 대조한다.
    fp: dict = {}
    fp_cross_ok = False
    result_fp = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                         "--date", FINAL_PACKAGE_DATE, "--json"])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {FINAL_PACKAGE_DATE} --json "
             f"-> 종료코드 {result_fp.returncode}")
    cross_before = len(problems)
    if result_fp.returncode != 0:
        problems.append(
            f"final_package 교차 종료코드 기대 0, 실제 {result_fp.returncode}: "
            f"{result_fp.stderr[:200]}")
    try:
        fp = json.loads(result_fp.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"final_package 교차 --json 파싱 실패: {e}")
    if fp:
        if fp.get("status") != "blocked":
            problems.append(
                f"final_package status 기대 'blocked', 실제 {fp.get('status')}")
        if fp.get("inventory_present") != inventory.get("present_files"):
            problems.append(
                f"final_package inventory_present가 인벤토리 present_files와 "
                f"다르다: {fp.get('inventory_present')} != "
                f"{inventory.get('present_files')}")
        if fp.get("inventory_total") != inventory.get("total_files"):
            problems.append(
                f"final_package inventory_total가 인벤토리 total_files와 "
                f"다르다: {fp.get('inventory_total')} != "
                f"{inventory.get('total_files')}")
        if fp.get("inventory_missing") != inventory.get("missing"):
            problems.append(
                f"final_package inventory_missing가 인벤토리 missing와 "
                f"다르다: {fp.get('inventory_missing')} != "
                f"{inventory.get('missing')}")
        if fp.get("export_total_bytes") != inventory.get("total_bytes"):
            problems.append(
                f"final_package export_total_bytes가 인벤토리 total_bytes와 "
                f"다르다: {fp.get('export_total_bytes')} != "
                f"{inventory.get('total_bytes')}")
        if fp.get("blockers") != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"final_package blockers 이상: {fp.get('blockers')}")
        if fp.get("submission_ready") is not False:
            problems.append(
                f"final_package submission_ready 기대 False, "
                f"실제 {fp.get('submission_ready')}")
    fp_cross_ok = bool(fp) and len(problems) == cross_before
    ctx.note(f"인벤토리↔최종 묶음 교차 대조 -> fp_cross_ok={fp_cross_ok}, "
             f"fp_inventory_present={fp.get('inventory_present')}, "
             f"fp_inventory_total={fp.get('inventory_total')}")

    summary = {"feature": "submission-inventory",
               "total_files": inventory.get("total_files"),
               "present_files": inventory.get("present_files"),
               "total_bytes": inventory.get("total_bytes"),
               "missing_count": len(inventory.get("missing") or []),
               "blocker_ids": blocker_ids,
               "submission_ready": inventory.get("submission_ready"),
               "validate_problems": validate_problems,
               "tamper_detected": tamper_detected,
               "totals_tamper_detected": totals_tamper_detected,
               "ready_tamper_detected": ready_tamper_detected,
               "empty_missing_count": empty_missing_count,
               "write_roundtrip_ok": write_roundtrip_ok,
               "fp_inventory_present": fp.get("inventory_present"),
               "fp_inventory_total": fp.get("inventory_total"),
               "fp_status": fp.get("status"),
               "fp_cross_ok": fp_cross_ok,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"submission-inventory.json": result_j.stdout,
                    "submission-inventory.txt": result.stdout,
                    "submission-inventory-final-package.json": result_fp.stdout})
    return summary

def drive_fallback_decision(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.fallback_decision import (build_decision, evaluate_decision,
                                      today_kst, validate_decision)

    result = run_cli(["-m", "qa.fallback_decision", "--date",
                      FALLBACK_DECISION_PENDING_DATE])
    ctx.note(f"python3 -m qa.fallback_decision --date {FALLBACK_DECISION_PENDING_DATE} "
             f"-> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(
            f"fallback_decision pending 종료코드 기대 0, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("STATUS: pending",
                   f"DECISION_DATE: {FALLBACK_DECISION_DATE}",
                   "FALLBACK_ADOPTED: false", "Pi 실촬영이 아닙니다"):
        if needle not in result.stdout:
            problems.append(f"fallback_decision 텍스트에 {needle!r} 없음")

    result_j = run_cli(["-m", "qa.fallback_decision", "--date",
                        FALLBACK_DECISION_PENDING_DATE, "--json"])
    ctx.note(f"python3 -m qa.fallback_decision --date {FALLBACK_DECISION_PENDING_DATE} "
             f"--json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 0:
        problems.append(
            f"fallback_decision pending --json 종료코드 기대 0, 실제 "
            f"{result_j.returncode}: {result_j.stderr[:200]}")
    pending: dict = {}
    try:
        pending = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"pending --json 파싱 실패: {e}")
    pending_blockers: list = []
    if pending:
        if pending.get("status") != "pending":
            problems.append(f"status 기대 'pending', 실제 {pending.get('status')}")
        if pending.get("fallback_adopted") is not False:
            problems.append(
                f"fallback_adopted 기대 False, 실제 {pending.get('fallback_adopted')}")
        if pending.get("pi_ready") is not False:
            problems.append(f"pi_ready 기대 False, 실제 {pending.get('pi_ready')}")
        pending_blockers = list(pending.get("pi_blockers") or [])
        if pending_blockers != list(EXPECTED_PI_READINESS_BLOCKER_IDS):
            problems.append(
                f"pi_blockers 기대 {list(EXPECTED_PI_READINESS_BLOCKER_IDS)}, "
                f"실제 {pending_blockers}")
        if pending.get("decision_date") != FALLBACK_DECISION_DATE:
            problems.append(
                f"decision_date 기대 {FALLBACK_DECISION_DATE}, 실제 "
                f"{pending.get('decision_date')}")
        if pending.get("fallback_asset") != FALLBACK_DECISION_ASSET:
            problems.append(
                f"fallback_asset 기대 {FALLBACK_DECISION_ASSET}, 실제 "
                f"{pending.get('fallback_asset')}")
        if pending.get("fallback_render") != FALLBACK_DECISION_RENDER:
            problems.append(
                f"fallback_render 기대 {FALLBACK_DECISION_RENDER}, 실제 "
                f"{pending.get('fallback_render')}")
        if pending.get("is_pi_real_capture") is not False:
            problems.append(
                f"is_pi_real_capture 기대 False, 실제 {pending.get('is_pi_real_capture')}")
        joined = " ".join(str(x) for x in pending.get("honesty", []))
        for marker in ("Pi 실촬영이 아닙니다", "Pi 실촬영 검증 완료를 뜻하지 않는다",
                       "결정일 전에는 폴백을 확정하지 않는다"):
            if marker not in joined:
                problems.append(f"honesty에 {marker!r} 없음")

    result_due = run_cli(["-m", "qa.fallback_decision", "--date",
                          FALLBACK_DECISION_DATE, "--json"])
    ctx.note(f"python3 -m qa.fallback_decision --date {FALLBACK_DECISION_DATE} "
             f"--json -> 종료코드 {result_due.returncode} "
             "(가정 날짜 구동이며 오늘 실제 전환 확정이 아니다)")
    if result_due.returncode != 0:
        problems.append(
            f"fallback_decision due --json 종료코드 기대 0, 실제 "
            f"{result_due.returncode}: {result_due.stderr[:200]}")
    due: dict = {}
    try:
        due = json.loads(result_due.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"due --json 파싱 실패: {e}")
    if due:
        if due.get("status") != "fallback_due":
            problems.append(f"due status 기대 'fallback_due', 실제 {due.get('status')}")
        if due.get("fallback_adopted") is not True:
            problems.append(
                f"due fallback_adopted 기대 True, 실제 {due.get('fallback_adopted')}")

    # 기본 날짜 구동 — --date 없는 기본 실행이 KST 오늘을 쓰는지 확인한다.
    # 시스템 로컬 날짜(UTC VM에서는 하루 전)를 쓰면 KST 결정일
    # 00:00~09:00 구간에 pending으로 잘못 판정되므로 이를 증거로 남긴다.
    result_default = run_cli(["-m", "qa.fallback_decision", "--json"])
    ctx.note(f"python3 -m qa.fallback_decision --json (기본 날짜) "
             f"-> 종료코드 {result_default.returncode}")
    if result_default.returncode != 0:
        problems.append(
            f"fallback_decision 기본 --json 종료코드 기대 0, 실제 "
            f"{result_default.returncode}: {result_default.stderr[:200]}")
    default_rep: dict = {}
    try:
        default_rep = json.loads(result_default.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"기본 --json 파싱 실패: {e}")
    kst_today = today_kst()
    default_date_is_kst = bool(default_rep) and default_rep.get("date") == kst_today
    ctx.note(f"폴백 결정 기본 날짜 -> date={default_rep.get('date')} "
             f"kst_today={kst_today} status={default_rep.get('status')}")
    if default_rep:
        if not default_date_is_kst:
            problems.append(
                f"기본 날짜 기대 KST 오늘 {kst_today}, 실제 {default_rep.get('date')}")
        v_default = validate_decision(default_rep)
        if v_default:
            problems.append(f"기본 보고 validate 문제: {v_default}")
        expected_default = evaluate_decision(
            str(default_rep.get("date")), bool(default_rep.get("pi_ready")),
            list(default_rep.get("pi_blockers") or []))
        if default_rep.get("status") != expected_default["status"]:
            problems.append(
                f"기본 status 기대 {expected_default['status']}, "
                f"실제 {default_rep.get('status')}")
        if default_rep.get("fallback_adopted") != expected_default["fallback_adopted"]:
            problems.append(
                f"기본 fallback_adopted 기대 {expected_default['fallback_adopted']}, "
                f"실제 {default_rep.get('fallback_adopted')}")

    # 영상 선택·최종 묶음과의 교차 대조 — 결정일(가정 날짜) 기준.
    # 가정 날짜 구동이며 오늘 실제 전환 확정이 아니다.
    vs_report: dict = {}
    fp_report: dict = {}
    result_vs = run_cli(["-m", "qa.video_selection", "--date",
                         FALLBACK_DECISION_DATE, "--json"])
    ctx.note(f"python3 -m qa.video_selection --date {FALLBACK_DECISION_DATE} "
             f"--json -> 종료코드 {result_vs.returncode} "
             "(폴백 결정 due와 같은 결정일, 가정 날짜 구동)")
    if result_vs.returncode != 0:
        problems.append(
            f"video_selection due --json 종료코드 기대 0, 실제 "
            f"{result_vs.returncode}: {result_vs.stderr[:200]}")
    try:
        vs_report = json.loads(result_vs.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"video_selection due --json 파싱 실패: {e}")
    result_fp = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                         "--date", FALLBACK_DECISION_DATE, "--json"])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {FALLBACK_DECISION_DATE} --json "
             f"-> 종료코드 {result_fp.returncode} "
             "(폴백 결정 due와 같은 결정일, 가정 날짜 구동)")
    if result_fp.returncode != 0:
        problems.append(
            f"final_package due --json 종료코드 기대 0, 실제 "
            f"{result_fp.returncode}: {result_fp.stderr[:200]}")
    try:
        fp_report = json.loads(result_fp.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"final_package due --json 파싱 실패: {e}")
    fp_cross_ok = False
    if vs_report and fp_report and due:
        cross_before = len(problems)
        if vs_report.get("fallback_status") != due.get("status"):
            problems.append(
                f"video_selection fallback_status가 fallback_decision due와 "
                f"다르다: {vs_report.get('fallback_status')} != {due.get('status')}")
        if vs_report.get("fallback_adopted") is not True:
            problems.append(
                f"video_selection fallback_adopted 기대 True, 실제 "
                f"{vs_report.get('fallback_adopted')}")
        if vs_report.get("selected_video") != FALLBACK_DECISION_RENDER:
            problems.append(
                f"video_selection selected_video 기대 {FALLBACK_DECISION_RENDER}, "
                f"실제 {vs_report.get('selected_video')}")
        if vs_report.get("selection_reason") != "fallback_due":
            problems.append(
                f"video_selection selection_reason 기대 fallback_due, 실제 "
                f"{vs_report.get('selection_reason')}")
        if vs_report.get("submission_ready") is not False:
            problems.append(
                f"video_selection submission_ready 기대 False, 실제 "
                f"{vs_report.get('submission_ready')}")
        try:
            fallback_size = (ROOT / FALLBACK_DECISION_RENDER).stat().st_size
        except OSError:
            fallback_size = None
        if fallback_size is not None \
                and vs_report.get("selected_size") != fallback_size:
            problems.append(
                f"video_selection selected_size가 폴백 렌더 실측과 다르다: "
                f"{vs_report.get('selected_size')} != {fallback_size}")
        if fp_report.get("status") != "blocked":
            problems.append(
                f"final_package status 기대 'blocked', 실제 {fp_report.get('status')}")
        for key in ("fallback_status", "selected_video", "selection_reason",
                    "selected_size"):
            if fp_report.get(key) != vs_report.get(key):
                problems.append(
                    f"final_package {key}가 video_selection과 다르다: "
                    f"{fp_report.get(key)} != {vs_report.get(key)}")
        if fp_report.get("fallback_adopted") is not True:
            problems.append(
                f"final_package fallback_adopted 기대 True, 실제 "
                f"{fp_report.get('fallback_adopted')}")
        if fp_report.get("blockers") != ["pi_real_capture_pending"]:
            problems.append(
                f"final_package blockers 이상: {fp_report.get('blockers')}")
        if fp_report.get("submission_ready") is not False:
            problems.append(
                f"final_package submission_ready 기대 False, 실제 "
                f"{fp_report.get('submission_ready')}")
        fp_cross_ok = len(problems) == cross_before
    ctx.note(f"폴백 결정↔영상 선택·최종 묶음 교차 대조 -> fp_cross_ok={fp_cross_ok} "
             "(가정 날짜 구동이며 오늘 실제 전환 확정이 아니다)")

    result_bad = run_cli(["-m", "qa.fallback_decision", "--date",
                          "2026-13-40", "--json"])
    ctx.note(f"python3 -m qa.fallback_decision --date 2026-13-40 --json "
             f"-> 종료코드 {result_bad.returncode}")
    if result_bad.returncode != 2:
        problems.append(
            f"잘못된 날짜 종료코드 기대 2, 실제 {result_bad.returncode}")

    blockers = list(EXPECTED_PI_READINESS_BLOCKER_IDS)
    try:
        ev_pending = evaluate_decision(FALLBACK_DECISION_PENDING_DATE, False, blockers)
        ev_due = evaluate_decision(FALLBACK_DECISION_DATE, False, blockers)
        ev_ready = evaluate_decision(FALLBACK_DECISION_DATE, True, [])
        if ev_pending.get("status") != "pending" \
                or ev_pending.get("fallback_adopted") is not False:
            problems.append(f"evaluate pending 이상: {ev_pending}")
        if ev_due.get("status") != "fallback_due" \
                or ev_due.get("fallback_adopted") is not True:
            problems.append(f"evaluate due 이상: {ev_due}")
        if ev_ready.get("status") != "pi_ready" \
                or ev_ready.get("fallback_adopted") is not False:
            problems.append(f"evaluate pi_ready 이상: {ev_ready}")
        for report in (ev_pending, ev_due, ev_ready):
            v = validate_decision(report)
            if v:
                problems.append(f"validate_decision 정상 보고 문제: {v}")
    except Exception as e:
        problems.append(f"evaluate_decision 실패: {type(e).__name__}: {e}")

    built_pending: dict = {}
    built_ready: dict = {}
    try:
        built_pending = build_decision(today=FALLBACK_DECISION_PENDING_DATE,
                                       pi_probe=PI_READINESS_MISSING_PROBE)
        built_ready = build_decision(today=FALLBACK_DECISION_DATE,
                                     pi_probe=PI_READINESS_READY_PROBE,
                                     device_confirmed=True)
    except Exception as e:
        problems.append(f"build_decision 실패: {type(e).__name__}: {e}")
    if built_pending:
        ctx.note(f"build_decision missing probe -> status={built_pending.get('status')}")
        if built_pending.get("status") != "pending":
            problems.append(f"build pending status 이상: {built_pending.get('status')}")
        if list(built_pending.get("pi_blockers") or []) != blockers:
            problems.append(
                f"build pending pi_blockers 이상: {built_pending.get('pi_blockers')}")
    pi_ready_status = built_ready.get("status") if built_ready else None
    if built_ready:
        ctx.note(f"build_decision ready probe -> status={pi_ready_status}")
        if pi_ready_status != "pi_ready":
            problems.append(f"build ready status 이상: {pi_ready_status}")
        if built_ready.get("pi_blockers") != []:
            problems.append(f"build ready pi_blockers 기대 [], 실제 "
                            f"{built_ready.get('pi_blockers')}")

    adopted_tamper_detected = False
    real_capture_tamper_detected = False
    status_tamper_detected = False
    try:
        base = evaluate_decision(FALLBACK_DECISION_PENDING_DATE, False, blockers)
        t1 = copy.deepcopy(base)
        t1["fallback_adopted"] = True
        adopted_tamper_detected = any("fallback_adopted" in p
                                      for p in validate_decision(t1))
        t2 = evaluate_decision(FALLBACK_DECISION_DATE, False, blockers)
        t2["is_pi_real_capture"] = True
        real_capture_tamper_detected = any("is_pi_real_capture" in p
                                           for p in validate_decision(t2))
        t3 = copy.deepcopy(base)
        t3["status"] = "fallback_due"
        status_tamper_detected = any("status" in p
                                     for p in validate_decision(t3))
    except Exception as e:
        problems.append(f"변조 탐지 구동 실패: {type(e).__name__}: {e}")
    tamper_detected = adopted_tamper_detected and real_capture_tamper_detected \
        and status_tamper_detected
    ctx.note(f"폴백 결정 변조 탐지 -> adopted {adopted_tamper_detected}, "
             f"real_capture {real_capture_tamper_detected}, "
             f"status {status_tamper_detected}")
    if not tamper_detected:
        problems.append("변조 탐지 실패: fallback_adopted/is_pi_real_capture/status 중 "
                        "하나를 바꿔도 문제를 찾지 못했다")

    summary = {"feature": "fallback-decision",
               "pending_status": pending.get("status"),
               "pending_blockers": pending_blockers,
               "default_date": default_rep.get("date"),
               "default_status": default_rep.get("status"),
               "default_fallback_adopted": default_rep.get("fallback_adopted"),
               "default_date_is_kst": default_date_is_kst,
               "default_exit_code": result.returncode,
               "due_status": due.get("status"),
               "due_fallback_adopted": due.get("fallback_adopted"),
               "pi_ready_status": pi_ready_status,
               "pi_ready_with_fake_probe": pi_ready_status == "pi_ready",
               "tamper_detected": tamper_detected,
               "adopted_tamper_detected": adopted_tamper_detected,
               "real_capture_tamper_detected": real_capture_tamper_detected,
               "invalid_date_exit_code": result_bad.returncode,
               "vs_selected_video": vs_report.get("selected_video"),
               "vs_selection_reason": vs_report.get("selection_reason"),
               "vs_selected_size": vs_report.get("selected_size"),
               "fp_fallback_status": fp_report.get("fallback_status"),
               "fp_selected_video": fp_report.get("selected_video"),
               "fp_selected_size": fp_report.get("selected_size"),
               "fp_cross_ok": fp_cross_ok,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"fallback-decision-pending.json": result_j.stdout,
                    "fallback-decision-due.json": result_due.stdout,
                    "fallback-decision-default.json": result_default.stdout,
                    "fallback-decision-video-selection.json": result_vs.stdout,
                    "fallback-decision-final-package.json": result_fp.stdout})
    return summary

def drive_deadline(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.deadline import build_deadline, evaluate_deadline, validate_deadline

    result = run_cli(["-m", "qa.deadline", "--now", DEADLINE_BEFORE_NOW])
    ctx.note(f"python3 -m qa.deadline --now {DEADLINE_BEFORE_NOW} "
             f"-> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(
            f"deadline before 종료코드 기대 0, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("STATUS: before_deadline",
                   "DEADLINE_KST: 2026-11-05T11:00:00+09:00",
                   f"REMAINING_SECONDS: {DEADLINE_BEFORE_REMAINING}",
                   "SUBMISSION_READY: false",
                   "실제로 제출하지 않는다"):
        if needle not in result.stdout:
            problems.append(f"deadline 텍스트에 {needle!r} 없음")

    result_j = run_cli(["-m", "qa.deadline", "--now", DEADLINE_BEFORE_NOW, "--json"])
    ctx.note(f"python3 -m qa.deadline --now {DEADLINE_BEFORE_NOW} --json "
             f"-> 종료코드 {result_j.returncode}")
    if result_j.returncode != 0:
        problems.append(
            f"deadline before --json 종료코드 기대 0, 실제 {result_j.returncode}")
    before: dict = {}
    try:
        before = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"before --json 파싱 실패: {e}")
    if before:
        if before.get("status") != "before_deadline":
            problems.append(f"status 기대 'before_deadline', 실제 {before.get('status')}")
        if before.get("remaining_seconds") != DEADLINE_BEFORE_REMAINING:
            problems.append(
                f"remaining_seconds 기대 {DEADLINE_BEFORE_REMAINING}, "
                f"실제 {before.get('remaining_seconds')}")
        if before.get("is_overdue") is not False:
            problems.append(f"is_overdue 기대 False, 실제 {before.get('is_overdue')}")
        if before.get("blockers") != ["pi_real_capture_pending"]:
            problems.append(f"blockers 이상: {before.get('blockers')}")
        if before.get("submission_ready") is not False:
            problems.append(
                f"submission_ready 기대 False, 실제 {before.get('submission_ready')}")
        joined = " ".join(str(x) for x in before.get("honesty", []))
        for marker in ("실제로 제출하지 않는다", "제출 준비 완료를 뜻하지 않는다",
                       "지각 제출은 고려되지 않는다"):
            if marker not in joined:
                problems.append(f"honesty에 {marker!r} 없음")

    result_due = run_cli(["-m", "qa.deadline", "--now", DEADLINE_DUE_SOON_NOW, "--json"])
    ctx.note(f"python3 -m qa.deadline --now {DEADLINE_DUE_SOON_NOW} --json "
             f"-> 종료코드 {result_due.returncode}")
    due: dict = {}
    try:
        due = json.loads(result_due.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"due_soon --json 파싱 실패: {e}")
    if due:
        if due.get("status") != "due_soon":
            problems.append(f"due status 기대 'due_soon', 실제 {due.get('status')}")
        if due.get("remaining_seconds") != 23 * 3600:
            problems.append(f"due remaining 이상: {due.get('remaining_seconds')}")

    result_over = run_cli(["-m", "qa.deadline", "--now", DEADLINE_OVERDUE_NOW, "--json"])
    ctx.note(f"python3 -m qa.deadline --now {DEADLINE_OVERDUE_NOW} --json "
             f"-> 종료코드 {result_over.returncode}")
    if result_over.returncode != 1:
        problems.append(
            f"deadline overdue 종료코드 기대 1, 실제 {result_over.returncode}")
    over: dict = {}
    try:
        over = json.loads(result_over.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"overdue --json 파싱 실패: {e}")
    if over:
        if over.get("status") != "overdue":
            problems.append(f"overdue status 기대 'overdue', 실제 {over.get('status')}")
        if over.get("remaining_seconds") != 0:
            problems.append(f"overdue remaining 기대 0, 실제 {over.get('remaining_seconds')}")
        if over.get("is_overdue") is not True:
            problems.append(f"overdue is_overdue 기대 True, 실제 {over.get('is_overdue')}")

    result_bad = run_cli(["-m", "qa.deadline", "--now", "not-a-date"])
    ctx.note(f"python3 -m qa.deadline --now not-a-date -> 종료코드 {result_bad.returncode}")
    if result_bad.returncode != 2:
        problems.append(f"잘못된 시각 종료코드 기대 2, 실제 {result_bad.returncode}")

    try:
        ev_before = evaluate_deadline(DEADLINE_BEFORE_NOW)
        ev_due = evaluate_deadline(DEADLINE_DUE_SOON_NOW)
        ev_over = evaluate_deadline(DEADLINE_OVERDUE_NOW)
        built = build_deadline(now=DEADLINE_BEFORE_NOW)
        if ev_before.get("status") != "before_deadline" or built.get("status") != "before_deadline":
            problems.append(f"evaluate/build before 이상: {ev_before.get('status')}")
        if ev_due.get("status") != "due_soon":
            problems.append(f"evaluate due_soon 이상: {ev_due.get('status')}")
        if ev_over.get("status") != "overdue":
            problems.append(f"evaluate overdue 이상: {ev_over.get('status')}")
        for report in (ev_before, ev_due, ev_over, built):
            v = validate_deadline(report)
            if v:
                problems.append(f"validate_deadline 정상 보고 문제: {v}")
    except Exception as e:
        problems.append(f"evaluate_deadline 실패: {type(e).__name__}: {e}")

    status_tamper_detected = False
    remaining_tamper_detected = False
    submission_ready_tamper_detected = False
    try:
        base = evaluate_deadline(DEADLINE_BEFORE_NOW)
        t1 = copy.deepcopy(base); t1["status"] = "overdue"
        status_tamper_detected = any("status" in p for p in validate_deadline(t1))
        t2 = copy.deepcopy(base); t2["remaining_seconds"] = 1
        remaining_tamper_detected = any("remaining_seconds" in p for p in validate_deadline(t2))
        t3 = copy.deepcopy(base); t3["submission_ready"] = True
        submission_ready_tamper_detected = any("submission_ready" in p for p in validate_deadline(t3))
    except Exception as e:
        problems.append(f"변조 탐지 구동 실패: {type(e).__name__}: {e}")
    tamper_detected = status_tamper_detected and remaining_tamper_detected and submission_ready_tamper_detected
    ctx.note(f"마감 점검 변조 탐지 -> status {status_tamper_detected}, "
             f"remaining {remaining_tamper_detected}, "
             f"submission_ready {submission_ready_tamper_detected}")
    if not tamper_detected:
        problems.append("변조 탐지 실패: status/remaining_seconds/submission_ready 중 하나를 바꿔도 문제를 찾지 못했다")

    # 최종 묶음 교차 대조: 같은 기준 시각의 qa.final_package 보고와 대조한다.
    fp: dict = {}
    fp_cross_ok = False
    result_fp = run_cli(["-m", "qa.final_package", "--now", DEADLINE_BEFORE_NOW,
                         "--date", "2026-10-31", "--json"])
    ctx.note(f"python3 -m qa.final_package --now {DEADLINE_BEFORE_NOW} "
             f"--date 2026-10-31 --json -> 종료코드 {result_fp.returncode}")
    cross_before = len(problems)
    if result_fp.returncode != 0:
        problems.append(
            f"final_package 교차 종료코드 기대 0, 실제 {result_fp.returncode}: "
            f"{result_fp.stderr[:200]}")
    try:
        fp = json.loads(result_fp.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"final_package 교차 --json 파싱 실패: {e}")
    if fp:
        if fp.get("status") != "blocked":
            problems.append(
                f"final_package status 기대 'blocked', 실제 {fp.get('status')}")
        if fp.get("deadline_status") != before.get("status"):
            problems.append(
                f"final_package deadline_status가 deadline status와 다르다: "
                f"{fp.get('deadline_status')} != {before.get('status')}")
        fp_remaining = fp.get("remaining_seconds")
        if not isinstance(fp_remaining, int) or isinstance(fp_remaining, bool) \
                or fp_remaining <= 0:
            problems.append(
                f"final_package remaining_seconds 기대 양의 int, 실제 {fp_remaining}")
        elif fp_remaining != DEADLINE_BEFORE_REMAINING:
            problems.append(
                f"final_package remaining_seconds 기대 {DEADLINE_BEFORE_REMAINING}, "
                f"실제 {fp_remaining}")
        elif fp_remaining != before.get("remaining_seconds"):
            problems.append(
                f"final_package remaining_seconds가 deadline remaining_seconds와 "
                f"다르다: {fp_remaining} != {before.get('remaining_seconds')}")
        if fp.get("blockers") != ["pi_real_capture_pending"]:
            problems.append(f"final_package blockers 이상: {fp.get('blockers')}")
        if fp.get("submission_ready") is not False:
            problems.append(
                f"final_package submission_ready 기대 False, "
                f"실제 {fp.get('submission_ready')}")
    fp_cross_ok = bool(fp) and len(problems) == cross_before
    ctx.note(f"마감↔최종 묶음 교차 대조 -> fp_cross_ok={fp_cross_ok}, "
             f"fp_remaining_seconds={fp.get('remaining_seconds')}, "
             f"fp_deadline_status={fp.get('deadline_status')}")

    summary = {"feature": "deadline",
               "before_status": before.get("status"),
               "before_remaining_seconds": before.get("remaining_seconds"),
               "due_soon_status": due.get("status"),
               "overdue_status": over.get("status"),
               "overdue_exit_code": result_over.returncode,
               "invalid_exit_code": result_bad.returncode,
               "tamper_detected": tamper_detected,
               "status_tamper_detected": status_tamper_detected,
               "remaining_tamper_detected": remaining_tamper_detected,
               "submission_ready_tamper_detected": submission_ready_tamper_detected,
               "fp_remaining_seconds": fp.get("remaining_seconds"),
               "fp_deadline_status": fp.get("deadline_status"),
               "fp_status": fp.get("status"),
               "fp_cross_ok": fp_cross_ok,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"deadline-before.json": result_j.stdout,
                    "deadline-overdue.json": result_over.stdout,
                    "deadline-final-package.json": result_fp.stdout})
    return summary


def drive_final_package(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.final_package import (build_final_package,
                                   evaluate_final_package,
                                   validate_final_package)
    try:
        primary_size = (ROOT / FINAL_PACKAGE_PRIMARY_VIDEO).stat().st_size
    except OSError:
        primary_size = None
    try:
        fallback_size = (ROOT / FINAL_PACKAGE_FALLBACK_VIDEO).stat().st_size
    except OSError:
        fallback_size = None
    if not isinstance(primary_size, int) or primary_size <= 0:
        problems.append(f"기본 영상 파일 크기 이상: {primary_size}")
    if not isinstance(fallback_size, int) or fallback_size <= 0:
        problems.append(f"폴백 영상 파일 크기 이상: {fallback_size}")
    due: dict = {}
    built_selected_video = built_selected_size = None
    built_due_selected_video = built_due_selected_size = None
    deadline_remaining = None
    deadline_status_from = None
    result_dl = None
    video_tamper_detected = False
    selected_video_tamper_detected = False
    selection_reason_tamper_detected = False
    selected_size_tamper_detected = False

    result = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                      "--date", FINAL_PACKAGE_DATE])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {FINAL_PACKAGE_DATE} -> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(
            f"final_package blocked 종료코드 기대 0, 실제 {result.returncode}: "
            f"{result.stderr[:200]}")
    for needle in ("STATUS: blocked",
                   f"PACKAGE_DATE_TARGET: {FINAL_PACKAGE_TARGET}",
                   "INVENTORY_PRESENT: 18",
                   "INVENTORY_TOTAL: 18",
                   "INVENTORY_MISSING: []",
                   "EXPORT_COPIED: 18",
                   "EXPORT_TOTAL: 18",
                   "EXPORT_MISSING: []",
                   "EXPORT_VERIFY_VERIFIED: true",
                   "EXPORT_VERIFY_COPIED_FILES: 18",
                   "DEADLINE_STATUS: before_deadline",
                   f"REMAINING_SECONDS: {FINAL_PACKAGE_REMAINING}",
                   "FALLBACK_STATUS: pending",
                   "FALLBACK_ADOPTED: false",
                   f"SELECTED_VIDEO: {FINAL_PACKAGE_PRIMARY_VIDEO}",
                   "SELECTION_REASON: pending_default",
                   "BLOCKERS: ['pi_real_capture_pending']",
                   "SUBMISSION_READY: false",
                   "실제로 제출하지 않는다"):
        if needle not in result.stdout:
            problems.append(f"final_package 텍스트에 {needle!r} 없음")
    if primary_size is not None and f"SELECTED_SIZE: {primary_size}" not in result.stdout:
        problems.append("final_package 텍스트에 SELECTED_SIZE(기본 영상 실측 크기) 없음")

    result_j = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                        "--date", FINAL_PACKAGE_DATE, "--json"])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {FINAL_PACKAGE_DATE} --json "
             f"-> 종료코드 {result_j.returncode}")
    if result_j.returncode != 0:
        problems.append(
            f"final_package blocked --json 종료코드 기대 0, 실제 {result_j.returncode}")
    blocked: dict = {}
    try:
        blocked = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"blocked --json 파싱 실패: {e}")
    if blocked:
        if blocked.get("status") != "blocked":
            problems.append(f"status 기대 'blocked', 실제 {blocked.get('status')}")
        if blocked.get("inventory_present") != 18:
            problems.append(f"inventory_present 기대 18, 실제 {blocked.get('inventory_present')}")
        if blocked.get("inventory_total") != 18:
            problems.append(f"inventory_total 기대 18, 실제 {blocked.get('inventory_total')}")
        if blocked.get("inventory_missing") != []:
            problems.append(f"inventory_missing 기대 [], 실제 {blocked.get('inventory_missing')}")
        if blocked.get("export_copied") != 18:
            problems.append(f"export_copied 기대 18, 실제 {blocked.get('export_copied')}")
        if blocked.get("export_total") != 18:
            problems.append(f"export_total 기대 18, 실제 {blocked.get('export_total')}")
        if blocked.get("export_missing") != []:
            problems.append(f"export_missing 기대 [], 실제 {blocked.get('export_missing')}")
        if not isinstance(blocked.get("export_total_bytes"), int) or blocked.get("export_total_bytes", 0) <= 0:
            problems.append(f"export_total_bytes 양의 정수 기대, 실제 {blocked.get('export_total_bytes')}")
        if blocked.get("export_verify_verified") is not True:
            problems.append(f"export_verify_verified 기대 True, 실제 {blocked.get('export_verify_verified')}")
        if blocked.get("export_verify_copied_files") != 18:
            problems.append(f"export_verify_copied_files 기대 18, 실제 {blocked.get('export_verify_copied_files')}")
        if blocked.get("export_verify_copied_files") != blocked.get("export_copied"):
            problems.append(f"export_verify_copied_files가 export_copied와 다르다: {blocked.get('export_verify_copied_files')} != {blocked.get('export_copied')}")
        if not isinstance(blocked.get("export_verify_total_bytes"), int) or isinstance(blocked.get("export_verify_total_bytes"), bool) or blocked.get("export_verify_total_bytes", 0) <= 0:
            problems.append(f"export_verify_total_bytes 양의 정수 기대, 실제 {blocked.get('export_verify_total_bytes')}")
        elif blocked.get("export_verify_total_bytes") != blocked.get("export_total_bytes"):
            problems.append(f"export_verify_total_bytes가 export_total_bytes와 다르다: {blocked.get('export_verify_total_bytes')} != {blocked.get('export_total_bytes')}")
        if blocked.get("export_verify_total_bytes") is not None and f"EXPORT_VERIFY_TOTAL_BYTES: {blocked.get('export_verify_total_bytes')}" not in result.stdout:
            problems.append("final_package 텍스트에 EXPORT_VERIFY_TOTAL_BYTES(재검증 합계 바이트) 없음")
        if blocked.get("export_copied") != blocked.get("inventory_present"):
            problems.append(f"export_copied가 inventory_present와 다르다: {blocked.get('export_copied')} != {blocked.get('inventory_present')}")
        if blocked.get("export_total") != blocked.get("inventory_total"):
            problems.append(f"export_total가 inventory_total와 다르다: {blocked.get('export_total')} != {blocked.get('inventory_total')}")
        if blocked.get("export_missing") != blocked.get("inventory_missing"):
            problems.append(f"export_missing가 inventory_missing와 다르다: {blocked.get('export_missing')} != {blocked.get('inventory_missing')}")
        if blocked.get("deadline_status") != "before_deadline":
            problems.append(f"deadline_status 기대 'before_deadline', 실제 {blocked.get('deadline_status')}")
        if blocked.get("remaining_seconds") != FINAL_PACKAGE_REMAINING:
            problems.append(
                f"remaining_seconds 기대 {FINAL_PACKAGE_REMAINING}, "
                f"실제 {blocked.get('remaining_seconds')}")
        if blocked.get("fallback_status") != "pending":
            problems.append(f"fallback_status 기대 'pending', 실제 {blocked.get('fallback_status')}")
        if blocked.get("fallback_adopted") is not False:
            problems.append(f"fallback_adopted 기대 False, 실제 {blocked.get('fallback_adopted')}")
        if blocked.get("selected_video") != FINAL_PACKAGE_PRIMARY_VIDEO:
            problems.append(f"selected_video 기대 {FINAL_PACKAGE_PRIMARY_VIDEO}, 실제 {blocked.get('selected_video')}")
        if blocked.get("selection_reason") != "pending_default":
            problems.append(f"selection_reason 기대 'pending_default', 실제 {blocked.get('selection_reason')}")
        if not isinstance(blocked.get("selected_size"), int) or isinstance(blocked.get("selected_size"), bool) or blocked.get("selected_size", 0) <= 0:
            problems.append(f"selected_size 양의 정수 기대, 실제 {blocked.get('selected_size')}")
        elif primary_size is not None and blocked.get("selected_size") != primary_size:
            problems.append(f"selected_size가 기본 영상 실측 크기와 다르다: {blocked.get('selected_size')} != {primary_size}")
        if blocked.get("blockers") != ["pi_real_capture_pending"]:
            problems.append(f"blockers 이상: {blocked.get('blockers')}")
        if blocked.get("submission_ready") is not False:
            problems.append(
                f"submission_ready 기대 False, 실제 {blocked.get('submission_ready')}")
        joined = " ".join(str(x) for x in blocked.get("honesty", []))
        for marker in ("실제로 제출하지 않는다", "제출 완료를 뜻하지 않는다",
                       "Pi 실촬영 검증 전"):
            if marker not in joined:
                problems.append(f"honesty에 {marker!r} 없음")

    result_dl = run_cli(["-m", "qa.deadline", "--now", FINAL_PACKAGE_NOW,
                         "--json"])
    ctx.note(f"python3 -m qa.deadline --now {FINAL_PACKAGE_NOW} --json "
             f"-> 종료코드 {result_dl.returncode} (최종 묶음과 같은 기준 시각)")
    if result_dl.returncode != 0:
        problems.append(
            f"deadline --json 종료코드 기대 0, 실제 {result_dl.returncode}: "
            f"{result_dl.stderr[:200]}")
    dl_report: dict = {}
    try:
        dl_report = json.loads(result_dl.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"deadline --json 파싱 실패: {e}")
    if dl_report:
        deadline_remaining = dl_report.get("remaining_seconds")
        deadline_status_from = dl_report.get("status")
        if deadline_status_from != "before_deadline":
            problems.append(
                f"deadline status 기대 'before_deadline', 실제 {deadline_status_from}")
        if not isinstance(deadline_remaining, int) or isinstance(deadline_remaining, bool) or deadline_remaining <= 0:
            problems.append(f"deadline remaining_seconds 기대 양의 int, 실제 {deadline_remaining}")
        elif deadline_remaining != FINAL_PACKAGE_REMAINING:
            problems.append(
                f"deadline remaining_seconds 기대 {FINAL_PACKAGE_REMAINING}, "
                f"실제 {deadline_remaining}")
        if dl_report.get("deadline_kst") != "2026-11-05T11:00:00+09:00":
            problems.append(f"deadline deadline_kst 이상: {dl_report.get('deadline_kst')}")
        if dl_report.get("blockers") != ["pi_real_capture_pending"]:
            problems.append(f"deadline blockers 이상: {dl_report.get('blockers')}")
        if dl_report.get("submission_ready") is not False:
            problems.append(
                f"deadline submission_ready 기대 False, 실제 {dl_report.get('submission_ready')}")
        if blocked:
            if blocked.get("remaining_seconds") != deadline_remaining:
                problems.append(
                    f"final_package remaining_seconds가 deadline remaining_seconds와 다르다: {blocked.get('remaining_seconds')} != {deadline_remaining}")
            if blocked.get("deadline_status") != deadline_status_from:
                problems.append(
                    f"final_package deadline_status가 deadline status와 다르다: {blocked.get('deadline_status')} != {deadline_status_from}")

    result_due = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                          "--date", FINAL_PACKAGE_DUE_DATE, "--json"])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {FINAL_PACKAGE_DUE_DATE} --json "
             f"-> 종료코드 {result_due.returncode} (가정 날짜 구동)")
    if result_due.returncode != 0:
        problems.append(
            f"final_package due --json 종료코드 기대 0, 실제 {result_due.returncode}")
    try:
        due = json.loads(result_due.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"due --json 파싱 실패: {e}")
    if due:
        if due.get("status") != "blocked":
            problems.append(f"due status 기대 'blocked', 실제 {due.get('status')}")
        if due.get("fallback_status") != "fallback_due":
            problems.append(f"due fallback_status 기대 'fallback_due', 실제 {due.get('fallback_status')}")
        if due.get("fallback_adopted") is not True:
            problems.append(f"due fallback_adopted 기대 True, 실제 {due.get('fallback_adopted')}")
        if due.get("export_verify_verified") is not True:
            problems.append(f"due export_verify_verified 기대 True, 실제 {due.get('export_verify_verified')}")
        if due.get("export_verify_copied_files") != 18:
            problems.append(f"due export_verify_copied_files 기대 18, 실제 {due.get('export_verify_copied_files')}")
        if due.get("export_verify_total_bytes") != blocked.get("export_total_bytes"):
            problems.append(f"due export_verify_total_bytes가 blocked export_total_bytes와 다르다: {due.get('export_verify_total_bytes')} != {blocked.get('export_total_bytes')}")
        if due.get("selected_video") != FINAL_PACKAGE_FALLBACK_VIDEO:
            problems.append(f"due selected_video 기대 {FINAL_PACKAGE_FALLBACK_VIDEO}, 실제 {due.get('selected_video')}")
        if due.get("selection_reason") != "fallback_due":
            problems.append(f"due selection_reason 기대 'fallback_due', 실제 {due.get('selection_reason')}")
        if fallback_size is not None and due.get("selected_size") != fallback_size:
            problems.append(f"due selected_size가 폴백 영상 실측 크기와 다르다: {due.get('selected_size')} != {fallback_size}")
        if due.get("submission_ready") is not False:
            problems.append(f"due submission_ready 기대 False, 실제 {due.get('submission_ready')}")

    result_over = run_cli(["-m", "qa.final_package", "--now",
                           DEADLINE_OVERDUE_NOW, "--date", FINAL_PACKAGE_DATE,
                           "--json"])
    ctx.note(f"python3 -m qa.final_package --now {DEADLINE_OVERDUE_NOW} "
             f"--date {FINAL_PACKAGE_DATE} --json "
             f"-> 종료코드 {result_over.returncode}")
    if result_over.returncode != 1:
        problems.append(
            f"final_package overdue 종료코드 기대 1, 실제 {result_over.returncode}")
    over: dict = {}
    try:
        over = json.loads(result_over.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"overdue --json 파싱 실패: {e}")
    if over:
        if over.get("status") != "overdue":
            problems.append(f"overdue status 기대 'overdue', 실제 {over.get('status')}")
        if over.get("deadline_status") != "overdue":
            problems.append(f"overdue deadline_status 기대 'overdue', 실제 {over.get('deadline_status')}")

    result_bad = run_cli(["-m", "qa.final_package", "--date", "not-a-date"])
    ctx.note(f"python3 -m qa.final_package --date not-a-date "
             f"-> 종료코드 {result_bad.returncode}")
    if result_bad.returncode != 2:
        problems.append(f"잘못된 날짜 종료코드 기대 2, 실제 {result_bad.returncode}")

    base_kwargs = dict(inventory_present=18, inventory_total=18,
                       inventory_missing=[],
                       export_copied=18, export_total=18,
                       export_missing=[], export_total_bytes=12345,
                       export_verify_verified=True,
                       export_verify_copied_files=18,
                       export_verify_total_bytes=12345,
                       deadline_status="before_deadline",
                       remaining_seconds=FINAL_PACKAGE_REMAINING,
                       fallback_status="pending", fallback_adopted=False,
                       selected_video=FINAL_PACKAGE_PRIMARY_VIDEO,
                       selection_reason="pending_default",
                       selected_size=12345,
                       blockers=["pi_real_capture_pending"])
    ready_status = incomplete_status = overdue_status = None
    export_incomplete_status = None
    built_export_total_bytes = None
    built_export_verify_verified = None
    built_export_verify_copied_files = None
    built_export_verify_total_bytes = None
    try:
        ev_blocked = evaluate_final_package(**base_kwargs)
        ev_ready = evaluate_final_package(**{**base_kwargs, "blockers": []})
        ready_status = ev_ready.get("status")
        ev_incomplete = evaluate_final_package(
            **{**base_kwargs, "inventory_present": 17,
               "inventory_missing": ["README.md"], "blockers": [],
               "export_copied": 17, "export_missing": ["README.md"],
               "export_verify_copied_files": 17})
        incomplete_status = ev_incomplete.get("status")
        ev_over = evaluate_final_package(
            **{**base_kwargs, "deadline_status": "overdue",
               "remaining_seconds": 0})
        overdue_status = ev_over.get("status")
        ev_export_inc = evaluate_final_package(
            **{**base_kwargs, "export_copied": 17,
               "export_missing": ["README.md"]})
        export_incomplete_status = ev_export_inc.get("status")
        if export_incomplete_status != "incomplete":
            problems.append(f"evaluate export incomplete 이상: {export_incomplete_status}")
        built = build_final_package(now=FINAL_PACKAGE_NOW,
                                    today=FINAL_PACKAGE_DATE)
        built_export_total_bytes = built.get("export_total_bytes")
        if built.get("export_copied") != 18 or built.get("export_total") != 18 or built.get("export_missing") != []:
            problems.append(f"build export 이상: {built.get('export_copied')}/{built.get('export_total')}/{built.get('export_missing')}")
        if not isinstance(built_export_total_bytes, int) or built_export_total_bytes <= 0:
            problems.append(f"build export_total_bytes 이상: {built_export_total_bytes}")
        if built_export_total_bytes != blocked.get("export_total_bytes"):
            problems.append(f"build export_total_bytes가 CLI blocked와 다르다: {built_export_total_bytes} != {blocked.get('export_total_bytes')}")
        built_export_verify_verified = built.get("export_verify_verified")
        built_export_verify_copied_files = built.get("export_verify_copied_files")
        built_export_verify_total_bytes = built.get("export_verify_total_bytes")
        if built_export_verify_verified is not True:
            problems.append(f"build export_verify_verified 기대 True, 실제 {built_export_verify_verified}")
        if built_export_verify_copied_files != 18 or built_export_verify_copied_files != built.get("export_copied"):
            problems.append(f"build export_verify_copied_files 이상: {built_export_verify_copied_files}")
        if built_export_verify_total_bytes != built_export_total_bytes or built_export_verify_total_bytes != blocked.get("export_verify_total_bytes"):
            problems.append(f"build export_verify_total_bytes가 build/CLI 재검증 바이트와 다르다: {built_export_verify_total_bytes} != {built_export_total_bytes}/{blocked.get('export_verify_total_bytes')}")
        if ev_blocked.get("status") != "blocked" or built.get("status") != "blocked":
            problems.append(f"evaluate/build blocked 이상: {built.get('status')}")
        if built.get("inventory_present") != 18 or built.get("inventory_total") != 18:
            problems.append(f"build inventory 이상: {built.get('inventory_present')}/{built.get('inventory_total')}")
        if ev_blocked.get("selected_video") != FINAL_PACKAGE_PRIMARY_VIDEO or ev_blocked.get("selection_reason") != "pending_default" or ev_blocked.get("selected_size") != 12345:
            problems.append(f"evaluate selected 이상: {ev_blocked.get('selected_video')}/{ev_blocked.get('selection_reason')}/{ev_blocked.get('selected_size')}")
        ev_fallback = evaluate_final_package(
            **{**base_kwargs, "fallback_status": "fallback_due",
               "fallback_adopted": True,
               "selected_video": FINAL_PACKAGE_FALLBACK_VIDEO,
               "selection_reason": "fallback_due"})
        if ev_fallback.get("status") != "blocked" or ev_fallback.get("selected_video") != FINAL_PACKAGE_FALLBACK_VIDEO:
            problems.append(f"evaluate fallback_due selected 이상: {ev_fallback.get('status')}/{ev_fallback.get('selected_video')}")
        built_selected_video = built.get("selected_video")
        built_selected_size = built.get("selected_size")
        if built_selected_video != FINAL_PACKAGE_PRIMARY_VIDEO or built.get("selection_reason") != "pending_default":
            problems.append(f"build selected 이상: {built_selected_video}/{built.get('selection_reason')}")
        if built_selected_size != blocked.get("selected_size"):
            problems.append(f"build selected_size가 CLI blocked와 다르다: {built_selected_size} != {blocked.get('selected_size')}")
        built_due = build_final_package(now=FINAL_PACKAGE_NOW,
                                        today=FINAL_PACKAGE_DUE_DATE)
        built_due_selected_video = built_due.get("selected_video")
        built_due_selected_size = built_due.get("selected_size")
        if built_due.get("fallback_status") != "fallback_due" or built_due_selected_video != FINAL_PACKAGE_FALLBACK_VIDEO or built_due.get("selection_reason") != "fallback_due":
            problems.append(f"build due selected 이상: {built_due.get('fallback_status')}/{built_due_selected_video}/{built_due.get('selection_reason')}")
        if built_due_selected_size != due.get("selected_size"):
            problems.append(f"build due selected_size가 CLI due와 다르다: {built_due_selected_size} != {due.get('selected_size')}")
        if ready_status != "ready_for_packaging":
            problems.append(f"evaluate ready 이상: {ready_status}")
        if incomplete_status != "incomplete":
            problems.append(f"evaluate incomplete 이상: {incomplete_status}")
        if overdue_status != "overdue":
            problems.append(f"evaluate overdue 이상: {overdue_status}")
        # ev_export_inc는 상태 판정 전용 프로브(validate는 export!=inventory를 무효로 보므로 검증 대상에서 제외)
        for report in (ev_blocked, ev_ready, ev_incomplete, ev_over, ev_fallback, built):
            v = validate_final_package(report)
            if v:
                problems.append(f"validate_final_package 정상 보고 문제: {v}")
    except Exception as e:
        problems.append(f"evaluate_final_package 실패: {type(e).__name__}: {e}")

    status_tamper_detected = False
    inventory_tamper_detected = False
    submission_ready_tamper_detected = False
    export_tamper_detected = False
    export_verify_verified_tamper_detected = False
    export_verify_copied_tamper_detected = False
    export_verify_bytes_tamper_detected = False
    export_verify_none_tamper_detected = False
    try:
        base = evaluate_final_package(**base_kwargs)
        t1 = copy.deepcopy(base); t1["status"] = "ready_for_packaging"
        status_tamper_detected = any("status" in p for p in validate_final_package(t1))
        t2 = copy.deepcopy(base); t2["inventory_present"] = 10
        inventory_tamper_detected = any("inventory_present" in p for p in validate_final_package(t2))
        t3 = copy.deepcopy(base); t3["submission_ready"] = True
        submission_ready_tamper_detected = any("submission_ready" in p for p in validate_final_package(t3))
        t4 = copy.deepcopy(base); t4["export_copied"] = 10
        export_tamper_detected = any("export_copied" in p for p in validate_final_package(t4))
        t5 = copy.deepcopy(base); t5["selected_video"] = FINAL_PACKAGE_FALLBACK_VIDEO
        selected_video_tamper_detected = any("selected_video" in p for p in validate_final_package(t5))
        t6 = copy.deepcopy(base); t6["selection_reason"] = "fallback_due"
        selection_reason_tamper_detected = any("selection_reason" in p for p in validate_final_package(t6))
        t7 = copy.deepcopy(base); t7["selected_size"] = 0
        selected_size_tamper_detected = any("selected_size" in p for p in validate_final_package(t7))
        t9 = copy.deepcopy(base); t9["export_verify_verified"] = False
        export_verify_verified_tamper_detected = any("export_verify_verified" in p for p in validate_final_package(t9))
        t10 = copy.deepcopy(base); t10["export_verify_copied_files"] = 10
        export_verify_copied_tamper_detected = any("export_verify_copied_files" in p for p in validate_final_package(t10))
        t11 = copy.deepcopy(base); t11["export_verify_total_bytes"] = 999
        export_verify_bytes_tamper_detected = any("export_verify_total_bytes" in p for p in validate_final_package(t11))
        t12 = copy.deepcopy(base); t12["export_verify_verified"] = None
        export_verify_none_tamper_detected = any(("export_verify_copied_files" in p or "export_verify_total_bytes" in p) for p in validate_final_package(t12))
        t8 = copy.deepcopy(base); t8["selected_video"] = None
        none_tamper_detected = any(("selection_reason" in p or "selected_size" in p) for p in validate_final_package(t8))
        if not none_tamper_detected:
            problems.append("변조 탐지 실패: selected_video를 None으로 바꿔도 문제를 찾지 못했다")
    except Exception as e:
        problems.append(f"변조 탐지 구동 실패: {type(e).__name__}: {e}")
    tamper_detected = (status_tamper_detected and inventory_tamper_detected
                       and submission_ready_tamper_detected)
    video_tamper_detected = (selected_video_tamper_detected
                             and selection_reason_tamper_detected
                             and selected_size_tamper_detected)
    ctx.note(f"최종 묶음 변조 탐지 -> status {status_tamper_detected}, "
             f"inventory {inventory_tamper_detected}, "
             f"submission_ready {submission_ready_tamper_detected}, "
             f"export {export_tamper_detected}, "
             f"selected_video {selected_video_tamper_detected}, "
             f"selection_reason {selection_reason_tamper_detected}, "
             f"selected_size {selected_size_tamper_detected}")
    if not video_tamper_detected:
        problems.append("변조 탐지 실패: selected_video/selection_reason/selected_size 중 하나를 바꿔도 문제를 찾지 못했다")
    if not tamper_detected:
        problems.append("변조 탐지 실패: status/inventory_present/submission_ready 중 하나를 바꿔도 문제를 찾지 못했다")
    if not export_tamper_detected:
        problems.append("변조 탐지 실패: export_copied를 바꿔도 문제를 찾지 못했다")
    export_verify_tamper_detected = (export_verify_verified_tamper_detected
                                     and export_verify_copied_tamper_detected
                                     and export_verify_bytes_tamper_detected
                                     and export_verify_none_tamper_detected)
    if not export_verify_tamper_detected:
        problems.append("변조 탐지 실패: export_verify_* 중 하나를 바꿔도 문제를 찾지 못했다")

    summary = {"feature": "final-package",
               "blocked_status": blocked.get("status"),
               "inventory_present": blocked.get("inventory_present"),
               "inventory_total": blocked.get("inventory_total"),
               "deadline_status": blocked.get("deadline_status"),
               "remaining_seconds": blocked.get("remaining_seconds"),
               "deadline_remaining_seconds": deadline_remaining,
               "deadline_status_from_deadline": deadline_status_from,
               "fallback_status": blocked.get("fallback_status"),
               "fallback_adopted": blocked.get("fallback_adopted"),
               "package_date_target": FINAL_PACKAGE_TARGET,
               "ready_status": ready_status,
               "incomplete_status": incomplete_status,
               "overdue_status": over.get("status") or overdue_status,
               "overdue_exit_code": result_over.returncode,
               "invalid_exit_code": result_bad.returncode,
               "export_copied": blocked.get("export_copied"),
               "export_total": blocked.get("export_total"),
               "export_missing": blocked.get("export_missing"),
               "export_total_bytes": blocked.get("export_total_bytes"),
               "built_export_total_bytes": built_export_total_bytes,
               "export_incomplete_status": export_incomplete_status,
               "export_tamper_detected": export_tamper_detected,
               "export_verify_verified": blocked.get("export_verify_verified"),
               "export_verify_copied_files": blocked.get("export_verify_copied_files"),
               "export_verify_total_bytes": blocked.get("export_verify_total_bytes"),
               "built_export_verify_verified": built_export_verify_verified,
               "built_export_verify_copied_files": built_export_verify_copied_files,
               "built_export_verify_total_bytes": built_export_verify_total_bytes,
               "export_verify_tamper_detected": export_verify_tamper_detected,
               "export_verify_verified_tamper_detected": export_verify_verified_tamper_detected,
               "export_verify_copied_tamper_detected": export_verify_copied_tamper_detected,
               "export_verify_bytes_tamper_detected": export_verify_bytes_tamper_detected,
               "export_verify_none_tamper_detected": export_verify_none_tamper_detected,
               "tamper_detected": tamper_detected,
               "status_tamper_detected": status_tamper_detected,
               "inventory_tamper_detected": inventory_tamper_detected,
               "submission_ready_tamper_detected": submission_ready_tamper_detected,
               "selected_video": blocked.get("selected_video"),
               "selection_reason": blocked.get("selection_reason"),
               "selected_size": blocked.get("selected_size"),
               "due_selected_video": due.get("selected_video"),
               "due_selection_reason": due.get("selection_reason"),
               "due_selected_size": due.get("selected_size"),
               "due_fallback_status": due.get("fallback_status"),
               "built_selected_video": built_selected_video,
               "built_selected_size": built_selected_size,
               "built_due_selected_video": built_due_selected_video,
               "built_due_selected_size": built_due_selected_size,
               "video_tamper_detected": video_tamper_detected,
               "selected_video_tamper_detected": selected_video_tamper_detected,
               "selection_reason_tamper_detected": selection_reason_tamper_detected,
               "selected_size_tamper_detected": selected_size_tamper_detected,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"final-package-blocked.json": result_j.stdout,
                    "final-package-overdue.json": result_over.stdout,
                    "final-package-deadline.json": result_dl.stdout if result_dl is not None else ""})
    return summary

def drive_package_export(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.package_export import (MANIFEST_NAME, build_export,
                                   validate_export, verify_export_dir)

    result = result_j = None
    exported: dict = {}
    total_bytes = None
    validate_problems: list = []
    tamper_detected = False
    ready_tamper_detected = False
    manifest_ok = False
    result_verify = result_verify_j = None
    verify_verified = False
    verify_exit_code = None
    verify_text_ok = False
    verify_readonly = False
    verify_tamper_detected = False
    verify_tamper_exit_code = None
    verify_missing_exit_code = None
    verify_conflict_exit_code = None
    verify_inproc_ok = False
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "pkg-cli"
        result = run_cli(["-m", "qa.package_export", "--out-dir", str(staging)])
        ctx.note(f"python3 -m qa.package_export --out-dir <tmp> -> 종료코드 {result.returncode}")
        if result.returncode != 0:
            problems.append(
                f"package_export 종료코드 기대 0, 실제 {result.returncode}: "
                f"{result.stderr[:200]}")
        for needle in ("제출물 18/18개 복사", "BLOCKERS: 1",
                       "pi_real_capture_pending", "SUBMISSION_READY: false",
                       "실제로 제출하지 않는다", "Pi 실촬영 검증 전",
                       f"매니페스트: {MANIFEST_NAME}"):
            if needle not in result.stdout:
                problems.append(f"package_export 텍스트에 {needle!r} 없음")

        staging_j = Path(tmp) / "pkg-json"
        result_j = run_cli(["-m", "qa.package_export", "--out-dir",
                            str(staging_j), "--json"])
        ctx.note(f"python3 -m qa.package_export --out-dir <tmp> --json "
                 f"-> 종료코드 {result_j.returncode}")
        if result_j.returncode != 0:
            problems.append(
                f"package_export --json 종료코드 기대 0, 실제 {result_j.returncode}: "
                f"{result_j.stderr[:200]}")
        try:
            exported = json.loads(result_j.stdout)
        except json.JSONDecodeError as e:
            problems.append(f"package_export --json 파싱 실패: {e}")
        if exported:
            if exported.get("total_files") != INVENTORY_TOTAL_FILES:
                problems.append(
                    f"total_files 기대 {INVENTORY_TOTAL_FILES}, 실제 {exported.get('total_files')}")
            if exported.get("copied_files") != INVENTORY_TOTAL_FILES:
                problems.append(
                    f"copied_files 기대 {INVENTORY_TOTAL_FILES}, 실제 {exported.get('copied_files')}")
            if exported.get("missing") != []:
                problems.append(f"missing 기대 [], 실제 {exported.get('missing')}")
            blocker_ids = [b.get("id") for b in exported.get("blockers", [])]
            if blocker_ids != list(EXPECTED_BLOCKER_IDS):
                problems.append(f"blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {blocker_ids}")
            if exported.get("submission_ready") is not False:
                problems.append(
                    f"submission_ready 기대 False, 실제 {exported.get('submission_ready')}")
            total_bytes = exported.get("total_bytes")
            copied_sum = sum(f.get("size_bytes") or 0
                             for f in exported.get("files", []) if f.get("copied"))
            if total_bytes != copied_sum or not total_bytes:
                problems.append(f"total_bytes 이상: {total_bytes} != 복사 합 {copied_sum}")
            joined = " ".join(str(x) for x in exported.get("honesty", []))
            for marker in ("실제로 제출하지 않는다", "Pi 실촬영 검증 전", "데모 기준"):
                if marker not in joined:
                    problems.append(f"honesty에 {marker!r} 없음")

        result_bad = run_cli(["-m", "qa.package_export"])
        ctx.note(f"python3 -m qa.package_export (인자 없음) -> 종료코드 {result_bad.returncode}")
        if result_bad.returncode != 2:
            problems.append(f"인자 없음 종료코드 기대 2, 실제 {result_bad.returncode}")

        staging_in = Path(tmp) / "pkg-inproc"
        built = build_export(staging_in, ROOT)
        validate_problems = validate_export(built, staging_in, ROOT)
        ctx.note(f"validate_export(build_export) -> 문제 {len(validate_problems)}건")
        if validate_problems:
            problems.append(f"validate_export 문제: {validate_problems}")
        manifest_path = staging_in / MANIFEST_NAME
        manifest_ok = manifest_path.is_file()
        paths = [f.get("path") for f in built.get("files", [])]
        if not manifest_ok:
            problems.append("package-manifest.json이 staging에 없다")
        if MANIFEST_NAME in paths:
            problems.append("매니페스트가 복사 대상에 포함됐다(자기 참조)")
        for entry in built.get("files", []):
            rel = entry.get("path")
            dest = staging_in / str(rel)
            if not dest.is_file():
                problems.append(f"복사본 파일 없음: {rel}")
                continue
            data = dest.read_bytes()
            if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
                problems.append(f"{rel}: 복사본 sha256이 기록과 다르다")
            if hashlib.sha256((ROOT / str(rel)).read_bytes()).hexdigest() != entry.get("sha256"):
                problems.append(f"{rel}: 기록 sha256이 원본과 다르다")

        (staging_in / "README.md").write_bytes(b"tampered")
        tamper_problems = validate_export(built, staging_in, ROOT)
        tamper_detected = any("README.md" in p for p in tamper_problems)
        ctx.note(f"복사본 변조 탐지 -> {tamper_detected}")
        if not tamper_detected:
            problems.append("변조 탐지 실패: 복사본 README.md를 바꿔도 문제를 찾지 못했다")

        # --- verify-dir 재검증 증거 (94회차 하네스 편입) ---
        def _snapshot(base: Path) -> dict:
            snap = {}
            for fp in sorted(base.rglob("*")):
                if fp.is_file():
                    data = fp.read_bytes()
                    snap[str(fp.relative_to(base))] = (len(data), hashlib.sha256(data).hexdigest())
            return snap

        staging_verify = Path(tmp) / "pkg-verify"
        built_verify = build_export(staging_verify, ROOT)
        snap_before = _snapshot(staging_verify)
        result_verify_j = run_cli(["-m", "qa.package_export", "--verify-dir",
                                   str(staging_verify), "--json"])
        verify_exit_code = result_verify_j.returncode
        ctx.note(f"python3 -m qa.package_export --verify-dir <tmp> --json "
                 f"-> 종료코드 {result_verify_j.returncode}")
        if result_verify_j.returncode != 0:
            problems.append(
                f"package_export --verify-dir --json 종료코드 기대 0, 실제 {result_verify_j.returncode}: "
                f"{result_verify_j.stderr[:200]}")
        try:
            verify_payload = json.loads(result_verify_j.stdout)
        except json.JSONDecodeError as e:
            verify_payload = {}
            problems.append(f"package_export --verify-dir --json 파싱 실패: {e}")
        if verify_payload:
            if verify_payload.get("verified") is not True:
                problems.append(f"verify-dir verified 기대 True, 실제 {verify_payload.get('verified')}")
            if verify_payload.get("problems") != []:
                problems.append(f"verify-dir problems 기대 [], 실제 {verify_payload.get('problems')}")
            vexp = verify_payload.get("export") or {}
            if vexp.get("copied_files") != INVENTORY_TOTAL_FILES:
                problems.append(f"verify-dir export copied_files 기대 {INVENTORY_TOTAL_FILES}, 실제 {vexp.get('copied_files')}")
            if vexp.get("total_files") != INVENTORY_TOTAL_FILES:
                problems.append(f"verify-dir export total_files 기대 {INVENTORY_TOTAL_FILES}, 실제 {vexp.get('total_files')}")
            if vexp.get("submission_ready") is not False:
                problems.append(f"verify-dir export submission_ready 기대 False, 실제 {vexp.get('submission_ready')}")
            verify_verified = verify_payload.get("verified") is True and verify_payload.get("problems") == []

        result_verify = run_cli(["-m", "qa.package_export", "--verify-dir",
                                 str(staging_verify)])
        ctx.note(f"python3 -m qa.package_export --verify-dir <tmp> -> 종료코드 {result_verify.returncode}")
        if result_verify.returncode != 0:
            problems.append(f"package_export --verify-dir 종료코드 기대 0, 실제 {result_verify.returncode}")
        verify_text_ok = True
        for needle in ("Argus 제출 패키지 재검증", "VERIFIED: true",
                       "SUBMISSION_READY: false", "실제로 제출하지 않는다",
                       "Pi 실촬영 검증 전"):
            if needle not in result_verify.stdout:
                verify_text_ok = False
                problems.append(f"package_export --verify-dir 텍스트에 {needle!r} 없음")

        snap_after = _snapshot(staging_verify)
        verify_readonly = snap_before == snap_after and bool(snap_before)
        ctx.note(f"verify-dir 읽기 전용(스냅샷 불변) -> {verify_readonly}")
        if not verify_readonly:
            problems.append("verify-dir가 staging 파일을 변경했다(읽기 전용 위반)")

        vexp_inproc, vprobs_inproc = verify_export_dir(staging_verify, ROOT)
        verify_inproc_ok = (vexp_inproc is not None and vprobs_inproc == []
                            and vexp_inproc.get("copied_files") == INVENTORY_TOTAL_FILES)
        ctx.note(f"verify_export_dir(깨끗한 staging) -> 문제 {len(vprobs_inproc)}건")
        if not verify_inproc_ok:
            problems.append(f"verify_export_dir 문제: {vprobs_inproc}")

        staging_vt = Path(tmp) / "pkg-verify-tamper"
        build_export(staging_vt, ROOT)
        (staging_vt / "README.md").write_bytes(b"tampered")
        result_vt = run_cli(["-m", "qa.package_export", "--verify-dir",
                             str(staging_vt), "--json"])
        verify_tamper_exit_code = result_vt.returncode
        ctx.note(f"python3 -m qa.package_export --verify-dir <변조 tmp> --json -> 종료코드 {result_vt.returncode}")
        try:
            vt_payload = json.loads(result_vt.stdout)
        except json.JSONDecodeError:
            vt_payload = {}
        verify_tamper_detected = (result_vt.returncode == 1
                                  and vt_payload.get("verified") is False
                                  and any("README.md" in str(x) for x in vt_payload.get("problems", [])))
        if not verify_tamper_detected:
            problems.append("verify-dir 변조 탐지 실패: 복사본 README.md를 바꿔도 verified=false로 잡지 못했다")

        empty_dir = Path(tmp) / "pkg-verify-empty"
        empty_dir.mkdir()
        result_vm = run_cli(["-m", "qa.package_export", "--verify-dir",
                             str(empty_dir), "--json"])
        verify_missing_exit_code = result_vm.returncode
        ctx.note(f"python3 -m qa.package_export --verify-dir <빈 tmp> --json -> 종료코드 {result_vm.returncode}")
        try:
            vm_payload = json.loads(result_vm.stdout)
        except json.JSONDecodeError:
            vm_payload = {}
        if result_vm.returncode != 2 or vm_payload.get("verified") is not False:
            problems.append(f"verify-dir 매니페스트 없음 기대 종료코드 2·verified false, 실제 {result_vm.returncode}·{vm_payload.get('verified')}")

        result_vc = run_cli(["-m", "qa.package_export", "--out-dir",
                             str(Path(tmp) / "pkg-x"), "--verify-dir",
                             str(staging_verify)])
        verify_conflict_exit_code = result_vc.returncode
        ctx.note(f"python3 -m qa.package_export --out-dir+--verify-dir -> 종료코드 {result_vc.returncode}")
        if result_vc.returncode != 2:
            problems.append(f"verify-dir 인자 충돌 종료코드 기대 2, 실제 {result_vc.returncode}")

        tampered_ready = copy.deepcopy(built)
        tampered_ready["submission_ready"] = True
        ready_tamper_detected = any(
            "submission_ready" in p
            for p in validate_export(tampered_ready, staging_in, ROOT))
        ctx.note(f"submission_ready 변조 탐지 -> {ready_tamper_detected}")
        if not ready_tamper_detected:
            problems.append("변조 탐지 실패: submission_ready를 True로 바꿔도 문제를 찾지 못했다")

    # 최종 묶음 교차 대조: 같은 제출물의 qa.final_package 보고와 대조한다.
    fp: dict = {}
    fp_cross_ok = False
    result_fp = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                         "--date", FINAL_PACKAGE_DATE, "--json"])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {FINAL_PACKAGE_DATE} --json "
             f"-> 종료코드 {result_fp.returncode}")
    cross_before = len(problems)
    if result_fp.returncode != 0:
        problems.append(
            f"final_package 교차 종료코드 기대 0, 실제 {result_fp.returncode}: "
            f"{result_fp.stderr[:200]}")
    try:
        fp = json.loads(result_fp.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"final_package 교차 --json 파싱 실패: {e}")
    if fp:
        if fp.get("status") != "blocked":
            problems.append(
                f"final_package status 기대 'blocked', 실제 {fp.get('status')}")
        if fp.get("export_copied") != exported.get("copied_files"):
            problems.append(
                f"final_package export_copied가 내보내기 copied_files와 "
                f"다르다: {fp.get('export_copied')} != "
                f"{exported.get('copied_files')}")
        if fp.get("export_total") != exported.get("total_files"):
            problems.append(
                f"final_package export_total가 내보내기 total_files와 "
                f"다르다: {fp.get('export_total')} != "
                f"{exported.get('total_files')}")
        if fp.get("export_missing") != exported.get("missing"):
            problems.append(
                f"final_package export_missing가 내보내기 missing와 "
                f"다르다: {fp.get('export_missing')} != "
                f"{exported.get('missing')}")
        fp_bytes = fp.get("export_total_bytes")
        if not isinstance(fp_bytes, int) or fp_bytes <= 0 \
                or fp_bytes != total_bytes:
            problems.append(
                f"final_package export_total_bytes가 내보내기 total_bytes와 "
                f"다르다: {fp_bytes} != {total_bytes}")
        if fp.get("export_verify_verified") is not True:
            problems.append(
                f"final_package export_verify_verified 기대 True, "
                f"실제 {fp.get('export_verify_verified')}")
        if fp.get("export_verify_copied_files") != fp.get("export_copied"):
            problems.append(
                f"final_package export_verify_copied_files가 export_copied와 "
                f"다르다: {fp.get('export_verify_copied_files')} != "
                f"{fp.get('export_copied')}")
        if fp.get("export_verify_total_bytes") != fp.get("export_total_bytes"):
            problems.append(
                f"final_package export_verify_total_bytes가 "
                f"export_total_bytes와 다르다: "
                f"{fp.get('export_verify_total_bytes')} != "
                f"{fp.get('export_total_bytes')}")
        if fp.get("blockers") != list(EXPECTED_BLOCKER_IDS):
            problems.append(f"final_package blockers 이상: {fp.get('blockers')}")
        if fp.get("submission_ready") is not False:
            problems.append(
                f"final_package submission_ready 기대 False, "
                f"실제 {fp.get('submission_ready')}")
    fp_cross_ok = bool(fp) and len(problems) == cross_before
    ctx.note(f"내보내기↔최종 묶음 교차 대조 -> fp_cross_ok={fp_cross_ok}, "
             f"fp_export_copied={fp.get('export_copied')}, "
             f"fp_export_total={fp.get('export_total')}")

    summary = {"feature": "package-export",
               "total_files": exported.get("total_files"),
               "copied_files": exported.get("copied_files"),
               "total_bytes": total_bytes,
               "blockers": [b.get("id") for b in exported.get("blockers", [])],
               "submission_ready": exported.get("submission_ready"),
               "validate_problems": validate_problems,
               "manifest_ok": manifest_ok,
               "tamper_detected": tamper_detected,
               "ready_tamper_detected": ready_tamper_detected,
               "invalid_exit_code": result_bad.returncode,
               "verify_verified": verify_verified,
               "verify_exit_code": verify_exit_code,
               "verify_text_ok": verify_text_ok,
               "verify_readonly": verify_readonly,
               "verify_tamper_detected": verify_tamper_detected,
               "verify_tamper_exit_code": verify_tamper_exit_code,
               "verify_missing_exit_code": verify_missing_exit_code,
               "verify_conflict_exit_code": verify_conflict_exit_code,
               "verify_inproc_ok": verify_inproc_ok,
               "fp_status": fp.get("status"),
               "fp_export_copied": fp.get("export_copied"),
               "fp_export_total": fp.get("export_total"),
               "fp_export_missing": fp.get("export_missing"),
               "fp_export_total_bytes": fp.get("export_total_bytes"),
               "fp_cross_ok": fp_cross_ok,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"package-export.json": result_j.stdout if result_j else "",
                    "package-export.txt": result.stdout if result else "",
                    "package-export-verify.json": result_verify_j.stdout if result_verify_j else "",
                    "package-export-verify.txt": result_verify.stdout if result_verify else "",
                    "package-export-final-package.json": result_fp.stdout})
    return summary

def drive_sam_live_evidence(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    import copy as _copy
    from qa.sam_live_evidence import (EXPECTED_ENDPOINT, build_report,
                                      validate_evidence, validate_report)
    from terminal.demo_data import demo_bin_ids, demo_ledger

    def _make_evidence() -> dict:
        ledger = demo_ledger()
        bins = []
        for bin_id in demo_bin_ids():
            book = ledger[bin_id].book_qty
            qty = SAM_EVIDENCE_COUNTED[bin_id]
            diff = qty - book
            verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
            sha = hashlib.sha256(f"fake-evidence-{bin_id}".encode()).hexdigest()
            bins.append({"bin_id": bin_id, "book_qty": book, "counted_qty": qty,
                         "diff": diff, "verdict": verdict, "image_sha256": sha})
        matched = sum(1 for b in bins if b["diff"] == 0)
        summary = {"counted_bins": len(bins), "matched": matched,
                   "mismatched": len(bins) - matched,
                   "match_rate": matched / len(bins),
                   "abs_diff_total": sum(abs(b["diff"]) for b in bins),
                   "net_diff": sum(b["diff"] for b in bins)}
        return {"bridge": "custom.meta-model-api connector transport (surrogate)",
                "endpoint": EXPECTED_ENDPOINT,
                "image_source": "synthetic probe photo, 6 distinct crops",
                "report": {"status": "passed", "attempted": True,
                           "ready_for_live_call": True, "blockers": [],
                           "session_id": SAM_EVIDENCE_SESSION_ID,
                           "source": "sam", "distinct_image_count": 6,
                           "bins": bins, "summary": summary, "error_type": None,
                           "honesty": ["빈별 사진은 가상 사진의 서로 다른 잘라내기이며 실제 빈 촬영이나 Pi 실촬영이 아니다"]}}

    valid_ev = _make_evidence()
    base_problems = validate_evidence(valid_ev)
    ctx.note(f"validate_evidence 유효 증거 -> problems={base_problems}")
    if base_problems != []:
        problems.append(f"유효 증거 validate_evidence 기대 [], 실제 {base_problems}")
    report = build_report(valid_ev)
    if report.get("valid") is not True or report.get("problems") != []:
        problems.append(f"build_report 유효 기대, 실제 {report}")
    if report.get("source") != "sam":
        problems.append(f"source 기대 sam, 실제 {report.get('source')}")
    if report.get("distinct_image_count") != 6:
        problems.append(f"distinct 기대 6, 실제 {report.get('distinct_image_count')}")
    if report.get("session_id") != SAM_EVIDENCE_SESSION_ID:
        problems.append(f"session 기대 {SAM_EVIDENCE_SESSION_ID}, 실제 {report.get('session_id')}")
    if report.get("submission_ready") is not False:
        problems.append("submission_ready는 False여야 한다")
    vr = validate_report(report)
    if vr != []:
        problems.append(f"validate_report 기대 [], 실제 {vr}")

    dup = _copy.deepcopy(valid_ev)
    dup["report"]["bins"][1]["image_sha256"] = dup["report"]["bins"][0]["image_sha256"]
    dup_problems = validate_evidence(dup)
    duplicate_detected = any("distinct" in x for x in dup_problems)
    ctx.note(f"validate_evidence 중복 해시 -> duplicate_detected={duplicate_detected}")
    if not duplicate_detected:
        problems.append(f"중복 해시 탐지 실패: {dup_problems}")

    summ = _copy.deepcopy(valid_ev)
    summ["report"]["summary"]["net_diff"] += 1
    summ_problems = validate_evidence(summ)
    summary_tamper_detected = any("summary" in x for x in summ_problems)
    if not summary_tamper_detected:
        problems.append(f"요약 변조 탐지 실패: {summ_problems}")

    difft = _copy.deepcopy(valid_ev)
    difft["report"]["bins"][0]["diff"] += 1
    diff_problems = validate_evidence(difft)
    diff_tamper_detected = any(("diff" in x or "verdict" in x) for x in diff_problems)
    if not diff_tamper_detected:
        problems.append(f"diff 변조 탐지 실패: {diff_problems}")

    mockt = _copy.deepcopy(valid_ev)
    mockt["report"]["source"] = "mock"
    mockt["report"]["status"] = "blocked"
    mock_problems = validate_evidence(mockt)
    mock_source_blocked = any("source" in x for x in mock_problems) and any("status" in x for x in mock_problems)
    if not mock_source_blocked:
        problems.append(f"mock source/blocked 탐지 실패: {mock_problems}")

    endt = _copy.deepcopy(valid_ev)
    endt["endpoint"] = "https://example.invalid/v1/responses"
    endt["bridge"] = "unknown"
    end_problems = validate_evidence(endt)
    endpoint_tamper_detected = any("endpoint" in x for x in end_problems) and any("bridge" in x for x in end_problems)
    if not endpoint_tamper_detected:
        problems.append(f"endpoint/bridge 탐지 실패: {end_problems}")

    # CLI 구동
    valid_cli_stdout = ""
    valid_exit = -1
    tamper_exit = -1
    cli_report: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        good = root / "evidence.json"
        good.write_text(json.dumps(valid_ev, ensure_ascii=False), encoding="utf-8")
        result = run_cli(["-m", "qa.sam_live_evidence", "--file", str(good)])
        valid_cli_stdout_text = result.stdout
        valid_exit = result.returncode
        ctx.note(f"python3 -m qa.sam_live_evidence --file 유효 -> 종료코드 {result.returncode}")
        if result.returncode != 0:
            problems.append(f"유효 CLI 종료코드 기대 0, 실제 {result.returncode}: {result.stderr[:200]}")
        for needle in ("VALID: true", f"SESSION: {SAM_EVIDENCE_SESSION_ID}", "SOURCE: sam", "DISTINCT_IMAGES: 6", "SUBMISSION_READY: false"):
            if needle not in result.stdout:
                problems.append(f"유효 CLI 텍스트에 {needle!r} 없음")
        result_j = run_cli(["-m", "qa.sam_live_evidence", "--file", str(good), "--json"])
        valid_cli_stdout = result_j.stdout
        ctx.note(f"python3 -m qa.sam_live_evidence --file 유효 --json -> 종료코드 {result_j.returncode}")
        if result_j.returncode != 0:
            problems.append(f"유효 CLI --json 종료코드 기대 0, 실제 {result_j.returncode}")
        try:
            cli_report = json.loads(result_j.stdout)
        except json.JSONDecodeError as e:
            problems.append(f"유효 CLI --json 파싱 실패: {e}")
        if cli_report:
            if cli_report.get("valid") is not True:
                problems.append(f"CLI valid 기대 True, 실제 {cli_report.get('valid')}")
            if cli_report.get("distinct_image_count") != 6:
                problems.append(f"CLI distinct 기대 6, 실제 {cli_report.get('distinct_image_count')}")
            sm = cli_report.get("summary") or {}
            if sm.get("abs_diff_total") != 30 or sm.get("net_diff") != -28 or sm.get("matched") != 1 or sm.get("mismatched") != 5:
                problems.append(f"CLI summary 기대 matched1/mismatched5/abs30/net-28, 실제 {sm}")
            joined = " ".join(str(x) for x in cli_report.get("honesty", []))
            for marker in ("API를 호출하지 않는다", "Pi 실촬영이 아니다"):
                if marker not in joined:
                    problems.append(f"CLI honesty에 {marker!r} 없음")
        bad = root / "evidence-dup.json"
        bad.write_text(json.dumps(dup, ensure_ascii=False), encoding="utf-8")
        result_bad = run_cli(["-m", "qa.sam_live_evidence", "--file", str(bad), "--json"])
        tamper_exit = result_bad.returncode
        ctx.note(f"python3 -m qa.sam_live_evidence --file 중복 --json -> 종료코드 {result_bad.returncode}")
        if result_bad.returncode != 1:
            problems.append(f"변조 CLI 종료코드 기대 1, 실제 {result_bad.returncode}")
        else:
            try:
                bad_report = json.loads(result_bad.stdout)
                if bad_report.get("valid") is not False:
                    problems.append(f"변조 CLI valid 기대 False, 실제 {bad_report.get('valid')}")
            except json.JSONDecodeError as e:
                problems.append(f"변조 CLI --json 파싱 실패: {e}")
        result_missing = run_cli(["-m", "qa.sam_live_evidence", "--file", str(root / "nope.json")])
        missing_exit = result_missing.returncode
        ctx.note(f"python3 -m qa.sam_live_evidence --file 없음 -> 종료코드 {result_missing.returncode}")
        if result_missing.returncode != 2:
            problems.append(f"없는 파일 종료코드 기대 2, 실제 {result_missing.returncode}")

    smry = report.get("summary") or {}
    summary = {"feature": "sam-live-evidence",
               "valid_ok": report.get("valid") is True and not problems,
               "session_id": report.get("session_id"),
               "source": report.get("source"),
               "distinct_image_count": report.get("distinct_image_count"),
               "matched": smry.get("matched"),
               "mismatched": smry.get("mismatched"),
               "abs_diff_total": smry.get("abs_diff_total"),
               "net_diff": smry.get("net_diff"),
               "duplicate_detected": duplicate_detected,
               "summary_tamper_detected": summary_tamper_detected,
               "diff_tamper_detected": diff_tamper_detected,
               "mock_source_blocked": mock_source_blocked,
               "endpoint_tamper_detected": endpoint_tamper_detected,
               "missing_file_exit_code": missing_exit,
               "tamper_exit_code": tamper_exit,
               "valid_exit_code": valid_exit,
               "all_ok": not problems, "problems": problems}
    # valid_ok는 problems 기준으로 재계산 (위에서 problems가 없을 때만 True)
    summary["valid_ok"] = report.get("valid") is True
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-live-evidence-valid.json": valid_cli_stdout,
                    "sam-live-evidence-report.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n"})
    return summary



def drive_sam_session_evidence(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    import copy as _copy
    from qa.sam_session_evidence import (EXPECTED_ENDPOINT, build_report,
                                         validate_evidence, validate_report)
    from terminal.demo_data import demo_bin_ids, demo_ledger

    def _make_evidence() -> dict:
        ledger = demo_ledger()
        bins = []
        hashes = {}
        for bin_id in demo_bin_ids():
            book = ledger[bin_id].book_qty
            qty = SAM_SESSION_EVIDENCE_COUNTED[bin_id]
            diff = qty - book
            verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
            bins.append({"bin_id": bin_id, "book_qty": book, "counted_qty": qty,
                         "diff": diff, "verdict": verdict})
            hashes[bin_id] = hashlib.sha256(
                f"fake-session-evidence-{bin_id}".encode()).hexdigest()
        matched = sum(1 for b in bins if b["diff"] == 0)
        summary = {"counted_bins": len(bins), "matched": matched,
                   "mismatched": len(bins) - matched,
                   "match_rate": matched / len(bins),
                   "abs_diff_total": sum(abs(b["diff"]) for b in bins),
                   "net_diff": sum(b["diff"] for b in bins)}
        return {"bridge": "custom.meta-model-api connector transport (surrogate)",
                "endpoint": EXPECTED_ENDPOINT,
                "image_source": "synthetic probe photo, 6 distinct crops",
                "image_hashes": hashes,
                "report": {"status": "passed", "attempted": True,
                           "ready_for_live_call": True, "blockers": [],
                           "session_id": SAM_SESSION_EVIDENCE_SESSION_ID,
                           "source": "sam", "bins": bins, "summary": summary,
                           "error_type": None,
                           "honesty": ["전체 세션 실호출이어도 Pi 실촬영이 아니며 사진은 호출자가 제공한 것이다"]}}

    valid_ev = _make_evidence()
    base_problems = validate_evidence(valid_ev)
    ctx.note(f"validate_evidence 유효 세션 증거 -> problems={base_problems}")
    if base_problems != []:
        problems.append(f"유효 세션 증거 validate_evidence 기대 [], 실제 {base_problems}")
    report = build_report(valid_ev)
    if report.get("valid") is not True or report.get("problems") != []:
        problems.append(f"build_report 유효 기대, 실제 {report}")
    if report.get("source") != "sam":
        problems.append(f"source 기대 sam, 실제 {report.get('source')}")
    if report.get("distinct_image_count") != 6:
        problems.append(f"distinct 기대 6, 실제 {report.get('distinct_image_count')}")
    if report.get("session_id") != SAM_SESSION_EVIDENCE_SESSION_ID:
        problems.append(f"session 기대 {SAM_SESSION_EVIDENCE_SESSION_ID}, 실제 {report.get('session_id')}")
    if report.get("submission_ready") is not False:
        problems.append("submission_ready는 False여야 한다")
    vr = validate_report(report)
    if vr != []:
        problems.append(f"validate_report 기대 [], 실제 {vr}")

    dup = _copy.deepcopy(valid_ev)
    dup["image_hashes"]["A-01-02"] = dup["image_hashes"]["A-01-01"]
    dup_problems = validate_evidence(dup)
    duplicate_detected = any("distinct" in x for x in dup_problems)
    ctx.note(f"validate_evidence 중복 해시 -> duplicate_detected={duplicate_detected}")
    if not duplicate_detected:
        problems.append(f"중복 해시 탐지 실패: {dup_problems}")

    miss = _copy.deepcopy(valid_ev)
    del miss["image_hashes"]["B-02-02"]
    miss_problems = validate_evidence(miss)
    missing_detected = any("image_hashes" in x for x in miss_problems)
    ctx.note(f"validate_evidence 해시 누락 -> missing_detected={missing_detected}")
    if not missing_detected:
        problems.append(f"해시 누락 탐지 실패: {miss_problems}")

    summ = _copy.deepcopy(valid_ev)
    summ["report"]["summary"]["net_diff"] += 1
    summ_problems = validate_evidence(summ)
    summary_tamper_detected = any("summary" in x for x in summ_problems)
    if not summary_tamper_detected:
        problems.append(f"요약 변조 탐지 실패: {summ_problems}")

    difft = _copy.deepcopy(valid_ev)
    difft["report"]["bins"][0]["diff"] += 1
    diff_problems = validate_evidence(difft)
    diff_tamper_detected = any(("diff" in x or "verdict" in x) for x in diff_problems)
    if not diff_tamper_detected:
        problems.append(f"diff 변조 탐지 실패: {diff_problems}")

    mockt = _copy.deepcopy(valid_ev)
    mockt["report"]["source"] = "mock"
    mockt["report"]["status"] = "blocked"
    mock_problems = validate_evidence(mockt)
    mock_source_blocked = any("source" in x for x in mock_problems) and any("status" in x for x in mock_problems)
    if not mock_source_blocked:
        problems.append(f"mock source/blocked 탐지 실패: {mock_problems}")

    endt = _copy.deepcopy(valid_ev)
    endt["endpoint"] = "https://example.invalid/v1/responses"
    endt["bridge"] = "unknown"
    end_problems = validate_evidence(endt)
    endpoint_tamper_detected = any("endpoint" in x for x in end_problems) and any("bridge" in x for x in end_problems)
    if not endpoint_tamper_detected:
        problems.append(f"endpoint/bridge 탐지 실패: {end_problems}")

    valid_cli_stdout = ""
    valid_exit = -1
    tamper_exit = -1
    missing_exit = -1
    cli_report: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        good = root / "session-evidence.json"
        good.write_text(json.dumps(valid_ev, ensure_ascii=False), encoding="utf-8")
        result = run_cli(["-m", "qa.sam_session_evidence", "--file", str(good)])
        valid_exit = result.returncode
        ctx.note(f"python3 -m qa.sam_session_evidence --file 유효 -> 종료코드 {result.returncode}")
        if result.returncode != 0:
            problems.append(f"유효 CLI 종료코드 기대 0, 실제 {result.returncode}: {result.stderr[:200]}")
        for needle in ("VALID: true", f"SESSION: {SAM_SESSION_EVIDENCE_SESSION_ID}", "SOURCE: sam", "DISTINCT_IMAGES: 6", "SUBMISSION_READY: false"):
            if needle not in result.stdout:
                problems.append(f"유효 CLI 텍스트에 {needle!r} 없음")
        result_j = run_cli(["-m", "qa.sam_session_evidence", "--file", str(good), "--json"])
        valid_cli_stdout = result_j.stdout
        ctx.note(f"python3 -m qa.sam_session_evidence --file 유효 --json -> 종료코드 {result_j.returncode}")
        if result_j.returncode != 0:
            problems.append(f"유효 CLI --json 종료코드 기대 0, 실제 {result_j.returncode}")
        try:
            cli_report = json.loads(result_j.stdout)
        except json.JSONDecodeError as e:
            problems.append(f"유효 CLI --json 파싱 실패: {e}")
        if cli_report:
            if cli_report.get("valid") is not True:
                problems.append(f"CLI valid 기대 True, 실제 {cli_report.get('valid')}")
            if cli_report.get("distinct_image_count") != 6:
                problems.append(f"CLI distinct 기대 6, 실제 {cli_report.get('distinct_image_count')}")
            sm = cli_report.get("summary") or {}
            if sm.get("abs_diff_total") != 30 or sm.get("net_diff") != -28 or sm.get("matched") != 1 or sm.get("mismatched") != 5:
                problems.append(f"CLI summary 기대 matched1/mismatched5/abs30/net-28, 실제 {sm}")
            joined = " ".join(str(x) for x in cli_report.get("honesty", []))
            for marker in ("API를 호출하지 않는다", "Pi 실촬영이 아니다"):
                if marker not in joined:
                    problems.append(f"CLI honesty에 {marker!r} 없음")
        bad = root / "session-evidence-dup.json"
        bad.write_text(json.dumps(dup, ensure_ascii=False), encoding="utf-8")
        result_bad = run_cli(["-m", "qa.sam_session_evidence", "--file", str(bad), "--json"])
        tamper_exit = result_bad.returncode
        ctx.note(f"python3 -m qa.sam_session_evidence --file 중복 --json -> 종료코드 {result_bad.returncode}")
        if result_bad.returncode != 1:
            problems.append(f"변조 CLI 종료코드 기대 1, 실제 {result_bad.returncode}")
        else:
            try:
                bad_report = json.loads(result_bad.stdout)
                if bad_report.get("valid") is not False:
                    problems.append(f"변조 CLI valid 기대 False, 실제 {bad_report.get('valid')}")
            except json.JSONDecodeError as e:
                problems.append(f"변조 CLI --json 파싱 실패: {e}")
        result_missing = run_cli(["-m", "qa.sam_session_evidence", "--file", str(root / "nope.json")])
        missing_exit = result_missing.returncode
        ctx.note(f"python3 -m qa.sam_session_evidence --file 없음 -> 종료코드 {result_missing.returncode}")
        if result_missing.returncode != 2:
            problems.append(f"없는 파일 종료코드 기대 2, 실제 {result_missing.returncode}")

    smry = report.get("summary") or {}
    summary = {"feature": "sam-session-evidence",
               "valid_ok": report.get("valid") is True,
               "session_id": report.get("session_id"),
               "source": report.get("source"),
               "distinct_image_count": report.get("distinct_image_count"),
               "matched": smry.get("matched"),
               "mismatched": smry.get("mismatched"),
               "abs_diff_total": smry.get("abs_diff_total"),
               "net_diff": smry.get("net_diff"),
               "duplicate_detected": duplicate_detected,
               "missing_detected": missing_detected,
               "summary_tamper_detected": summary_tamper_detected,
               "diff_tamper_detected": diff_tamper_detected,
               "mock_source_blocked": mock_source_blocked,
               "endpoint_tamper_detected": endpoint_tamper_detected,
               "missing_file_exit_code": missing_exit,
               "tamper_exit_code": tamper_exit,
               "valid_exit_code": valid_exit,
               "all_ok": not problems, "problems": problems}
    summary["valid_ok"] = report.get("valid") is True and not problems
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-session-evidence-valid.json": valid_cli_stdout,
                    "sam-session-evidence-report.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_sam_photo_evidence(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    import copy as _copy
    from qa.sam_photo_evidence import (EXPECTED_ENDPOINT, build_report,
                                       validate_evidence, validate_report)
    from terminal.demo_data import demo_bin_ids, demo_ledger

    def _make_evidence() -> dict:
        ledger = demo_ledger()
        bins = []
        for bin_id in demo_bin_ids():
            entry = ledger[bin_id]
            qty = SAM_PHOTO_EVIDENCE_COUNTED[bin_id]
            diff = qty - entry.book_qty
            verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
            sha = hashlib.sha256(
                f"fake-photo-evidence-{bin_id}".encode()).hexdigest()
            bins.append({"bin_id": bin_id, "item_code": entry.item_code,
                         "book_qty": entry.book_qty, "counted_qty": qty,
                         "diff": diff, "verdict": verdict,
                         "photo": {"image_ref": f"{bin_id}.jpg",
                                   "size_bytes": 1000 + len(bin_id),
                                   "sha256": sha, "suffix": ".jpg"}})
        matched = sum(1 for b in bins if b["diff"] == 0)
        summary = {"counted_bins": len(bins), "matched": matched,
                   "mismatched": len(bins) - matched,
                   "match_rate": matched / len(bins),
                   "abs_diff_total": sum(abs(b["diff"]) for b in bins),
                   "net_diff": sum(b["diff"] for b in bins)}
        return {"bridge": "custom.meta-model-api connector transport (surrogate)",
                "endpoint": EXPECTED_ENDPOINT,
                "path": "terminal.photo_intake.run_photo_intake with injected LiveSamCounter",
                "image_source": "synthetic probe photo, 6 distinct crops",
                "report": {"session_id": SAM_PHOTO_EVIDENCE_SESSION_ID,
                           "generated_at": "2026-11-02T00:00:00+00:00",
                           "source": "sam", "capture_source": "file",
                           "honesty": ["파일 기반 입력이며 Pi 실촬영이 아닙니다"],
                           "bins": bins, "summary": summary}}

    valid_ev = _make_evidence()
    base_problems = validate_evidence(valid_ev)
    ctx.note(f"validate_evidence 유효 파일 입력 증거 -> problems={base_problems}")
    if base_problems != []:
        problems.append(f"유효 증거 validate_evidence 기대 [], 실제 {base_problems}")
    report = build_report(valid_ev)
    if report.get("valid") is not True or report.get("problems") != []:
        problems.append(f"build_report 유효 기대, 실제 {report}")
    if report.get("source") != "sam":
        problems.append(f"source 기대 sam, 실제 {report.get('source')}")
    if report.get("capture_source") != "file":
        problems.append(f"capture_source 기대 file, 실제 {report.get('capture_source')}")
    if report.get("distinct_image_count") != 6:
        problems.append(f"distinct 기대 6, 실제 {report.get('distinct_image_count')}")
    if report.get("session_id") != SAM_PHOTO_EVIDENCE_SESSION_ID:
        problems.append(f"session 기대 {SAM_PHOTO_EVIDENCE_SESSION_ID}, 실제 {report.get('session_id')}")
    if report.get("submission_ready") is not False:
        problems.append("submission_ready는 False여야 한다")
    vr = validate_report(report)
    if vr != []:
        problems.append(f"validate_report 기대 [], 실제 {vr}")

    dup = _copy.deepcopy(valid_ev)
    dup["report"]["bins"][1]["photo"]["sha256"] = dup["report"]["bins"][0]["photo"]["sha256"]
    dup_problems = validate_evidence(dup)
    duplicate_detected = any("distinct" in x for x in dup_problems)
    ctx.note(f"validate_evidence 중복 사진 해시 -> duplicate_detected={duplicate_detected}")
    if not duplicate_detected:
        problems.append(f"중복 해시 탐지 실패: {dup_problems}")

    summ = _copy.deepcopy(valid_ev)
    summ["report"]["summary"]["net_diff"] += 1
    summ_problems = validate_evidence(summ)
    summary_tamper_detected = any("summary" in x for x in summ_problems)
    if not summary_tamper_detected:
        problems.append(f"요약 변조 탐지 실패: {summ_problems}")

    difft = _copy.deepcopy(valid_ev)
    difft["report"]["bins"][0]["diff"] += 1
    diff_problems = validate_evidence(difft)
    diff_tamper_detected = any(("diff" in x or "verdict" in x) for x in diff_problems)
    if not diff_tamper_detected:
        problems.append(f"diff 변조 탐지 실패: {diff_problems}")

    mockt = _copy.deepcopy(valid_ev)
    mockt["report"]["source"] = "mock"
    mockt["report"]["capture_source"] = "pi-camera"
    mock_problems = validate_evidence(mockt)
    mock_source_blocked = any("source" in x for x in mock_problems) and any("capture_source" in x for x in mock_problems)
    if not mock_source_blocked:
        problems.append(f"mock source/capture_source 탐지 실패: {mock_problems}")

    endt = _copy.deepcopy(valid_ev)
    endt["endpoint"] = "https://example.invalid/v1/responses"
    endt["path"] = "qa.sam_session.run_sam_session"
    end_problems = validate_evidence(endt)
    endpoint_tamper_detected = any("endpoint" in x for x in end_problems) and any("path" in x for x in end_problems)
    if not endpoint_tamper_detected:
        problems.append(f"endpoint/path 탐지 실패: {end_problems}")

    valid_cli_stdout = ""
    valid_exit = -1
    tamper_exit = -1
    missing_exit = -1
    cli_report: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        good = root / "photo-evidence.json"
        good.write_text(json.dumps(valid_ev, ensure_ascii=False), encoding="utf-8")
        result = run_cli(["-m", "qa.sam_photo_evidence", "--file", str(good)])
        valid_exit = result.returncode
        ctx.note(f"python3 -m qa.sam_photo_evidence --file 유효 -> 종료코드 {result.returncode}")
        if result.returncode != 0:
            problems.append(f"유효 CLI 종료코드 기대 0, 실제 {result.returncode}: {result.stderr[:200]}")
        for needle in ("VALID: true", f"SESSION: {SAM_PHOTO_EVIDENCE_SESSION_ID}", "SOURCE: sam", "CAPTURE_SOURCE: file", "DISTINCT_IMAGES: 6", "SUBMISSION_READY: false"):
            if needle not in result.stdout:
                problems.append(f"유효 CLI 텍스트에 {needle!r} 없음")
        result_j = run_cli(["-m", "qa.sam_photo_evidence", "--file", str(good), "--json"])
        valid_cli_stdout = result_j.stdout
        ctx.note(f"python3 -m qa.sam_photo_evidence --file 유효 --json -> 종료코드 {result_j.returncode}")
        if result_j.returncode != 0:
            problems.append(f"유효 CLI --json 종료코드 기대 0, 실제 {result_j.returncode}")
        try:
            cli_report = json.loads(result_j.stdout)
        except json.JSONDecodeError as e:
            problems.append(f"유효 CLI --json 파싱 실패: {e}")
        if cli_report:
            if cli_report.get("valid") is not True:
                problems.append(f"CLI valid 기대 True, 실제 {cli_report.get('valid')}")
            if cli_report.get("distinct_image_count") != 6:
                problems.append(f"CLI distinct 기대 6, 실제 {cli_report.get('distinct_image_count')}")
            if cli_report.get("capture_source") != "file":
                problems.append(f"CLI capture_source 기대 file, 실제 {cli_report.get('capture_source')}")
            sm = cli_report.get("summary") or {}
            if sm.get("abs_diff_total") != 30 or sm.get("net_diff") != -28 or sm.get("matched") != 1 or sm.get("mismatched") != 5:
                problems.append(f"CLI summary 기대 matched1/mismatched5/abs30/net-28, 실제 {sm}")
            joined = " ".join(str(x) for x in cli_report.get("honesty", []))
            for marker in ("API를 호출하지 않는다", "Pi 실촬영이 아니다"):
                if marker not in joined:
                    problems.append(f"CLI honesty에 {marker!r} 없음")
        bad = root / "photo-evidence-dup.json"
        bad.write_text(json.dumps(dup, ensure_ascii=False), encoding="utf-8")
        result_bad = run_cli(["-m", "qa.sam_photo_evidence", "--file", str(bad), "--json"])
        tamper_exit = result_bad.returncode
        ctx.note(f"python3 -m qa.sam_photo_evidence --file 중복 --json -> 종료코드 {result_bad.returncode}")
        if result_bad.returncode != 1:
            problems.append(f"변조 CLI 종료코드 기대 1, 실제 {result_bad.returncode}")
        else:
            try:
                bad_report = json.loads(result_bad.stdout)
                if bad_report.get("valid") is not False:
                    problems.append(f"변조 CLI valid 기대 False, 실제 {bad_report.get('valid')}")
            except json.JSONDecodeError as e:
                problems.append(f"변조 CLI --json 파싱 실패: {e}")
        result_missing = run_cli(["-m", "qa.sam_photo_evidence", "--file", str(root / "nope.json")])
        missing_exit = result_missing.returncode
        ctx.note(f"python3 -m qa.sam_photo_evidence --file 없음 -> 종료코드 {result_missing.returncode}")
        if result_missing.returncode != 2:
            problems.append(f"없는 파일 종료코드 기대 2, 실제 {result_missing.returncode}")

    smry = report.get("summary") or {}
    summary = {"feature": "sam-photo-evidence",
               "valid_ok": report.get("valid") is True,
               "session_id": report.get("session_id"),
               "source": report.get("source"),
               "capture_source": report.get("capture_source"),
               "distinct_image_count": report.get("distinct_image_count"),
               "matched": smry.get("matched"),
               "mismatched": smry.get("mismatched"),
               "abs_diff_total": smry.get("abs_diff_total"),
               "net_diff": smry.get("net_diff"),
               "duplicate_detected": duplicate_detected,
               "summary_tamper_detected": summary_tamper_detected,
               "diff_tamper_detected": diff_tamper_detected,
               "mock_source_blocked": mock_source_blocked,
               "endpoint_tamper_detected": endpoint_tamper_detected,
               "missing_file_exit_code": missing_exit,
               "tamper_exit_code": tamper_exit,
               "valid_exit_code": valid_exit,
               "all_ok": not problems, "problems": problems}
    summary["valid_ok"] = report.get("valid") is True and not problems
    write_evidence(evidence, ctx.lines, summary,
                   {"sam-photo-evidence-valid.json": valid_cli_stdout,
                    "sam-photo-evidence-report.json": json.dumps(report, ensure_ascii=False, indent=2) + "\n"})
    return summary


def drive_video_selection(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.fallback_decision import today_kst
    from qa.video_selection import (FALLBACK_VIDEO, PRIMARY_VIDEO,
                                    build_selection, evaluate_selection,
                                    validate_selection)

    blockers = list(EXPECTED_PI_READINESS_BLOCKER_IDS)

    result = run_cli(["-m", "qa.video_selection", "--date",
                      VIDEO_SELECTION_PENDING_DATE])
    ctx.note(f"python3 -m qa.video_selection --date {VIDEO_SELECTION_PENDING_DATE} "
             f"-> 종료코드 {result.returncode}")
    if result.returncode != 0:
        problems.append(f"video_selection pending 종료코드 기대 0, 실제 {result.returncode}: {result.stderr[:200]}")
    for needle in ("FALLBACK_STATUS: pending",
                   f"SELECTED_VIDEO: {PRIMARY_VIDEO}",
                   "SELECTION_REASON: pending_default",
                   "SUBMISSION_READY: false", "Pi 실촬영이 아닙니다"):
        if needle not in result.stdout:
            problems.append(f"video_selection 텍스트에 {needle!r} 없음")

    result_j = run_cli(["-m", "qa.video_selection", "--date",
                        VIDEO_SELECTION_PENDING_DATE, "--json"])
    ctx.note(f"python3 -m qa.video_selection --date {VIDEO_SELECTION_PENDING_DATE} --json -> 종료코드 {result_j.returncode}")
    if result_j.returncode != 0:
        problems.append(f"video_selection pending --json 종료코드 기대 0, 실제 {result_j.returncode}")
    pending: dict = {}
    try:
        pending = json.loads(result_j.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"pending --json 파싱 실패: {e}")
    if pending:
        if pending.get("fallback_status") != "pending":
            problems.append(f"pending status 기대 pending, 실제 {pending.get('fallback_status')}")
        if pending.get("selected_video") != PRIMARY_VIDEO:
            problems.append(f"pending selected 기대 {PRIMARY_VIDEO}, 실제 {pending.get('selected_video')}")
        if pending.get("selection_reason") != "pending_default":
            problems.append(f"pending reason 기대 pending_default, 실제 {pending.get('selection_reason')}")
        if pending.get("submission_ready") is not False:
            problems.append("pending submission_ready는 False여야 한다")
        if list(pending.get("pi_blockers") or []) != blockers:
            problems.append(f"pending pi_blockers 기대 {blockers}, 실제 {pending.get('pi_blockers')}")
        if not (isinstance(pending.get("primary_size"), int) and pending["primary_size"] > 0):
            problems.append(f"pending primary_size 이상: {pending.get('primary_size')}")
        if not (isinstance(pending.get("fallback_size"), int) and pending["fallback_size"] > 0):
            problems.append(f"pending fallback_size 이상: {pending.get('fallback_size')}")
        joined = " ".join(str(x) for x in pending.get("honesty", []))
        for marker in ("실제로 제출하지 않는다", "제출 준비 완료를 뜻하지 않는다",
                       "Pi 실촬영이 아닙니다", "실촬영본이 되지는 않는다"):
            if marker not in joined:
                problems.append(f"pending honesty에 {marker!r} 없음")

    result_due = run_cli(["-m", "qa.video_selection", "--date",
                          VIDEO_SELECTION_DUE_DATE, "--json"])
    ctx.note(f"python3 -m qa.video_selection --date {VIDEO_SELECTION_DUE_DATE} --json -> 종료코드 {result_due.returncode} (가정 날짜 구동)")
    if result_due.returncode != 0:
        problems.append(f"video_selection due --json 종료코드 기대 0, 실제 {result_due.returncode}")
    due: dict = {}
    try:
        due = json.loads(result_due.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"due --json 파싱 실패: {e}")
    if due:
        if due.get("fallback_status") != "fallback_due":
            problems.append(f"due status 기대 fallback_due, 실제 {due.get('fallback_status')}")
        if due.get("selected_video") != FALLBACK_VIDEO:
            problems.append(f"due selected 기대 {FALLBACK_VIDEO}, 실제 {due.get('selected_video')}")
        if due.get("fallback_adopted") is not True:
            problems.append(f"due fallback_adopted 기대 True, 실제 {due.get('fallback_adopted')}")
        if due.get("selection_reason") != "fallback_due":
            problems.append(f"due reason 기대 fallback_due, 실제 {due.get('selection_reason')}")

    # 기본 날짜 구동 — --date 없는 기본 실행이 KST 오늘을 쓰는지 확인한다.
    result_default_vs = run_cli(["-m", "qa.video_selection", "--json"])
    ctx.note(f"python3 -m qa.video_selection --json (기본 날짜) "
             f"-> 종료코드 {result_default_vs.returncode}")
    if result_default_vs.returncode != 0:
        problems.append(f"video_selection 기본 --json 종료코드 기대 0, 실제 {result_default_vs.returncode}")
    default_vs: dict = {}
    try:
        default_vs = json.loads(result_default_vs.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"video_selection 기본 --json 파싱 실패: {e}")
    kst_today_vs = today_kst()
    default_vs_date_is_kst = bool(default_vs) and default_vs.get("date") == kst_today_vs
    ctx.note(f"영상 선택 기본 날짜 -> date={default_vs.get('date')} "
             f"kst_today={kst_today_vs} status={default_vs.get('fallback_status')} "
             f"selected={default_vs.get('selected_video')}")
    if default_vs:
        if not default_vs_date_is_kst:
            problems.append(
                f"영상 선택 기본 날짜 기대 KST 오늘 {kst_today_vs}, 실제 {default_vs.get('date')}")
        v_default_vs = validate_selection(default_vs)
        if v_default_vs:
            problems.append(f"영상 선택 기본 보고 validate 문제: {v_default_vs}")
        expected_vs = evaluate_selection(
            str(default_vs.get("date")), bool(default_vs.get("pi_ready")),
            list(default_vs.get("pi_blockers") or []),
            primary_size=default_vs.get("primary_size"),
            fallback_size=default_vs.get("fallback_size"))
        for key in ("fallback_status", "fallback_adopted", "selected_video",
                    "selection_reason", "selected_size"):
            if default_vs.get(key) != expected_vs.get(key):
                problems.append(
                    f"영상 선택 기본 {key} 기대 {expected_vs.get(key)}, 실제 {default_vs.get(key)}")

    # 최종 묶음(qa.final_package)과의 교차 대조 — 같은 날짜 기준
    fp_pending: dict = {}
    fp_due: dict = {}
    fp_cross_ok = False
    result_fp = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                         "--date", VIDEO_SELECTION_PENDING_DATE, "--json"])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {VIDEO_SELECTION_PENDING_DATE} --json "
             f"-> 종료코드 {result_fp.returncode} (영상 선택 pending과 같은 날짜)")
    if result_fp.returncode != 0:
        problems.append(
            f"final_package pending --json 종료코드 기대 0, 실제 {result_fp.returncode}")
    try:
        fp_pending = json.loads(result_fp.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"final_package pending --json 파싱 실패: {e}")
    result_fp_due = run_cli(["-m", "qa.final_package", "--now", FINAL_PACKAGE_NOW,
                             "--date", VIDEO_SELECTION_DUE_DATE, "--json"])
    ctx.note(f"python3 -m qa.final_package --now {FINAL_PACKAGE_NOW} "
             f"--date {VIDEO_SELECTION_DUE_DATE} --json "
             f"-> 종료코드 {result_fp_due.returncode} (영상 선택 due와 같은 날짜)")
    if result_fp_due.returncode != 0:
        problems.append(
            f"final_package due --json 종료코드 기대 0, 실제 {result_fp_due.returncode}")
    try:
        fp_due = json.loads(result_fp_due.stdout)
    except json.JSONDecodeError as e:
        problems.append(f"final_package due --json 파싱 실패: {e}")
    if fp_pending and pending:
        cross_before = len(problems)
        if fp_pending.get("status") != "blocked":
            problems.append(
                f"final_package pending status 기대 'blocked', 실제 {fp_pending.get('status')}")
        for key in ("fallback_status", "selected_video", "selection_reason",
                    "selected_size"):
            if fp_pending.get(key) != pending.get(key):
                problems.append(
                    f"final_package pending {key}가 video_selection pending과 다르다: "
                    f"{fp_pending.get(key)} != {pending.get(key)}")
        if fp_pending.get("fallback_adopted") is not False:
            problems.append(
                f"final_package pending fallback_adopted 기대 False, 실제 {fp_pending.get('fallback_adopted')}")
        if fp_pending.get("blockers") != ["pi_real_capture_pending"]:
            problems.append(f"final_package pending blockers 이상: {fp_pending.get('blockers')}")
        if fp_pending.get("submission_ready") is not False:
            problems.append(
                f"final_package pending submission_ready 기대 False, 실제 {fp_pending.get('submission_ready')}")
        fp_pending_ok = len(problems) == cross_before
    else:
        fp_pending_ok = False
    if fp_due and due:
        cross_before = len(problems)
        if fp_due.get("status") != "blocked":
            problems.append(
                f"final_package due status 기대 'blocked', 실제 {fp_due.get('status')}")
        for key in ("fallback_status", "selected_video", "selection_reason",
                    "selected_size"):
            if fp_due.get(key) != due.get(key):
                problems.append(
                    f"final_package due {key}가 video_selection due와 다르다: "
                    f"{fp_due.get(key)} != {due.get(key)}")
        if fp_due.get("fallback_adopted") is not True:
            problems.append(
                f"final_package due fallback_adopted 기대 True, 실제 {fp_due.get('fallback_adopted')}")
        if fp_due.get("blockers") != ["pi_real_capture_pending"]:
            problems.append(f"final_package due blockers 이상: {fp_due.get('blockers')}")
        if fp_due.get("submission_ready") is not False:
            problems.append(
                f"final_package due submission_ready 기대 False, 실제 {fp_due.get('submission_ready')}")
        fp_due_ok = len(problems) == cross_before
    else:
        fp_due_ok = False
    fp_cross_ok = bool(fp_pending_ok and fp_due_ok)
    ctx.note(f"영상 선택↔최종 묶음 교차 대조 -> fp_cross_ok={fp_cross_ok}")

    result_bad = run_cli(["-m", "qa.video_selection", "--date", "not-a-date"])
    ctx.note(f"python3 -m qa.video_selection --date not-a-date -> 종료코드 {result_bad.returncode}")
    if result_bad.returncode != 2:
        problems.append(f"잘못된 날짜 종료코드 기대 2, 실제 {result_bad.returncode}")

    # In-process evaluate / validate
    ev_pending = ev_due = ev_ready = {}
    try:
        ev_pending = evaluate_selection(VIDEO_SELECTION_PENDING_DATE, False, blockers,
                                        VIDEO_SELECTION_PRIMARY_SIZE, VIDEO_SELECTION_FALLBACK_SIZE)
        ev_due = evaluate_selection(VIDEO_SELECTION_DUE_DATE, False, blockers,
                                    VIDEO_SELECTION_PRIMARY_SIZE, VIDEO_SELECTION_FALLBACK_SIZE)
        ev_ready = evaluate_selection(VIDEO_SELECTION_READY_DATE, True, [],
                                      VIDEO_SELECTION_PRIMARY_SIZE, VIDEO_SELECTION_FALLBACK_SIZE)
        for label, rep_ in (("pending", ev_pending), ("due", ev_due), ("ready", ev_ready)):
            v = validate_selection(rep_)
            if v:
                problems.append(f"validate_selection {label} 문제: {v}")
            if rep_.get("problems") != []:
                problems.append(f"evaluate {label} problems 기대 [], 실제 {rep_.get('problems')}")
        if ev_pending.get("selected_video") != PRIMARY_VIDEO or ev_pending.get("selection_reason") != "pending_default":
            problems.append(f"evaluate pending 선택 이상: {ev_pending}")
        if ev_due.get("selected_video") != FALLBACK_VIDEO or ev_due.get("fallback_adopted") is not True:
            problems.append(f"evaluate due 선택 이상: {ev_due}")
        if ev_ready.get("fallback_status") != "pi_ready" or ev_ready.get("selected_video") != PRIMARY_VIDEO:
            problems.append(f"evaluate ready 선택 이상: {ev_ready}")
    except Exception as e:
        problems.append(f"evaluate_selection 실패: {type(e).__name__}: {e}")

    # build_selection with probes
    built_pending: dict = {}
    built_ready: dict = {}
    try:
        built_pending = build_selection(today=VIDEO_SELECTION_PENDING_DATE,
                                        pi_probe=PI_READINESS_MISSING_PROBE)
        built_ready = build_selection(today=VIDEO_SELECTION_DUE_DATE,
                                      pi_probe=PI_READINESS_READY_PROBE,
                                      device_confirmed=True)
    except Exception as e:
        problems.append(f"build_selection 실패: {type(e).__name__}: {e}")
    if built_pending:
        ctx.note(f"build_selection missing probe -> status={built_pending.get('fallback_status')} selected={built_pending.get('selected_video')}")
        if built_pending.get("fallback_status") != "pending" or built_pending.get("selected_video") != PRIMARY_VIDEO:
            problems.append(f"build pending 이상: {built_pending}")
        if validate_selection(built_pending) != []:
            problems.append(f"build pending validate 문제: {validate_selection(built_pending)}")
    if built_ready:
        ctx.note(f"build_selection ready probe -> status={built_ready.get('fallback_status')} selected={built_ready.get('selected_video')}")
        if built_ready.get("fallback_status") != "pi_ready" or built_ready.get("selected_video") != PRIMARY_VIDEO:
            problems.append(f"build ready 이상: {built_ready}")

    # Missing selected detection
    missing_detected = False
    try:
        miss = evaluate_selection(VIDEO_SELECTION_DUE_DATE, False, blockers,
                                  VIDEO_SELECTION_PRIMARY_SIZE, None)
        missing_detected = any(FALLBACK_VIDEO in p for p in (miss.get("problems") or []))
    except Exception as e:
        problems.append(f"missing 구동 실패: {type(e).__name__}: {e}")
    ctx.note(f"영상 선택 missing 탐지 -> {missing_detected}")
    if not missing_detected:
        problems.append("missing 탐지 실패: 폴백 크기 None인데 문제를 찾지 못했다")

    # Tamper detection
    tamper_parts = {}
    try:
        base = evaluate_selection(VIDEO_SELECTION_PENDING_DATE, False, blockers,
                                  VIDEO_SELECTION_PRIMARY_SIZE, VIDEO_SELECTION_FALLBACK_SIZE)
        t1 = dict(base, selected_video=FALLBACK_VIDEO)
        tamper_parts["selected_video"] = any("selected_video" in p for p in validate_selection(t1))
        t2 = dict(base, submission_ready=True)
        tamper_parts["submission_ready"] = any("submission_ready" in p for p in validate_selection(t2))
        t3 = dict(base, fallback_status="fallback_due")
        tamper_parts["fallback_status"] = any("fallback_status" in p for p in validate_selection(t3))
        t4 = dict(base, honesty=["선택은 실제로 제출하지 않는다"])
        tamper_parts["honesty"] = any("honesty" in p for p in validate_selection(t4))
    except Exception as e:
        problems.append(f"변조 탐지 구동 실패: {type(e).__name__}: {e}")
    tamper_detected = bool(tamper_parts) and all(tamper_parts.values())
    ctx.note(f"영상 선택 변조 탐지 -> {tamper_parts}")
    if not tamper_detected:
        problems.append(f"변조 탐지 실패: {tamper_parts}")

    summary = {"feature": "video-selection",
               "pending_status": pending.get("fallback_status"),
               "due_status": due.get("fallback_status"),
               "default_date": default_vs.get("date"),
               "default_status": default_vs.get("fallback_status"),
               "default_selected": default_vs.get("selected_video"),
               "default_date_is_kst": default_vs_date_is_kst,
               "ready_status": ev_ready.get("fallback_status"),
               "pending_selected": pending.get("selected_video"),
               "due_selected": due.get("selected_video"),
               "ready_selected": ev_ready.get("selected_video"),
               "pending_reason": pending.get("selection_reason"),
               "due_reason": due.get("selection_reason"),
               "pending_primary_size": pending.get("primary_size"),
               "pending_fallback_size": pending.get("fallback_size"),
               "submission_ready": pending.get("submission_ready"),
               "tamper_detected": tamper_detected,
               "tamper_parts": tamper_parts,
               "missing_detected": missing_detected,
               "invalid_exit_code": result_bad.returncode,
               "pending_exit_code": result.returncode,
               "due_exit_code": result_due.returncode,
               "fp_pending_selected_video": fp_pending.get("selected_video"),
               "fp_pending_selected_size": fp_pending.get("selected_size"),
               "fp_due_selected_video": fp_due.get("selected_video"),
               "fp_due_selected_size": fp_due.get("selected_size"),
               "fp_cross_ok": fp_cross_ok,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"video-selection-pending.json": result_j.stdout,
                    "video-selection-due.json": result_due.stdout,
                    "video-selection-default.json": result_default_vs.stdout,
                    "video-selection-final-package-pending.json": result_fp.stdout,
                    "video-selection-final-package-due.json": result_fp_due.stdout})
    return summary


def drive_package_archive(ctx: Ctx, evidence: Path) -> dict:
    problems: list[str] = []
    from qa.package_archive import (build_archive, build_archive_verify,
                                    validate_archive)
    from qa.video_selection import FALLBACK_VIDEO

    result = result_j = None
    archived: dict = {}
    total_bytes = None
    validate_problems: list = []
    manifest_ok = False
    selected_sha_ok = False
    tamper_detected = False
    ready_tamper_detected = False
    result_verify = result_verify_j = None
    verify_exit_code = None
    verify_text_ok = False
    verify_readonly = False
    verify_tamper_detected = False
    verify_tamper_exit_code = None
    verify_missing_exit_code = None
    verify_inproc_ok = False
    with tempfile.TemporaryDirectory() as tmp:
        arch = Path(tmp) / "arc-cli"
        result = run_cli(["-m", "qa.package_archive", "--out-dir", str(arch)])
        ctx.note(f"python3 -m qa.package_archive --out-dir <tmp> -> 종료코드 {result.returncode}")
        if result.returncode != 0:
            problems.append(
                f"package_archive 종료코드 기대 0, 실제 {result.returncode}: "
                f"{result.stderr[:200]}")
        for needle in ("Argus 제출 패키지 아카이브", "STATUS: archived",
                       "COPIED: 18", "TOTAL: 18", "ARCHIVE_VERIFIED: true",
                       f"SELECTED_VIDEO: {FALLBACK_VIDEO}",
                       "SUBMISSION_READY: false",
                       "실제로 제출하지 않는다", "Pi 실촬영 검증 전"):
            if needle not in result.stdout:
                problems.append(f"package_archive 텍스트에 {needle!r} 없음")

        arch_j = Path(tmp) / "arc-json"
        result_j = run_cli(["-m", "qa.package_archive", "--out-dir",
                            str(arch_j), "--json"])
        ctx.note(f"python3 -m qa.package_archive --out-dir <tmp> --json "
                 f"-> 종료코드 {result_j.returncode}")
        if result_j.returncode != 0:
            problems.append(
                f"package_archive --json 종료코드 기대 0, 실제 {result_j.returncode}: "
                f"{result_j.stderr[:200]}")
        try:
            archived = json.loads(result_j.stdout)
        except json.JSONDecodeError as e:
            problems.append(f"package_archive --json 파싱 실패: {e}")
        if archived:
            if archived.get("status") != "archived":
                problems.append(f"status 기대 archived, 실제 {archived.get('status')}")
            if archived.get("mode") != "export":
                problems.append(f"mode 기대 export, 실제 {archived.get('mode')}")
            if archived.get("copied") != INVENTORY_TOTAL_FILES:
                problems.append(f"copied 기대 {INVENTORY_TOTAL_FILES}, 실제 {archived.get('copied')}")
            if archived.get("total") != INVENTORY_TOTAL_FILES:
                problems.append(f"total 기대 {INVENTORY_TOTAL_FILES}, 실제 {archived.get('total')}")
            if archived.get("missing") != []:
                problems.append(f"missing 기대 [], 실제 {archived.get('missing')}")
            if archived.get("verify_verified") is not True:
                problems.append(f"verify_verified 기대 True, 실제 {archived.get('verify_verified')}")
            if archived.get("archive_verified") is not True:
                problems.append(f"archive_verified 기대 True, 실제 {archived.get('archive_verified')}")
            if archived.get("blockers") != list(EXPECTED_BLOCKER_IDS):
                problems.append(f"blockers 기대 {list(EXPECTED_BLOCKER_IDS)}, 실제 {archived.get('blockers')}")
            if archived.get("submission_ready") is not False:
                problems.append(f"submission_ready 기대 False, 실제 {archived.get('submission_ready')}")
            if archived.get("selected_video") != FALLBACK_VIDEO:
                problems.append(f"selected_video 기대 {FALLBACK_VIDEO}, 실제 {archived.get('selected_video')}")
            if archived.get("selected_copied") is not True:
                problems.append(f"selected_copied 기대 True, 실제 {archived.get('selected_copied')}")
            sel_size = archived.get("selected_size")
            if not isinstance(sel_size, int) or sel_size <= 0:
                problems.append(f"selected_size 이상: {sel_size}")
            if archived.get("selected_size_in_archive") != sel_size:
                problems.append(
                    f"selected_size_in_archive가 selected_size와 다르다: "
                    f"{archived.get('selected_size_in_archive')} != {sel_size}")
            sha = archived.get("selected_sha256")
            if not (isinstance(sha, str) and len(sha) == 64):
                problems.append(f"selected_sha256 이상: {sha}")
            total_bytes = archived.get("total_bytes")
            if not isinstance(total_bytes, int) or total_bytes <= 0:
                problems.append(f"total_bytes 이상: {total_bytes}")
            joined = " ".join(str(x) for x in archived.get("honesty", []))
            for marker in ("실제로 제출하지 않는다", "제출 준비 완료를 뜻하지 않는다",
                           "Pi 실촬영 검증 전", "데모 기준"):
                if marker not in joined:
                    problems.append(f"honesty에 {marker!r} 없음")

        result_bad = run_cli(["-m", "qa.package_archive"])
        ctx.note(f"python3 -m qa.package_archive (인자 없음) -> 종료코드 {result_bad.returncode}")
        if result_bad.returncode != 2:
            problems.append(f"인자 없음 종료코드 기대 2, 실제 {result_bad.returncode}")
        invalid_exit_code = result_bad.returncode

        result_conflict = run_cli(["-m", "qa.package_archive", "--out-dir",
                                   str(Path(tmp) / "arc-x"), "--verify-dir",
                                   str(arch)])
        ctx.note(f"python3 -m qa.package_archive --out-dir+--verify-dir -> 종료코드 {result_conflict.returncode}")
        if result_conflict.returncode != 2:
            problems.append(f"인자 충돌 종료코드 기대 2, 실제 {result_conflict.returncode}")
        conflict_exit_code = result_conflict.returncode

        arch_in = Path(tmp) / "arc-inproc"
        built = build_archive(arch_in, ROOT)
        validate_problems = validate_archive(built)
        ctx.note(f"validate_archive(build_archive) -> 문제 {len(validate_problems)}건")
        if validate_problems:
            problems.append(f"validate_archive 문제: {validate_problems}")
        if built.get("status") != "archived" or built.get("archive_verified") is not True:
            problems.append(f"build_archive archived 아님: {built.get('status')}")
        manifest_ok = (arch_in / "package-manifest.json").is_file()
        if not manifest_ok:
            problems.append("package-manifest.json이 아카이브에 없다")
        copied_video = arch_in / str(built.get("selected_video"))
        if not copied_video.is_file():
            problems.append(f"선택 영상 복사본 없음: {built.get('selected_video')}")
        else:
            digest = hashlib.sha256(copied_video.read_bytes()).hexdigest()
            selected_sha_ok = digest == built.get("selected_sha256")
            if not selected_sha_ok:
                problems.append("선택 영상 복사본 sha256이 기록과 다르다")
            if copied_video.stat().st_size != built.get("selected_size_in_archive"):
                problems.append("선택 영상 복사본 크기가 기록과 다르다")
        ctx.note(f"선택 영상 복사본 SHA-256 일치 -> {selected_sha_ok}")

        tampered_status = copy.deepcopy(built)
        tampered_status["status"] = "mismatch"
        tamper_detected = any(
            "status" in p for p in validate_archive(tampered_status))
        ctx.note(f"status 변조 탐지 -> {tamper_detected}")
        if not tamper_detected:
            problems.append("변조 탐지 실패: status를 mismatch로 바꿔도 문제를 찾지 못했다")
        tampered_ready = copy.deepcopy(built)
        tampered_ready["submission_ready"] = True
        ready_tamper_detected = any(
            "submission_ready" in p for p in validate_archive(tampered_ready))
        ctx.note(f"submission_ready 변조 탐지 -> {ready_tamper_detected}")
        if not ready_tamper_detected:
            problems.append("변조 탐지 실패: submission_ready를 True로 바꿔도 문제를 찾지 못했다")

        def _snapshot(base: Path) -> dict:
            snap = {}
            for fp in sorted(base.rglob("*")):
                if fp.is_file():
                    data = fp.read_bytes()
                    snap[str(fp.relative_to(base))] = (len(data), hashlib.sha256(data).hexdigest())
            return snap

        arch_verify = Path(tmp) / "arc-verify"
        build_archive(arch_verify, ROOT)
        snap_before = _snapshot(arch_verify)
        result_verify_j = run_cli(["-m", "qa.package_archive", "--verify-dir",
                                   str(arch_verify), "--json"])
        verify_exit_code = result_verify_j.returncode
        ctx.note(f"python3 -m qa.package_archive --verify-dir <tmp> --json "
                 f"-> 종료코드 {result_verify_j.returncode}")
        if result_verify_j.returncode != 0:
            problems.append(
                f"package_archive --verify-dir --json 종료코드 기대 0, 실제 {result_verify_j.returncode}: "
                f"{result_verify_j.stderr[:200]}")
        try:
            verify_payload = json.loads(result_verify_j.stdout)
        except json.JSONDecodeError as e:
            verify_payload = {}
            problems.append(f"package_archive --verify-dir --json 파싱 실패: {e}")
        if verify_payload:
            if verify_payload.get("mode") != "verify":
                problems.append(f"verify mode 기대 verify, 실제 {verify_payload.get('mode')}")
            if verify_payload.get("status") != "archived":
                problems.append(f"verify status 기대 archived, 실제 {verify_payload.get('status')}")
            if verify_payload.get("archive_verified") is not True:
                problems.append(f"verify archive_verified 기대 True, 실제 {verify_payload.get('archive_verified')}")
            if verify_payload.get("submission_ready") is not False:
                problems.append(f"verify submission_ready 기대 False, 실제 {verify_payload.get('submission_ready')}")

        result_verify = run_cli(["-m", "qa.package_archive", "--verify-dir",
                                 str(arch_verify)])
        ctx.note(f"python3 -m qa.package_archive --verify-dir <tmp> -> 종료코드 {result_verify.returncode}")
        if result_verify.returncode != 0:
            problems.append(f"package_archive --verify-dir 종료코드 기대 0, 실제 {result_verify.returncode}")
        verify_text_ok = True
        for needle in ("Argus 제출 패키지 아카이브", "STATUS: archived",
                       "ARCHIVE_VERIFIED: true", "SUBMISSION_READY: false",
                       "실제로 제출하지 않는다", "Pi 실촬영 검증 전"):
            if needle not in result_verify.stdout:
                verify_text_ok = False
                problems.append(f"package_archive --verify-dir 텍스트에 {needle!r} 없음")

        snap_after = _snapshot(arch_verify)
        verify_readonly = snap_before == snap_after and bool(snap_before)
        ctx.note(f"verify-dir 읽기 전용(스냅샷 불변) -> {verify_readonly}")
        if not verify_readonly:
            problems.append("verify-dir가 아카이브 파일을 변경했다(읽기 전용 위반)")

        verified_inproc = build_archive_verify(arch_verify, ROOT)
        verify_inproc_ok = (verified_inproc.get("status") == "archived"
                            and verified_inproc.get("archive_verified") is True
                            and validate_archive(verified_inproc) == [])
        ctx.note(f"build_archive_verify(깨끗한 아카이브) -> status {verified_inproc.get('status')}")
        if not verify_inproc_ok:
            problems.append(f"build_archive_verify 문제: {verified_inproc.get('problems')}")

        arch_vt = Path(tmp) / "arc-verify-tamper"
        build_archive(arch_vt, ROOT)
        (arch_vt / "README.md").write_bytes(b"tampered")
        result_vt = run_cli(["-m", "qa.package_archive", "--verify-dir",
                             str(arch_vt), "--json"])
        verify_tamper_exit_code = result_vt.returncode
        ctx.note(f"python3 -m qa.package_archive --verify-dir <변조 tmp> --json -> 종료코드 {result_vt.returncode}")
        try:
            vt_payload = json.loads(result_vt.stdout)
        except json.JSONDecodeError:
            vt_payload = {}
        verify_tamper_detected = (result_vt.returncode == 1
                                  and vt_payload.get("archive_verified") is False
                                  and vt_payload.get("status") != "archived")
        if not verify_tamper_detected:
            problems.append("verify-dir 변조 탐지 실패: 복사본 README.md를 바꿔도 archive_verified=false로 잡지 못했다")

        empty_dir = Path(tmp) / "arc-verify-empty"
        empty_dir.mkdir()
        result_vm = run_cli(["-m", "qa.package_archive", "--verify-dir",
                             str(empty_dir), "--json"])
        verify_missing_exit_code = result_vm.returncode
        ctx.note(f"python3 -m qa.package_archive --verify-dir <빈 tmp> --json -> 종료코드 {result_vm.returncode}")
        try:
            vm_payload = json.loads(result_vm.stdout)
        except json.JSONDecodeError:
            vm_payload = {}
        if result_vm.returncode != 1 or vm_payload.get("archive_verified") is not False \
                or vm_payload.get("status") == "archived":
            problems.append(
                f"verify-dir 매니페스트 없음 기대 종료코드 1·archive_verified false·status archived 아님, "
                f"실제 {result_vm.returncode}·{vm_payload.get('archive_verified')}·{vm_payload.get('status')}")

    summary = {"feature": "package-archive",
               "status": archived.get("status"),
               "copied": archived.get("copied"),
               "total": archived.get("total"),
               "total_bytes": total_bytes,
               "verify_verified": archived.get("verify_verified"),
               "archive_verified": archived.get("archive_verified"),
               "selected_video": archived.get("selected_video"),
               "selected_size": archived.get("selected_size"),
               "blockers": archived.get("blockers"),
               "submission_ready": archived.get("submission_ready"),
               "validate_problems": validate_problems,
               "manifest_ok": manifest_ok,
               "selected_sha_ok": selected_sha_ok,
               "tamper_detected": tamper_detected,
               "ready_tamper_detected": ready_tamper_detected,
               "invalid_exit_code": invalid_exit_code,
               "conflict_exit_code": conflict_exit_code,
               "verify_exit_code": verify_exit_code,
               "verify_text_ok": verify_text_ok,
               "verify_readonly": verify_readonly,
               "verify_tamper_detected": verify_tamper_detected,
               "verify_tamper_exit_code": verify_tamper_exit_code,
               "verify_missing_exit_code": verify_missing_exit_code,
               "verify_inproc_ok": verify_inproc_ok,
               "all_ok": not problems, "problems": problems}
    write_evidence(evidence, ctx.lines, summary,
                   {"package-archive.json": result_j.stdout if result_j else "",
                    "package-archive.txt": result.stdout if result else "",
                    "package-archive-verify.json": result_verify_j.stdout if result_verify_j else "",
                    "package-archive-verify.txt": result_verify.stdout if result_verify else ""})
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
           "console-readiness": drive_console_readiness,
           "sam-smoke": drive_sam_smoke,
           "pi-smoke": drive_pi_smoke,
           "devpost-submission": drive_devpost_submission,
           "file-fallback": drive_file_fallback,
           "sam-session": drive_sam_session,
           "pi-session-full": drive_pi_session_full,
           "submission-inventory": drive_submission_inventory,
           "fallback-decision": drive_fallback_decision,
           "deadline": drive_deadline,
           "final-package": drive_final_package,
           "package-export": drive_package_export,
           "sam-per-bin": drive_sam_per_bin,
           "sam-live-evidence": drive_sam_live_evidence,
           "sam-session-evidence": drive_sam_session_evidence,
           "video-selection": drive_video_selection,
           "package-archive": drive_package_archive,
           "sam-photo-evidence": drive_sam_photo_evidence}


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
