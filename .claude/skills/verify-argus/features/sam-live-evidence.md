# SAM 실호출 증거 검증

SAM 실호출 증거 검증은 `qa.sam_live_evidence`의 `validate_evidence`·`build_report`·`validate_report`가 커넥터 브리지(`custom.meta-model-api`, endpoint `https://api.meta.ai/v1/responses`)로 수행한 SAM 3.1 빈별 실호출 증거 JSON의 내부 정합만 다시 검증하는지 확인하는 절차다. 이 검증은 실제 API를 호출하지 않는다: 합성한 유효 증거를 CLI 파일 구동과 프로세스 내 검증 함수로만 구동한다. 증거 검증 통과는 실제 빈 촬영이나 Pi 실촬영이 아니며 제출 준비 완료를 뜻하지 않는다. 빈별 사진은 가상 사진의 서로 다른 잘라내기이며, 빈 해시는 SHA-256으로 서로 다름을 검사하고 `distinct_image_count`는 6이어야 한다. 세션 ID 예시는 `VERIFY-SAM-EVIDENCE-1`이다. 하네스는 `API를 호출하지 않는다`는 정직성 표기를 포함한다.

## Sub-features

- `sam-live-evidence-valid` 유효 증거 통과: 프로세스 안에서 합성한 유효 증거(빈별 계수 9·3·7·5·6·11, 요약 일치 1·불일치 5·절대 차이 30·순 차이 -28)는 `validate_evidence` 문제가 없고 `build_report`가 `valid` true·`source` sam·`distinct_image_count` 6·`submission_ready` false를 내며 `validate_report`도 문제가 없음을 확인한다.
- `sam-live-evidence-cli-json` CLI JSON 구동: `python3 -m qa.sam_live_evidence --file <경로> --json`이 종료코드 0을 내고 `VALID: true` 텍스트 구동과 함께 세션·source·distinct·요약을 대조함을 확인한다.
- `sam-live-evidence-duplicate-detected` 중복 해시 탐지: 두 빈의 `image_sha256`을 같게 만들면 `distinct` 문제를 내고 CLI 종료코드 1로 실패함을 확인한다.
- `sam-live-evidence-summary-tamper` 요약·diff·source·endpoint 변조 탐지: 요약 `net_diff` 변조는 `summary` 문제로, diff 변조는 diff/verdict 문제로, `source` mock과 `status` blocked는 각각 탐지되고, endpoint와 bridge 변조도 탐지됨을 확인한다.
- `sam-live-evidence-missing-file` 없는 파일 차단: 없는 증거 파일은 종료코드 2이며 유효로 처리하지 않음을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.sam_live_evidence --file <증거 JSON 경로> [--json]`를 실행한다. 종료코드는 유효 0, 무효 1, 파일 오류 2다.
- 이 하네스는 증거 파일만 읽는다. 실제 API를 호출하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-live-evidence --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 실호출 세션 자체는 이 절차의 범위가 아니다. 빈별 실호출은 2026-10-31과 2026-11-01 커넥터 브리지로 스킬 밖에서 통과한 기록이 따로 있으며(가상 사진의 서로 다른 잘라내기, 실제 빈 촬영 아님), 이 절차의 합성 증거 통과를 그 실호출 성공으로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제 API를 호출하지 않는다. 네트워크와 실제 키를 쓰지 않는다.
- 합성 증거는 헬퍼 상수 `SAM_EVIDENCE_COUNTED`와 `SAM_EVIDENCE_SESSION_ID`로만 만들며 실제 키나 실제 사진이 아니다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-live-evidence --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `drive_sam_live_evidence`로 CLI 서브프로세스와 프로세스 내 검증 함수만 실행한다.
- **유효 증거 확인.** 헬퍼가 `validate_evidence`·`build_report`·`validate_report`로 유효 증거의 valid·source sam·distinct 6·요약 재계산을 대조한다.
- **CLI 확인.** 헬퍼가 임시 증거 파일로 `qa.sam_live_evidence` CLI 텍스트·`--json` 구동을 실행해 종료코드 0과 `VALID: true`·세션·source·distinct·`SUBMISSION_READY: false`를 확인한다.
- **변조 탐지 확인.** 헬퍼가 중복 해시·요약·diff·mock source·endpoint/bridge 변조를 각각 탐지하는지 확인하고, 중복 파일 CLI는 종료코드 1임을 확인한다.
- **없는 파일 확인.** 헬퍼가 없는 파일 CLI 종료코드 2를 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `sam-live-evidence-valid.json`(유효 CLI `--json` stdout 원문)과 `sam-live-evidence-report.json`(`build_report` 보고)이 남고, `summary.json`의 `feature`가 `sam-live-evidence`이며 `valid_ok`가 true, `distinct_image_count`가 6, `duplicate_detected`와 `summary_tamper_detected`가 true, `missing_file_exit_code`가 2인지 대조한다.

## Gotchas

- 합성 증거 통과를 실호출 성공으로 서술하지 않는다. 이 절차는 증거 내부 정합 검증일 뿐이며 API를 호출하지 않는다.
- 빈별 사진은 가상 사진의 서로 다른 잘라내기이며 실제 빈 촬영이나 Pi 실촬영이 아니다. 증거 검증 통과는 제출 준비 완료를 뜻하지 않는다.
- 해시가 하나라도 겹치거나 `distinct_image_count`가 실제 서로 다른 해시 수와 다르면 실패다. SHA-256은 64자 hex여야 한다.
- 요약은 bins에서 재계산한 값과 하나라도 다르면 실패다. diff는 counted-book과, verdict는 diff 부호와 맞아야 한다.
- 없는 파일이나 JSON 오류를 유효로 처리하면 실패다. 종료코드 2를 0이나 1로 바꾸지 않는다.
