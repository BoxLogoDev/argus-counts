# 제출물 인벤토리

제출물 인벤토리는 `qa.submission_inventory`가 제출물 18개(문서 6·영상 2·데모 자산 10)의 존재·크기·SHA-256을 고정하는지 검증하는 절차다. 이 검증은 파일 대조만 하며 실제로 제출하지 않는다: CLI 텍스트·`--json` 출력과 프로세스 내 `build_inventory`·`validate_inventory`·`write_inventory`만으로 구동한다. 인벤토리가 온전해도 제출 가능을 뜻하지 않으며, 블로커 `pi_real_capture_pending`가 남아 있는 동안 `SUBMISSION_READY: false`다. Pi 실촬영 검증 전이며 수치는 데모 기준이다.

## Sub-features

- `inventory-cli-text` CLI 텍스트: `python3 -m qa.submission_inventory`가 종료코드 0을 내고, stdout에 제출물 18/18개 존재와 `BLOCKERS: 1`과 `pi_real_capture_pending`과 `SUBMISSION_READY: false`와 '실제로 제출하지 않는다'와 'Pi 실촬영 검증 전'이 있음을 확인한다.
- `inventory-cli-json` CLI JSON: `python3 -m qa.submission_inventory --json`이 종료코드 0을 내고, `total_files` 18·`present_files` 18·`missing` 빈 목록·blockers [`pi_real_capture_pending`]·`submission_ready` false·저장소 `https://github.com/BoxLogoDev/argus-counts`·마감 `2026-11-05 11:00 KST`이며, deliverables 18개의 category가 document 6·video 2·demo_asset 10이고 각 항목의 크기와 SHA-256이 실제 파일 바이트와 일치함을 확인한다.
- `inventory-build-validate` 프로세스 내 대조: `build_inventory`로 만든 인벤토리를 `validate_inventory`에 넣으면 문제 0건이며, 합계 바이트가 실제 파일 크기의 합과 같음을 확인한다. 구동 함수는 `drive_submission_inventory`다.
- `inventory-tamper` 변조 탐지: 첫 제출물의 `sha256`을 바꾸면 README.md 해시 문제를, `total_bytes`를 바꾸면 합계 문제를, `submission_ready`를 true로 바꾸고 blockers를 비우면 ready·blocker 문제를 각각 지목함을 확인한다.
- `inventory-empty-root` 빈 루트 정직 보고: 빈 디렉터리를 루트로 주면 present 0·missing 18로 누락을 숨기지 않으며, 그 인벤토리 자체는 `validate_inventory`에서 모순이 아님을 확인한다.
- `inventory-write-roundtrip` 쓰기 왕복: `write_inventory`가 임시 디렉터리에 `submission-inventory.json`·`submission-inventory.txt`를 쓰고, 다시 읽은 JSON이 검증을 통과하며 텍스트에 `SUBMISSION_READY: false`와 블로커가 있음을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.submission_inventory`를 실행한다. 기계가 읽을 출력이 필요하면 `--json`을, 인벤토리 파일을 남기려면 `--out-dir <경로>`를 붙인다. 종료코드는 검증 통과 0, 실패 1이다.
- 이 CLI는 파일을 읽어 대조만 하며 실제로 제출하지 않는다. 인벤토리가 온전해도 제출 가능을 뜻하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature submission-inventory --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 제출 경로는 이 절차의 범위가 아니다. 이 절차의 통과를 제출 완료나 제출 준비 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 제출하지 않는다. 네트워크 제출·업로드를 하지 않으며, 파일은 읽기만 하고 쓰기는 임시 디렉터리의 인벤토리 산출에만 한다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature submission-inventory --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 CLI 서브프로세스와 프로세스 내 `build_inventory`·`validate_inventory`·`write_inventory`만으로 `drive_submission_inventory`를 실행한다.
- **CLI 텍스트·JSON 확인.** 헬퍼가 `qa.submission_inventory` CLI를 텍스트와 `--json`으로 실행해 종료코드 0, 제출물 18/18, 블로커 1건, `SUBMISSION_READY: false`, 저장소·마감, category 구성, 각 파일의 크기와 SHA-256 실물 대조를 확인한다.
- **프로세스 내 대조 확인.** 헬퍼가 `build_inventory`와 `validate_inventory`로 문제 0건을 확인한다.
- **변조 탐지 확인.** 헬퍼가 해시·합계·ready/blockers를 각각 변조한 사본을 `validate_inventory`에 넣어 해당 문제를 지목하는지 확인한다.
- **빈 루트·쓰기 왕복 확인.** 헬퍼가 빈 루트에서 missing 18의 정직 보고를, 임시 디렉터리 `write_inventory` 왕복으로 JSON 검증 통과와 텍스트 표기를 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `submission-inventory.json`(CLI `--json` stdout 원문)과 `submission-inventory.txt`(CLI 텍스트 stdout 원문)가 남고, `summary.json`의 `feature`가 `submission-inventory`이며 `total_files` 18·`present_files` 18·`submission_ready` false·`tamper_detected` true·`write_roundtrip_ok` true인지 대조한다.

## Gotchas

- 인벤토리가 온전해도 제출 가능을 뜻하지 않는다. 블로커 `pi_real_capture_pending`가 남아 있는 동안 `submission_ready`는 항상 false여야 한다.
- 실제로 제출하지 않는다. 이 절차는 파일 존재·크기·해시 대조까지만 하며, 통과를 제출 완료로 서술하면 실패다.
- 인벤토리 산출 파일 자체는 제출물 목록에 넣지 않는다. 자기 해시를 자기 안에 적는 모순이 생기기 때문이다.
- 누락을 숨기면 실패다. 빈 루트에서는 missing 18을 그대로 보고해야 하며, 누락 보고 자체를 검증 모순으로 만들지 않는다.
- 해시는 실제 파일 바이트로 다시 계산해 대조한다. 인벤토리 안의 값만 서로 비교하면 낡은 파일이 섞여도 잡지 못한다.
- Pi 실촬영 검증 전이며 수치는 데모 기준이다. 인벤토리 통과를 Pi 실촬영 성공으로 서술하지 않는다.
