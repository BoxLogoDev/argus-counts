"""제출 전 전수 점검 하네스.

기존 점검들(QA 기준값 대조, standalone 점검, 현재형 주장 감사)과
SAM 실호출 준비 점검·Pi 실촬영 준비 점검의 상태 정합,
콘솔 준비 상태(console.readiness)가 같은 조건의 두 준비 점검과
어긋나지 않는지의 정합, SAM 단일 빈 스모크(qa.sam_smoke) 보고가
SAM 준비 점검 보고와 어긋나지 않는지의 정합, SAM 전체 세션
(qa.sam_session) 보고가 SAM 준비 점검 보고와 어긋나지 않는지의
정합, Pi 단일 빈 스모크
(qa.pi_smoke) 보고가 Pi 준비 점검 보고와 어긋나지 않는지의 정합,
Pi 전체 촬영 세션(qa.pi_session) 보고가 Pi 준비 점검 보고와
어긋나지 않는지의 정합,
제출 문안 패키지(docs/devpost-submission.md) 원문이 전수 점검
블로커와 어긋나지 않는지의 정합, 제출 런북(docs/submission-runbook.md)
원문이 전수 점검 블로커와 어긋나지 않는지의 정합, 제출 스토리
(docs/submission-story.md) 원문이 전수 점검 블로커와 어긋나지
않는지의 정합, 영문 제출 요약(docs/submission-summary-en.md) 원문이
전수 점검 블로커와 어긋나지 않는지의 정합, 데모 대본
(docs/demo-script.md) 원문이 전수 점검 블로커와 어긋나지 않는지의
정합, README(README.md) 원문이 전수 점검 블로커와 어긋나지
않는지의 정합, 제출물 인벤토리(qa.submission_inventory) 보고가 전수 점검
블로커와 어긋나지 않는지의 정합, 폴백 결정(qa.fallback_decision) 보고가
Pi 준비 점검 보고와 어긋나지 않는지의 정합, 파일 입력 폴백 자산(demo/assets/fallback.json)이
Pi 실촬영으로 주장되지 않고 전수 점검 블로커와 어긋나지 않는지의
정합, 제출 마감 점검(qa.deadline) 보고가 전수 점검 블로커와
어긋나지 않는지의 정합, 제출 패키지 최종 묶음(qa.final_package) 보고가
제출물 인벤토리·제출 마감·폴백 결정 보고와 어긋나지 않는지의 정합,
데모 자산의 존재·정합을
한 번에 묶어 기계적으로 확인한다. 기계 점검은 총 24종이다.
데모 자산 정합(demo_assets_consistent)에는 조립 매니페스트
(demo/assets/assembly.json) 컷 3의 파일 입력 폴백 참조가 폴백
자산과 어긋나지 않는지의 대조도 포함된다. 조립 폴백 대조는
저장된 JSON 자산을 읽어 대조만 하며, 폴백 참조를 Pi 실촬영이나
컷 3 전환 확정으로 주장하지 않는다.
문안·런북·스토리·영문 요약·데모 대본·README 정합은 파일 원문을 읽어 대조만 하며 실제로 제출하지 않는다.
인벤토리 정합은 제출물 파일을 다시 읽어 해시·크기를 대조만 하며 실제로 제출하지 않는다.
폴백 정합은 저장된 JSON 자산을 읽어 대조만 하며 Pi 실촬영으로 주장하지 않는다.
폴백 결정 정합은 날짜·준비 상태 판정만 대조하며 실제 촬영을 하지 않는다.
마감 정합은 남은 시간 계산·상태 판정만 대조하며 실제로 제출하지 않는다.
마감 전이어도 제출 준비 완료를 뜻하지 않는다.
최종 묶음 정합은 세 보고를 모아 만든 묶음 보고를 대조만 하며 실제로 제출하지 않는다.
최종 묶음 상태가 blocked인 것은 실패가 아니고, ready_for_packaging이어도 제출 완료를 뜻하지 않는다.
결정일 전 pending은 실패가 아니고, fallback_due(폴백 채택)도 Pi 실촬영
성공을 뜻하지 않는다.
스모크·전체 세션 정합은 가짜 counter와 가짜 session으로만 구동하며 실제
API를 호출하지 않고 실제 촬영도 하지 않는다.
준비 점검 자체는 실호출·실촬영을 하지 않으며, 준비가 안 된
상태(블로커 존재)는 기계 점검 실패가 아니다. 실패는 준비
점검 보고가 내부적으로 모순되거나 전수 점검 블로커와
어긋나는 경우뿐이다.
video 체크는 MP4 크기와 함께 컷 1~9 데이터 패널 정합도 확인한다.
폴백 렌더 정합은 video 체크 안에서 폴백 MP4
(demo/assets/argus-demo-fallback-draft.mp4) 크기와 컷 3 폴백 패널
(파일 입력 폴백 — Pi 실촬영 아님·결정일 2026-11-02·capture_source=file·
source=mock·요약·A-01-02 사진 해시)이 현재 폴백 매니페스트와 맞는지
대조한다. 폴백 렌더 대조는 저장·생성 자산 대조만 하며 Pi 실촬영으로
주장하지 않는다.
기계적 체크가 전부 통과해도 제출 블로커가 남아 있으면 제출 가능
상태가 아니다. 블로커는 종료코드가 아니라 별도 목록으로 보고한다:
Pi 실촬영 검증은 아직 하지 않은 일이다. SAM 3.1 실호출은
2026-10-30 단일 빈 스모크에 이어 전체 세션도 커넥터 브리지로
통과했다(같은 가상 사진 재사용, 빈별 정확도 아님).

실행: 프로젝트 루트에서 `python3 -m qa.pre_submission`
`--json`을 주면 같은 내용을 JSON으로 출력하며 readiness 섹션을 포함한다.
기계적 체크가 전부 통과하면 종료코드 0, 하나라도 실패하면 1.
"""
from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from console.readiness import build_readiness as build_console_readiness
from qa.claims_audit import audit_files, audit_text
from qa.harness import run_checks as run_qa_checks
from qa.pi_readiness import check_readiness as check_pi_readiness
from qa.sam_readiness import check_readiness as check_sam_readiness
from qa.pi_smoke import run_smoke as run_pi_smoke
from qa.sam_smoke import run_smoke as run_sam_smoke
from qa.pi_session import run_pi_full_session
from qa.sam_session import run_sam_session
from qa.standalone import run_standalone_checks
from qa.submission_inventory import DELIVERABLES as INVENTORY_DELIVERABLES
from qa.submission_inventory import build_inventory, validate_inventory
from qa.fallback_decision import DECISION_DATE as FB_DECISION_DATE
from qa.fallback_decision import FALLBACK_ASSET as FB_DECISION_ASSET
from qa.fallback_decision import FALLBACK_RENDER as FB_DECISION_RENDER
from qa.fallback_decision import build_decision as _build_fb_decision
from qa.fallback_decision import validate_decision as _validate_fb_decision
from qa.deadline import DEADLINE_ET_TEXT as DL_ET_TEXT
from qa.deadline import DEADLINE_KST_ISO as DL_KST_ISO
from qa.deadline import build_deadline as _build_dl
from qa.deadline import validate_deadline as _validate_dl
from qa.final_package import PACKAGE_DATE_TARGET as FP_PACKAGE_DATE_TARGET
from qa.final_package import build_final_package as _build_fp
from qa.final_package import validate_final_package as _validate_fp

ROOT = Path(__file__).resolve().parent.parent

# 현재 사실인 제출 블로커. 코드가 임의로 해소 판정하지 않고 항상 보고한다.
BLOCKERS = [
    {
        "id": "pi_real_capture_pending",
        "detail": "Pi 실촬영 검증 전 — 데모 컷 3은 플레이스홀더이며 Pi 도착 후 교체해야 한다",
    },
]

DEMO_ASSET_FILES = [
    "demo/assets/captions.srt",
    "demo/assets/captions.vtt",
    "demo/assets/shot-list.json",
    "demo/assets/assembly.json",
    "demo/assets/narration.json",
    "demo/assets/captures/capture-manifest.json",
    "demo/assets/argus-demo-draft.mp4",
]

VIDEO_MIN_BYTES = 100_000

EXPECTED_BIN_IDS = ("A-01-01", "A-01-02", "A-02-02", "A-03-01", "B-01-02", "B-02-02")

HONESTY = [
    "기계적 체크 통과는 제출 가능을 뜻하지 않는다",
    "모의 어댑터 동작 중",
    "수치는 데모 기준",
]

SAM_READINESS_BLOCKER_ORDER = ("sam_credit_not_confirmed", "sam_base_url_missing", "sam_api_key_missing")

PI_READINESS_BLOCKER_ORDER = ("pi_device_arrival_not_confirmed", "pi_camera_command_missing")

SMOKE_BIN_ID = "A-01-02"

SMOKE_FAKE_COUNT = 5

PI_SMOKE_BIN_ID = "A-01-02"

PI_SMOKE_FAKE_COUNT = 5

PI_SMOKE_FAKE_SHA = "f" * 64

DEVPOST_REL = "docs/devpost-submission.md"

DEVPOST_SECTIONS = (
    "## 프로젝트 이름",
    "## 한 줄 소개",
    "## 소개",
    "## 동작 방식",
    "## Meta AI 도구 활용",
    "## 기술 구성",
    "## 데모 데이터",
    "## 해커톤 기간 중 신규 제작",
    "## 데모 영상",
    "## 현재 블로커와 제출 상태",
    "## 제출 전 교체할 항목",
)

DEVPOST_DEMO_MARKERS = (
    "데모 기준: 빈 6개 중 일치 4건, 불일치 2건",
    "데모 기준: 절대 차이 6개, 순차이 0, 일치율 66.7%",
    "실제 창고 성과가 아니다",
)

DEVPOST_HONESTY_MARKERS = (
    "모의 어댑터가 동작 중이지만 SAM 3.1 실호출은 전체 세션으로 검증했다(같은 가상 사진 재사용, 빈별 정확도 아님)",
    "가짜 transport",
    "Secure Vault",
    "가안",
    "컷 3은 Pi 실촬영 교체 예정인 플레이스홀더",
)

DEVPOST_REPO_URL = "https://github.com/BoxLogoDev/argus-counts"

DEVPOST_DEADLINE_ET = "2026-11-04 21:00 ET"

DEVPOST_DEADLINE_KST = "2026-11-05 11:00 KST"

RUNBOOK_REL = "docs/submission-runbook.md"

RUNBOOK_SECTIONS = (
    "## 0. 현재 상태",
    "## 1. 크레딧 확인",
    "## 2. API 키",
    "## 3. SAM 전환",
    "## 4. Pi 촬영",
    "## 5. 최종 점검",
    "## 6. 제출",
)

RUNBOOK_FINAL_COMMANDS = (
    "python3 -m unittest discover -s tests",
    "python3 -m qa",
    "python3 -m qa.standalone",
    "python3 -m qa.claims_audit",
    "python3 -m qa.pre_submission",
    "verify_argus.py --doctor",
    "verify_argus.py --feature all",
    "python3 -m demo.render_video",
)

RUNBOOK_CREDIT_AT = "2026-10-29 09:30"

RUNBOOK_DEADLINE_ET = "2026-11-04 21:00 ET"

RUNBOOK_DEADLINE_KST = "2026-11-05 11:00 KST"

RUNBOOK_REPO = "BoxLogoDev/argus-counts"

RUNBOOK_KEY_MARKERS = (
    "Secure Vault",
    "SAM_API_BASE_URL",
    "SAM_API_KEY",
    "--credit-confirmed",
)

RUNBOOK_HONESTY_MARKERS = ("모의", "검증 전", "단일 빈 스모크")

STORY_REL = "docs/submission-story.md"

STORY_SECTIONS = (
    "## 문제",
    "## 해결",
    "## 이번에 만든 것과 기존에 있던 것",
    "## Meta AI 도구 활용",
    "## 기술 깊이",
    "## 영향",
    "## 현재 상태",
)

STORY_DEMO_MARKERS = (
    "데모 빈은 6개다.",
    "일치는 4건이다.",
    "불일치는 2건이다.",
    "절대 차이 합계는 6이다.",
    "일치율은 66.7%다.",
    "데모 기준. 빈 6개 중 불일치 2건",
)

STORY_HONESTY_MARKERS = (
    "가안",
    "모의(mock) 어댑터로 동작한다",
    "SAM 3.1 실호출은 2026-10-30 단일 빈 스모크로 검증했다",
    "Pi 실기 카메라 연동은 아직 검증 전이다",
    "전체 세션 실호출은 2026-10-30 커넥터 브리지로 통과했다(같은 가상 사진 재사용, 빈별 정확도 아님)",
)

STORY_THEME_MARKER = "Build for Your World"

STORY_NEW_WORK_MARKER = "2026-10-27 이후 해커톤 기간에 새로 작성했다"

EN_SUMMARY_REL = "docs/submission-summary-en.md"

EN_SUMMARY_SECTIONS = (
    "## Problem",
    "## Workflow",
    "## What we built vs. what already existed",
    "## Meta AI tools",
    "## Technical depth",
    "## Demo data",
    "## Impact",
    "## Current status",
)

EN_SUMMARY_DEMO_MARKERS = (
    "There are 6 demo bins.",
    "4 bins matched.",
    "2 bins mismatched.",
    "Total absolute delta is 6.",
    "Match rate is 66.7%.",
    "Demo basis:",
)

EN_SUMMARY_HONESTY_MARKERS = (
    "tentative",
    "A live SAM 3.1 call was verified on 2026-10-30 in a single-bin smoke test.",
    "Argus is currently running on the mock adapter.",
    "Mock results are never claimed as live results.",
    "Pi device camera integration is not yet verified.",
    "A full-session live run was verified on 2026-10-30 via the connector bridge (same virtual photo reused for all bins; not a per-bin accuracy check).",
)

EN_SUMMARY_THEME_MARKER = "Build for Your World"

EN_SUMMARY_NEW_WORK_MARKER = "Newly written during the hackathon period starting 2026-10-27."

DEMO_SCRIPT_REL = "docs/demo-script.md"

DEMO_SCRIPT_SECTIONS = (
    "## 컷 표",
    "## 촬영 체크리스트",
    "## 현재 상태",
)

DEMO_SCRIPT_DEMO_MARKERS = (
    "데모 기준 빈 6개 중 불일치 2건",
    "일치 4건과 불일치 2건",
    "절대 차이 6개와 일치율 66.7%",
    "A-01-02는 장부 8에서 실측 5로 부족입니다",
    "B-01-02는 장부 6에서 실측 9로 초과입니다",
)

DEMO_SCRIPT_HONESTY_MARKERS = (
    "가안",
    "SAM 3.1 실호출은 2026-10-30 단일 빈 스모크로 검증했다.",
    "전체 세션 실호출은 2026-10-30 커넥터 브리지로 통과했다(같은 가상 사진 재사용, 빈별 정확도 아님)",
    "현재는 모의(mock) 어댑터로 동작한다.",
    "Pi 실기 카메라 연동은 아직 검증 전이다.",
    "이 컷은 Pi 도착 후 실촬영으로 교체합니다.",
)

DEMO_SCRIPT_THEME_MARKER = "Build for Your World"

DEMO_SCRIPT_NEW_WORK_MARKER = "2026-10-27 이후 해커톤 기간에 새로 작성했다"

README_REL = "README.md"

README_SECTIONS = (
    "## 구성 (계획)",
    "## SAM 3.1 연동",
    "## 실행법 (초안)",
    "## 일정",
    "## 현재 상태",
)

README_DEMO_MARKERS = (
    "데모 기준: 빈 6개 중 일치 4건, 불일치 2건",
    "절대 차이 6개",
    "일치율 66.7%",
)

README_HONESTY_MARKERS = (
    "모의 어댑터로 진행한다",
    "SAM 3.1 실호출은 2026-10-30 단일 빈 스모크로 검증했다",
    "전체 세션 실호출은 2026-10-30 커넥터 브리지로 통과했다(같은 가상 사진 재사용, 빈별 정확도 아님)",
    "Pi 실촬영 검증 전",
    "가짜 전송(fake transport) 테스트로도 검증했다",
    "모의 결과는 화면에서 '모의'로 구분해 표기한다",
)

README_THEME_MARKER = "Build for Your World"

README_NEW_WORK_MARKER = "이 저장소의 모든 코드는 행사 기간 안에 새로 작성했다"

FALLBACK_REL = "demo/assets/fallback.json"

FALLBACK_CUT_INDEX = 3

FALLBACK_DECISION_DATE = "2026-11-02"

FALLBACK_SESSION_ID = "FALLBACK-FILE-INPUT"

FALLBACK_EXPECTED_SUMMARY = {
    "counted_bins": 6,
    "matched": 4,
    "mismatched": 2,
    "abs_diff_total": 6,
    "net_diff": 0,
}

FALLBACK_HONESTY_MARKERS = (
    "Pi 실촬영이 아닙니다",
    "Pi 실촬영 검증 전",
    "이 폴백 실행에서는 SAM 실호출을 하지 않았다",
    "데모 기준",
)

ASSEMBLY_FALLBACK_ASSET = "demo/assets/fallback.json"

ASSEMBLY_FALLBACK_HONESTY_MARKER = "컷 3 폴백은 파일 입력이며 Pi 실촬영이 아닙니다"

ASSEMBLY_FALLBACK_EXPECTED = {
    "asset": ASSEMBLY_FALLBACK_ASSET,
    "cut_index": FALLBACK_CUT_INDEX,
    "decision_date": FALLBACK_DECISION_DATE,
    "is_pi_real_capture": False,
    "capture_source": "file",
    "replaces": "pi-placeholder",
}

FALLBACK_VIDEO_REL = "demo/assets/argus-demo-fallback-draft.mp4"

FALLBACK_RENDER_CUT_INDEX = FALLBACK_CUT_INDEX

EXPECTED_PRE_SUBMISSION_BLOCKER_IDS = ("pi_real_capture_pending",)


@dataclass(frozen=True)
class PreSubmissionCheck:
    name: str
    passed: bool
    detail: str


def _aggregate(name: str, checks) -> PreSubmissionCheck:
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    return PreSubmissionCheck(name, passed == total, f"{passed}/{total} passed")


def validate_assembly_fallback(assembly) -> list[str]:
    """조립 매니페스트 컷 3의 파일 입력 폴백 참조가 기준과 맞는지 검사한다."""
    problems: list[str] = []
    if not isinstance(assembly, dict):
        return [f"assembly fallback: assembly is not a dict: {assembly!r}"]
    segments = assembly.get("segments")
    if not isinstance(segments, list):
        problems.append(f"assembly fallback: segments is not a list: {segments!r}")
        segments = []
    cut3 = None
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        fallback = seg.get("fallback")
        if seg.get("index") == FALLBACK_CUT_INDEX:
            cut3 = seg
            if not isinstance(fallback, dict):
                problems.append("assembly fallback: cut 3 fallback missing")
            else:
                for key, expected in ASSEMBLY_FALLBACK_EXPECTED.items():
                    actual = fallback.get(key)
                    if key == "is_pi_real_capture":
                        if actual is not False:
                            problems.append(
                                f"assembly fallback: cut 3 is_pi_real_capture={actual!r} is not False"
                            )
                    elif actual != expected:
                        problems.append(
                            f"assembly fallback: cut 3 {key}={actual!r} != {expected!r}"
                        )
        elif fallback is not None:
            problems.append(
                f"assembly fallback: fallback present on cut {seg.get('index')!r}, expected only cut 3"
            )
    if cut3 is None:
        problems.append("assembly fallback: cut 3 segment missing")
    honesty = assembly.get("honesty") or []
    joined = " ".join(str(line) for line in honesty) if isinstance(honesty, list) else ""
    if ASSEMBLY_FALLBACK_HONESTY_MARKER not in joined:
        problems.append(
            f"assembly fallback: missing honesty marker {ASSEMBLY_FALLBACK_HONESTY_MARKER!r}"
        )
    return problems


def _check_demo_consistency(root: Path) -> PreSubmissionCheck:
    name = "demo_assets_consistent"
    try:
        shot = json.loads((root / "demo/assets/shot-list.json").read_text(encoding="utf-8"))
        assembly = json.loads((root / "demo/assets/assembly.json").read_text(encoding="utf-8"))
        narration = json.loads((root / "demo/assets/narration.json").read_text(encoding="utf-8"))
        manifest = json.loads(
            (root / "demo/assets/captures/capture-manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        return PreSubmissionCheck(name, False, f"asset read failed: {exc!r}")
    problems: list[str] = []
    if shot.get("total_seconds") != 180 or shot.get("cut_count") != 9:
        problems.append(
            f"shot-list total_seconds={shot.get('total_seconds')} cut_count={shot.get('cut_count')}"
        )
    placeholders = [s for s in assembly.get("segments", []) if s.get("placeholder")]
    if assembly.get("total_seconds") != 180 or assembly.get("segment_count") != 9:
        problems.append(
            f"assembly total_seconds={assembly.get('total_seconds')} "
            f"segment_count={assembly.get('segment_count')}"
        )
    if len(placeholders) != 1 or placeholders[0].get("index") != 3:
        problems.append(f"assembly placeholders={[s.get('index') for s in placeholders]}")
    if narration.get("total_seconds") != 180 or narration.get("pace_warnings") != []:
        problems.append(
            f"narration total_seconds={narration.get('total_seconds')} "
            f"pace_warnings={narration.get('pace_warnings')}"
        )
    if manifest.get("all_ok") is not True or manifest.get("capture_count") != 4:
        problems.append(
            f"manifest all_ok={manifest.get('all_ok')} capture_count={manifest.get('capture_count')}"
        )
    problems.extend(validate_assembly_fallback(assembly))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems))
    return PreSubmissionCheck(name, True, "shot/assembly/narration/manifest consistent at 180s, 9 cuts, assembly_fallback_cut=3")


def validate_data_panel(panel) -> list[str]:
    """컷 1~9 데이터 패널 줄이 데모 기준과 맞는지 검사한다.

    panel은 컷 번호(int 또는 str 키) -> 줄 리스트 dict다.
    키를 int로 정규화해 검사하고 문제 문자열 리스트를 반환한다.
    """
    problems: list[str] = []
    if not isinstance(panel, dict):
        return [f"panel is not a dict: {panel!r}"]
    normalized: dict[int, object] = {}
    for key, lines in panel.items():
        try:
            cut = int(key)
        except (TypeError, ValueError):
            problems.append(f"invalid cut key: {key!r}")
            continue
        normalized[cut] = lines

    def _lines(cut: int) -> list[str] | None:
        lines = normalized.get(cut)
        if not isinstance(lines, (list, tuple)) or not lines:
            return None
        return [line if isinstance(line, str) else str(line) for line in lines]

    for cut in range(1, 10):
        if _lines(cut) is None:
            problems.append(f"cut {cut}: missing or empty")

    lines1 = _lines(1)
    if lines1 is not None and not any("일치율 66.7%" in line for line in lines1):
        problems.append("cut 1: missing '일치율 66.7%' line")

    lines3 = _lines(3)
    if lines3 is not None and lines3 != ["실촬영 데이터 없음 — Pi 도착 후 교체"]:
        problems.append(f"cut 3: expected placeholder line only, got {lines3!r}")

    lines5 = _lines(5)
    if lines5 is not None:
        if len(lines5) != 6:
            problems.append(f"cut 5: expected 6 lines, got {len(lines5)}")
        for bin_id in EXPECTED_BIN_IDS:
            if not any(bin_id in line for line in lines5):
                problems.append(f"cut 5: missing bin {bin_id}")
        for line in lines5:
            if "장부" not in line or "→ 실측" not in line:
                problems.append(f"cut 5: line missing '장부' or '→ 실측': {line!r}")

    lines6 = _lines(6)
    if lines6 is not None:
        if len(lines6) != 2:
            problems.append(f"cut 6: expected 2 lines, got {len(lines6)}")
        found: list[str] = []
        for line in lines6:
            in_line = [bin_id for bin_id in EXPECTED_BIN_IDS if bin_id in line]
            in_line.sort(key=line.index)
            found.extend(in_line)
        if found != ["A-01-02", "B-01-02"]:
            problems.append(f"cut 6: bin order {found} != ['A-01-02', 'B-01-02']")

    lines9 = _lines(9)
    if lines9 is not None:
        if len(lines9) != 1:
            problems.append(f"cut 9: expected 1 line, got {len(lines9)}")
        if not any("데모 기준" in line for line in lines9):
            problems.append("cut 9: missing '데모 기준'")

    return problems


def build_current_data_panel() -> dict[int, list[str]]:
    """현재 시뮬레이션 리포트로 컷 1~9 데이터 패널 줄을 만든다."""
    from demo.render_video import build_data_panel_lines
    from terminal.simulator import run_simulation

    report = run_simulation()
    return {cut: build_data_panel_lines(cut, report=report) for cut in range(1, 10)}


def validate_fallback_panel(lines) -> list[str]:
    """컷 3 파일 입력 폴백 패널 줄이 폴백 기준과 맞는지 검사한다."""
    problems: list[str] = []
    if not isinstance(lines, (list, tuple)):
        return [f"fallback panel is not a list: {lines!r}"]
    norm = [line if isinstance(line, str) else str(line) for line in lines]
    if len(norm) != 4:
        problems.append(f"fallback panel: expected 4 lines, got {len(norm)}")
        return problems
    first, second, third, fourth = norm
    if "파일 입력 폴백 — Pi 실촬영 아님" not in first:
        problems.append("fallback panel: line 1 missing '파일 입력 폴백 — Pi 실촬영 아님'")
    if f"결정일 {FALLBACK_DECISION_DATE}" not in first:
        problems.append(f"fallback panel: line 1 missing decision date {FALLBACK_DECISION_DATE}")
    if FALLBACK_SESSION_ID not in second:
        problems.append(f"fallback panel: line 2 missing session {FALLBACK_SESSION_ID}")
    if "capture_source=file" not in second:
        problems.append("fallback panel: line 2 missing 'capture_source=file'")
    if "source=mock" not in second:
        problems.append("fallback panel: line 2 missing 'source=mock'")
    for marker in ("빈 6", "일치 4", "불일치 2", "절대 차이 6"):
        if marker not in third:
            problems.append(f"fallback panel: line 3 missing {marker!r}")
    try:
        import hashlib

        from demo.fallback import fake_photo_bytes

        sha8 = hashlib.sha256(fake_photo_bytes("A-01-02")).hexdigest()[:8]
    except Exception:
        sha8 = "106573c1"
    for marker in ("A-01-02", "장부 8", "실측 5", sha8):
        if marker not in fourth:
            problems.append(f"fallback panel: line 4 missing {marker!r}")
    return problems


def build_current_fallback_panel() -> list[str]:
    """현재 폴백 매니페스트로 컷 3 폴백 패널 줄을 만든다."""
    from demo.fallback import build_fallback_manifest
    from demo.render_video import build_data_panel_lines
    from terminal.simulator import run_simulation

    report = run_simulation()
    manifest = build_fallback_manifest()
    return build_data_panel_lines(
        FALLBACK_RENDER_CUT_INDEX, report=report, fallback_manifest=manifest
    )


def _check_video_draft(root: Path) -> PreSubmissionCheck:
    name = "video_draft_present"
    video = root / "demo/assets/argus-demo-draft.mp4"
    try:
        size = video.stat().st_size if video.is_file() else 0
    except OSError:
        size = 0
    if size <= VIDEO_MIN_BYTES:
        return PreSubmissionCheck(
            name, False, f"bytes={size}" if size else "video missing"
        )
    try:
        problems = validate_data_panel(build_current_data_panel())
    except Exception as exc:
        return PreSubmissionCheck(
            name, False, f"bytes={size}; data panel raised: {exc!r}"
        )
    if problems:
        return PreSubmissionCheck(
            name, False, f"bytes={size}; data panel problems: " + "; ".join(problems)
        )
    fallback_video = root / FALLBACK_VIDEO_REL
    try:
        fallback_size = fallback_video.stat().st_size if fallback_video.is_file() else 0
    except OSError:
        fallback_size = 0
    if fallback_size <= VIDEO_MIN_BYTES:
        return PreSubmissionCheck(
            name,
            False,
            f"bytes={size}, data_panel_cuts=9; fallback video missing or too small: fallback_bytes={fallback_size}",
        )
    try:
        fallback_problems = validate_fallback_panel(build_current_fallback_panel())
    except Exception as exc:
        return PreSubmissionCheck(
            name,
            False,
            f"bytes={size}, fallback_bytes={fallback_size}; fallback panel raised: {exc!r}",
        )
    if fallback_problems:
        return PreSubmissionCheck(
            name,
            False,
            f"bytes={size}, fallback_bytes={fallback_size}; fallback panel problems: "
            + "; ".join(fallback_problems),
        )
    return PreSubmissionCheck(
        name,
        True,
        f"bytes={size}, data_panel_cuts=9, fallback_bytes={fallback_size}, fallback_render_cut={FALLBACK_RENDER_CUT_INDEX}",
    )


def _pre_submission_blocker_ids(blockers) -> set:
    ids = set()
    if isinstance(blockers, (list, tuple)):
        for blocker in blockers:
            if isinstance(blocker, dict):
                ids.add(blocker.get("id"))
            else:
                ids.add(blocker)
    return ids


def _readiness_blocker_ids(report_blockers, problems: list[str], label: str) -> list:
    if not isinstance(report_blockers, (list, tuple)):
        problems.append(f"{label}: blockers is not a list: {report_blockers!r}")
        return []
    ids: list = []
    for blocker in report_blockers:
        if isinstance(blocker, dict) and "id" in blocker:
            ids.append(blocker["id"])
        else:
            problems.append(f"{label}: blocker entry missing 'id': {blocker!r}")
            ids.append(None)
    return ids


def _check_honesty(report: dict, problems: list[str], label: str, phrase: str) -> None:
    if "honesty" not in report:
        return
    honesty = report["honesty"]
    if isinstance(honesty, str):
        lines = [honesty]
    elif isinstance(honesty, (list, tuple)):
        lines = [line if isinstance(line, str) else str(line) for line in honesty]
    else:
        problems.append(f"{label}: honesty is not a list: {honesty!r}")
        return
    if not any(phrase in line for line in lines):
        problems.append(f"{label}: honesty missing line containing {phrase!r}")


def validate_sam_readiness(report, blockers=None) -> list[str]:
    """SAM 준비 점검 보고가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    required = (
        "base_url_present",
        "api_key_present",
        "credit_confirmed",
        "ready_for_live_call",
        "blockers",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"missing required keys: {missing}")
        return problems
    ids = _readiness_blocker_ids(report["blockers"], problems, "sam readiness")
    if isinstance(report["blockers"], (list, tuple)):
        expected_subsequence = [b for b in SAM_READINESS_BLOCKER_ORDER if b in ids]
        if ids != expected_subsequence:
            problems.append(
                f"sam readiness: blocker ids {ids} are not a subsequence of "
                f"{list(SAM_READINESS_BLOCKER_ORDER)}"
            )
    base_url_present = bool(report["base_url_present"])
    api_key_present = bool(report["api_key_present"])
    credit_confirmed = bool(report["credit_confirmed"])
    ready = bool(report["ready_for_live_call"])
    if ready != (credit_confirmed and base_url_present and api_key_present):
        problems.append(
            f"sam readiness: ready_for_live_call={report['ready_for_live_call']!r} "
            f"!= (credit_confirmed={report['credit_confirmed']!r} and "
            f"base_url_present={report['base_url_present']!r} and "
            f"api_key_present={report['api_key_present']!r})"
        )
    if isinstance(report["blockers"], (list, tuple)):
        if ready != (len(report["blockers"]) == 0):
            problems.append(
                f"sam readiness: ready_for_live_call={report['ready_for_live_call']!r} "
                f"!= (blockers empty: {len(report['blockers']) == 0})"
            )
    if "would_select_live" in report:
        if bool(report["would_select_live"]) != (base_url_present and api_key_present):
            problems.append(
                f"sam readiness: would_select_live={report['would_select_live']!r} "
                f"!= (base_url_present={report['base_url_present']!r} and "
                f"api_key_present={report['api_key_present']!r})"
            )
    if "sam_real_call_pending" in _pre_submission_blocker_ids(blockers):
        problems.append(
            "sam readiness: pre-submission blockers still contain stale "
            "'sam_real_call_pending' (SAM live call verified by single-bin "
            "smoke on 2026-10-30; env readiness is a separate state)"
        )
    _check_honesty(report, problems, "sam readiness", "실호출 성공")
    return problems


def validate_pi_readiness(report, blockers=None) -> list[str]:
    """Pi 준비 점검 보고가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    required = (
        "device_confirmed",
        "camera_available",
        "ready_for_real_capture",
        "blockers",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"missing required keys: {missing}")
        return problems
    ids = _readiness_blocker_ids(report["blockers"], problems, "pi readiness")
    if isinstance(report["blockers"], (list, tuple)):
        expected_subsequence = [b for b in PI_READINESS_BLOCKER_ORDER if b in ids]
        if ids != expected_subsequence:
            problems.append(
                f"pi readiness: blocker ids {ids} are not a subsequence of "
                f"{list(PI_READINESS_BLOCKER_ORDER)}"
            )
    device_confirmed = bool(report["device_confirmed"])
    camera_available = bool(report["camera_available"])
    ready = bool(report["ready_for_real_capture"])
    if ready != (device_confirmed and camera_available):
        problems.append(
            f"pi readiness: ready_for_real_capture={report['ready_for_real_capture']!r} "
            f"!= (device_confirmed={report['device_confirmed']!r} and "
            f"camera_available={report['camera_available']!r})"
        )
    if isinstance(report["blockers"], (list, tuple)):
        if ready != (len(report["blockers"]) == 0):
            problems.append(
                f"pi readiness: ready_for_real_capture={report['ready_for_real_capture']!r} "
                f"!= (blockers empty: {len(report['blockers']) == 0})"
            )
    if not ready and "pi_real_capture_pending" not in _pre_submission_blocker_ids(blockers):
        problems.append(
            "pi readiness: ready_for_real_capture is False but pre-submission "
            "blockers missing 'pi_real_capture_pending'"
        )
    _check_honesty(report, problems, "pi readiness", "실촬영 성공")
    return problems


def validate_console_readiness(report, sam_report=None, pi_report=None) -> list[str]:
    """콘솔 준비 상태가 내부적으로, 그리고 두 준비 점검 보고와 맞는지 검사한다."""
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    required = (
        "sam",
        "pi",
        "sam_blockers",
        "pi_blockers",
        "blocker_count",
        "sam_ready",
        "pi_ready",
        "overall_ready",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"missing required keys: {missing}")
        return problems
    sam_blockers = report["sam_blockers"]
    pi_blockers = report["pi_blockers"]
    if not isinstance(sam_blockers, (list, tuple)):
        problems.append(f"console readiness: sam_blockers is not a list: {sam_blockers!r}")
        sam_blockers = []
    if not isinstance(pi_blockers, (list, tuple)):
        problems.append(f"console readiness: pi_blockers is not a list: {pi_blockers!r}")
        pi_blockers = []
    sam = report["sam"] if isinstance(report["sam"], dict) else None
    pi = report["pi"] if isinstance(report["pi"], dict) else None
    if sam is None:
        problems.append(f"console readiness: sam is not a dict: {report['sam']!r}")
    if pi is None:
        problems.append(f"console readiness: pi is not a dict: {report['pi']!r}")
    if sam is not None and isinstance(sam.get("blockers"), (list, tuple)):
        sam_ids = _readiness_blocker_ids(sam["blockers"], problems, "console sam")
        if list(sam_blockers) != sam_ids:
            problems.append(
                f"console readiness: sam_blockers {list(sam_blockers)} != "
                f"console sam blocker ids {sam_ids}"
            )
    if pi is not None and isinstance(pi.get("blockers"), (list, tuple)):
        pi_ids = _readiness_blocker_ids(pi["blockers"], problems, "console pi")
        if list(pi_blockers) != pi_ids:
            problems.append(
                f"console readiness: pi_blockers {list(pi_blockers)} != "
                f"console pi blocker ids {pi_ids}"
            )
    if report["blocker_count"] != len(sam_blockers) + len(pi_blockers):
        problems.append(
            f"console readiness: blocker_count={report['blocker_count']!r} "
            f"!= len(sam_blockers)+len(pi_blockers)="
            f"{len(sam_blockers) + len(pi_blockers)}"
        )
    sam_ready = bool(report["sam_ready"])
    pi_ready = bool(report["pi_ready"])
    if sam is not None and "ready_for_live_call" in sam:
        if sam_ready != bool(sam["ready_for_live_call"]):
            problems.append(
                f"console readiness: sam_ready={report['sam_ready']!r} "
                f"!= sam.ready_for_live_call={sam['ready_for_live_call']!r}"
            )
    if pi is not None and "ready_for_real_capture" in pi:
        if pi_ready != bool(pi["ready_for_real_capture"]):
            problems.append(
                f"console readiness: pi_ready={report['pi_ready']!r} "
                f"!= pi.ready_for_real_capture={pi['ready_for_real_capture']!r}"
            )
    if bool(report["overall_ready"]) != (sam_ready and pi_ready):
        problems.append(
            f"console readiness: overall_ready={report['overall_ready']!r} "
            f"!= (sam_ready={report['sam_ready']!r} and pi_ready={report['pi_ready']!r})"
        )
    if sam_report is not None and isinstance(sam_report, dict):
        ext_ids: list[str] = []
        ext_problems: list[str] = []
        if isinstance(sam_report.get("blockers"), (list, tuple)):
            ext_ids = _readiness_blocker_ids(
                sam_report["blockers"], ext_problems, "sam readiness"
            )
            problems.extend(ext_problems)
            if list(sam_blockers) != ext_ids:
                problems.append(
                    f"console readiness: sam_blockers {list(sam_blockers)} != "
                    f"sam readiness blocker ids {ext_ids}"
                )
        if "ready_for_live_call" in sam_report:
            if sam_ready != bool(sam_report["ready_for_live_call"]):
                problems.append(
                    f"console readiness: sam_ready={report['sam_ready']!r} "
                    f"!= sam readiness ready_for_live_call="
                    f"{sam_report['ready_for_live_call']!r}"
                )
    if pi_report is not None and isinstance(pi_report, dict):
        ext_ids = []
        ext_problems = []
        if isinstance(pi_report.get("blockers"), (list, tuple)):
            ext_ids = _readiness_blocker_ids(
                pi_report["blockers"], ext_problems, "pi readiness"
            )
            problems.extend(ext_problems)
            if list(pi_blockers) != ext_ids:
                problems.append(
                    f"console readiness: pi_blockers {list(pi_blockers)} != "
                    f"pi readiness blocker ids {ext_ids}"
                )
        if "ready_for_real_capture" in pi_report:
            if pi_ready != bool(pi_report["ready_for_real_capture"]):
                problems.append(
                    f"console readiness: pi_ready={report['pi_ready']!r} "
                    f"!= pi readiness ready_for_real_capture="
                    f"{pi_report['ready_for_real_capture']!r}"
                )
    _check_honesty(report, problems, "console readiness", "실호출·실촬영 성공")
    return problems


class _SmokeFakeCounter:
    """전수 점검 전용 가짜 counter. 실제 API를 부르지 않는다."""

    def __init__(self):
        self.calls = 0

    def count(self, bin_id, image_ref=None):
        self.calls += 1
        return SimpleNamespace(source="sam", counted_qty=SMOKE_FAKE_COUNT)


def validate_sam_smoke(report, sam_report=None, blockers=None) -> list[str]:
    """SAM 스모크 보고가 내부적으로, 그리고 SAM 준비 보고와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    required = (
        "status",
        "attempted",
        "ready_for_live_call",
        "blockers",
        "bin_id",
        "source",
        "counted_qty",
        "book_qty",
        "diff",
        "error_type",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"missing required keys: {missing}")
        return problems
    ids = _readiness_blocker_ids(report["blockers"], problems, "sam smoke")
    if isinstance(report["blockers"], (list, tuple)):
        expected_subsequence = [b for b in SAM_READINESS_BLOCKER_ORDER if b in ids]
        if ids != expected_subsequence:
            problems.append(
                f"sam smoke: blocker ids {ids} are not a subsequence of "
                f"{list(SAM_READINESS_BLOCKER_ORDER)}"
            )
    ready = bool(report["ready_for_live_call"])
    if isinstance(sam_report, dict):
        if "ready_for_live_call" in sam_report:
            if ready != bool(sam_report["ready_for_live_call"]):
                problems.append(
                    f"sam smoke: ready_for_live_call={report['ready_for_live_call']!r} "
                    f"!= sam readiness ready_for_live_call="
                    f"{sam_report['ready_for_live_call']!r}"
                )
        if isinstance(sam_report.get("blockers"), (list, tuple)):
            sam_ids = _readiness_blocker_ids(
                sam_report["blockers"], problems, "sam readiness"
            )
            if ids != sam_ids:
                problems.append(
                    f"sam smoke: blocker ids {ids} != "
                    f"sam readiness blocker ids {sam_ids}"
                )
    status = report["status"]
    if status not in ("blocked", "passed", "failed"):
        problems.append(
            f"sam smoke: status={status!r} is not one of "
            f"['blocked', 'passed', 'failed']"
        )
    if not ready:
        if status != "blocked":
            problems.append(
                f"sam smoke: status={status!r} != 'blocked' "
                f"when ready_for_live_call is False"
            )
        if bool(report["attempted"]):
            problems.append(
                f"sam smoke: attempted={report['attempted']!r} != False "
                f"when ready_for_live_call is False"
            )
        for key in ("source", "counted_qty", "diff", "error_type"):
            if report[key] is not None:
                problems.append(
                    f"sam smoke: {key}={report[key]!r} is not None "
                    f"when ready_for_live_call is False"
                )
        if "sam_real_call_pending" in _pre_submission_blocker_ids(blockers):
            problems.append(
                "sam smoke: pre-submission blockers still contain stale "
                "'sam_real_call_pending' (SAM live call verified by "
                "single-bin smoke on 2026-10-30)"
            )
    if ready and status == "passed":
        if not report["attempted"]:
            problems.append(
                f"sam smoke: attempted={report['attempted']!r} != True "
                f"when ready_for_live_call is True and status is 'passed'"
            )
        if report["source"] != "sam":
            problems.append(
                f"sam smoke: source={report['source']!r} != 'sam' "
                f"when ready_for_live_call is True and status is 'passed'"
            )
        counted_qty = report["counted_qty"]
        book_qty = report["book_qty"]
        counted_is_int = isinstance(counted_qty, int) and not isinstance(
            counted_qty, bool
        )
        book_is_int = isinstance(book_qty, int) and not isinstance(book_qty, bool)
        if not counted_is_int:
            problems.append(
                f"sam smoke: counted_qty={counted_qty!r} is not an int "
                f"when ready_for_live_call is True and status is 'passed'"
            )
        if not book_is_int:
            problems.append(
                f"sam smoke: book_qty={book_qty!r} is not an int "
                f"when ready_for_live_call is True and status is 'passed'"
            )
        if counted_is_int and book_is_int:
            if report["diff"] != counted_qty - book_qty:
                problems.append(
                    f"sam smoke: diff={report['diff']!r} != "
                    f"counted_qty - book_qty={counted_qty - book_qty}"
                )
    if ready and status == "failed":
        error_type = report["error_type"]
        if not isinstance(error_type, str) or not error_type:
            problems.append(
                f"sam smoke: error_type={error_type!r} is not a non-empty "
                f"string when ready_for_live_call is True and status is 'failed'"
            )
        if error_type != "unknown_bin" and not report["attempted"]:
            problems.append(
                f"sam smoke: attempted={report['attempted']!r} != True "
                f"when ready_for_live_call is True and status is 'failed'"
            )
    _check_honesty(report, problems, "sam smoke", "호출하지 않는다")
    _check_honesty(report, problems, "sam smoke", "대체하지 않는다")
    return problems


def _check_sam_readiness(sam_env=None, sam_credit_confirmed=False):
    name = "sam_readiness_consistent"
    try:
        report = check_sam_readiness(env=sam_env, credit_confirmed=sam_credit_confirmed)
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_sam_readiness(report)
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"ready_for_live_call={report['ready_for_live_call']} "
        f"blockers={[b['id'] for b in report['blockers']]}"
    )
    return PreSubmissionCheck(name, True, detail), report


def _check_pi_readiness(pi_probe=None, pi_device_confirmed=False, pi_which=None):
    name = "pi_readiness_consistent"
    try:
        report = check_pi_readiness(
            probe=pi_probe, device_confirmed=pi_device_confirmed, which=pi_which
        )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_pi_readiness(report)
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"ready_for_real_capture={report['ready_for_real_capture']} "
        f"blockers={[b['id'] for b in report['blockers']]}"
    )
    return PreSubmissionCheck(name, True, detail), report


def _check_console_readiness(
    sam_env=None,
    sam_credit_confirmed=False,
    pi_probe=None,
    pi_device_confirmed=False,
    pi_which=None,
    sam_report=None,
    pi_report=None,
):
    name = "console_readiness_consistent"
    try:
        report = build_console_readiness(
            env=sam_env,
            sam_credit_confirmed=sam_credit_confirmed,
            pi_device_confirmed=pi_device_confirmed,
            pi_probe=pi_probe,
            pi_which=pi_which,
        )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_console_readiness(
        report, sam_report=sam_report, pi_report=pi_report
    )
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"overall_ready={report['overall_ready']} "
        f"blocker_count={report['blocker_count']} "
        f"sam_blockers={report['sam_blockers']} "
        f"pi_blockers={report['pi_blockers']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def _check_sam_smoke(sam_env=None, sam_credit_confirmed=False, sam_report=None):
    name = "sam_smoke_consistent"
    fake = _SmokeFakeCounter()
    try:
        report = run_sam_smoke(
            env=sam_env,
            credit_confirmed=sam_credit_confirmed,
            bin_id=SMOKE_BIN_ID,
            counter=fake,
        )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_sam_smoke(report, sam_report=sam_report)
    if isinstance(report, dict) and "ready_for_live_call" in report:
        if not bool(report["ready_for_live_call"]) and fake.calls != 0:
            problems.append(
                f"sam smoke: fake counter calls={fake.calls} != 0 "
                f"when ready_for_live_call is False"
            )
        if bool(report["ready_for_live_call"]) and fake.calls != 1:
            problems.append(
                f"sam smoke: fake counter calls={fake.calls} != 1 "
                f"when ready_for_live_call is True"
            )
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"status={report['status']} attempted={report['attempted']} "
        f"blockers={[b['id'] for b in report['blockers']]} "
        f"fake_calls={fake.calls}"
    )
    return PreSubmissionCheck(name, True, detail), report


class _SessionFakeCounter:
    """전수 점검 전용 가짜 전체 세션 counter. 실제 API를 부르지 않는다.

    데모 기준 계수(DEMO_COUNTED_QTY)를 source="sam"으로 돌려줘,
    전체 세션 리포트가 데모 기준 요약과 맞아야 함을 검증 가능하게 한다.
    """

    def __init__(self):
        self.calls = []

    def count(self, bin_id, image_ref=None):
        from terminal.demo_data import DEMO_COUNTED_QTY
        from terminal.models import CountResult

        self.calls.append((bin_id, image_ref))
        return CountResult(
            bin_id=bin_id, counted_qty=DEMO_COUNTED_QTY[bin_id], source="sam"
        )


def validate_sam_session(report, sam_report=None, blockers=None) -> list[str]:
    """SAM 전체 세션 보고가 내부적으로, 그리고 SAM 준비 보고와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    required = (
        "status",
        "attempted",
        "ready_for_live_call",
        "blockers",
        "session_id",
        "source",
        "bins",
        "summary",
        "error_type",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"missing required keys: {missing}")
        return problems
    ids = _readiness_blocker_ids(report["blockers"], problems, "sam session")
    if isinstance(report["blockers"], (list, tuple)):
        expected_subsequence = [b for b in SAM_READINESS_BLOCKER_ORDER if b in ids]
        if ids != expected_subsequence:
            problems.append(
                f"sam session: blocker ids {ids} are not a subsequence of "
                f"{list(SAM_READINESS_BLOCKER_ORDER)}"
            )
    ready = bool(report["ready_for_live_call"])
    if isinstance(sam_report, dict):
        if "ready_for_live_call" in sam_report:
            if ready != bool(sam_report["ready_for_live_call"]):
                problems.append(
                    f"sam session: ready_for_live_call={report['ready_for_live_call']!r} "
                    f"!= sam readiness ready_for_live_call="
                    f"{sam_report['ready_for_live_call']!r}"
                )
        if isinstance(sam_report.get("blockers"), (list, tuple)):
            sam_ids = _readiness_blocker_ids(
                sam_report["blockers"], problems, "sam readiness"
            )
            if ids != sam_ids:
                problems.append(
                    f"sam session: blocker ids {ids} != "
                    f"sam readiness blocker ids {sam_ids}"
                )
    status = report["status"]
    if status not in ("blocked", "passed", "failed"):
        problems.append(
            f"sam session: status={status!r} is not one of "
            f"['blocked', 'passed', 'failed']"
        )
    if not ready:
        if status != "blocked":
            problems.append(
                f"sam session: status={status!r} != 'blocked' "
                f"when ready_for_live_call is False"
            )
        if bool(report["attempted"]):
            problems.append(
                f"sam session: attempted={report['attempted']!r} != False "
                f"when ready_for_live_call is False"
            )
        if report["source"] is not None:
            problems.append(
                f"sam session: source={report['source']!r} is not None "
                f"when ready_for_live_call is False"
            )
        if report["bins"] != []:
            problems.append(
                f"sam session: bins={report['bins']!r} != [] "
                f"when ready_for_live_call is False"
            )
        if report["summary"] is not None:
            problems.append(
                f"sam session: summary={report['summary']!r} is not None "
                f"when ready_for_live_call is False"
            )
        if report["error_type"] is not None:
            problems.append(
                f"sam session: error_type={report['error_type']!r} is not None "
                f"when ready_for_live_call is False"
            )
        if "sam_real_call_pending" in _pre_submission_blocker_ids(blockers):
            problems.append(
                "sam session: pre-submission blockers still contain stale "
                "'sam_real_call_pending' (SAM live call verified by "
                "full-session run on 2026-10-30)"
            )
    if ready and status == "passed":
        if not report["attempted"]:
            problems.append(
                f"sam session: attempted={report['attempted']!r} != True "
                f"when ready_for_live_call is True and status is 'passed'"
            )
        if report["source"] != "sam":
            problems.append(
                f"sam session: source={report['source']!r} != 'sam' "
                f"when ready_for_live_call is True and status is 'passed'"
            )
        bins = report["bins"]
        if not isinstance(bins, (list, tuple)) or len(bins) != len(EXPECTED_BIN_IDS):
            problems.append(
                f"sam session: bins={bins!r} does not have "
                f"{len(EXPECTED_BIN_IDS)} entries when status is 'passed'"
            )
            bins = []
        bin_ids = [
            comp.get("bin_id") if isinstance(comp, dict) else None for comp in bins
        ]
        if bins and bin_ids != list(EXPECTED_BIN_IDS):
            problems.append(
                f"sam session: bin order {bin_ids} != {list(EXPECTED_BIN_IDS)}"
            )
        diffs_ok = True
        for comp in bins:
            if not isinstance(comp, dict):
                problems.append(f"sam session: bin entry is not a dict: {comp!r}")
                diffs_ok = False
                continue
            counted = comp.get("counted_qty")
            book = comp.get("book_qty")
            if not (isinstance(counted, int) and not isinstance(counted, bool)
                    and isinstance(book, int) and not isinstance(book, bool)):
                problems.append(
                    f"sam session: bin {comp.get('bin_id')!r} counted_qty/book_qty "
                    f"are not ints: {comp!r}"
                )
                diffs_ok = False
            elif comp.get("diff") != counted - book:
                problems.append(
                    f"sam session: bin {comp.get('bin_id')!r} "
                    f"diff={comp.get('diff')!r} != counted_qty - book_qty="
                    f"{counted - book}"
                )
                diffs_ok = False
        summary = report["summary"]
        if not isinstance(summary, dict):
            problems.append(
                f"sam session: summary={summary!r} is not a dict "
                f"when status is 'passed'"
            )
        elif bins and diffs_ok:
            matched = sum(1 for comp in bins if comp.get("verdict") == "match")
            expected_summary = {
                "counted_bins": len(bins),
                "matched": matched,
                "mismatched": len(bins) - matched,
                "abs_diff_total": sum(abs(comp["diff"]) for comp in bins),
                "net_diff": sum(comp["diff"] for comp in bins),
            }
            for key, expected in expected_summary.items():
                if summary.get(key) != expected:
                    problems.append(
                        f"sam session: summary {key}={summary.get(key)!r} "
                        f"!= {expected} computed from bins"
                    )
            if summary.get("counted_bins"):
                expected_rate = matched / summary["counted_bins"]
                rate = summary.get("match_rate")
                if not isinstance(rate, (int, float)) or isinstance(rate, bool) \
                        or abs(rate - expected_rate) > 1e-9:
                    problems.append(
                        f"sam session: summary match_rate={rate!r} "
                        f"!= {expected_rate} computed from bins"
                    )
    if ready and status == "failed":
        error_type = report["error_type"]
        if not isinstance(error_type, str) or not error_type:
            problems.append(
                f"sam session: error_type={error_type!r} is not a non-empty "
                f"string when ready_for_live_call is True and status is 'failed'"
            )
        if not report["attempted"]:
            problems.append(
                f"sam session: attempted={report['attempted']!r} != True "
                f"when ready_for_live_call is True and status is 'failed'"
            )
        if report["summary"] is not None:
            problems.append(
                f"sam session: summary={report['summary']!r} is not None "
                f"when status is 'failed'"
            )
        if report["bins"] != []:
            problems.append(
                f"sam session: bins={report['bins']!r} != [] "
                f"when status is 'failed'"
            )
    _check_honesty(report, problems, "sam session", "호출하지 않는다")
    _check_honesty(report, problems, "sam session", "대체하지 않는다")
    _check_honesty(report, problems, "sam session", "Pi 실촬영이 아니며")
    return problems


def _check_sam_session(sam_env=None, sam_credit_confirmed=False, sam_report=None):
    name = "sam_session_consistent"
    fake = _SessionFakeCounter()
    try:
        report = run_sam_session(
            env=sam_env,
            credit_confirmed=sam_credit_confirmed,
            counter=fake,
            session_id="PRE-SUBMISSION-SAM-SESSION",
        )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_sam_session(report, sam_report=sam_report)
    if isinstance(report, dict) and "ready_for_live_call" in report:
        if not bool(report["ready_for_live_call"]) and len(fake.calls) != 0:
            problems.append(
                f"sam session: fake counter calls={len(fake.calls)} != 0 "
                f"when ready_for_live_call is False"
            )
        if bool(report["ready_for_live_call"]) and len(fake.calls) != len(EXPECTED_BIN_IDS):
            problems.append(
                f"sam session: fake counter calls={len(fake.calls)} != "
                f"{len(EXPECTED_BIN_IDS)} when ready_for_live_call is True"
            )
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"status={report['status']} attempted={report['attempted']} "
        f"blockers={[b['id'] for b in report['blockers']]} "
        f"fake_calls={len(fake.calls)}"
    )
    return PreSubmissionCheck(name, True, detail), report


class _PiSmokeFakeSession:
    """전수 점검 전용 가짜 session. 실제 촬영을 하지 않는다."""

    def __init__(self):
        self.calls = []

    def __call__(self, output_dir, bin_ids=None, session_id=None, runner=None, which=None):
        self.calls.append(
            {"output_dir": output_dir, "bin_ids": bin_ids, "session_id": session_id}
        )
        return {
            "session_id": "PI-SMOKE",
            "source": "mock",
            "capture_source": "pi-camera",
            "bins": [
                {
                    "bin_id": PI_SMOKE_BIN_ID,
                    "book_qty": 8,
                    "counted_qty": PI_SMOKE_FAKE_COUNT,
                    "diff": PI_SMOKE_FAKE_COUNT - 8,
                    "photo": {
                        "sha256": PI_SMOKE_FAKE_SHA,
                        "image_ref": PI_SMOKE_BIN_ID + ".jpg",
                    },
                }
            ],
        }


def _pi_which_from_probe(probe, fallback_which):
    if probe is None:
        return fallback_which
    if probe.get("available") and probe.get("command"):
        command = probe["command"]

        def _which(name, _command=command):
            return f"/usr/bin/{_command}" if name == _command else None

        return _which

    def _none(name):
        return None

    return _none


def validate_pi_smoke(report, pi_report=None, blockers=None) -> list[str]:
    """Pi 스모크 보고가 내부적으로, 그리고 Pi 준비 보고와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    required = (
        "status",
        "attempted",
        "ready_for_real_capture",
        "blockers",
        "bin_id",
        "source",
        "capture_source",
        "counted_qty",
        "book_qty",
        "diff",
        "photo_sha256",
        "error_type",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"missing required keys: {missing}")
        return problems
    ids = _readiness_blocker_ids(report["blockers"], problems, "pi smoke")
    if isinstance(report["blockers"], (list, tuple)):
        expected_subsequence = [b for b in PI_READINESS_BLOCKER_ORDER if b in ids]
        if ids != expected_subsequence:
            problems.append(
                f"pi smoke: blocker ids {ids} are not a subsequence of "
                f"{list(PI_READINESS_BLOCKER_ORDER)}"
            )
    ready = bool(report["ready_for_real_capture"])
    if isinstance(pi_report, dict):
        if "ready_for_real_capture" in pi_report:
            if ready != bool(pi_report["ready_for_real_capture"]):
                problems.append(
                    f"pi smoke: ready_for_real_capture={report['ready_for_real_capture']!r} "
                    f"!= pi readiness ready_for_real_capture="
                    f"{pi_report['ready_for_real_capture']!r}"
                )
        if isinstance(pi_report.get("blockers"), (list, tuple)):
            pi_ids = _readiness_blocker_ids(
                pi_report["blockers"], problems, "pi readiness"
            )
            if ids != pi_ids:
                problems.append(
                    f"pi smoke: blocker ids {ids} != "
                    f"pi readiness blocker ids {pi_ids}"
                )
    status = report["status"]
    if status not in ("blocked", "passed", "failed"):
        problems.append(
            f"pi smoke: status={status!r} is not one of "
            f"['blocked', 'passed', 'failed']"
        )
    if not ready:
        if status != "blocked":
            problems.append(
                f"pi smoke: status={status!r} != 'blocked' "
                f"when ready_for_real_capture is False"
            )
        if bool(report["attempted"]):
            problems.append(
                f"pi smoke: attempted={report['attempted']!r} != False "
                f"when ready_for_real_capture is False"
            )
        for key in ("source", "capture_source", "counted_qty", "diff", "photo_sha256", "error_type"):
            if report[key] is not None:
                problems.append(
                    f"pi smoke: {key}={report[key]!r} is not None "
                    f"when ready_for_real_capture is False"
                )
        if "pi_real_capture_pending" not in _pre_submission_blocker_ids(blockers):
            problems.append(
                "pi smoke: ready_for_real_capture is False but pre-submission "
                "blockers missing 'pi_real_capture_pending'"
            )
    if ready and status == "passed":
        if not report["attempted"]:
            problems.append(
                f"pi smoke: attempted={report['attempted']!r} != True "
                f"when ready_for_real_capture is True and status is 'passed'"
            )
        if report["capture_source"] != "pi-camera":
            problems.append(
                f"pi smoke: capture_source={report['capture_source']!r} != 'pi-camera' "
                f"when ready_for_real_capture is True and status is 'passed'"
            )
        if not isinstance(report["source"], str) or not report["source"]:
            problems.append(
                f"pi smoke: source={report['source']!r} is not a non-empty string "
                f"when ready_for_real_capture is True and status is 'passed'"
            )
        counted_qty = report["counted_qty"]
        book_qty = report["book_qty"]
        counted_is_int = isinstance(counted_qty, int) and not isinstance(counted_qty, bool)
        book_is_int = isinstance(book_qty, int) and not isinstance(book_qty, bool)
        if not counted_is_int:
            problems.append(f"pi smoke: counted_qty={counted_qty!r} is not an int")
        if not book_is_int:
            problems.append(f"pi smoke: book_qty={book_qty!r} is not an int")
        if counted_is_int and book_is_int:
            if report["diff"] != counted_qty - book_qty:
                problems.append(
                    f"pi smoke: diff={report['diff']!r} != "
                    f"counted_qty - book_qty={counted_qty - book_qty}"
                )
        if not isinstance(report["photo_sha256"], str) or not report["photo_sha256"]:
            problems.append(
                f"pi smoke: photo_sha256={report['photo_sha256']!r} is not a non-empty string"
            )
    if ready and status == "failed":
        error_type = report["error_type"]
        if not isinstance(error_type, str) or not error_type:
            problems.append(
                f"pi smoke: error_type={error_type!r} is not a non-empty "
                f"string when ready_for_real_capture is True and status is 'failed'"
            )
        if error_type != "unknown_bin" and not report["attempted"]:
            problems.append(
                f"pi smoke: attempted={report['attempted']!r} != True "
                f"when ready_for_real_capture is True and status is 'failed'"
            )
    _check_honesty(report, problems, "pi smoke", "촬영하지 않는다")
    _check_honesty(report, problems, "pi smoke", "대체하지 않는다")
    return problems


def _check_pi_smoke(pi_probe=None, pi_device_confirmed=False, pi_which=None, pi_report=None):
    name = "pi_smoke_consistent"
    fake = _PiSmokeFakeSession()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_pi_smoke(
                output_dir=Path(tmp) / "pi-smoke-captures",
                device_confirmed=pi_device_confirmed,
                bin_id=PI_SMOKE_BIN_ID,
                which=_pi_which_from_probe(pi_probe, pi_which),
                session_fn=fake,
            )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_pi_smoke(report, pi_report=pi_report)
    if isinstance(report, dict) and "ready_for_real_capture" in report:
        if not bool(report["ready_for_real_capture"]) and len(fake.calls) != 0:
            problems.append(
                f"pi smoke: fake session calls={len(fake.calls)} != 0 "
                f"when ready_for_real_capture is False"
            )
        if bool(report["ready_for_real_capture"]) and len(fake.calls) != 1:
            problems.append(
                f"pi smoke: fake session calls={len(fake.calls)} != 1 "
                f"when ready_for_real_capture is True"
            )
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"status={report['status']} attempted={report['attempted']} "
        f"blockers={[b['id'] for b in report['blockers']]} "
        f"fake_calls={len(fake.calls)}"
    )
    return PreSubmissionCheck(name, True, detail), report


class _PiFullFakeSession:
    """전수 점검 전용 가짜 전체 촬영 session. 실제 촬영을 하지 않는다."""

    def __init__(self):
        self.calls = []

    def __call__(self, output_dir, bin_ids=None, session_id=None, runner=None, which=None):
        self.calls.append(
            {"output_dir": output_dir, "bin_ids": bin_ids, "session_id": session_id}
        )
        from terminal.demo_data import DEMO_COUNTED_QTY, demo_bin_ids, demo_ledger

        ledger = demo_ledger()
        bins = []
        for bin_id in demo_bin_ids():
            counted = DEMO_COUNTED_QTY[bin_id]
            book = ledger[bin_id].book_qty
            diff = counted - book
            verdict = "match" if diff == 0 else ("short" if diff < 0 else "over")
            bins.append(
                {
                    "bin_id": bin_id,
                    "book_qty": book,
                    "counted_qty": counted,
                    "diff": diff,
                    "verdict": verdict,
                    "photo": {"sha256": PI_SMOKE_FAKE_SHA, "image_ref": bin_id + ".jpg"},
                }
            )
        return {
            "session_id": session_id or "PI-FULL",
            "source": "mock",
            "capture_source": "pi-camera",
            "bins": bins,
            "summary": {
                "counted_bins": 6,
                "matched": 4,
                "mismatched": 2,
                "match_rate": 4 / 6,
                "abs_diff_total": 6,
                "net_diff": 0,
            },
        }


def validate_pi_session(report, pi_report=None, blockers=None) -> list[str]:
    """Pi 전체 세션 보고가 내부적으로, 그리고 Pi 준비 보고와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"report is not a dict: {report!r}"]
    required = (
        "status",
        "attempted",
        "ready_for_real_capture",
        "blockers",
        "session_id",
        "source",
        "capture_source",
        "bins",
        "summary",
        "error_type",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"missing required keys: {missing}")
        return problems
    ids = _readiness_blocker_ids(report["blockers"], problems, "pi session")
    if isinstance(report["blockers"], (list, tuple)):
        expected_subsequence = [b for b in PI_READINESS_BLOCKER_ORDER if b in ids]
        if ids != expected_subsequence:
            problems.append(
                f"pi session: blocker ids {ids} are not a subsequence of "
                f"{list(PI_READINESS_BLOCKER_ORDER)}"
            )
    ready = bool(report["ready_for_real_capture"])
    if isinstance(pi_report, dict):
        if "ready_for_real_capture" in pi_report:
            if ready != bool(pi_report["ready_for_real_capture"]):
                problems.append(
                    f"pi session: ready_for_real_capture={report['ready_for_real_capture']!r} "
                    f"!= pi readiness ready_for_real_capture="
                    f"{pi_report['ready_for_real_capture']!r}"
                )
        if isinstance(pi_report.get("blockers"), (list, tuple)):
            pi_ids = _readiness_blocker_ids(
                pi_report["blockers"], problems, "pi readiness"
            )
            if ids != pi_ids:
                problems.append(
                    f"pi session: blocker ids {ids} != "
                    f"pi readiness blocker ids {pi_ids}"
                )
    status = report["status"]
    if status not in ("blocked", "passed", "failed"):
        problems.append(
            f"pi session: status={status!r} is not one of "
            f"['blocked', 'passed', 'failed']"
        )
    if not ready:
        if status != "blocked":
            problems.append(
                f"pi session: status={status!r} != 'blocked' "
                f"when ready_for_real_capture is False"
            )
        if bool(report["attempted"]):
            problems.append(
                f"pi session: attempted={report['attempted']!r} != False "
                f"when ready_for_real_capture is False"
            )
        if report["source"] is not None:
            problems.append(
                f"pi session: source={report['source']!r} is not None "
                f"when ready_for_real_capture is False"
            )
        if report["capture_source"] is not None:
            problems.append(
                f"pi session: capture_source={report['capture_source']!r} is not None "
                f"when ready_for_real_capture is False"
            )
        if report["bins"] != []:
            problems.append(
                f"pi session: bins={report['bins']!r} != [] "
                f"when ready_for_real_capture is False"
            )
        if report["summary"] is not None:
            problems.append(
                f"pi session: summary={report['summary']!r} is not None "
                f"when ready_for_real_capture is False"
            )
        if report["error_type"] is not None:
            problems.append(
                f"pi session: error_type={report['error_type']!r} is not None "
                f"when ready_for_real_capture is False"
            )
        if "pi_real_capture_pending" not in _pre_submission_blocker_ids(blockers):
            problems.append(
                "pi session: ready_for_real_capture is False but pre-submission "
                "blockers missing 'pi_real_capture_pending'"
            )
    if ready and status == "passed":
        if not report["attempted"]:
            problems.append(
                f"pi session: attempted={report['attempted']!r} != True "
                f"when ready_for_real_capture is True and status is 'passed'"
            )
        if report["capture_source"] != "pi-camera":
            problems.append(
                f"pi session: capture_source={report['capture_source']!r} != 'pi-camera' "
                f"when ready_for_real_capture is True and status is 'passed'"
            )
        if not isinstance(report["source"], str) or not report["source"]:
            problems.append(
                f"pi session: source={report['source']!r} is not a non-empty string "
                f"when ready_for_real_capture is True and status is 'passed'"
            )
        bins = report["bins"]
        if not isinstance(bins, (list, tuple)) or len(bins) != len(EXPECTED_BIN_IDS):
            problems.append(
                f"pi session: bins={bins!r} does not have "
                f"{len(EXPECTED_BIN_IDS)} entries when status is 'passed'"
            )
            bins = []
        bin_ids = [
            comp.get("bin_id") if isinstance(comp, dict) else None for comp in bins
        ]
        if bins and bin_ids != list(EXPECTED_BIN_IDS):
            problems.append(
                f"pi session: bin order {bin_ids} != {list(EXPECTED_BIN_IDS)}"
            )
        diffs_ok = True
        for comp in bins:
            if not isinstance(comp, dict):
                problems.append(f"pi session: bin entry is not a dict: {comp!r}")
                diffs_ok = False
                continue
            counted = comp.get("counted_qty")
            book = comp.get("book_qty")
            if not (isinstance(counted, int) and not isinstance(counted, bool)
                    and isinstance(book, int) and not isinstance(book, bool)):
                problems.append(
                    f"pi session: bin {comp.get('bin_id')!r} counted_qty/book_qty "
                    f"are not ints: {comp!r}"
                )
                diffs_ok = False
            elif comp.get("diff") != counted - book:
                problems.append(
                    f"pi session: bin {comp.get('bin_id')!r} "
                    f"diff={comp.get('diff')!r} != counted_qty - book_qty="
                    f"{counted - book}"
                )
                diffs_ok = False
            if not isinstance(comp.get("photo_sha256"), str) or not comp.get("photo_sha256"):
                problems.append(
                    f"pi session: bin {comp.get('bin_id')!r} photo_sha256 "
                    f"is not a non-empty string"
                )
        summary = report["summary"]
        if not isinstance(summary, dict):
            problems.append(
                f"pi session: summary={summary!r} is not a dict "
                f"when status is 'passed'"
            )
        elif bins and diffs_ok:
            matched = sum(1 for comp in bins if comp.get("diff") == 0)
            expected_summary = {
                "counted_bins": len(bins),
                "matched": matched,
                "mismatched": len(bins) - matched,
                "abs_diff_total": sum(abs(comp["diff"]) for comp in bins),
                "net_diff": sum(comp["diff"] for comp in bins),
            }
            for key, expected in expected_summary.items():
                if summary.get(key) != expected:
                    problems.append(
                        f"pi session: summary {key}={summary.get(key)!r} "
                        f"!= {expected} computed from bins"
                    )
            if summary.get("counted_bins"):
                expected_rate = matched / summary["counted_bins"]
                rate = summary.get("match_rate")
                if not isinstance(rate, (int, float)) or isinstance(rate, bool) \
                        or abs(rate - expected_rate) > 1e-9:
                    problems.append(
                        f"pi session: summary match_rate={rate!r} "
                        f"!= {expected_rate} computed from bins"
                    )
    if ready and status == "failed":
        error_type = report["error_type"]
        if not isinstance(error_type, str) or not error_type:
            problems.append(
                f"pi session: error_type={error_type!r} is not a non-empty "
                f"string when ready_for_real_capture is True and status is 'failed'"
            )
        if not report["attempted"]:
            problems.append(
                f"pi session: attempted={report['attempted']!r} != True "
                f"when ready_for_real_capture is True and status is 'failed'"
            )
        if report["summary"] is not None:
            problems.append(
                f"pi session: summary={report['summary']!r} is not None "
                f"when status is 'failed'"
            )
        if report["bins"] != []:
            problems.append(
                f"pi session: bins={report['bins']!r} != [] "
                f"when status is 'failed'"
            )
    _check_honesty(report, problems, "pi session", "촬영하지 않는다")
    _check_honesty(report, problems, "pi session", "대체하지 않는다")
    _check_honesty(report, problems, "pi session", "검증 완료를 뜻하지 않는다")
    return problems


def _check_pi_session_full(pi_probe=None, pi_device_confirmed=False, pi_which=None, pi_report=None):
    name = "pi_session_consistent"
    fake = _PiFullFakeSession()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_pi_full_session(
                output_dir=Path(tmp) / "pi-full-captures",
                device_confirmed=pi_device_confirmed,
                which=_pi_which_from_probe(pi_probe, pi_which),
                session_fn=fake,
                session_id="PRE-SUBMISSION-PI-SESSION",
            )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_pi_session(report, pi_report=pi_report)
    if isinstance(report, dict) and "ready_for_real_capture" in report:
        if not bool(report["ready_for_real_capture"]) and len(fake.calls) != 0:
            problems.append(
                f"pi session: fake session calls={len(fake.calls)} != 0 "
                f"when ready_for_real_capture is False"
            )
        if bool(report["ready_for_real_capture"]) and len(fake.calls) != 1:
            problems.append(
                f"pi session: fake session calls={len(fake.calls)} != 1 "
                f"when ready_for_real_capture is True"
            )
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"status={report['status']} attempted={report['attempted']} "
        f"blockers={[b['id'] for b in report['blockers']]} "
        f"fake_calls={len(fake.calls)}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_devpost_text(text, blockers=None) -> list[str]:
    """제출 문안 원문이 절·블로커·정직성 표기 기준과 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(text, str):
        return [f"devpost: text is not a string: {text!r}"]
    positions = [text.find(section) for section in DEVPOST_SECTIONS]
    missing = [s for s, pos in zip(DEVPOST_SECTIONS, positions) if pos < 0]
    if missing:
        problems.append(f"devpost: missing sections {missing}")
    elif positions != sorted(positions):
        problems.append(f"devpost: section order positions {positions}")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    found_ids = [bid for _, bid in sorted(found)]
    if found_ids != list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS):
        problems.append(
            f"devpost: blocker ids in text {found_ids} != "
            f"{list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS)}"
        )
    elif expected_ids and found_ids != expected_ids:
        problems.append(
            f"devpost: blocker ids {found_ids} != pre-submission blockers {expected_ids}"
        )
    if "SUBMISSION_READY: false" not in text or "SUBMISSION_READY: true" in text:
        problems.append("devpost: SUBMISSION_READY must be false and never true")
    for needle in DEVPOST_DEMO_MARKERS:
        if needle not in text:
            problems.append(f"devpost: missing demo marker {needle!r}")
    for needle in DEVPOST_HONESTY_MARKERS:
        if needle not in text:
            problems.append(f"devpost: missing honesty marker {needle!r}")
    for needle in (DEVPOST_REPO_URL, DEVPOST_DEADLINE_ET, DEVPOST_DEADLINE_KST):
        if needle not in text:
            problems.append(f"devpost: missing {needle!r}")
    violations = audit_text(DEVPOST_REL, text)
    if violations:
        problems.append(f"devpost: claims audit violations {violations}")
    return problems


def validate_devpost_report(report, blockers=None) -> list[str]:
    """devpost 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"devpost report is not a dict: {report!r}"]
    required = ("section_count", "blockers", "submission_ready", "claims_audit_clean")
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"devpost: missing required keys: {missing}")
        return problems
    if report["section_count"] != len(DEVPOST_SECTIONS):
        problems.append(
            f"devpost: section_count={report['section_count']!r} != {len(DEVPOST_SECTIONS)}"
        )
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"devpost: blockers {list(report['blockers'])} != {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append(
            f"devpost: submission_ready={report['submission_ready']!r} is not False"
        )
    if report["claims_audit_clean"] is not True:
        problems.append("devpost: claims_audit_clean is not True")
    return problems


def build_devpost_report(root, blockers=None) -> dict:
    """문안 파일에서 section_count·블로커·submission_ready 보고를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    path = Path(root) / DEVPOST_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "section_count": 0,
            "blockers": [],
            "submission_ready": False,
            "claims_audit_clean": False,
        }
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    return {
        "section_count": sum(1 for s in DEVPOST_SECTIONS if s in text),
        "blockers": [bid for _, bid in sorted(found)],
        "submission_ready": "SUBMISSION_READY: true" in text,
        "claims_audit_clean": audit_text(DEVPOST_REL, text) == [],
    }


def _check_devpost(root):
    name = "devpost_consistent"
    path = Path(root) / DEVPOST_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report = build_devpost_report(root)
        return PreSubmissionCheck(name, False, f"read failed: {exc!r}"), report
    problems = validate_devpost_text(text)
    report = build_devpost_report(root)
    problems.extend(validate_devpost_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"section_count={report['section_count']} "
        f"blockers={report['blockers']} "
        f"submission_ready={report['submission_ready']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_runbook_text(text, blockers=None) -> list[str]:
    """제출 런북 원문이 절·블로커·정직성 표기 기준과 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(text, str):
        return [f"runbook: text is not a string: {text!r}"]
    positions = [text.find(section) for section in RUNBOOK_SECTIONS]
    missing = [s for s, pos in zip(RUNBOOK_SECTIONS, positions) if pos < 0]
    if missing:
        problems.append(f"runbook: missing sections {missing}")
    elif positions != sorted(positions):
        problems.append(f"runbook: section order positions {positions}")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    found_ids = [bid for _, bid in sorted(found)]
    if found_ids != list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS):
        problems.append(
            f"runbook: blocker ids in text {found_ids} != "
            f"{list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS)}"
        )
    elif expected_ids and found_ids != expected_ids:
        problems.append(
            f"runbook: blocker ids {found_ids} != pre-submission blockers {expected_ids}"
        )
    if "SUBMISSION_READY: false" not in text or "SUBMISSION_READY: true" in text:
        problems.append("runbook: SUBMISSION_READY must be false and never true")
    if RUNBOOK_CREDIT_AT not in text:
        problems.append(f"runbook: missing credit marker {RUNBOOK_CREDIT_AT!r}")
    for needle in RUNBOOK_KEY_MARKERS:
        if needle not in text:
            problems.append(f"runbook: missing key marker {needle!r}")
    for needle in RUNBOOK_HONESTY_MARKERS:
        if needle not in text:
            problems.append(f"runbook: missing honesty marker {needle!r}")
    for command in RUNBOOK_FINAL_COMMANDS:
        if command not in text:
            problems.append(f"runbook: missing final command {command!r}")
    for needle in (RUNBOOK_DEADLINE_ET, RUNBOOK_DEADLINE_KST, RUNBOOK_REPO):
        if needle not in text:
            problems.append(f"runbook: missing {needle!r}")
    violations = audit_text(RUNBOOK_REL, text)
    if violations:
        problems.append(f"runbook: claims audit violations {violations}")
    return problems


def validate_runbook_report(report, blockers=None) -> list[str]:
    """runbook 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"runbook report is not a dict: {report!r}"]
    required = (
        "section_count",
        "blockers",
        "submission_ready",
        "claims_audit_clean",
        "final_command_count",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"runbook: missing required keys: {missing}")
        return problems
    if report["section_count"] != len(RUNBOOK_SECTIONS):
        problems.append(
            f"runbook: section_count={report['section_count']!r} != {len(RUNBOOK_SECTIONS)}"
        )
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"runbook: blockers {list(report['blockers'])} != {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append(
            f"runbook: submission_ready={report['submission_ready']!r} is not False"
        )
    if report["claims_audit_clean"] is not True:
        problems.append("runbook: claims_audit_clean is not True")
    if report["final_command_count"] != len(RUNBOOK_FINAL_COMMANDS):
        problems.append(
            f"runbook: final_command_count={report['final_command_count']!r} "
            f"!= {len(RUNBOOK_FINAL_COMMANDS)}"
        )
    return problems


def build_runbook_report(root, blockers=None) -> dict:
    """런북 파일에서 section_count·블로커·submission_ready 보고를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    path = Path(root) / RUNBOOK_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "section_count": 0,
            "blockers": [],
            "submission_ready": False,
            "claims_audit_clean": False,
            "final_command_count": 0,
        }
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    return {
        "section_count": sum(1 for s in RUNBOOK_SECTIONS if s in text),
        "blockers": [bid for _, bid in sorted(found)],
        "submission_ready": "SUBMISSION_READY: true" in text,
        "claims_audit_clean": audit_text(RUNBOOK_REL, text) == [],
        "final_command_count": sum(1 for c in RUNBOOK_FINAL_COMMANDS if c in text),
    }


def _check_runbook(root):
    name = "runbook_consistent"
    path = Path(root) / RUNBOOK_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report = build_runbook_report(root)
        return PreSubmissionCheck(name, False, f"read failed: {exc!r}"), report
    problems = validate_runbook_text(text)
    report = build_runbook_report(root)
    problems.extend(validate_runbook_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"section_count={report['section_count']} "
        f"blockers={report['blockers']} "
        f"submission_ready={report['submission_ready']} "
        f"final_commands={report['final_command_count']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_story_text(text, blockers=None) -> list[str]:
    """제출 스토리 원문이 절·블로커·정직성 표기 기준과 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(text, str):
        return [f"story: text is not a string: {text!r}"]
    positions = [text.find(section) for section in STORY_SECTIONS]
    missing = [s for s, pos in zip(STORY_SECTIONS, positions) if pos < 0]
    if missing:
        problems.append(f"story: missing sections {missing}")
    elif positions != sorted(positions):
        problems.append(f"story: section order positions {positions}")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    found_ids = [bid for _, bid in sorted(found)]
    if found_ids != list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS):
        problems.append(
            f"story: blocker ids in text {found_ids} != "
            f"{list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS)}"
        )
    elif expected_ids and found_ids != expected_ids:
        problems.append(
            f"story: blocker ids {found_ids} != pre-submission blockers {expected_ids}"
        )
    if "SUBMISSION_READY: false" not in text or "SUBMISSION_READY: true" in text:
        problems.append("story: SUBMISSION_READY must be false and never true")
    for needle in STORY_DEMO_MARKERS:
        if needle not in text:
            problems.append(f"story: missing demo marker {needle!r}")
    for needle in STORY_HONESTY_MARKERS:
        if needle not in text:
            problems.append(f"story: missing honesty marker {needle!r}")
    for needle in (STORY_THEME_MARKER, STORY_NEW_WORK_MARKER):
        if needle not in text:
            problems.append(f"story: missing {needle!r}")
    violations = audit_text(STORY_REL, text)
    if violations:
        problems.append(f"story: claims audit violations {violations}")
    return problems


def validate_story_report(report, blockers=None) -> list[str]:
    """story 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"story report is not a dict: {report!r}"]
    required = ("section_count", "blockers", "submission_ready", "claims_audit_clean")
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"story: missing required keys: {missing}")
        return problems
    if report["section_count"] != len(STORY_SECTIONS):
        problems.append(
            f"story: section_count={report['section_count']!r} != {len(STORY_SECTIONS)}"
        )
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"story: blockers {list(report['blockers'])} != {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append(
            f"story: submission_ready={report['submission_ready']!r} is not False"
        )
    if report["claims_audit_clean"] is not True:
        problems.append("story: claims_audit_clean is not True")
    return problems


def build_story_report(root, blockers=None) -> dict:
    """스토리 파일에서 section_count·블로커·submission_ready 보고를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    path = Path(root) / STORY_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "section_count": 0,
            "blockers": [],
            "submission_ready": False,
            "claims_audit_clean": False,
        }
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    return {
        "section_count": sum(1 for s in STORY_SECTIONS if s in text),
        "blockers": [bid for _, bid in sorted(found)],
        "submission_ready": "SUBMISSION_READY: true" in text,
        "claims_audit_clean": audit_text(STORY_REL, text) == [],
    }


def _check_story(root):
    name = "story_consistent"
    path = Path(root) / STORY_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report = build_story_report(root)
        return PreSubmissionCheck(name, False, f"read failed: {exc!r}"), report
    problems = validate_story_text(text)
    report = build_story_report(root)
    problems.extend(validate_story_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"section_count={report['section_count']} "
        f"blockers={report['blockers']} "
        f"submission_ready={report['submission_ready']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_en_summary_text(text, blockers=None) -> list[str]:
    """영문 제출 요약 원문이 절·블로커·정직성 표기 기준과 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(text, str):
        return [f"en_summary: text is not a string: {text!r}"]
    positions = [text.find(section) for section in EN_SUMMARY_SECTIONS]
    missing = [s for s, pos in zip(EN_SUMMARY_SECTIONS, positions) if pos < 0]
    if missing:
        problems.append(f"en_summary: missing sections {missing}")
    elif positions != sorted(positions):
        problems.append(f"en_summary: section order positions {positions}")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    found_ids = [bid for _, bid in sorted(found)]
    if found_ids != list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS):
        problems.append(
            f"en_summary: blocker ids in text {found_ids} != "
            f"{list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS)}"
        )
    elif expected_ids and found_ids != expected_ids:
        problems.append(
            f"en_summary: blocker ids {found_ids} != pre-submission blockers {expected_ids}"
        )
    if "SUBMISSION_READY: false" not in text or "SUBMISSION_READY: true" in text:
        problems.append("en_summary: SUBMISSION_READY must be false and never true")
    for needle in EN_SUMMARY_DEMO_MARKERS:
        if needle not in text:
            problems.append(f"en_summary: missing demo marker {needle!r}")
    for needle in EN_SUMMARY_HONESTY_MARKERS:
        if needle not in text:
            problems.append(f"en_summary: missing honesty marker {needle!r}")
    for needle in (EN_SUMMARY_THEME_MARKER, EN_SUMMARY_NEW_WORK_MARKER):
        if needle not in text:
            problems.append(f"en_summary: missing {needle!r}")
    violations = audit_text(EN_SUMMARY_REL, text)
    if violations:
        problems.append(f"en_summary: claims audit violations {violations}")
    return problems


def validate_en_summary_report(report, blockers=None) -> list[str]:
    """en_summary 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"en_summary report is not a dict: {report!r}"]
    required = ("section_count", "blockers", "submission_ready", "claims_audit_clean")
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"en_summary: missing required keys: {missing}")
        return problems
    if report["section_count"] != len(EN_SUMMARY_SECTIONS):
        problems.append(
            f"en_summary: section_count={report['section_count']!r} != {len(EN_SUMMARY_SECTIONS)}"
        )
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"en_summary: blockers {list(report['blockers'])} != {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append(
            f"en_summary: submission_ready={report['submission_ready']!r} is not False"
        )
    if report["claims_audit_clean"] is not True:
        problems.append("en_summary: claims_audit_clean is not True")
    return problems


def build_en_summary_report(root, blockers=None) -> dict:
    """영문 요약 파일에서 section_count·블로커·submission_ready 보고를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    path = Path(root) / EN_SUMMARY_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "section_count": 0,
            "blockers": [],
            "submission_ready": False,
            "claims_audit_clean": False,
        }
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    return {
        "section_count": sum(1 for s in EN_SUMMARY_SECTIONS if s in text),
        "blockers": [bid for _, bid in sorted(found)],
        "submission_ready": "SUBMISSION_READY: true" in text,
        "claims_audit_clean": audit_text(EN_SUMMARY_REL, text) == [],
    }


def _check_en_summary(root):
    name = "en_summary_consistent"
    path = Path(root) / EN_SUMMARY_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report = build_en_summary_report(root)
        return PreSubmissionCheck(name, False, f"read failed: {exc!r}"), report
    problems = validate_en_summary_text(text)
    report = build_en_summary_report(root)
    problems.extend(validate_en_summary_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"section_count={report['section_count']} "
        f"blockers={report['blockers']} "
        f"submission_ready={report['submission_ready']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_demo_script_text(text, blockers=None) -> list[str]:
    """데모 대본 원문이 절·블로커·정직성 표기 기준과 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(text, str):
        return [f"demo_script: text is not a string: {text!r}"]
    positions = [text.find(section) for section in DEMO_SCRIPT_SECTIONS]
    missing = [s for s, pos in zip(DEMO_SCRIPT_SECTIONS, positions) if pos < 0]
    if missing:
        problems.append(f"demo_script: missing sections {missing}")
    elif positions != sorted(positions):
        problems.append(f"demo_script: section order positions {positions}")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    found_ids = [bid for _, bid in sorted(found)]
    if found_ids != list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS):
        problems.append(
            f"demo_script: blocker ids in text {found_ids} != "
            f"{list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS)}"
        )
    elif expected_ids and found_ids != expected_ids:
        problems.append(
            f"demo_script: blocker ids {found_ids} != pre-submission blockers {expected_ids}"
        )
    if "SUBMISSION_READY: false" not in text or "SUBMISSION_READY: true" in text:
        problems.append("demo_script: SUBMISSION_READY must be false and never true")
    for needle in DEMO_SCRIPT_DEMO_MARKERS:
        if needle not in text:
            problems.append(f"demo_script: missing demo marker {needle!r}")
    for needle in DEMO_SCRIPT_HONESTY_MARKERS:
        if needle not in text:
            problems.append(f"demo_script: missing honesty marker {needle!r}")
    for needle in (DEMO_SCRIPT_THEME_MARKER, DEMO_SCRIPT_NEW_WORK_MARKER):
        if needle not in text:
            problems.append(f"demo_script: missing {needle!r}")
    violations = audit_text(DEMO_SCRIPT_REL, text)
    if violations:
        problems.append(f"demo_script: claims audit violations {violations}")
    return problems


def validate_demo_script_report(report, blockers=None) -> list[str]:
    """demo_script 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"demo_script report is not a dict: {report!r}"]
    required = ("section_count", "blockers", "submission_ready", "claims_audit_clean")
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"demo_script: missing required keys: {missing}")
        return problems
    if report["section_count"] != len(DEMO_SCRIPT_SECTIONS):
        problems.append(
            f"demo_script: section_count={report['section_count']!r} != {len(DEMO_SCRIPT_SECTIONS)}"
        )
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"demo_script: blockers {list(report['blockers'])} != {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append(
            f"demo_script: submission_ready={report['submission_ready']!r} is not False"
        )
    if report["claims_audit_clean"] is not True:
        problems.append("demo_script: claims_audit_clean is not True")
    return problems


def build_demo_script_report(root, blockers=None) -> dict:
    """데모 대본 파일에서 section_count·블로커·submission_ready 보고를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    path = Path(root) / DEMO_SCRIPT_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "section_count": 0,
            "blockers": [],
            "submission_ready": False,
            "claims_audit_clean": False,
        }
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    return {
        "section_count": sum(1 for s in DEMO_SCRIPT_SECTIONS if s in text),
        "blockers": [bid for _, bid in sorted(found)],
        "submission_ready": "SUBMISSION_READY: true" in text,
        "claims_audit_clean": audit_text(DEMO_SCRIPT_REL, text) == [],
    }


def _check_demo_script(root):
    name = "demo_script_consistent"
    path = Path(root) / DEMO_SCRIPT_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report = build_demo_script_report(root)
        return PreSubmissionCheck(name, False, f"read failed: {exc!r}"), report
    problems = validate_demo_script_text(text)
    report = build_demo_script_report(root)
    problems.extend(validate_demo_script_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"section_count={report['section_count']} "
        f"blockers={report['blockers']} "
        f"submission_ready={report['submission_ready']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_readme_text(text, blockers=None) -> list[str]:
    """README 원문이 절·블로커·정직성 표기 기준과 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(text, str):
        return [f"readme: text is not a string: {text!r}"]
    positions = [text.find(section) for section in README_SECTIONS]
    missing = [s for s, pos in zip(README_SECTIONS, positions) if pos < 0]
    if missing:
        problems.append(f"readme: missing sections {missing}")
    elif positions != sorted(positions):
        problems.append(f"readme: section order positions {positions}")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    found_ids = [bid for _, bid in sorted(found)]
    if found_ids != list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS):
        problems.append(
            f"readme: blocker ids in text {found_ids} != "
            f"{list(EXPECTED_PRE_SUBMISSION_BLOCKER_IDS)}"
        )
    elif expected_ids and found_ids != expected_ids:
        problems.append(
            f"readme: blocker ids {found_ids} != pre-submission blockers {expected_ids}"
        )
    if "SUBMISSION_READY: false" not in text or "SUBMISSION_READY: true" in text:
        problems.append("readme: SUBMISSION_READY must be false and never true")
    for needle in README_DEMO_MARKERS:
        if needle not in text:
            problems.append(f"readme: missing demo marker {needle!r}")
    for needle in README_HONESTY_MARKERS:
        if needle not in text:
            problems.append(f"readme: missing honesty marker {needle!r}")
    for needle in (README_THEME_MARKER, README_NEW_WORK_MARKER):
        if needle not in text:
            problems.append(f"readme: missing {needle!r}")
    violations = audit_text(README_REL, text)
    if violations:
        problems.append(f"readme: claims audit violations {violations}")
    return problems


def validate_readme_report(report, blockers=None) -> list[str]:
    """readme 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"readme report is not a dict: {report!r}"]
    required = ("section_count", "blockers", "submission_ready", "claims_audit_clean")
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"readme: missing required keys: {missing}")
        return problems
    if report["section_count"] != len(README_SECTIONS):
        problems.append(
            f"readme: section_count={report['section_count']!r} != {len(README_SECTIONS)}"
        )
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"readme: blockers {list(report['blockers'])} != {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append(
            f"readme: submission_ready={report['submission_ready']!r} is not False"
        )
    if report["claims_audit_clean"] is not True:
        problems.append("readme: claims_audit_clean is not True")
    return problems


def build_readme_report(root, blockers=None) -> dict:
    """README 파일에서 section_count·블로커·submission_ready 보고를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    path = Path(root) / README_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {
            "section_count": 0,
            "blockers": [],
            "submission_ready": False,
            "claims_audit_clean": False,
        }
    found = []
    for blocker_id in EXPECTED_PRE_SUBMISSION_BLOCKER_IDS:
        pos = text.find(blocker_id)
        if pos >= 0:
            found.append((pos, blocker_id))
    return {
        "section_count": sum(1 for s in README_SECTIONS if s in text),
        "blockers": [bid for _, bid in sorted(found)],
        "submission_ready": "SUBMISSION_READY: true" in text,
        "claims_audit_clean": audit_text(README_REL, text) == [],
    }


def _check_readme(root):
    name = "readme_consistent"
    path = Path(root) / README_REL
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        report = build_readme_report(root)
        return PreSubmissionCheck(name, False, f"read failed: {exc!r}"), report
    problems = validate_readme_text(text)
    report = build_readme_report(root)
    problems.extend(validate_readme_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"section_count={report['section_count']} "
        f"blockers={report['blockers']} "
        f"submission_ready={report['submission_ready']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_fallback_manifest(manifest, blockers=None) -> list[str]:
    """폴백 자산 dict가 컷·플래그·요약·해시·정직성 기준과 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(manifest, dict):
        return [f"fallback: manifest is not a dict: {manifest!r}"]
    if manifest.get("cut_index") != FALLBACK_CUT_INDEX:
        problems.append(f"fallback: cut_index={manifest.get('cut_index')!r} != {FALLBACK_CUT_INDEX}")
    if manifest.get("replaces") != "pi-placeholder":
        problems.append(f"fallback: replaces={manifest.get('replaces')!r} != 'pi-placeholder'")
    if manifest.get("decision_date") != FALLBACK_DECISION_DATE:
        problems.append(f"fallback: decision_date={manifest.get('decision_date')!r} != {FALLBACK_DECISION_DATE!r}")
    if manifest.get("is_pi_real_capture") is not False:
        problems.append(f"fallback: is_pi_real_capture={manifest.get('is_pi_real_capture')!r} is not False")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if "pi_real_capture_pending" in expected_ids and manifest.get("is_pi_real_capture") is not False:
        problems.append("fallback: pi blocker present but is_pi_real_capture is not False")
    if manifest.get("capture_source") != "file":
        problems.append(f"fallback: capture_source={manifest.get('capture_source')!r} != 'file'")
    if manifest.get("source") != "mock":
        problems.append(f"fallback: source={manifest.get('source')!r} != 'mock'")
    if manifest.get("session_id") != FALLBACK_SESSION_ID:
        problems.append(f"fallback: session_id={manifest.get('session_id')!r} != {FALLBACK_SESSION_ID!r}")
    summary = manifest.get("summary") or {}
    if not isinstance(summary, dict):
        problems.append(f"fallback: summary is not a dict: {summary!r}")
        summary = {}
    for key, expected in FALLBACK_EXPECTED_SUMMARY.items():
        if summary.get(key) != expected:
            problems.append(f"fallback: summary.{key}={summary.get(key)!r} != {expected}")
    bins = manifest.get("bins") or []
    if not isinstance(bins, list) or len(bins) != 6:
        problems.append(f"fallback: bins len={len(bins) if isinstance(bins, list) else bins!r} != 6")
        bins = bins if isinstance(bins, list) else []
    bin_ids = [e.get("bin_id") if isinstance(e, dict) else None for e in bins]
    if bin_ids != list(EXPECTED_BIN_IDS):
        problems.append(f"fallback: bin ids {bin_ids} != {list(EXPECTED_BIN_IDS)}")
    try:
        from demo.fallback import fake_photo_bytes as _fake_bytes
        import hashlib as _hl
        for entry in bins:
            if not isinstance(entry, dict):
                continue
            bin_id = entry.get("bin_id")
            photo = entry.get("photo") or {}
            expected_sha = _hl.sha256(_fake_bytes(str(bin_id))).hexdigest()
            if photo.get("sha256") != expected_sha:
                problems.append(f"fallback: bin {bin_id} photo sha256 mismatch")
            if bin_id == "A-01-02":
                if entry.get("verdict") != "short":
                    problems.append(f"fallback: A-01-02 verdict={entry.get('verdict')!r} != 'short'")
                if entry.get("diff") != -3:
                    problems.append(f"fallback: A-01-02 diff={entry.get('diff')!r} != -3")
                if entry.get("book_qty") != 8:
                    problems.append(f"fallback: A-01-02 book_qty={entry.get('book_qty')!r} != 8")
                if entry.get("counted_qty") != 5:
                    problems.append(f"fallback: A-01-02 counted_qty={entry.get('counted_qty')!r} != 5")
    except Exception as exc:
        problems.append(f"fallback: hash check raised: {exc!r}")
    honesty = manifest.get("honesty") or []
    joined = " ".join(str(line) for line in honesty) if isinstance(honesty, list) else ""
    for needle in FALLBACK_HONESTY_MARKERS:
        if needle not in joined:
            problems.append(f"fallback: missing honesty marker {needle!r}")
    return problems


def validate_fallback_report(report, blockers=None) -> list[str]:
    """fallback 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"fallback report is not a dict: {report!r}"]
    required = ("cut_index", "is_pi_real_capture", "capture_source", "source", "blockers", "submission_ready")
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"fallback: missing required keys: {missing}")
        return problems
    if report["cut_index"] != FALLBACK_CUT_INDEX:
        problems.append(f"fallback: cut_index={report['cut_index']!r} != {FALLBACK_CUT_INDEX}")
    if report["is_pi_real_capture"] is not False:
        problems.append(f"fallback: is_pi_real_capture={report['is_pi_real_capture']!r} is not False")
    if report["capture_source"] != "file":
        problems.append(f"fallback: capture_source={report['capture_source']!r} != 'file'")
    if report["source"] != "mock":
        problems.append(f"fallback: source={report['source']!r} != 'mock'")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(f"fallback: blockers {list(report['blockers'])} != {expected_ids}")
    if report["submission_ready"] is not False:
        problems.append(f"fallback: submission_ready={report['submission_ready']!r} is not False")
    return problems


def build_fallback_report(root, blockers=None) -> dict:
    """폴백 JSON 파일에서 cut·플래그·블로커·submission_ready 보고를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    path = Path(root) / FALLBACK_REL
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"cut_index": 0, "is_pi_real_capture": True, "capture_source": "", "source": "", "blockers": [], "submission_ready": False}
    if not isinstance(manifest, dict):
        return {"cut_index": 0, "is_pi_real_capture": True, "capture_source": "", "source": "", "blockers": [], "submission_ready": False}
    return {
        "cut_index": manifest.get("cut_index"),
        "is_pi_real_capture": manifest.get("is_pi_real_capture"),
        "capture_source": manifest.get("capture_source"),
        "source": manifest.get("source"),
        "blockers": [b["id"] if isinstance(b, dict) else b for b in blockers],
        "submission_ready": False,
    }


INVENTORY_TOTAL_FILES = len(INVENTORY_DELIVERABLES)


def validate_submission_inventory(inventory, blockers=None) -> list[str]:
    """제출물 인벤토리 보고가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(inventory, dict):
        return [f"submission inventory: inventory is not a dict: {inventory!r}"]
    required = ("deliverables", "missing", "total_files", "present_files", "total_bytes", "blockers", "submission_ready", "honesty")
    missing_keys = [k for k in required if k not in inventory]
    if missing_keys:
        problems.append(f"submission inventory: missing required keys: {missing_keys}")
        return problems
    if inventory["total_files"] != INVENTORY_TOTAL_FILES:
        problems.append(f"submission inventory: total_files={inventory['total_files']!r} != {INVENTORY_TOTAL_FILES}")
    deliverables = inventory["deliverables"]
    if not isinstance(deliverables, list):
        problems.append(f"submission inventory: deliverables is not a list: {deliverables!r}")
        deliverables = []
    if len(deliverables) != INVENTORY_TOTAL_FILES:
        problems.append(f"submission inventory: deliverables len={len(deliverables)} != {INVENTORY_TOTAL_FILES}")
    missing_expected = [e.get("path") for e in deliverables if isinstance(e, dict) and not e.get("exists")]
    if inventory["missing"] != missing_expected:
        problems.append(f"submission inventory: missing={inventory['missing']!r} != {missing_expected!r} from deliverables")
    if inventory["present_files"] != INVENTORY_TOTAL_FILES - len(missing_expected):
        problems.append(f"submission inventory: present_files={inventory['present_files']!r} != {INVENTORY_TOTAL_FILES - len(missing_expected)}")
    ids = _readiness_blocker_ids(inventory["blockers"], problems, "submission inventory") if isinstance(inventory["blockers"], (list, tuple)) else []
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if ids != expected_ids:
        problems.append(f"submission inventory: blocker ids {ids} != pre-submission blockers {expected_ids}")
    if inventory["submission_ready"] is not False:
        problems.append(f"submission inventory: submission_ready={inventory['submission_ready']!r} is not False")
    _check_honesty(inventory, problems, "submission inventory", "실제로 제출하지 않는다")
    _check_honesty(inventory, problems, "submission inventory", "Pi 실촬영 검증 전")
    _check_honesty(inventory, problems, "submission inventory", "데모 기준")
    return problems


def build_inventory_report(root, blockers=None) -> dict:
    """인벤토리에서 total/present/missing/total_bytes 보고 dict를 만든다."""
    if blockers is None:
        blockers = BLOCKERS
    try:
        inv = build_inventory(Path(root))
    except Exception:
        return {"total_files": 0, "present_files": 0, "missing": [], "total_bytes": 0, "blockers": [], "submission_ready": False}
    return {
        "total_files": inv.get("total_files", 0),
        "present_files": inv.get("present_files", 0),
        "missing": list(inv.get("missing") or []),
        "total_bytes": inv.get("total_bytes", 0),
        "blockers": [b["id"] if isinstance(b, dict) else b for b in (inv.get("blockers") or [])],
        "submission_ready": False,
    }


def validate_inventory_report(report, blockers=None) -> list[str]:
    """인벤토리 trimmed 보고 dict가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"submission inventory report is not a dict: {report!r}"]
    required = ("total_files", "present_files", "missing", "total_bytes", "blockers", "submission_ready")
    missing_keys = [k for k in required if k not in report]
    if missing_keys:
        problems.append(f"submission inventory: missing required keys: {missing_keys}")
        return problems
    if report["total_files"] != INVENTORY_TOTAL_FILES:
        problems.append(f"submission inventory: total_files={report['total_files']!r} != {INVENTORY_TOTAL_FILES}")
    missing = report["missing"]
    if not isinstance(missing, list):
        problems.append(f"submission inventory: missing is not a list: {missing!r}")
        missing = []
    if report["present_files"] != INVENTORY_TOTAL_FILES - len(missing):
        problems.append(f"submission inventory: present_files={report['present_files']!r} != {INVENTORY_TOTAL_FILES - len(missing)}")
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(f"submission inventory: blockers {list(report['blockers'])} != {expected_ids}")
    if report["submission_ready"] is not False:
        problems.append(f"submission inventory: submission_ready={report['submission_ready']!r} is not False")
    return problems


def _check_submission_inventory(root):
    name = "submission_inventory_consistent"
    try:
        inventory = build_inventory(Path(root))
    except Exception as exc:
        report = build_inventory_report(root)
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), report
    problems = validate_inventory(inventory, Path(root))
    problems.extend(validate_submission_inventory(inventory))
    report = build_inventory_report(root)
    problems.extend(validate_inventory_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"total_files={report['total_files']} "
        f"present_files={report['present_files']} "
        f"missing={report['missing']} "
        f"total_bytes={report['total_bytes']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def _check_fallback(root):
    name = "fallback_consistent"
    path = Path(root) / FALLBACK_REL
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        report = build_fallback_report(root)
        return PreSubmissionCheck(name, False, f"read failed: {exc!r}"), report
    problems = validate_fallback_manifest(manifest)
    report = build_fallback_report(root)
    problems.extend(validate_fallback_report(report))
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"cut_index={report['cut_index']} "
        f"capture_source={report['capture_source']} "
        f"source={report['source']} "
        f"is_pi_real_capture={report['is_pi_real_capture']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_fallback_decision(report, pi_report=None, blockers=None) -> list[str]:
    """폴백 결정 보고가 내부적으로, 그리고 Pi 준비 보고와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"fallback decision: report is not a dict: {report!r}"]
    required = (
        "date",
        "decision_date",
        "pi_ready",
        "pi_blockers",
        "status",
        "fallback_adopted",
        "fallback_asset",
        "fallback_render",
        "is_pi_real_capture",
        "honesty",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"fallback decision: missing required keys: {missing}")
        return problems
    if report["decision_date"] != FB_DECISION_DATE:
        problems.append(
            f"fallback decision: decision_date={report['decision_date']!r} != {FB_DECISION_DATE!r}"
        )
    if report["fallback_asset"] != FB_DECISION_ASSET:
        problems.append(
            f"fallback decision: fallback_asset={report['fallback_asset']!r} != {FB_DECISION_ASSET!r}"
        )
    if report["fallback_render"] != FB_DECISION_RENDER:
        problems.append(
            f"fallback decision: fallback_render={report['fallback_render']!r} != {FB_DECISION_RENDER!r}"
        )
    try:
        for problem in _validate_fb_decision(report):
            problems.append(f"fallback decision: {problem}")
    except Exception as exc:
        problems.append(f"fallback decision: validate_decision raised: {exc!r}")
    if isinstance(pi_report, dict):
        if "ready_for_real_capture" in pi_report:
            if bool(report["pi_ready"]) != bool(pi_report["ready_for_real_capture"]):
                problems.append(
                    f"fallback decision: pi_ready={report['pi_ready']!r} "
                    f"!= pi readiness ready_for_real_capture="
                    f"{pi_report['ready_for_real_capture']!r}"
                )
        if isinstance(pi_report.get("blockers"), (list, tuple)):
            pi_ids = _readiness_blocker_ids(
                pi_report["blockers"], problems, "pi readiness"
            )
            if list(report["pi_blockers"]) != pi_ids:
                problems.append(
                    f"fallback decision: pi_blockers {list(report['pi_blockers'])} != "
                    f"pi readiness blocker ids {pi_ids}"
                )
    if not bool(report["pi_ready"]) and (
        "pi_real_capture_pending" not in _pre_submission_blocker_ids(blockers)
    ):
        problems.append(
            "fallback decision: pi_ready is False but pre-submission "
            "blockers missing 'pi_real_capture_pending'"
        )
    return problems


def _check_fallback_decision(
    pi_probe=None, pi_device_confirmed=False, pi_which=None, pi_report=None
):
    name = "fallback_decision_consistent"
    try:
        report = _build_fb_decision(
            pi_probe=pi_probe, device_confirmed=pi_device_confirmed, which=pi_which
        )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_fallback_decision(report, pi_report=pi_report)
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"status={report['status']} "
        f"fallback_adopted={report['fallback_adopted']} "
        f"pi_ready={report['pi_ready']} "
        f"pi_blockers={report['pi_blockers']} "
        f"decision_date={report['decision_date']}"
    )
    return PreSubmissionCheck(name, True, detail), report

def validate_deadline_report(report, blockers=None) -> list[str]:
    """제출 마감 점검 보고가 내부적으로, 그리고 전수 블로커와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"deadline: report is not a dict: {report!r}"]
    required = (
        "now",
        "deadline_kst",
        "deadline_et",
        "status",
        "is_overdue",
        "remaining_seconds",
        "remaining_hours",
        "blockers",
        "submission_ready",
        "honesty",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"deadline: missing required keys: {missing}")
        return problems
    if report["deadline_kst"] != DL_KST_ISO:
        problems.append(
            f"deadline: deadline_kst={report['deadline_kst']!r} != {DL_KST_ISO!r}"
        )
    if report["deadline_et"] != DL_ET_TEXT:
        problems.append(
            f"deadline: deadline_et={report['deadline_et']!r} != {DL_ET_TEXT!r}"
        )
    expected_ids = [b["id"] for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"deadline: blockers {list(report['blockers'])} != "
            f"pre-submission blocker ids {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append("deadline: submission_ready is not False")
    try:
        for problem in _validate_dl(report):
            problems.append(f"deadline: {problem}")
    except Exception as exc:
        problems.append(f"deadline: validate_deadline raised: {exc!r}")
    return problems


def _check_deadline(deadline_now=None):
    name = "deadline_consistent"
    try:
        report = _build_dl(now=deadline_now)
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_deadline_report(report)
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"status={report['status']} "
        f"remaining_seconds={report['remaining_seconds']} "
        f"deadline_kst={report['deadline_kst']} "
        f"blockers={report['blockers']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def validate_final_package_report(report, blockers=None, inventory_report=None, deadline_report=None, decision_report=None) -> list[str]:
    """최종 묶음 보고가 내부적으로, 그리고 인벤토리·마감·폴백 결정 보고와 맞는지 검사한다."""
    if blockers is None:
        blockers = BLOCKERS
    problems: list[str] = []
    if not isinstance(report, dict):
        return [f"final package: report is not a dict: {report!r}"]
    required = (
        "inventory_present",
        "inventory_total",
        "inventory_missing",
        "deadline_status",
        "remaining_seconds",
        "fallback_status",
        "fallback_adopted",
        "blockers",
        "status",
        "submission_ready",
        "honesty",
    )
    missing = [key for key in required if key not in report]
    if missing:
        problems.append(f"final package: missing required keys: {missing}")
        return problems
    expected_ids = [b["id"] if isinstance(b, dict) else b for b in blockers]
    if list(report["blockers"]) != expected_ids:
        problems.append(
            f"final package: blockers {list(report['blockers'])} != "
            f"pre-submission blocker ids {expected_ids}"
        )
    if report["submission_ready"] is not False:
        problems.append("final package: submission_ready is not False")
    try:
        for problem in _validate_fp(report):
            problems.append(f"final package: {problem}")
    except Exception as exc:
        problems.append(f"final package: validate_final_package raised: {exc!r}")
    if isinstance(inventory_report, dict):
        if "total_files" in inventory_report and report["inventory_total"] != inventory_report["total_files"]:
            problems.append(
                f"final package: inventory_total={report['inventory_total']!r} != "
                f"submission inventory total_files={inventory_report['total_files']!r}"
            )
        if "present_files" in inventory_report and report["inventory_present"] != inventory_report["present_files"]:
            problems.append(
                f"final package: inventory_present={report['inventory_present']!r} != "
                f"submission inventory present_files={inventory_report['present_files']!r}"
            )
        if "missing" in inventory_report and list(report["inventory_missing"]) != list(inventory_report["missing"]):
            problems.append(
                f"final package: inventory_missing {list(report['inventory_missing'])} != "
                f"submission inventory missing {list(inventory_report['missing'])}"
            )
    if isinstance(deadline_report, dict):
        if "status" in deadline_report and report["deadline_status"] != deadline_report["status"]:
            problems.append(
                f"final package: deadline_status={report['deadline_status']!r} != "
                f"deadline status={deadline_report['status']!r}"
            )
        if "remaining_seconds" in deadline_report and report["remaining_seconds"] != deadline_report["remaining_seconds"]:
            problems.append(
                f"final package: remaining_seconds={report['remaining_seconds']!r} != "
                f"deadline remaining_seconds={deadline_report['remaining_seconds']!r}"
            )
    if isinstance(decision_report, dict):
        if "status" in decision_report and report["fallback_status"] != decision_report["status"]:
            problems.append(
                f"final package: fallback_status={report['fallback_status']!r} != "
                f"fallback decision status={decision_report['status']!r}"
            )
        if "fallback_adopted" in decision_report and bool(report["fallback_adopted"]) != bool(decision_report["fallback_adopted"]):
            problems.append(
                f"final package: fallback_adopted={report['fallback_adopted']!r} != "
                f"fallback decision fallback_adopted={decision_report['fallback_adopted']!r}"
            )
    _check_honesty(report, problems, "final package", "실제로 제출하지 않는다")
    _check_honesty(report, problems, "final package", "제출 완료를 뜻하지 않는다")
    _check_honesty(report, problems, "final package", "Pi 실촬영 검증 전")
    return problems


def _check_final_package(root, deadline_now=None, pi_probe=None, pi_device_confirmed=False, pi_which=None, inventory_report=None, deadline_report=None, decision_report=None):
    name = "final_package_consistent"
    try:
        report = _build_fp(
            root=Path(root),
            now=deadline_now,
            today=None,
            pi_probe=pi_probe,
            device_confirmed=pi_device_confirmed,
            which=pi_which,
        )
    except Exception as exc:
        return PreSubmissionCheck(name, False, f"raised: {exc!r}"), None
    problems = validate_final_package_report(
        report,
        inventory_report=inventory_report,
        deadline_report=deadline_report,
        decision_report=decision_report,
    )
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems)), report
    detail = (
        f"status={report['status']} "
        f"package_date_target={FP_PACKAGE_DATE_TARGET} "
        f"inventory_present={report['inventory_present']} "
        f"inventory_total={report['inventory_total']} "
        f"deadline_status={report['deadline_status']} "
        f"fallback_status={report['fallback_status']} "
        f"blockers={report['blockers']}"
    )
    return PreSubmissionCheck(name, True, detail), report


def run_pre_submission_checks(
    root: Path | None = None,
    sam_env=None,
    sam_credit_confirmed: bool = False,
    pi_probe=None,
    pi_device_confirmed: bool = False,
    pi_which=None,
    deadline_now=None,
) -> dict:
    """전수 점검을 실행한다. 개별 예외는 그 체크만 실패로 기록한다."""
    root = Path(root) if root is not None else ROOT
    checks: list[PreSubmissionCheck] = []

    try:
        checks.append(_aggregate("qa_harness", run_qa_checks()))
    except Exception as exc:
        checks.append(PreSubmissionCheck("qa_harness", False, f"raised: {exc!r}"))

    try:
        checks.append(_aggregate("standalone", run_standalone_checks(root)))
    except Exception as exc:
        checks.append(PreSubmissionCheck("standalone", False, f"raised: {exc!r}"))

    try:
        claims = audit_files(root)
        if not claims["violations"] and not claims["missing"]:
            checks.append(
                PreSubmissionCheck("claims_audit", True, f"{claims['checked_files']} files clean")
            )
        else:
            parts = [f"missing={claims['missing']}"] if claims["missing"] else []
            parts.extend(
                f"{v['file']}:{v['line']}: {v['text']}" for v in claims["violations"]
            )
            checks.append(PreSubmissionCheck("claims_audit", False, "; ".join(parts)))
    except Exception as exc:
        checks.append(PreSubmissionCheck("claims_audit", False, f"raised: {exc!r}"))

    sam_check, sam_report = _check_sam_readiness(
        sam_env=sam_env, sam_credit_confirmed=sam_credit_confirmed
    )
    checks.append(sam_check)

    pi_check, pi_report = _check_pi_readiness(
        pi_probe=pi_probe, pi_device_confirmed=pi_device_confirmed, pi_which=pi_which
    )
    checks.append(pi_check)

    console_check, console_report = _check_console_readiness(
        sam_env=sam_env,
        sam_credit_confirmed=sam_credit_confirmed,
        pi_probe=pi_probe,
        pi_device_confirmed=pi_device_confirmed,
        pi_which=pi_which,
        sam_report=sam_report,
        pi_report=pi_report,
    )
    checks.append(console_check)

    smoke_check, smoke_report = _check_sam_smoke(
        sam_env=sam_env,
        sam_credit_confirmed=sam_credit_confirmed,
        sam_report=sam_report,
    )
    checks.append(smoke_check)

    session_check, session_report = _check_sam_session(
        sam_env=sam_env,
        sam_credit_confirmed=sam_credit_confirmed,
        sam_report=sam_report,
    )
    checks.append(session_check)

    pi_smoke_check, pi_smoke_report = _check_pi_smoke(
        pi_probe=pi_probe,
        pi_device_confirmed=pi_device_confirmed,
        pi_which=pi_which,
        pi_report=pi_report,
    )
    checks.append(pi_smoke_check)

    pi_session_check, pi_session_report = _check_pi_session_full(
        pi_probe=pi_probe,
        pi_device_confirmed=pi_device_confirmed,
        pi_which=pi_which,
        pi_report=pi_report,
    )
    checks.append(pi_session_check)

    devpost_check, devpost_report = _check_devpost(root)
    checks.append(devpost_check)

    runbook_check, runbook_report = _check_runbook(root)
    checks.append(runbook_check)

    story_check, story_report = _check_story(root)
    checks.append(story_check)

    en_check, en_report = _check_en_summary(root)
    checks.append(en_check)

    demo_script_check, demo_script_report = _check_demo_script(root)
    checks.append(demo_script_check)

    readme_check, readme_report = _check_readme(root)
    checks.append(readme_check)

    fallback_check, fallback_report = _check_fallback(root)
    checks.append(fallback_check)

    inventory_check, inventory_report = _check_submission_inventory(root)
    checks.append(inventory_check)

    decision_check, decision_report = _check_fallback_decision(
        pi_probe=pi_probe,
        pi_device_confirmed=pi_device_confirmed,
        pi_which=pi_which,
        pi_report=pi_report,
    )
    checks.append(decision_check)

    deadline_check, deadline_report = _check_deadline(deadline_now=deadline_now)
    checks.append(deadline_check)

    fp_check, fp_report = _check_final_package(
        root,
        deadline_now=deadline_now,
        pi_probe=pi_probe,
        pi_device_confirmed=pi_device_confirmed,
        pi_which=pi_which,
        inventory_report=inventory_report,
        deadline_report=deadline_report,
        decision_report=decision_report,
    )
    checks.append(fp_check)

    missing = [rel for rel in DEMO_ASSET_FILES if not (root / rel).is_file()]
    checks.append(
        PreSubmissionCheck(
            "demo_assets_present",
            not missing,
            f"missing={missing}" if missing else f"{len(DEMO_ASSET_FILES)} assets present",
        )
    )

    checks.append(_check_demo_consistency(root))

    checks.append(_check_video_draft(root))

    passed = sum(1 for c in checks if c.passed)
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "mechanical_pass": passed == len(checks),
        "blockers": [dict(b) for b in BLOCKERS],
        "readiness": {
            "sam": sam_report,
            "pi": pi_report,
            "console": console_report,
            "smoke": smoke_report,
            "sam_session": session_report,
            "pi_smoke": pi_smoke_report,
            "pi_session": pi_session_report,
            "devpost": devpost_report,
            "runbook": runbook_report,
            "story": story_report,
            "en_summary": en_report,
            "demo_script": demo_script_report,
            "readme": readme_report,
            "fallback": fallback_report,
            "submission_inventory": inventory_report,
            "fallback_decision": decision_report,
            "deadline": deadline_report,
            "final_package": fp_report,
        },
        # 블로커가 남아 있는 한 기계적 통과와 무관하게 항상 False다.
        "submission_ready": False,
    }


def build_report(
    root: Path | None = None,
    sam_env=None,
    sam_credit_confirmed: bool = False,
    pi_probe=None,
    pi_device_confirmed: bool = False,
    pi_which=None,
    deadline_now=None,
) -> dict:
    """run_pre_submission_checks 결과를 JSON 직렬화 가능한 dict로 바꾼다."""
    result = run_pre_submission_checks(
        root,
        sam_env=sam_env,
        sam_credit_confirmed=sam_credit_confirmed,
        pi_probe=pi_probe,
        pi_device_confirmed=pi_device_confirmed,
        pi_which=pi_which,
        deadline_now=deadline_now,
    )
    return {
        "checks": [
            {"name": c.name, "passed": c.passed, "detail": c.detail} for c in result["checks"]
        ],
        "passed": result["passed"],
        "total": result["total"],
        "mechanical_pass": result["mechanical_pass"],
        "blockers": result["blockers"],
        "readiness": result["readiness"],
        "submission_ready": result["submission_ready"],
        "honesty": list(HONESTY),
    }


def format_text_report(report: dict) -> str:
    lines: list[str] = []
    for check in report["checks"]:
        mark = "PASS" if check["passed"] else "FAIL"
        lines.append(f"[{mark}] {check['name']} — {check['detail']}")
    lines.append(
        f"PRE_SUBMISSION: {report['passed']}/{report['total']} mechanical passed"
    )
    lines.append(f"BLOCKERS: {len(report['blockers'])}")
    for blocker in report["blockers"]:
        lines.append(f"- {blocker['id']}: {blocker['detail']}")
    lines.append("SUBMISSION_READY: false")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = list(argv) if argv is not None else []
    report = build_report()
    if "--json" in argv:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(format_text_report(report))
    return 0 if report["mechanical_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
