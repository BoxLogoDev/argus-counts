# 제출 전 전수 점검

제출 전 전수 점검은 기존 기계적 점검 17종을 한 번에 구동하는 CLI다. 기계적 점검이 전부 통과해도 제출 블로커 2건이 남아 `submission_ready`는 항상 false이며, 기계적 통과를 제출 가능으로 서술하지 않는다.

## Sub-features

- `pre-run` 기본 실행: `python3 -m qa.pre_submission`으로 기계적 점검 17종을 한 번에 구동해 텍스트 보고를 얻는다.
- `pre-json` `--json` 보고: 같은 점검을 JSON으로 얻어 passed·total·mechanical_pass·checks를 확인한다.
- `pre-blockers` 블로커 2건 분리 보고: `pi_real_capture_pending`과 `sam_real_call_pending`을 종료코드와 별도 목록으로 보고한다.
- `pre-not-ready` submission_ready false 확인: 기계적 통과와 무관하게 `submission_ready`가 false인지 확인한다.
- `pre-honesty` honesty 표기: `honesty`에 '모의'를 포함한 줄과 '데모 기준'을 포함한 줄이 있는지 확인한다.
- `pre-readiness` 준비 점검 정합: SAM 실호출 준비 점검과 Pi 실촬영 준비 점검의 보고가 내부적으로 모순되지 않고 전수 점검 블로커 2건과 어긋나지 않는지 확인하며, JSON의 `readiness` 섹션에 두 준비 점검의 블로커가 그대로 기록된다. 준비가 안 된 상태 자체는 기계 점검 실패가 아니다.
- `pre-console-readiness` 콘솔 준비 상태 정합: 콘솔 준비 상태(`console.readiness`)가 같은 조건의 SAM·Pi 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.console`에 blocker_count와 overall_ready가 그대로 기록된다. 콘솔 패널이 준비 점검과 어긋나면 기계 점검 실패다.
- `pre-sam-smoke` SAM 스모크 정합: SAM 단일 빈 스모크(`qa.sam_smoke`) 보고가 SAM 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.smoke`에 status와 블로커가 그대로 기록된다. 스모크 정합은 전수 점검 전용 가짜 counter로만 구동하며 실제 API를 호출하지 않는다. 준비가 안 된 상태에서는 스모크가 blocked이고 가짜 counter 호출이 0건이어야 한다.
- `pre-devpost` 제출 문안 정합: 제출 문안 패키지(`docs/devpost-submission.md`) 원문의 절 11개 순서·블로커 2건·`SUBMISSION_READY: false`·데모 기준 수치가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.devpost`에 section_count와 블로커가 그대로 기록된다. 문안 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-readme` README 정합: README(`README.md`) 원문의 절 5개 순서·블로커 2건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.readme`에 section_count와 블로커가 그대로 기록된다. README 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-demo-script` 데모 대본 정합: 데모 대본(`docs/demo-script.md`) 원문의 절 3개 순서·블로커 2건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.demo_script`에 section_count와 블로커가 그대로 기록된다. 데모 대본 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-en-summary` 영문 제출 요약 정합: 영문 제출 요약(`docs/submission-summary-en.md`) 원문의 절 8개 순서·블로커 2건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.en_summary`에 section_count와 블로커가 그대로 기록된다. 영문 요약 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-story` 제출 스토리 정합: 제출 스토리(`docs/submission-story.md`) 원문의 절 7개 순서·블로커 2건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.story`에 section_count와 블로커가 그대로 기록된다. 스토리 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-runbook` 제출 런북 정합: 제출 런북(`docs/submission-runbook.md`) 원문의 절 7개 순서·블로커 2건·`SUBMISSION_READY: false`·최종 점검 명령 8종이 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.runbook`에 section_count와 블로커·final_command_count가 그대로 기록된다. 런북 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-pi-smoke` Pi 스모크 정합: Pi 단일 빈 스모크(`qa.pi_smoke`) 보고가 Pi 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.pi_smoke`에 status와 블로커가 그대로 기록된다. 스모크 정합은 전수 점검 전용 가짜 session으로만 구동하며 실제 촬영을 하지 않는다. 준비가 안 된 상태에서는 스모크가 blocked이고 가짜 session 호출이 0건이어야 한다.
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

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pre-submission --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼가 `python3 -m qa.pre_submission`을 CLI 서브프로세스로 구동한다. 종료코드 0이고, stdout에 `PRE_SUBMISSION: 17/17 mechanical passed`, `BLOCKERS: 2`, `SUBMISSION_READY: false`와 블로커 id `pi_real_capture_pending`·`sam_real_call_pending`이 각각 포함되는지, 두 실행의 종료코드를 증거 transcript에 남기는지 확인한다.
- **직접 CLI 확인.** 프로젝트 루트에서 `python3 -m qa.pre_submission`과 `python3 -m qa.pre_submission --json`을 직접 실행해도 같은 수치를 확인한다.
- **JSON 수치 확인.** `--json` 출력에서 passed 17, total 17, 즉 17/17인지, `mechanical_pass`가 true인지, checks가 17개이고 전부 passed true인지 확인한다.
- **준비 점검 확인.** JSON `readiness.sam.blockers`가 `sam_credit_not_confirmed`·`sam_base_url_missing`·`sam_api_key_missing` 3종 순서 그대로이고 `readiness.pi.blockers`가 `pi_device_arrival_not_confirmed`·`pi_camera_command_missing` 2종 순서 그대로이며, 두 ready 플래그가 모두 false인지 확인한다. 증거 summary에도 `readiness_sam_blockers`·`readiness_pi_blockers`로 남는다.
- **콘솔 준비 상태 확인.** JSON `readiness.console`의 sam_blockers·pi_blockers가 위 두 목록과 각각 같고, blocker_count가 5, overall_ready가 false인지 확인한다. 증거 summary에도 `readiness_console_blocker_count`·`readiness_console_overall_ready`로 남는다.
- **제출 문안 확인.** JSON `readiness.devpost`의 section_count가 11, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_devpost_section_count`·`readiness_devpost_blockers`로 남는다. 문안 정합은 원문 대조만이며 실제 제출이 아니다.
- **README 확인.** JSON `readiness.readme`의 section_count가 5, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_readme_section_count`·`readiness_readme_blockers`로 남는다. README 정합은 원문 대조만이며 실제 제출이 아니다.
- **데모 대본 확인.** JSON `readiness.demo_script`의 section_count가 3, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_demo_script_section_count`·`readiness_demo_script_blockers`로 남는다. 데모 대본 정합은 원문 대조만이며 실제 제출이 아니다.
- **영문 제출 요약 확인.** JSON `readiness.en_summary`의 section_count가 8, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_en_summary_section_count`·`readiness_en_summary_blockers`로 남는다. 영문 요약 정합은 원문 대조만이며 실제 제출이 아니다.
- **제출 스토리 확인.** JSON `readiness.story`의 section_count가 7, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_story_section_count`·`readiness_story_blockers`로 남는다. 스토리 정합은 원문 대조만이며 실제 제출이 아니다.
- **제출 런북 확인.** JSON `readiness.runbook`의 section_count가 7, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true, final_command_count가 8인지 확인한다. 증거 summary에도 `readiness_runbook_section_count`·`readiness_runbook_blockers`로 남는다. 런북 정합은 원문 대조만이며 실제 제출이 아니다.
- **Pi 스모크 확인.** JSON `readiness.pi_smoke`의 status가 blocked, attempted가 false, blockers가 Pi 준비 점검 블로커 2종과 같은지 확인한다. 증거 summary에도 `readiness_pi_smoke_status`·`readiness_pi_smoke_blockers`로 남는다. 스모크 정합은 가짜 session으로만 구동하므로 실제 촬영이 아니다.
- **SAM 스모크 확인.** JSON `readiness.smoke`의 status가 blocked, attempted가 false, blockers가 SAM 준비 점검 블로커 3종과 같은지 확인한다. 증거 summary에도 `readiness_smoke_status`·`readiness_smoke_blockers`로 남는다. 스모크 정합은 가짜 counter로만 구동하므로 실제 API 호출이 아니다.
- **블로커 확인.** blockers의 id 목록이 `pi_real_capture_pending`·`sam_real_call_pending` 순서 그대로 2건(BLOCKERS: 2)인지 확인한다.
- **제출 가능 아님 확인.** `submission_ready`가 false(SUBMISSION_READY: false)인지 확인한다. true이면 심각한 문제다.
- **표기 확인.** `honesty`에 '모의'를 포함한 줄과 '데모 기준'을 포함한 줄이 있는지 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pre-submission-stdout.txt`(텍스트 stdout), `pre-submission.json`(JSON stdout), `summary.json`, `transcript.txt`가 남았는지 확인한다.

## Gotchas

- 기계적 통과를 제출 가능으로 오인하지 않는다. `mechanical_pass`가 true여도 `submission_ready`는 false이며, 이를 제출 가능으로 서술하면 검증이 무효다.
- 블로커는 종료코드에 반영되지 않는다. 종료코드 0은 기계적 점검 17종 통과만을 뜻하므로, 블로커 2건은 텍스트의 `BLOCKERS: 2`와 JSON blockers 목록으로 따로 확인한다.
- SAM 실호출과 Pi 실촬영은 아직 하지 않은 일이다. 이 기능은 모의 어댑터 기준 기계적 점검만 구동하며, 실호출·실촬영을 수행하거나 수행한 것으로 서술하지 않는다.
