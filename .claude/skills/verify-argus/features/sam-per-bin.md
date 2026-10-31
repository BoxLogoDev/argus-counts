# SAM 빈별 서로 다른 사진 세션

SAM 빈별 서로 다른 사진 세션은 `qa.sam_per_bin`의 `run_sam_per_bin`이 준비 점검을 통과한 뒤에만 데모 빈 6개마다 서로 다른 사진 파일을 받아 각각 계수해 장부와 대조하는지 검증하는 절차다. 이 검증은 실제 API를 호출하지 않는다: 기본 CLI 실행의 차단 보고와 프로세스 안에 주입한 가짜 counter만으로 구동한다. 가짜 counter 성공은 `DEMO_COUNTED_QTY` 기준 수량의 대조 검증일 뿐이며, 호출자가 제공한 가상 사진의 서로 다른 잘라내기(`fake-per-bin-photo-<빈>`)를 쓴 것으로, 실제 빈 촬영이나 Pi 실촬영이 아니고 빈별 정확도 검증도 아니다. 세션 ID 예시는 `VERIFY-SAM-PERBIN-1`이다. 블로커는 결정적 순서로 `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing` 세 가지이며, 텍스트 출력의 `SESSION_PASSED` 줄이 세션 통과 여부를, `distinct_image_count`가 서로 다른 사진 수(통과 시 6)를 나타낸다. 사진 동일성은 파일 SHA-256으로 검사한다. 환경변수 값은 출력하지 않는다.

## Sub-features

- `sam-per-bin-blocked-text` 기본 차단 텍스트: SAM 환경변수를 비운 CLI `python3 -m qa.sam_per_bin`가 종료코드 1을 내고, stdout에 `STATUS: blocked`와 `ATTEMPTED: false`와 `DISTINCT_IMAGES: 0`와 `BLOCKERS: 3`와 `SESSION_PASSED: false`와 블로커 id 세 개가 이 순서대로 있음을 확인한다.
- `sam-per-bin-blocked-json` 기본 차단 JSON: `python3 -m qa.sam_per_bin --json`이 종료코드 1을 내고, `status`가 `blocked`이며 `attempted`와 `ready_for_live_call`이 모두 `false`이고 blockers id 목록이 위 세 id와 일치하며 `source`가 `null`, `distinct_image_count`가 0, `bins`가 빈 목록, `summary`가 `null`임을 확인한다. `honesty`에는 준비가 안 되면 실제 API를 호출하지 않는다는 줄과 빈마다 서로 다른 사진을 쓰지 않으면 호출하지 않는다는 줄, 빈별 사진은 가상 사진의 잘라내기이며 Pi 실촬영이 아니다라는 줄이 각각 있다.
- `sam-per-bin-fake-passed` 가짜 counter 성공: 프로세스 안에서 `run_sam_per_bin`에 가짜 환경과 크레딧 확인, 빈마다 내용이 다른 임시 사진 파일 6개와 `DEMO_COUNTED_QTY`를 돌려주는 가짜 counter를 넘기면 `status`가 `passed`이고 `source`가 `sam`, `distinct_image_count`가 6, counter 호출이 데모 빈 6개 순서대로 각 빈의 자기 사진으로 6회이며, 각 빈의 `image_sha256`이 그 파일 바이트의 SHA-256과 일치하고, 요약이 빈 6·일치 4·불일치 2·절대 차이 6·순 차이 0이고 A-01-02가 장부 8·실측 5·diff -3·short, B-01-02가 diff 3·over임을 확인한다.
- `sam-per-bin-blocked-counter` 차단 시 counter 무호출: 준비 안 된 환경에서는 `blocked`이고 counter를 호출하지 않는다.
- `sam-per-bin-distinct-images` 서로 다른 사진 강제: 두 빈이 같은 사진 파일을 가리키면(`duplicate_image`) 어떤 빈도 호출하지 않고 `failed`이며 `attempted`가 `false`이고, 사진이 하나라도 빠지면(`missing_image`) 역시 호출 없이 `failed`임을 확인한다. 서로 다른 사진을 쓰지 않으면 호출하지 않는다.
- `sam-per-bin-mock-source-blocked` 모의 source 차단: `source`가 `mock`인 결과를 돌려주는 counter를 넘기면 세션 전체가 `failed`이고 `error_type`이 `unexpected_source`이며 `summary`가 `null`임을 확인한다. 실패를 모의 결과로 대체하지 않는다.
- `sam-per-bin-error-blocked` 오류 차단: `SamCountingError`를 일으키는 counter를 넘기면 `failed`이고 `error_type`이 `SamCountingError`이며, 일반 `RuntimeError`를 일으키는 counter는 `error_type`이 `RuntimeError`이고 예외 원본 문자열이 보고에 새지 않음을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.sam_per_bin --image <빈>=<경로> ...`를 빈 6개 전부 붙여 실행한다. 크레딧 입금을 외부에서 확인했으면 `--credit-confirmed`를, 기계가 읽을 출력이 필요하면 `--json`을, 세션 이름은 `--session-id`를 붙인다. 종료코드는 통과 0, 차단 1, 실패 2다.
- 준비가 안 된 기본 실행에서는 실제 API를 호출하지 않는다. 차단 보고만 나오고 어떤 빈도 계수하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-per-bin --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 API 주소와 실제 키를 넣고 호출하는 경로는 이 절차의 범위가 아니다. 실제 빈별 실호출은 2026-10-31 커넥터 브리지로 스킬 밖에서 통과한 기록이 따로 있으며(가상 사진의 서로 다른 잘라내기, 실제 빈 촬영 아님), 이 절차의 가짜 성공을 그 실호출 성공으로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제 API를 호출하지 않는다. 네트워크와 실제 키를 쓰지 않으며, 헬퍼의 기본 CLI 실행은 `clean_env()`로 SAM 환경변수를 비운 상태다.
- 가짜 환경은 헬퍼 상수 `SAM_PERBIN_FAKE_URL`과 `SAM_PERBIN_FAKE_KEY_VALUE`로만 만들며, `qa.sam_readiness`의 `ENV_BASE_URL`·`ENV_KEY_VAR` 이름으로만 넘긴다. 이 값들은 도달 대상도 실제 자격도 아니다. 환경변수 값은 출력하지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-per-bin --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 네트워크를 쓰지 않고 CLI 서브프로세스와 프로세스 내 `run_sam_per_bin`만으로 `drive_sam_per_bin`를 실행한다.
- **기본 차단 텍스트 확인.** 헬퍼가 `qa.sam_per_bin` CLI를 서브프로세스로 실행해 종료코드 1, `STATUS: blocked`, `ATTEMPTED: false`, `DISTINCT_IMAGES: 0`, `BLOCKERS: 3`, `SESSION_PASSED: false`, 블로커 id 세 개의 순서를 대조한다.
- **기본 차단 JSON 확인.** 헬퍼가 `--json` CLI를 실행해 `status` `blocked`, `attempted`와 `ready_for_live_call`의 `false`, 블로커 id 목록과 `EXPECTED_READINESS_BLOCKER_IDS`의 일치, `source`의 `null`, `distinct_image_count` 0, `bins`의 빈 목록, `summary`의 `null`, `honesty`의 호출하지 않는다는 줄과 서로 다른 사진 줄과 Pi 실촬영이 아니다 줄을 확인한다.
- **가짜 counter 성공 확인.** 헬퍼가 프로세스 안에서 임시 디렉터리에 빈마다 다른 바이트의 사진 6개를 만들고 가짜 환경과 크레딧 확인으로 `run_sam_per_bin`를 부르면 가짜 counter가 데모 기준 수량을 돌려줘 `passed`가 되고, counter 호출 6회와 빈별 `image_sha256` 대조, `distinct_image_count` 6, 요약 수치를 확인한다. 준비 안 된 환경에서는 `blocked`이며 counter 호출이 0건이다.
- **서로 다른 사진 강제 확인.** 헬퍼가 두 빈에 같은 파일을 주는 `duplicate_image`와 사진 하나를 빼는 `missing_image`에서 각각 counter 호출 0건으로 `failed`가 되는지 확인한다.
- **모의 source 차단 확인.** 헬퍼가 `source` `mock`인 결과를 돌려주는 counter로 세션 전체 `failed`와 `error_type` `unexpected_source`를 받는지 확인한다.
- **오류 차단 확인.** 헬퍼가 `SamCountingError`와 일반 예외를 일으키는 counter로 각각 `failed`와 해당 `error_type`을 받고, 예외 원본 문자열이 보고에 없는지 확인한다.
- **값 누출 없음 확인.** 헬퍼가 성공·차단·중복·누락·모의·오류 보고를 JSON으로 바꾼 문자열과 기본 CLI stdout 어디에도 가짜 키와 가짜 주소 값과 예외 원본 sentinel이 없음을 대조한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `sam-per-bin-blocked.json`(기본 차단 `--json` stdout 원문)과 `sam-per-bin-passed.json`(가짜 counter 성공 보고)이 남고, `summary.json`의 `feature`가 `sam-per-bin`이며 `fake_passed`가 `true`, `distinct_image_count`가 6, `duplicate_blocked`와 `missing_blocked`가 `true`, `blocked_counter_calls`가 0, `sentinel_leaked`가 `false`인지 대조한다.

## Gotchas

- 차단 상태나 사진 조건이 안 되면 counter를 부르면 실패다. 준비 점검이 통과하지 못한 보고는 `attempted`가 `false`여야 하고, 사진 누락·중복 보고도 counter 호출 기록이 비어 있어야 한다.
- 가짜 성공을 실호출 성공으로 서술하지 않는다. 이 절차의 `passed`는 가짜 counter와 데모 기준 수량의 대조 검증이며, 실제 빈별 실호출 기록(가상 사진 잘라내기, 실제 빈 촬영 아님)과 섞지 않는다.
- 빈별 실호출이어도 Pi 실촬영이 아니다. 사진은 호출자가 제공한 가상 사진의 잘라내기이며, 이 절차는 빈별 정확도 검증도 아니다.
- 환경변수 값은 출력하지 않는다. 가짜 키와 가짜 주소 값, 예외 원본 문자열이 보고 JSON·CLI stdout·증거 파일에 나타나면 실패로 본다.
- 실패를 모의 결과로 대체하면 실패다. 한 빈이라도 `SamCountingError`가 나거나 `source`가 `mock`이면 세션 전체를 `failed`로 보고하고 `summary`는 `null`이다.
- 블로커 순서는 결정적이다: `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing`. 순서가 바뀌면 실패로 본다.
- 가짜 환경과 가짜 counter와 임시 사진은 프로세스 안과 자식 프로세스 환경으로만 넘긴다. 실제 API를 호출하거나 셸 환경에 가짜 값을 남기면 검증이 무효가 된다.
