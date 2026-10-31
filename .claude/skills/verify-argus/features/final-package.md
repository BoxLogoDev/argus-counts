# 제출 패키지 최종 묶음

제출 패키지 최종 묶음은 `qa.final_package`가 제출물 인벤토리·제출 마감·Pi 폴백 결정 세 보고와 패키지 내보내기 실측(임시 staging 복사 대조)을 모아 패키지 상태를 판정하는지 검증하는 절차다. 이 검증은 실제로 제출하지 않는다: CLI에 기준 시각과 날짜를 명시해 구동하고 프로세스 내 `evaluate_final_package`·`build_final_package`·`validate_final_package`으로만 확인한다. 패키지 준비 상태는 제출 완료를 뜻하지 않으며, Pi 실촬영 검증 전이고 수치는 데모 기준이다. 패키지 날짜 목표는 2026-11-03이다.

## Sub-features

- `final-package-cli-blocked` CLI 블로커 잔존 판정: `python3 -m qa.final_package --now 2026-10-31T04:50:00+09:00 --date 2026-10-31`이 종료코드 0을 내고, 텍스트에 `STATUS: blocked`·`PACKAGE_DATE_TARGET: 2026-11-03`·`INVENTORY_PRESENT: 18`·`INVENTORY_TOTAL: 18`·`DEADLINE_STATUS: before_deadline`·`REMAINING_SECONDS: 454200`·`FALLBACK_STATUS: pending`·`SUBMISSION_READY: false`가 있으며, `--json`에서는 status blocked·inventory_missing []·fallback_adopted false·blockers [`pi_real_capture_pending`]·submission_ready false·honesty 3종(실제로 제출하지 않는다, 제출 완료를 뜻하지 않는다, Pi 실촬영 검증 전)임을 확인한다.
- `final-package-cli-overdue` CLI 마감 경과 판정: `python3 -m qa.final_package --now 2026-11-05T11:00:00+09:00 --date 2026-10-31 --json`이 종료코드 1을 내고 status overdue·deadline_status overdue임을 확인한다.
- `final-package-evaluate` 프로세스 내 판정식: `evaluate_final_package`가 블로커 잔존 시 blocked, 블로커가 없으면 ready_for_packaging, 제출물이 누락되면 incomplete, 마감 경과 시 overdue를 내고, `build_final_package`가 기준 시각·날짜에서 blocked를 내며, 모든 보고가 `validate_final_package`에서 문제 0건임을 확인한다. 구동 함수는 `drive_final_package`다.
- `final-package-tamper` 변조 탐지: status를 바꾸면 status 문제를, inventory_present를 바꾸면 inventory_present 문제를, submission_ready를 true로 바꾸면 submission_ready 문제를, export_copied를 바꾸면 export_copied 문제를 `validate_final_package`가 각각 지목함을 확인한다.
- `final-package-export-evidence` 패키지 내보내기 증거: CLI 텍스트의 `EXPORT_COPIED: 18`·`EXPORT_TOTAL: 18`·`EXPORT_MISSING: []`와 JSON의 export_copied·export_total·export_missing·export_total_bytes(양의 정수)를 확인하고, export 필드가 인벤토리 필드(export_copied=inventory_present·export_total=inventory_total·export_missing=inventory_missing)와 어긋나지 않는지 교차 대조한다. `build_final_package` 실측의 export_total_bytes가 CLI blocked 보고와 같은지도 대조하며, 증거 summary에 `export_copied`·`export_total`·`export_missing`·`export_total_bytes`·`built_export_total_bytes`·`export_incomplete_status`·`export_tamper_detected`를 남긴다. 내보내기 실측은 임시 staging 복사·대조까지만이며 실제로 제출하지 않는다.
- `final-package-invalid-date` 잘못된 날짜 차단: `python3 -m qa.final_package --date not-a-date`가 종료코드 2로 거부됨을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.final_package`를 실행한다. 기준 시각을 고정하려면 `--now ISO8601`을, 판정 날짜를 고정하려면 `--date YYYY-MM-DD`를, 기계가 읽을 출력이 필요하면 `--json`을 붙인다. 종료코드는 보고가 유효하고 마감이 지나지 않았으면 0, 지났으면 1, 입력이 유효하지 않으면 2다.
- 이 CLI는 실제로 제출하지 않으며, 패키지 준비 상태는 제출 완료를 뜻하지 않는다. blocked는 제출 블로커가 남아 있다는 판정일 뿐이다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature final-package --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 제출 경로는 이 절차의 범위가 아니다. 이 절차의 통과를 제출 완료나 제출 준비 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 제출하지 않는다. 네트워크 호출도 하지 않으며, 기준 시각과 날짜는 CLI 인자로만 고정한다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature final-package --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 CLI 서브프로세스와 프로세스 내 `evaluate_final_package`·`build_final_package`·`validate_final_package`만으로 `drive_final_package`를 실행한다.
- **CLI 판정 확인.** 헬퍼가 `qa.final_package` CLI를 `--now 2026-10-31T04:50:00+09:00 --date 2026-10-31` 텍스트·JSON과 `--now 2026-11-05T11:00:00+09:00 --date 2026-10-31 --json`으로 실행해 종료코드와 blocked·overdue 판정, 인벤토리·남은 초·폴백 상태·블로커·honesty 표기를 확인한다.
- **프로세스 내 판정 확인.** 헬퍼가 `evaluate_final_package` 4상태(blocked·ready_for_packaging·incomplete·overdue)와 `build_final_package` blocked 판정, `validate_final_package` 문제 0건을 확인한다.
- **변조·잘못된 날짜 확인.** 헬퍼가 status·inventory_present·submission_ready·export_copied 변조 탐지와 잘못된 날짜 종료코드 2를 확인한다.
- **내보내기 증거 확인.** 헬퍼가 CLI·JSON·build 실측의 export 필드(복사 18/18·missing []·total_bytes 양의 정수)를 인벤토리와 교차 대조하고, export 불일치 시 incomplete 판정(상태 전용 프로브)을 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `final-package-blocked.json`(CLI blocked `--json` stdout 원문)과 `final-package-overdue.json`(CLI overdue `--json` stdout 원문)이 남고, `summary.json`의 `feature`가 `final-package`이며 `blocked_status` blocked·`inventory_present` 18·`inventory_total` 18·`deadline_status` before_deadline·`remaining_seconds` 454200·`fallback_status` pending·`overdue_status` overdue·`tamper_detected` true·`invalid_exit_code` 2·`export_copied` 18·`export_total` 18·`export_missing` []·`export_total_bytes` 양의 정수·`built_export_total_bytes`와 일치·`export_incomplete_status` incomplete·`export_tamper_detected` true인지 대조한다.

## Gotchas

- 패키지 준비 상태는 제출 완료를 뜻하지 않는다. ready_for_packaging이어도 submission_ready는 항상 false다.
- blocked는 실패가 아니다. 제출물 18개가 모두 있어도 블로커 `pi_real_capture_pending`이 남아 있으면 blocked가 정답이다.
- 남은 시간과 폴백 판정은 제공된 기준 시각·날짜로만 계산한다. 기준을 고정하지 않은 구동을 결정적 증거로 쓰지 않는다.
- 마감 경과가 최우선이다. 제출물이 누락돼 있어도 deadline_status가 overdue면 status는 overdue다.
- 파일 입력 폴백은 Pi 실촬영이 아니다. fallback_status와 fallback_adopted로 Pi 실촬영 검증 완료를 주장하지 않는다.
