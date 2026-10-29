# SAM 단일 빈 스모크

SAM 단일 빈 스모크는 `qa.sam_smoke`의 `run_smoke`가 준비 점검을 통과한 뒤에만 단일 빈 1개에 대해 계수를 시도하는지 검증하는 절차다. 이 검증은 실제 API를 호출하지 않는다: 기본 CLI 실행의 차단 보고와 프로세스 안에 주입한 가짜 counter만으로 구동한다. 성공해도 전체 세션 성공을 뜻하지 않는다. 단일 빈 1개의 스모크일 뿐이다. 기본 빈은 `A-01-02`이며 장부 수량은 8이다. 블로커는 결정적 순서로 `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing` 세 가지이며, 텍스트 출력의 `SMOKE_PASSED` 줄이 스모크 통과 여부를 나타낸다. 환경변수 값은 출력하지 않는다.

## Sub-features

- `sam-smoke-blocked-text` 기본 차단 텍스트: SAM 환경변수를 비운 CLI `python3 -m qa.sam_smoke`가 종료코드 1을 내고, stdout에 `STATUS: blocked`와 `ATTEMPTED: false`와 `BLOCKERS: 3`와 `SMOKE_PASSED: false`와 블로커 id `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing`이 이 순서대로 있음을 확인한다.
- `sam-smoke-blocked-json` 기본 차단 JSON: `python3 -m qa.sam_smoke --json`이 종료코드 1을 내고, `status`가 `blocked`이며 `attempted`와 `ready_for_live_call`이 모두 `false`이고 blockers id 목록이 위 세 id와 일치하며 `counted_qty`와 `source`가 `null`임을 확인한다. `honesty`에는 준비가 안 되면 실제 API를 호출하지 않는다는 줄과 실패를 모의 결과로 대체하지 않는다는 줄이 각각 있다.
- `sam-smoke-fake-passed` 가짜 counter 성공: 프로세스 안에서 `run_smoke`에 가짜 환경과 크레딧 확인, `source`가 `sam`인 `CountResult`를 돌려주는 가짜 counter를 넘기면 `status`가 `passed`이고 `counted_qty` 5, `book_qty` 8, `diff` -3이며 counter 호출이 `A-01-02` 한 번뿐임을 확인한다. 같은 가짜 counter로 준비 안 된 환경을 넘기면 `blocked`이고 counter를 호출하지 않는다.
- `sam-smoke-mock-source-blocked` 모의 source 차단: `source`가 `mock`인 결과를 돌려주는 counter를 넘기면 `status`가 `failed`이고 `error_type`이 `unexpected_source`임을 확인한다.
- `sam-smoke-error-blocked` 오류 차단: `SamCountingError`를 일으키는 counter를 넘기면 `status`가 `failed`이고 `error_type`이 `SamCountingError`이며 `counted_qty`가 `null`임을 확인한다. 실패를 모의 결과로 대체하지 않는다.
- `sam-smoke-unknown-bin` 알 수 없는 빈 차단: `bin_id`에 `Z-99-99`를 넘기면 `status`가 `failed`이고 `error_type`이 `unknown_bin`이며 `attempted`가 `false`이고 counter를 호출하지 않는다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.sam_smoke`를 실행한다. 크레딧 입금을 외부에서 확인했으면 `--credit-confirmed`를, 기계가 읽을 출력이 필요하면 `--json`을, 다른 빈을 보려면 `--bin`을 붙인다. 종료코드는 통과 0, 차단 1, 실패 2다.
- 준비가 안 된 기본 실행에서는 실제 API를 호출하지 않는다. 차단 보고만 나오고 계수는 시도하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-smoke --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 API 주소와 실제 키를 넣고 호출하는 경로는 이 절차의 범위가 아니다. 성공해도 전체 세션 성공이 아니므로, 전체 세션 평가는 실호출 뒤 별도로 한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제 API를 호출하지 않는다. 네트워크와 실제 키를 쓰지 않으며, 헬퍼의 기본 CLI 실행은 `clean_env()`로 SAM 환경변수를 비운 상태다.
- 가짜 환경은 헬퍼 상수 `SAM_SMOKE_FAKE_URL`과 `SAM_SMOKE_FAKE_KEY_VALUE`로만 만들며, `qa.sam_readiness`의 `ENV_BASE_URL`·`ENV_KEY_VAR` 이름으로만 넘긴다. 이 값들은 도달 대상도 실제 자격도 아니다. 환경변수 값은 출력하지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-smoke --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 네트워크를 쓰지 않고 CLI 서브프로세스와 프로세스 내 `run_smoke`만으로 `drive_sam_smoke`를 실행한다.
- **기본 차단 텍스트 확인.** 헬퍼가 `qa.sam_smoke` CLI를 서브프로세스로 실행해 종료코드 1, `STATUS: blocked`, `ATTEMPTED: false`, `BLOCKERS: 3`, `SMOKE_PASSED: false`, 블로커 id 세 개의 순서를 대조한다.
- **기본 차단 JSON 확인.** 헬퍼가 `--json` CLI를 실행해 `status` `blocked`, `attempted`와 `ready_for_live_call`의 `false`, 블로커 id 목록과 `EXPECTED_READINESS_BLOCKER_IDS`의 일치, `counted_qty`와 `source`의 `null`, `honesty`의 호출하지 않는다는 줄과 대체하지 않는다는 줄을 확인한다.
- **가짜 counter 성공 확인.** 헬퍼가 프로세스 안에서 가짜 환경과 크레딧 확인으로 `run_smoke`를 부르면 가짜 counter가 `source` `sam`인 결과를 돌려줘 `passed`가 되고, `counted_qty` 5와 `book_qty` 8과 `diff` -3, counter 호출 한 번을 확인한다. 준비 안 된 환경에서는 `blocked`이며 counter 호출이 0건이다.
- **모의 source 차단 확인.** 헬퍼가 `source` `mock`인 결과를 돌려주는 counter로 `failed`와 `error_type` `unexpected_source`를 받는지 확인한다.
- **오류 차단 확인.** 헬퍼가 `SamCountingError`를 일으키는 counter로 `failed`와 `error_type` `SamCountingError`를 받고 `counted_qty`가 `null`인지 확인한다.
- **알 수 없는 빈 확인.** 헬퍼가 `bin_id` `Z-99-99`로 `failed`와 `error_type` `unknown_bin`, `attempted` `false`, counter 호출 0건을 확인한다.
- **값 누출 없음 확인.** 헬퍼가 성공·차단·모의·오류·알 수 없는 빈 보고를 JSON으로 바꾼 문자열과 기본 CLI stdout 어디에도 가짜 키와 가짜 주소 값이 없음을 대조한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `sam-smoke-blocked.json`(기본 차단 `--json` stdout 원문)과 `sam-smoke-passed.json`(가짜 counter 성공 보고)이 남고, `summary.json`의 `feature`가 `sam-smoke`이며 `fake_passed`가 `true`, `blocked_counter_calls`가 0, `sentinel_leaked`가 `false`인지 대조한다.

## Gotchas

- 차단 상태에서 counter를 부르면 실패다. 준비 점검이 통과하지 못한 보고는 `attempted`가 `false`여야 하고 counter 호출 기록이 비어 있어야 한다.
- 성공을 전체 세션 성공으로 서술하지 않는다. 단일 빈 스모크의 `passed`는 전체 세션 성공을 뜻하지 않으며, 증거와 보고 모두 그렇게 표기한다.
- 환경변수 값은 출력하지 않는다. 가짜 키와 가짜 주소 값이 보고 JSON·CLI stdout·증거 파일에 나타나면 실패로 본다.
- 실패를 모의 결과로 대체하면 실패다. `SamCountingError`가 나면 `failed`로 보고하고 `counted_qty`는 `null`이며, `source`가 `mock`인 결과도 `unexpected_source`로 차단한다.
- 블로커 순서는 결정적이다: `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing`. 순서가 바뀌면 실패로 본다.
- 가짜 환경과 가짜 counter는 프로세스 안과 자식 프로세스 환경으로만 넘긴다. 실제 API를 호출하거나 셸 환경에 가짜 값을 남기면 검증이 무효가 된다.
