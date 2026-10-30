# 제출 마감 점검

제출 마감 점검은 `qa.deadline`이 제출 마감 2026-11-05T11:00:00+09:00(2026-11-04 21:00 ET)를 기준으로 제공된 기준 시각과의 차이로 before_deadline·due_soon·overdue를 판정하는지 검증하는 절차다. 이 검증은 실제로 제출하지 않는다: CLI에 기준 시각을 명시해 구동하고 프로세스 내 `evaluate_deadline`·`build_deadline`·`validate_deadline`으로만 확인한다. 마감 전이어도 제출 준비 완료를 뜻하지 않으며, 남은 시간은 제공된 기준 시각으로만 계산하고 지각 제출은 고려되지 않는다.

## Sub-features

- `deadline-cli-before` CLI 마감 전 판정: `python3 -m qa.deadline --now 2026-10-31T01:50:00+09:00`가 종료코드 0을 내고, 텍스트에 `STATUS: before_deadline`·`DEADLINE_KST: 2026-11-05T11:00:00+09:00`·`REMAINING_SECONDS: 465000`·`SUBMISSION_READY: false`가 있으며, `--json`에서는 status before_deadline·remaining_seconds 465000·is_overdue false·blockers [`pi_real_capture_pending`]·submission_ready false·honesty 3종(실제로 제출하지 않는다, 제출 준비 완료를 뜻하지 않는다, 지각 제출은 고려되지 않는다)임을 확인한다.
- `deadline-cli-due-soon` CLI 임박 판정: `python3 -m qa.deadline --now 2026-11-04T12:00:00+09:00 --json`이 status due_soon·remaining_seconds 82800을 냄을 확인한다.
- `deadline-cli-overdue` CLI 마감 도달 판정: `python3 -m qa.deadline --now 2026-11-05T11:00:00+09:00 --json`이 종료코드 1을 내고 status overdue·remaining_seconds 0·is_overdue true임을 확인한다.
- `deadline-evaluate` 프로세스 내 판정식: `evaluate_deadline`과 `build_deadline`이 마감 전·임박·마감 도달 3상태를 내고, 세 보고 모두 `validate_deadline`에서 문제 0건임을 확인한다. 구동 함수는 `drive_deadline`다.
- `deadline-tamper` 변조 탐지: status를 바꾸면 status 문제를, remaining_seconds를 바꾸면 remaining_seconds 문제를, submission_ready를 true로 바꾸면 submission_ready 문제를 `validate_deadline`이 각각 지목함을 확인한다.
- `deadline-invalid-now` 잘못된 시각 차단: `python3 -m qa.deadline --now not-a-date`가 종료코드 2로 거부됨을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.deadline`을 실행한다. 기준 시각을 고정하려면 `--now ISO8601`을, 기계가 읽을 출력이 필요하면 `--json`을 붙인다. 종료코드는 마감이 지나지 않았으면 0, 지났으면 1, 입력이 유효하지 않으면 2다.
- 이 CLI는 실제로 제출하지 않으며, 마감 전이어도 제출 준비 완료를 뜻하지 않는다. 남은 시간은 제공된 기준 시각으로만 계산한다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature deadline --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 제출 경로는 이 절차의 범위가 아니다. 이 절차의 통과를 제출 완료나 제출 준비 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 제출하지 않는다. 네트워크 호출도 하지 않으며, 기준 시각은 CLI 인자로만 고정한다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature deadline --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 CLI 서브프로세스와 프로세스 내 `evaluate_deadline`·`build_deadline`·`validate_deadline`만으로 `drive_deadline`을 실행한다.
- **CLI 3상태 확인.** 헬퍼가 `qa.deadline` CLI를 `--now 2026-10-31T01:50:00+09:00` 텍스트·JSON, `--now 2026-11-04T12:00:00+09:00 --json`, `--now 2026-11-05T11:00:00+09:00 --json`으로 실행해 종료코드와 before_deadline·due_soon·overdue 판정, 남은 초, 블로커, honesty 표기를 확인한다.
- **프로세스 내 판정 확인.** 헬퍼가 `evaluate_deadline` 3상태와 `build_deadline` 마감 전 판정, `validate_deadline` 문제 0건을 확인한다.
- **변조·잘못된 시각 확인.** 헬퍼가 status·remaining_seconds·submission_ready 변조 탐지와 잘못된 시각 종료코드 2를 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `deadline-before.json`(CLI 마감 전 `--json` stdout 원문)과 `deadline-overdue.json`(CLI 마감 도달 `--json` stdout 원문)이 남고, `summary.json`의 `feature`가 `deadline`이며 `before_status` before_deadline·`before_remaining_seconds` 465000·`due_soon_status` due_soon·`overdue_status` overdue·`tamper_detected` true·`invalid_exit_code` 2인지 대조한다.

## Gotchas

- 마감 전이어도 제출 준비 완료를 뜻하지 않는다. before_deadline은 남은 시간 판정일 뿐이며 submission_ready는 항상 false다.
- 지각 제출은 고려되지 않는다. 마감 시각에 도달하면 remaining_seconds 0으로 overdue다.
- 남은 시간은 제공된 기준 시각으로만 계산한다. 기준 시각을 고정하지 않은 구동을 결정적 증거로 쓰지 않는다.
- tz가 없는 입력은 KST로 해석된다. 다른 시간대와 섞어 남은 시간을 계산하면 오판한다.
- status와 remaining_seconds는 서로 맞아야 한다. 하나만 바꾸면 변조로 지목돼야 한다.
