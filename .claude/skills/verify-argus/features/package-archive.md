# 제출 패키지 영속 아카이브

제출 패키지 영속 아카이브는 `qa.package_archive`가 최종 묶음(qa.final_package)이 임시 staging에서만 확인하던 패키지 내보내기를 영속 디렉터리에 실제로 남기고, 아카이브 수치(복사 수·누락·합계 바이트·재검증 결과·선택 영상)를 최종 묶음 보고와 교차 대조하는지 검증하는 절차다. 구동 함수는 `drive_package_archive`다. 이 검증은 실제로 제출하지 않는다: CLI는 임시 디렉터리로만 구동하고 프로세스 내 `build_archive`·`build_archive_verify`·`validate_archive`으로만 확인한다. 아카이브가 archived여도 제출 준비 완료를 뜻하지 않으며, Pi 실촬영 검증 전이고 수치는 데모 기준이다.

## Sub-features

- `package-archive-cli` CLI 아카이브 생성: `python3 -m qa.package_archive --out-dir <임시 디렉터리>`가 종료코드 0을 내고, 텍스트에 `STATUS: archived`·`COPIED: 18`·`TOTAL: 18`·`ARCHIVE_VERIFIED: true`·선택 영상 `demo/assets/argus-demo-fallback-draft.mp4`·`SUBMISSION_READY: false`가 있으며, `--json`에서는 status archived·mode export·copied 18·total 18·missing []·verify_verified true·archive_verified true·blockers [`pi_real_capture_pending`]·submission_ready false·selected_copied true·selected_sha256 64자 hex·honesty(실제로 제출하지 않는다, 제출 준비 완료를 뜻하지 않는다, Pi 실촬영 검증 전, 데모 기준)임을 확인한다.
- `package-archive-build` 프로세스 내 아카이브: `build_archive`가 제출물 18개를 영속 디렉터리에 상대경로 그대로 복사하고 `package-manifest.json`을 남기며, 선택 영상 복사본의 SHA-256과 크기가 보고의 selected_sha256·selected_size_in_archive와 일치하고, 모든 보고가 `validate_archive`에서 문제 0건임을 확인한다.
- `package-archive-tamper` 변조 탐지: 보고의 status를 mismatch로 바꾸면 `validate_archive`가 status 문제를 지목하고, submission_ready를 true로 바꾸면 submission_ready 문제를 지목함을 확인한다.
- `package-archive-verify` 재검증 증거: 깨끗한 아카이브에 CLI `python3 -m qa.package_archive --verify-dir <아카이브> --json`이 종료코드 0·mode verify·status archived·archive_verified true·submission_ready false를 내고, 텍스트 실행은 `STATUS: archived`·`ARCHIVE_VERIFIED: true`·`SUBMISSION_READY: false`를 내며, 실행 전후 아카이브 파일 스냅샷(상대경로·크기·SHA-256)이 불변(읽기 전용)이고, 프로세스 내 `build_archive_verify`도 archived·문제 0건임을 확인한다. 복사본 README.md를 변조한 아카이브는 종료코드 1·archive_verified false로 탐지하고, 매니페스트 없는 빈 디렉터리는 종료코드 1·status가 archived가 아님으로 탐지한다.
- `package-archive-invalid-args` 인자 오류 차단: `python3 -m qa.package_archive`(`--out-dir`·`--verify-dir` 없음)가 종료코드 2로 거부되고, `--out-dir`와 `--verify-dir` 동시 지정도 종료코드 2로 거부됨을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.package_archive --out-dir <경로>`로 새 아카이브를 만들고, 이미 만든 아카이브는 `python3 -m qa.package_archive --verify-dir <경로>`로 파일을 쓰지 않고 재검증한다. 기계가 읽을 출력이 필요하면 `--json`을 붙인다. 종료코드는 아카이브 완결·검증 통과 0, 불완전·불일치 1, 입력 오류 2다.
- 이 CLI는 디렉터리로 파일을 복사할 뿐 실제로 제출하지 않으며, 아카이브 완결은 제출 준비 완료를 뜻하지 않는다. 블로커 `pi_real_capture_pending`이 남아 있는 동안 `SUBMISSION_READY: false`가 정답이다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature package-archive --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 제출 경로는 이 절차의 범위가 아니다. 이 절차의 통과를 제출 완료나 제출 준비 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 제출하지 않는다. 네트워크 호출도 하지 않으며, 아카이브 대상은 임시 디렉터리뿐이다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature package-archive --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 CLI 서브프로세스와 프로세스 내 `build_archive`·`build_archive_verify`·`validate_archive`만으로 `drive_package_archive`를 실행한다.
- **CLI 아카이브 확인.** 헬퍼가 `qa.package_archive` CLI를 임시 디렉터리로 텍스트·`--json` 실행해 종료코드와 archived·복사 18/18·선택 영상·블로커·honesty 표기를 확인하고, 인자 없음과 인자 충돌이 종료코드 2인지 확인한다.
- **프로세스 내 아카이브 확인.** 헬퍼가 `build_archive`로 임시 디렉터리에 복사하고 매니페스트 존재, 선택 영상 복사본의 SHA-256·크기 일치, `validate_archive` 문제 0건을 확인한다.
- **변조 확인.** 헬퍼가 보고의 status 변조 탐지와 submission_ready 변조 탐지를 확인한다.
- **재검증 확인.** 헬퍼가 깨끗한 아카이브를 새로 만들어 `--verify-dir` 텍스트·`--json` 구동, 읽기 전용 스냅샷 불변, 프로세스 내 `build_archive_verify`, 변조 아카이브 탐지(종료코드 1), 매니페스트 없음 탐지(종료코드 1)를 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `package-archive.json`(CLI `--json` stdout 원문)과 `package-archive.txt`(CLI 텍스트 stdout 원문)가 남고, `summary.json`의 `feature`가 `package-archive`이며 `status` archived·`copied` 18·`total` 18·`verify_verified` true·`archive_verified` true·`selected_video`가 폴백 렌더·`blockers` [`pi_real_capture_pending`]·`submission_ready` false·`validate_problems` []·`manifest_ok` true·`selected_sha_ok` true·`tamper_detected` true·`ready_tamper_detected` true·`invalid_exit_code` 2·`conflict_exit_code` 2·`verify_exit_code` 0·`verify_text_ok` true·`verify_readonly` true·`verify_tamper_detected` true·`verify_tamper_exit_code` 1·`verify_missing_exit_code` 1·`verify_inproc_ok` true인지 대조하고, `package-archive-verify.json`(재검증 `--json` stdout 원문)과 `package-archive-verify.txt`(재검증 텍스트 stdout 원문)도 남는지 확인한다.

## Gotchas

- 아카이브는 파일 복사·해시 대조·최종 묶음 교차 대조만 한다. archived여도 제출 가능을 뜻하지 않으며 submission_ready는 항상 false다.
- 매니페스트(package-manifest.json) 자체는 복사 대상이 아니다. 자기 해시를 자기 안에 적는 모순을 피하기 위해서다.
- 제출물 원본이 바뀌면 아카이브 해시 대조가 달라진다. 기준을 고정하지 않은 구동의 total_bytes를 결정적 증거로 쓰지 않는다.
- 파일 입력 폴백은 Pi 실촬영이 아니다. 선택 영상이 폴백 렌더라도 Pi 실촬영 검증 완료를 주장하지 않는다.
- 재검증(`--verify-dir`)은 읽기 전용이다. 변조 탐지용 아카이브는 별도로 만들어야 하며, 깨끗한 아카이브 자체를 변조하면 이후 재검증 증거가 무효가 된다. 재검증 통과도 제출이나 제출 준비 완료를 뜻하지 않는다.
- 검증 헬퍼가 만드는 아카이브는 임시 디렉터리의 산출물이다. 제출일에 대조할 영속 아카이브 자체와 혼동하지 않는다.
