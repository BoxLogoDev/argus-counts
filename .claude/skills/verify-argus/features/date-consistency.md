# 날짜·시각 기준 일관성 감사

날짜·시각 기준 일관성 감사는 `qa.date_consistency`가 날짜 판정 모듈에 시간대 없는 날짜·시각 호출이 없는지, 명시적 UTC 현재 시각이 허용 목록 5개 파일·7곳 안에서만 쓰이는지, 폴백 결정·영상 선택·제출 마감의 기본 날짜·시각이 실제 KST 계산과 일치하는지를 감사하는지 확인하는 절차다. 구동 함수는 `drive_date_consistency`다. 이 검증은 날짜·시각 기준만 감사하며 실제로 제출·촬영·호출하지 않는다. 감사 통과는 제출 준비 완료를 뜻하지 않으며, 세션 식별자와 생성 시각의 명시적 UTC는 날짜 판정이 아니다. 결정 모듈의 기본 날짜는 `today_kst`로 수렴해야 한다.

## Sub-features

- `date-consistency-valid` 유효 감사 통과: 실루트 `build_report`가 `consistent` true·`problems` []·naive/utc/decision 문제 0건·블로커 [`pi_real_capture_pending`]·`submission_ready` false를 내고, functional의 `today_kst`와 `fallback_default_date`가 `date_kst`와 같으며 `deadline_now`가 +09:00으로 끝나고 `validate_report`도 문제가 없음을 확인한다.
- `date-consistency-cli` CLI 구동: `python3 -m qa.date_consistency` 텍스트 구동이 종료코드 0과 `CONSISTENT: true`·`SUBMISSION_READY: false`를 내고, `--json` 구동도 종료코드 0이며 `date_kst`·`scanned_files`가 프로세스 내 보고와 일치하고 honesty에 제출 준비 완료를 뜻하지 않는다는 표기가 있음을 확인한다.
- `date-consistency-tamper` 변조 탐지: 보고의 `consistent`를 false로, `submission_ready`를 true로, `blockers`를 빈 목록으로 각각 바꾸면 `validate_report`가 해당 문제를 지목함을 확인한다.
- `date-consistency-naive-utc` 시간대 없는 호출·허용 목록 밖 UTC 탐지: 임시 루트에 조각을 이어붙여 만든 시간대 없는 호출 파일은 `scan_naive_patterns`가, 허용 목록 밖 UTC 호출 파일은 `scan_utc_allowlist`가 각각 지목함을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.date_consistency [--json]`를 실행한다. 종료코드는 일관성이 있으면 0, 일관성 문제가 있으면 1, 보고가 무효면 2다.
- 이 하네스는 소스 파일과 결정 모듈의 기본값만 읽는다. 실제로 제출·촬영·호출하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature date-consistency --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 제출 경로는 이 절차의 범위가 아니다. 이 절차의 통과를 제출 완료나 제출 준비 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 제출·촬영·호출하지 않는다. 네트워크와 실제 키를 쓰지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature date-consistency --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `drive_date_consistency`로 CLI 서브프로세스와 프로세스 내 감사 함수만 실행한다.
- **유효 감사 확인.** 헬퍼가 `build_report`·`validate_report`로 consistent·문제 0건·KST 기본값 일치를 대조한다.
- **CLI 확인.** 헬퍼가 `qa.date_consistency` CLI 텍스트·`--json` 구동을 실행해 종료코드 0과 `CONSISTENT: true`·`date_kst`·`scanned_files`를 확인한다.
- **변조 탐지 확인.** 헬퍼가 consistent·submission_ready·blockers 변조를 각각 탐지하는지 확인한다.
- **naive·UTC 탐지 확인.** 헬퍼가 임시 루트에 조각으로 만든 탐지 파일로 naive 패턴과 허용 목록 밖 UTC를 각각 탐지하는지 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `date-consistency.json`(CLI `--json` stdout 원문)과 `date-consistency.txt`(CLI 텍스트 stdout 원문)가 남고, `summary.json`의 `feature`가 `date-consistency`이며 `consistent` true·`tamper_detected` true·`naive_detected` true·`utc_detected` true·`valid_exit_code` 0·`json_exit_code` 0인지 대조한다.

## Gotchas

- 시간대 없는 호출이나 UTC 호출의 리터럴을 검증 코드 파일에 그대로 쓰면 날짜 감사 스캐너가 그 파일 자체를 문제로 잡는다. 탐지용 문자열은 조각을 이어붙여 만들어야 한다.
- 감사 통과는 제출 준비 완료를 뜻하지 않는다. 블로커 `pi_real_capture_pending`이 남아 있는 동안 `submission_ready`는 false가 정답이다.
- 세션 식별자와 생성 시각에 쓰는 명시적 UTC는 날짜 판정이 아니다. 허용 목록의 파일과 횟수가 바뀌면 그 변경 자체를 먼저 검토해야 한다.
- `scanned_files`는 tests·`__pycache__`·`.git` 경로를 제외한 실측이다. 기준을 고정하지 않은 구동의 스캔 수를 결정적 증거로 쓰지 않는다.
- 기본 날짜·시각은 KST 기준이다. 시스템 로컬 날짜(가상머신 UTC)를 쓰는 회귀가 생기면 KST 00:00~09:00 구간에 하루 전으로 판정된다.
