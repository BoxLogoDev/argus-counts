"""제출 전 전수 점검 하네스.

기존 점검들(QA 기준값 대조, standalone 점검, 현재형 주장 감사)과
SAM 실호출 준비 점검·Pi 실촬영 준비 점검의 상태 정합,
콘솔 준비 상태(console.readiness)가 같은 조건의 두 준비 점검과
어긋나지 않는지의 정합, SAM 단일 빈 스모크(qa.sam_smoke) 보고가
SAM 준비 점검 보고와 어긋나지 않는지의 정합, 데모 자산의
존재·정합을 한 번에 묶어 기계적으로 확인한다.
기계 점검은 총 10종이다.
스모크 정합은 가짜 counter로만 구동하며 실제 API를 호출하지 않는다.
준비 점검 자체는 실호출·실촬영을 하지 않으며, 준비가 안 된
상태(블로커 존재)는 기계 점검 실패가 아니다. 실패는 준비
점검 보고가 내부적으로 모순되거나 전수 점검 블로커와
어긋나는 경우뿐이다.
video 체크는 MP4 크기와 함께 컷 1~9 데이터 패널 정합도 확인한다.
기계적 체크가 전부 통과해도 제출 블로커가 남아 있으면 제출 가능
상태가 아니다. 블로커는 종료코드가 아니라 별도 목록으로 보고한다:
Pi 실촬영 검증과 SAM 3.1 실호출은 아직 하지 않은 일이다.

실행: 프로젝트 루트에서 `python3 -m qa.pre_submission`
`--json`을 주면 같은 내용을 JSON으로 출력하며 readiness 섹션을 포함한다.
기계적 체크가 전부 통과하면 종료코드 0, 하나라도 실패하면 1.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from console.readiness import build_readiness as build_console_readiness
from qa.claims_audit import audit_files
from qa.harness import run_checks as run_qa_checks
from qa.pi_readiness import check_readiness as check_pi_readiness
from qa.sam_readiness import check_readiness as check_sam_readiness
from qa.sam_smoke import run_smoke
from qa.standalone import run_standalone_checks

ROOT = Path(__file__).resolve().parent.parent

# 현재 사실인 제출 블로커. 코드가 임의로 해소 판정하지 않고 항상 보고한다.
BLOCKERS = [
    {
        "id": "pi_real_capture_pending",
        "detail": "Pi 실촬영 검증 전 — 데모 컷 3은 플레이스홀더이며 Pi 도착 후 교체해야 한다",
    },
    {
        "id": "sam_real_call_pending",
        "detail": "SAM 3.1 실호출 미실시 — 현재 모의(mock) 어댑터이며 크레딧 입금 확인과 API 키 발급 후 전환해야 한다",
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


@dataclass(frozen=True)
class PreSubmissionCheck:
    name: str
    passed: bool
    detail: str


def _aggregate(name: str, checks) -> PreSubmissionCheck:
    total = len(checks)
    passed = sum(1 for c in checks if c.passed)
    return PreSubmissionCheck(name, passed == total, f"{passed}/{total} passed")


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
    if problems:
        return PreSubmissionCheck(name, False, "; ".join(problems))
    return PreSubmissionCheck(name, True, "shot/assembly/narration/manifest consistent at 180s, 9 cuts")


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
    return PreSubmissionCheck(name, True, f"bytes={size}, data_panel_cuts=9")


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
    if not ready and "sam_real_call_pending" not in _pre_submission_blocker_ids(blockers):
        problems.append(
            "sam readiness: ready_for_live_call is False but pre-submission "
            "blockers missing 'sam_real_call_pending'"
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
        if "sam_real_call_pending" not in _pre_submission_blocker_ids(blockers):
            problems.append(
                "sam smoke: ready_for_live_call is False but pre-submission "
                "blockers missing 'sam_real_call_pending'"
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
        report = run_smoke(
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


def run_pre_submission_checks(
    root: Path | None = None,
    sam_env=None,
    sam_credit_confirmed: bool = False,
    pi_probe=None,
    pi_device_confirmed: bool = False,
    pi_which=None,
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
) -> dict:
    """run_pre_submission_checks 결과를 JSON 직렬화 가능한 dict로 바꾼다."""
    result = run_pre_submission_checks(
        root,
        sam_env=sam_env,
        sam_credit_confirmed=sam_credit_confirmed,
        pi_probe=pi_probe,
        pi_device_confirmed=pi_device_confirmed,
        pi_which=pi_which,
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
