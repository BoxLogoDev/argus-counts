# SAM 실호출 전환 준비 점검

SAM 실호출 전환 준비 점검은 `qa.sam_readiness`의 `check_readiness`가 실호출을 시작하기 전에 필요한 조건만 점검하는지 검증하는 절차다. 이 하네스는 실제 API를 호출하지 않는다. 네트워크를 쓰지 않으며, 환경변수는 존재 여부만 확인하고 값은 출력하지 않는다. 준비 완료는 실호출 성공을 뜻하지 않는다. 블로커는 결정적 순서로 `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing` 세 가지이며, 텍스트 출력의 `READY_FOR_LIVE_CALL` 줄과 JSON의 `ready_for_live_call`이 준비 판정을 나타낸다.

## Sub-features

- `sam-readiness-blocked-text` 기본 차단 텍스트: SAM 환경변수를 비운 CLI `python3 -m qa.sam_readiness`가 종료코드 1을 내고, stdout에 `BLOCKERS: 3`와 `READY_FOR_LIVE_CALL: false`와 블로커 id `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing`이 이 순서대로 있음을 확인한다.
- `sam-readiness-blocked-json` 기본 차단 JSON: `python3 -m qa.sam_readiness --json`이 종료코드 1을 내고, `ready_for_live_call`이 `false`이며 blockers id 목록이 위 세 id와 일치하고 `base_url_present`·`api_key_present`·`credit_confirmed`가 모두 `false`임을 확인한다. `honesty`에는 실제 API를 호출하지 않는다는 줄이 있다.
- `sam-readiness-fake-ready` 가짜 환경 준비 완료: 프로세스 안에서 `check_readiness`에 가짜 환경과 `credit_confirmed=True`를 넘기면 `ready_for_live_call`이 `true`이고 blockers가 비어 있으며 `would_select_live`가 `true`임을 확인한다. 결과를 JSON으로 바꿔도 가짜 키와 가짜 주소 값은 출력하지 않는다.
- `sam-readiness-credit-only` 크레딧만 남은 차단: 가짜 환경에 `credit_confirmed=False`를 넘기면 블로커가 `sam_credit_not_confirmed` 하나만 남음을 확인한다.
- `sam-readiness-cli-ready` CLI 가짜 환경 성공: 가짜 환경으로 `python3 -m qa.sam_readiness --credit-confirmed --json`을 실행하면 종료코드 0과 `ready_for_live_call` `true`를 받고, stdout에 가짜 키와 가짜 주소 값이 없음을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.sam_readiness`를 실행한다. 크레딧 입금을 외부에서 확인했으면 `--credit-confirmed`를, 기계가 읽을 출력이 필요하면 `--json`을 붙인다. 준비 완료이면 종료코드 0, 아니면 1이다.
- 이 CLI는 실제 API를 호출하지 않는다. 환경변수 `SAM_API_BASE_URL`과 키 환경변수는 존재 여부만 확인하며 값은 출력하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-readiness --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 API 주소와 실제 키를 넣고 호출하는 경로는 이 절차의 범위가 아니다. 준비 완료는 실호출 성공을 뜻하지 않으므로, 실제 호출 성공은 크레딧 입금과 키 발급 뒤 별도로 확인한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제 API를 호출하지 않는다. 네트워크와 실제 키를 쓰지 않으며, 헬퍼의 기본 CLI 실행은 `clean_env()`로 SAM 환경변수를 비운 상태다.
- 가짜 환경은 헬퍼 상수 `SAM_READINESS_FAKE_URL`과 `SAM_READINESS_FAKE_KEY_VALUE`로만 만들며, 이 값들은 도달 대상도 실제 자격도 아니다. 환경변수 값은 출력하지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-readiness --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 네트워크를 쓰지 않고 CLI 서브프로세스와 프로세스 내 `check_readiness`만으로 `drive_sam_readiness`를 실행한다.
- **기본 차단 텍스트 확인.** 헬퍼가 `qa.sam_readiness` CLI를 서브프로세스로 실행해 종료코드 1, `BLOCKERS: 3`, `READY_FOR_LIVE_CALL: false`, 블로커 id 세 개의 순서를 대조한다.
- **기본 차단 JSON 확인.** 헬퍼가 `--json` CLI를 실행해 `ready_for_live_call` `false`, 블로커 id 목록과 `EXPECTED_READINESS_BLOCKER_IDS`의 일치, 존재 플래그 세 개의 `false`, `honesty`의 호출하지 않는다는 줄을 확인한다.
- **가짜 환경 준비 완료 확인.** 헬퍼가 프로세스 안에서 `qa.sam_readiness`의 `ENV_BASE_URL`·`ENV_KEY_VAR`·`check_readiness`를 가져와 가짜 환경과 크레딧 확인으로 준비 완료를 확인하고, 결과 JSON에 가짜 키와 가짜 주소 값이 없음을 대조한다.
- **크레딧만 남은 차단 확인.** 헬퍼가 같은 가짜 환경에 크레딧 미확인을 넘겨 블로커가 `sam_credit_not_confirmed` 하나만 남는지 확인한다.
- **CLI 가짜 환경 성공 확인.** 헬퍼가 가짜 환경을 자식 환경에만 넣어 `--credit-confirmed --json` CLI를 실행해 종료코드 0과 `ready_for_live_call` `true`를 받고, stdout에 가짜 값이 없음을 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `sam-readiness-blocked.json`(기본 차단 `--json` stdout 원문)과 `sam-readiness-ready.json`(가짜 환경 `check_readiness` 결과, 존재 여부 bool만 있어 값 누출 없음)이 남고, `summary.json`의 `feature`가 `sam-readiness`이며 `sentinel_leaked`가 `false`인지 대조한다.

## Gotchas

- 준비 완료를 실호출 성공으로 서술하지 않는다. 준비 완료는 실호출 성공을 뜻하지 않으며, 증거와 보고 모두 그렇게 표기한다.
- 이 절차에서 실제 API를 호출하지 않는다. 실제 주소와 실제 키를 넣은 호출을 실행하면 검증이 무효가 된다.
- 환경변수는 존재 여부만 확인한다. 값은 출력하지 않으며, 가짜 키와 가짜 주소 값이 결과 JSON·CLI stdout·증거 파일에 나타나면 실패로 본다.
- 블로커 순서는 결정적이다: `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing`. 순서가 바뀌면 실패로 본다.
- 기본 차단 상태에서 종료코드 0이거나 `READY_FOR_LIVE_CALL: true`면 실패로 본다. 크레딧 확인 플래그가 없는데 크레딧 블로커가 사라져도 실패로 본다.
- 가짜 환경은 자식 프로세스 환경과 프로세스 내 `env` 인자로만 넘긴다. 셸 환경이나 상주 프로세스에 가짜 값을 남기지 않는다.
