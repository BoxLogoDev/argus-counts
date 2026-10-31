# 데모 영상 제출 후보 선택

데모 영상 제출 후보 선택은 `qa.video_selection`의 `evaluate_selection`·`build_selection`·`validate_selection`이 폴백 결정(`qa.fallback_decision`, 결정일 2026-11-02)을 재사용해 패키징 시점에 어떤 기존 MP4를 제출 후보로 고르는지 확인하는 절차다. 판정은 pending이면 기본 영상을 기본 후보로, fallback_due면 폴백 렌더를, pi_ready면 기본 영상을 고르며, 고른 파일의 존재와 크기를 대조한다. 이 검증은 실제로 제출하지 않는다: 선택은 제출 준비 완료를 뜻하지 않는다. 폴백 영상은 Pi 실촬영이 아닙니다. Pi 준비 완료만으로 기본 영상이 실촬영본이 되지는 않는다 — Pi가 준비되면 컷 3 실촬영 교체와 재렌더가 별도로 필요하다. 드라이버는 `drive_video_selection`이며 증거로 `video-selection-pending.json`과 `video-selection-due.json`을 남긴다.

## Sub-features

- `video-selection-pending` 결정일 전 기본 후보: 날짜 2026-11-01, Pi 미준비이면 `fallback_status`가 pending, `SELECTED_VIDEO`가 기본 영상(`demo/assets/argus-demo-draft.mp4`), `SELECTION_REASON`이 pending_default, `SUBMISSION_READY: false`임을 확인한다.
- `video-selection-fallback-due` 폴백 채택 시 폴백 렌더: 날짜 2026-11-02, Pi 미준비이면 fallback_due, 폴백 영상(`demo/assets/argus-demo-fallback-draft.mp4`) 선택, `fallback_adopted` true를 확인한다.
- `video-selection-pi-ready` Pi 준비 시 기본 영상: pi_ready이면 기본 영상을 고르고 폴백을 채택하지 않음을 확인한다. Pi 준비 완료만으로 기본 영상이 실촬영본이 되지는 않는다.
- `video-selection-missing-tamper` 누락·변조 탐지: 고른 영상의 크기가 없거나 0이면 문제를 내고, `selected_video`·`submission_ready`·`fallback_status`·honesty 변조를 `validate_selection`이 탐지함을 확인한다.
- `video-selection-cli-invalid` CLI 잘못된 날짜 차단: 잘못된 날짜는 종료코드 2이며 유효한 선택으로 처리하지 않음을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.video_selection [--date YYYY-MM-DD] [--device-confirmed] [--json]`를 실행한다. 종료코드는 보고가 유효하면 0, 무효면 2다.
- 이 하네스는 실제로 제출하지 않고 영상을 새로 만들지도 않는다. 기존 두 MP4의 크기만 읽는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature video-selection --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 오늘(결정일 전)의 실제 판정은 pending이라 기본 영상이 기본 후보일 뿐이며, 이를 제출 확정이나 제출 준비 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 제출하지 않는다. 네트워크와 실제 키를 쓰지 않는다.
- 합성 크기는 헬퍼 상수 `VIDEO_SELECTION_PRIMARY_SIZE`·`VIDEO_SELECTION_FALLBACK_SIZE`로만 만들며 실제 제출 파일이 아니다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature video-selection --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `drive_video_selection`으로 CLI 서브프로세스와 프로세스 내 선택 함수만 실행한다.
- **pending 확인.** 헬퍼가 `--date 2026-11-01` 텍스트·`--json` 구동으로 pending·기본 영상·pending_default·`SUBMISSION_READY: false`·Pi 블로커 2건을 대조한다.
- **fallback_due 확인.** 헬퍼가 `--date 2026-11-02 --json` 가정 날짜 구동으로 fallback_due·폴백 렌더 선택·`fallback_adopted` true를 확인한다.
- **pi_ready·build 확인.** 헬퍼가 `evaluate_selection`의 pi_ready 판정과 `build_selection`의 missing probe(pending)·ready probe(pi_ready, 실제 파일 크기 0 초과)를 대조한다.
- **누락·변조 확인.** 헬퍼가 고른 영상 크기 없음 탐지와 `selected_video`·`submission_ready`·`fallback_status`·honesty 변조 탐지를 확인하고, 잘못된 날짜 CLI 종료코드 2를 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `video-selection-pending.json`(pending CLI `--json` stdout 원문)과 `video-selection-due.json`(due CLI `--json` stdout 원문)이 남고, `summary.json`의 `feature`가 `video-selection`이며 `pending_status`가 pending, `due_status`가 fallback_due, `tamper_detected`와 `missing_detected`가 true, `invalid_exit_code`가 2인지 대조한다.

## Gotchas

- pending에서 기본 영상이 기본 후보라는 것은 제출 확정도, 제출 준비 완료도 아니다. 실제로 제출하지 않는다.
- 폴백 영상은 Pi 실촬영이 아닙니다. 폴백 렌더를 Pi 실촬영본처럼 서술하면 실패다.
- Pi 준비 완료만으로 기본 영상이 실촬영본이 되지는 않는다. Pi가 준비되면 컷 3 실촬영 교체와 재렌더가 별도로 필요하다.
- 고른 파일이 없거나 크기가 0이면 선택은 유효하지 않다. 크기를 지어내면 실패다.
- 잘못된 날짜를 유효로 처리하면 실패다. 종료코드 2를 0으로 바꾸지 않는다.
