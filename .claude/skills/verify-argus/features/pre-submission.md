# 제출 전 전수 점검

제출 전 전수 점검은 기존 기계적 점검 9종을 한 번에 구동하는 CLI다. 기계적 점검이 전부 통과해도 제출 블로커 2건이 남아 `submission_ready`는 항상 false이며, 기계적 통과를 제출 가능으로 서술하지 않는다.

## Sub-features

- `pre-run` 기본 실행: `python3 -m qa.pre_submission`으로 기계적 점검 9종을 한 번에 구동해 텍스트 보고를 얻는다.
- `pre-json` `--json` 보고: 같은 점검을 JSON으로 얻어 passed·total·mechanical_pass·checks를 확인한다.
- `pre-blockers` 블로커 2건 분리 보고: `pi_real_capture_pending`과 `sam_real_call_pending`을 종료코드와 별도 목록으로 보고한다.
- `pre-not-ready` submission_ready false 확인: 기계적 통과와 무관하게 `submission_ready`가 false인지 확인한다.
- `pre-honesty` honesty 표기: `honesty`에 '모의'를 포함한 줄과 '데모 기준'을 포함한 줄이 있는지 확인한다.
- `pre-readiness` 준비 점검 정합: SAM 실호출 준비 점검과 Pi 실촬영 준비 점검의 보고가 내부적으로 모순되지 않고 전수 점검 블로커 2건과 어긋나지 않는지 확인하며, JSON의 `readiness` 섹션에 두 준비 점검의 블로커가 그대로 기록된다. 준비가 안 된 상태 자체는 기계 점검 실패가 아니다.
- `pre-console-readiness` 콘솔 준비 상태 정합: 콘솔 준비 상태(`console.readiness`)가 같은 조건의 SAM·Pi 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.console`에 blocker_count와 overall_ready가 그대로 기록된다. 콘솔 패널이 준비 점검과 어긋나면 기계 점검 실패다.
- `pre-video-panel` 영상 데이터 패널 정합: `video_draft_present` 체크가 MP4 크기에 더해 컷 1~9 데이터 패널(컷 5 전체 빈 6줄·컷 6 불일치 2줄·컷 3 플레이스홀더 정직 표기·컷 9 '데모 기준')이 현재 시뮬레이션 리포트와 맞는지 확인하고, 통과 detail에 `data_panel_cuts=9`가 포함된다.

## How to get to it (user POV)

- 터미널에서 프로젝트 루트로 이동해 전수 점검 모듈을 실행한다: `python3 -m qa.pre_submission`.
- 기계 판독용 보고가 필요하면 `--json`을 붙여 실행한다: `python3 -m qa.pre_submission --json`.
- 검증 헬퍼로 구동하려면 `--feature pre-submission`을 준다. 헬퍼가 텍스트 실행과 `--json` 실행을 모두 구동하고 증거를 남긴다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다. SAM 실호출은 이 기능의 범위가 아니며, 헬퍼의 자식 환경에서도 제거된다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pre-submission --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼가 `python3 -m qa.pre_submission`을 CLI 서브프로세스로 구동한다. 종료코드 0이고, stdout에 `PRE_SUBMISSION: 9/9 mechanical passed`, `BLOCKERS: 2`, `SUBMISSION_READY: false`와 블로커 id `pi_real_capture_pending`·`sam_real_call_pending`이 각각 포함되는지, 두 실행의 종료코드를 증거 transcript에 남기는지 확인한다.
- **직접 CLI 확인.** 프로젝트 루트에서 `python3 -m qa.pre_submission`과 `python3 -m qa.pre_submission --json`을 직접 실행해도 같은 수치를 확인한다.
- **JSON 수치 확인.** `--json` 출력에서 passed 9, total 9, 즉 9/9인지, `mechanical_pass`가 true인지, checks가 9개이고 전부 passed true인지 확인한다.
- **준비 점검 확인.** JSON `readiness.sam.blockers`가 `sam_credit_not_confirmed`·`sam_base_url_missing`·`sam_api_key_missing` 3종 순서 그대로이고 `readiness.pi.blockers`가 `pi_device_arrival_not_confirmed`·`pi_camera_command_missing` 2종 순서 그대로이며, 두 ready 플래그가 모두 false인지 확인한다. 증거 summary에도 `readiness_sam_blockers`·`readiness_pi_blockers`로 남는다.
- **콘솔 준비 상태 확인.** JSON `readiness.console`의 sam_blockers·pi_blockers가 위 두 목록과 각각 같고, blocker_count가 5, overall_ready가 false인지 확인한다. 증거 summary에도 `readiness_console_blocker_count`·`readiness_console_overall_ready`로 남는다.
- **블로커 확인.** blockers의 id 목록이 `pi_real_capture_pending`·`sam_real_call_pending` 순서 그대로 2건(BLOCKERS: 2)인지 확인한다.
- **제출 가능 아님 확인.** `submission_ready`가 false(SUBMISSION_READY: false)인지 확인한다. true이면 심각한 문제다.
- **표기 확인.** `honesty`에 '모의'를 포함한 줄과 '데모 기준'을 포함한 줄이 있는지 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pre-submission-stdout.txt`(텍스트 stdout), `pre-submission.json`(JSON stdout), `summary.json`, `transcript.txt`가 남았는지 확인한다.

## Gotchas

- 기계적 통과를 제출 가능으로 오인하지 않는다. `mechanical_pass`가 true여도 `submission_ready`는 false이며, 이를 제출 가능으로 서술하면 검증이 무효다.
- 블로커는 종료코드에 반영되지 않는다. 종료코드 0은 기계적 점검 9종 통과만을 뜻하므로, 블로커 2건은 텍스트의 `BLOCKERS: 2`와 JSON blockers 목록으로 따로 확인한다.
- SAM 실호출과 Pi 실촬영은 아직 하지 않은 일이다. 이 기능은 모의 어댑터 기준 기계적 점검만 구동하며, 실호출·실촬영을 수행하거나 수행한 것으로 서술하지 않는다.
