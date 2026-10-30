# Pi 폴백 결정

Pi 폴백 결정은 `qa.fallback_decision`이 결정일 2026-11-02를 기준으로 Pi 준비 상태를 판정해 pending·fallback_due·pi_ready 중 하나로 보고하는지 검증하는 절차다. 이 검증은 실제 촬영을 하지 않는다: CLI에 날짜를 명시해 구동하고 프로세스 내 `evaluate_decision`·`build_decision`·`validate_decision`으로만 확인한다. 파일 입력 폴백은 Pi 실촬영이 아닙니다. 폴백 채택은 Pi 실촬영 검증 완료를 뜻하지 않으며, 결정일 전에는 폴백을 확정하지 않는다. 결정일 가정 날짜 구동에서 fallback_due가 나와도 오늘 실제 전환 확정으로 서술하지 않는다.

## Sub-features

- `fallback-decision-cli-pending` CLI 결정일 전 판정: `python3 -m qa.fallback_decision --date 2026-10-30`가 종료코드 0을 내고, 텍스트에 `STATUS: pending`·`DECISION_DATE: 2026-11-02`·`FALLBACK_ADOPTED: false`·'Pi 실촬영이 아닙니다'가 있으며, `--json`에서는 status pending·fallback_adopted false·pi_ready false·pi_blockers [`pi_device_arrival_not_confirmed`, `pi_camera_command_missing`]·is_pi_real_capture false·honesty 3종(파일 입력 폴백은 Pi 실촬영이 아닙니다, 폴백 결정은 Pi 실촬영 검증 완료를 뜻하지 않는다, 결정일 전에는 폴백을 확정하지 않는다)임을 확인한다.
- `fallback-decision-cli-due` CLI 결정일 판정: `python3 -m qa.fallback_decision --date 2026-11-02 --json`이 종료코드 0을 내고 status fallback_due·fallback_adopted true임을 확인한다. 이것은 가정 날짜 구동이며 오늘 실제 전환 확정이 아니다.
- `fallback-decision-evaluate` 프로세스 내 판정식: `evaluate_decision`이 결정일 전 미준비에서 pending, 결정일 당일 미준비에서 fallback_due, Pi 준비 완료에서는 어느 날짜든 pi_ready·fallback_adopted false를 내고, 세 보고 모두 `validate_decision`에서 문제 0건임을 확인한다. 구동 함수는 `drive_fallback_decision`다.
- `fallback-decision-build-probe` 프로세스 내 준비 대조: `build_decision`이 없는 probe(2026-10-30)에서는 pending·pi_blockers [`pi_device_arrival_not_confirmed`, `pi_camera_command_missing`]를, 준비된 probe와 장치 확인(2026-11-02)에서는 pi_ready·pi_blockers 빈 목록을 냄을 확인한다.
- `fallback-decision-tamper` 변조 탐지: pending 보고의 fallback_adopted를 true로 바꾸면 fallback_adopted 문제를, due 보고의 is_pi_real_capture를 true로 바꾸면 is_pi_real_capture 문제를, status를 바꾸면 status 문제를 `validate_decision`이 각각 지목함을 확인한다.
- `fallback-decision-invalid-date` 잘못된 날짜 차단: `python3 -m qa.fallback_decision --date 2026-13-40 --json`이 종료코드 2로 거부됨을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.fallback_decision`을 실행한다. 판정 날짜를 고정하려면 `--date YYYY-MM-DD`를, Pi 장치 도착을 외부에서 확인했으면 `--device-confirmed`를, 기계가 읽을 출력이 필요하면 `--json`을 붙인다. 종료코드는 보고가 유효하면 0, 무효면 2다.
- 이 CLI는 실제 촬영을 하지 않으며 Pi 준비 상태는 존재 탐지만으로 확인한다. 판정이 fallback_due여도 파일 입력 폴백은 Pi 실촬영이 아니며, 폴백 결정은 Pi 실촬영 검증 완료를 뜻하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature fallback-decision --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 Pi 촬영 경로는 이 절차의 범위가 아니다. 이 절차의 통과를 Pi 실촬영 성공이나 오늘 폴백 전환 확정으로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제 촬영을 하지 않는다. 네트워크 호출도 하지 않으며, 날짜는 CLI 인자로만 고정한다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature fallback-decision --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 CLI 서브프로세스와 프로세스 내 `evaluate_decision`·`build_decision`·`validate_decision`만으로 `drive_fallback_decision`을 실행한다.
- **CLI pending·due 확인.** 헬퍼가 `qa.fallback_decision` CLI를 `--date 2026-10-30` 텍스트·JSON과 `--date 2026-11-02 --json`으로 실행해 종료코드 0, pending/fallback_due 판정, 블로커 2건 순서, fallback 자산·렌더 경로, honesty 표기를 확인한다.
- **프로세스 내 판정 확인.** 헬퍼가 `evaluate_decision` 3상태와 `build_decision`의 missing/ready probe 대조, `validate_decision` 문제 0건을 확인한다.
- **변조·잘못된 날짜 확인.** 헬퍼가 fallback_adopted·is_pi_real_capture·status 변조 탐지와 잘못된 날짜 종료코드 2를 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `fallback-decision-pending.json`(CLI pending `--json` stdout 원문)과 `fallback-decision-due.json`(CLI due `--json` stdout 원문)가 남고, `summary.json`의 `feature`가 `fallback-decision`이며 `pending_status` pending·`due_status` fallback_due·`pi_ready_status` pi_ready·`tamper_detected` true·`invalid_date_exit_code` 2인지 대조한다.

## Gotchas

- 결정일 전에는 폴백을 확정하지 않는다. 2026-10-30 판정은 pending이며, fallback_due는 2026-11-02 가정 날짜를 넣었을 때만 나오는 판정식 확인이다.
- 파일 입력 폴백은 Pi 실촬영이 아닙니다. 폴백 채택을 Pi 실촬영 검증 완료로 서술하면 실패다.
- Pi가 준비되면 날짜와 무관하게 pi_ready이며 폴백을 채택하지 않는다. pi_ready인데 pi_blockers가 남아 있으면 모순이다.
- is_pi_real_capture는 어떤 보고에서도 항상 false여야 한다. true로 바뀌면 변조로 지목돼야 한다.
- 날짜 문자열 비교는 ISO 날짜(YYYY-MM-DD)일 때만 성립한다. 잘못된 날짜는 판정하지 말고 종료코드 2로 거부해야 한다.
