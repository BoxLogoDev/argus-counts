# 제출 패키지 내보내기

제출 패키지 내보내기는 `qa.package_export`가 제출물 인벤토리(qa.submission_inventory)가 고정한 제출물 18개를 staging 디렉터리로 실제로 복사하고, 복사본의 크기·SHA-256을 원본과 다시 대조하는지 검증하는 절차다. 이 검증은 실제로 제출하지 않는다: CLI는 임시 staging 디렉터리로만 구동하고 프로세스 내 `build_export`·`validate_export`으로만 확인하며, 재검증 증거는 깨끗한 staging을 새로 만들어 CLI `--verify-dir`(텍스트·`--json`)와 프로세스 내 `verify_export_dir`로 다시 대조한다. 내보내기가 온전해도 제출 가능을 뜻하지 않으며, Pi 실촬영 검증 전이고 수치는 데모 기준이다.

## Sub-features

- `package-export-cli` CLI 내보내기: `python3 -m qa.package_export --out-dir <임시 staging>`이 종료코드 0을 내고, 텍스트에 `제출물 18/18개 복사`·`BLOCKERS: 1`·`pi_real_capture_pending`·`SUBMISSION_READY: false`·`매니페스트: package-manifest.json`가 있으며, `--json`에서는 total_files 18·copied_files 18·missing []·blockers [`pi_real_capture_pending`]·submission_ready false·honesty 3종(실제로 제출하지 않는다, Pi 실촬영 검증 전, 데모 기준)임을 확인한다.
- `package-export-build` 프로세스 내 내보내기: `build_export`가 제출물 18개를 상대경로 그대로 복사하고 복사본 크기·SHA-256을 다시 계산하며, `package-manifest.json`을 staging에 쓰되 매니페스트 자체는 복사 대상에 넣지 않고, 모든 복사본이 `validate_export`에서 문제 0건임을 확인한다. 구동 함수는 `drive_package_export`다.
- `package-export-tamper` 변조 탐지: 복사본 파일(README.md)을 변조하면 `validate_export`가 그 경로를 지목하고, submission_ready를 true로 바꾸면 submission_ready 문제를 지목함을 확인한다.
- `package-export-verify` 재검증 증거: 깨끗한 staging에 CLI `python3 -m qa.package_export --verify-dir <staging> --json`이 종료코드 0·`verified` true·`problems` []·copied 18·submission_ready false를 내고, 텍스트 실행은 `Argus 제출 패키지 재검증`·`VERIFIED: true`·`SUBMISSION_READY: false`를 내며, 실행 전후 staging 파일 스냅샷(상대경로·크기·SHA-256)이 불변(읽기 전용)이고, 프로세스 내 `verify_export_dir`도 문제 0건임을 확인한다. 복사본 README.md를 변조한 staging은 종료코드 1·verified false로 탐지하고, 매니페스트 없는 빈 디렉터리는 종료코드 2다.
- `package-export-invalid-args` 인자 오류 차단: `python3 -m qa.package_export`(`--out-dir` 없음)가 종료코드 2로 거부되고, `--out-dir`와 `--verify-dir` 동시 지정도 종료코드 2로 거부됨을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.package_export --out-dir <경로>`를 실행한다. 기계가 읽을 출력이 필요하면 `--json`을 붙인다. 종료코드는 검증 통과 0, 검증 실패 1, 인자 오류 2다.
- 이 CLI는 staging 디렉터리로 파일을 복사할 뿐 실제로 제출하지 않으며, 내보내기가 온전해도 제출 가능을 뜻하지 않는다. 블로커 `pi_real_capture_pending`이 남아 있는 동안 `SUBMISSION_READY: false`가 정답이다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature package-export --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 제출 경로는 이 절차의 범위가 아니다. 이 절차의 통과를 제출 완료나 제출 준비 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 제출하지 않는다. 네트워크 호출도 하지 않으며, 내보내기 대상은 임시 staging 디렉터리뿐이다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature package-export --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 CLI 서브프로세스와 프로세스 내 `build_export`·`validate_export`만으로 `drive_package_export`를 실행한다.
- **CLI 내보내기 확인.** 헬퍼가 `qa.package_export` CLI를 임시 staging으로 텍스트·`--json` 실행해 종료코드와 복사 18/18·합계 바이트·블로커·honesty 표기를 확인하고, `--out-dir` 없는 실행이 종료코드 2인지 확인한다.
- **프로세스 내 내보내기 확인.** 헬퍼가 `build_export`로 임시 staging에 복사하고 복사본 18개의 실존과 SHA-256 원본 일치, 매니페스트 존재와 자기 참조 없음, `validate_export` 문제 0건을 확인한다.
- **변조 확인.** 헬퍼가 복사본 README.md 변조 탐지와 submission_ready 변조 탐지를 확인한다.
- **재검증 확인.** 헬퍼가 깨끗한 staging을 새로 만들어 `--verify-dir` 텍스트·`--json` 구동, 읽기 전용 스냅샷 불변, 프로세스 내 `verify_export_dir`, 변조 staging 탐지(종료코드 1), 매니페스트 없음(종료코드 2), 인자 충돌(종료코드 2)을 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `package-export.json`(CLI `--json` stdout 원문)과 `package-export.txt`(CLI 텍스트 stdout 원문)가 남고, `summary.json`의 `feature`가 `package-export`이며 `total_files` 18·`copied_files` 18·`blockers` [`pi_real_capture_pending`]·`submission_ready` false·`validate_problems` []·`manifest_ok` true·`tamper_detected` true·`ready_tamper_detected` true·`invalid_exit_code` 2·`verify_verified` true·`verify_exit_code` 0·`verify_text_ok` true·`verify_readonly` true·`verify_tamper_detected` true·`verify_tamper_exit_code` 1·`verify_missing_exit_code` 2·`verify_conflict_exit_code` 2·`verify_inproc_ok` true인지 대조하고, `package-export-verify.json`(재검증 `--json` stdout 원문)과 `package-export-verify.txt`(재검증 텍스트 stdout 원문)도 남는지 확인한다.

## Gotchas

- 내보내기는 staging 복사·해시 대조만 한다. 복사 18/18이어도 제출 가능을 뜻하지 않으며 submission_ready는 항상 false다.
- 매니페스트(package-manifest.json) 자체는 복사 대상이 아니다. 자기 해시를 자기 안에 적는 모순을 피하기 위해서다.
- 제출물 원본이 바뀌면 복사본 해시 대조가 달라진다. 기준을 고정하지 않은 구동의 total_bytes를 결정적 증거로 쓰지 않는다.
- 파일 입력 폴백은 Pi 실촬영이 아니다. 이 내보내기로 Pi 실촬영 검증 완료를 주장하지 않는다.
- staging 디렉터리는 임시 산출물이다. 증거는 매니페스트와 CLI 원문이며, staging 복사본 자체를 제출물로 서술하지 않는다.
- 재검증(`--verify-dir`)은 읽기 전용이다. 변조 탐지용 staging은 별도로 만들어야 하며, 깨끗한 staging 자체를 변조하면 이후 재검증 증거가 무효가 된다. 재검증 통과도 제출이나 제출 준비 완료를 뜻하지 않는다.
