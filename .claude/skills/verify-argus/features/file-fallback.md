# 파일 입력 폴백

파일 입력 폴백은 Pi 실기가 2026-11-02 기준일까지 늦을 경우 데모 컷 3을 파일 입력 경로로 대체하기 위한 자산(`demo.fallback`)을 검증하는 절차다. 이 절차는 `demo.fallback` CLI를 임시 출력 디렉터리로 구동해 `fallback.json`과 `fallback.txt`를 새로 만들고, `build_fallback_manifest`와 `validate_fallback`로 그 자산이 Pi 실촬영이 아님을 확인한다. 세션은 `FALLBACK-FILE-INPUT`이며 사진 바이트는 `fake-fallback-photo-<빈>` 가짜 바이트다. 성공해도 Pi 실촬영 검증 완료가 아니며, 컷 3의 실제 전환 확정은 2026-11-02 기준일에 별도로 판단한다.

## Sub-features

- `fallback-cli-write` CLI 자산 생성: `python3 -m demo.fallback --out <임시 디렉터리>`가 종료코드 0과 `검증 통과`를 내고 `fallback.json`·`fallback.txt`를 만드는지 확인한다. `drive_file_fallback`이 이 CLI 출력을 증거로 남긴다.
- `fallback-manifest-shape` 매니페스트 모양: `cut_index` 3, `replaces`가 `pi-placeholder`, `decision_date`가 `2026-11-02`, `is_pi_real_capture`가 `false`, `capture_source`가 `file`, `source`가 `mock`, `session_id`가 `FALLBACK-FILE-INPUT`인지 확인한다.
- `fallback-summary-bins` 요약과 빈: 요약이 빈 6개·일치 4·불일치 2·절대 차이 6·순차이 0이고, 빈 6개의 사진 SHA-256이 `fake_photo_bytes` 가짜 바이트 해시와 일치하며, `A-01-02`가 장부 8·실측 5·`short`·차이 -3인지 확인한다. 수치는 데모 기준이다.
- `fallback-validate-asset` 검증과 저장소 자산: `validate_fallback` 결과가 비어 있고, 저장소 자산 `demo/assets/fallback.json`도 같은 검증을 통과하며 요약이 같은지 확인한다.
- `fallback-tamper-detection` 변조 탐지: 복사본에서 `is_pi_real_capture`를 `true`로 바꾸거나 `capture_source`를 `pi-camera`로 바꾸면 `validate_fallback`이 문제를 잡아야 한다. 원본 파일은 바꾸지 않는다.
- `fallback-honesty` 정직성 표기: `honesty`에 Pi 실촬영이 아닙니다·Pi 실촬영 검증 전·SAM 실호출 미실시·데모 기준 표기가 모두 있고, `fallback.txt`에도 파일 입력 폴백과 Pi 실촬영이 아닙니다와 데모 기준이 있는지 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 프로젝트 루트에서 `python3 -m demo.fallback`를 실행하는 것이다. 기본 출력은 `demo/assets/`의 `fallback.json`·`fallback.txt`이며 `--out`으로 출력 디렉터리를 바꿀 수 있다.
- 이 자산은 Pi가 늦을 경우 컷 3을 파일 입력으로 보여 주기 위한 대체안이다. Pi 실촬영 컷이 아니며, 촬영 단계는 파일 기반 사진 입력 파이프라인(`terminal.photo_intake`)으로 수행한다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature file-fallback --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 Pi 촬영 경로는 이 절차의 범위가 아니다. Pi가 도착하면 `pi_smoke` 하네스로 빈 1개부터 실촬영을 검증하고, 이 폴백은 대체안으로만 남긴다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- `demo.fallback` 모듈과 저장소 자산 `demo/assets/fallback.json`이 있다.
- 실제로 촬영하지 않는다. 사진은 `fake-fallback-photo-` 가짜 바이트로만 만들고, SAM 실호출도 하지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature file-fallback --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `drive_file_fallback`이 CLI를 임시 출력 디렉터리로 구동한다.
- **CLI 자산 확인.** 헬퍼가 종료코드 0과 `검증 통과` 표기, 생성된 `fallback.json`·`fallback.txt` 실물을 확인한다.
- **매니페스트 대조.** 헬퍼가 컷 3·`pi-placeholder`·2026-11-02·`is_pi_real_capture` false·`capture_source` file·`source` mock·`FALLBACK-FILE-INPUT`을 대조한다.
- **요약과 사진 해시 확인.** 헬퍼가 요약 기준값과 빈 6개를 대조하고, 전 빈 사진 SHA-256이 가짜 바이트 해시와 일치하는지, `A-01-02`가 `short`·-3인지 확인한다.
- **검증과 자산 확인.** 헬퍼가 `validate_fallback` 결과가 비어 있는지와 저장소 자산 `fallback.json`의 유효성을 확인한다.
- **변조 탐지 확인.** 헬퍼가 복사본에서 실촬영 플래그와 `capture_source`를 바꿔 `validate_fallback`이 각각 문제를 잡는지 확인한다. 원본은 수정하지 않는다.
- **증거 확인.** 종료 후 증거 디렉터리에 `fallback.json`과 `fallback.txt`가 남고, `summary.json`의 `feature`가 `file-fallback`이며 `tamper_detected`와 `capture_source_tamper_detected`와 `asset_valid`가 `true`, `is_pi_real_capture`가 `false`인지 대조한다.

## Gotchas

- 이 자산을 Pi 실촬영으로 서술하면 실패다. `is_pi_real_capture`는 항상 `false`여야 하고 `capture_source`는 `pi-camera`가 아니라 `file`이어야 한다.
- 가짜 사진을 실제 촬영 파일로 치면 실패다. 사진 해시는 `fake-fallback-photo-<빈>` 바이트 해시와 일치해야 하며, 그 일치가 곧 가짜 바이트로 만들었다는 증거다.
- 수치를 실제 성과처럼 고치면 실패다. 요약은 데모 기준 빈 6개·일치 4·불일치 2로 고정해 대조한다.
- 변조 검사는 복사본으로만 한다. 저장소 자산 `fallback.json` 원본을 고쳐 탐지를 확인하지 않는다.
- 폴백 통과가 컷 3 전환 확정을 뜻하지 않는다. 전환 판단은 2026-11-02 기준일에 Pi 도착 상태를 보고 별도로 하며, 그 전에는 대체안 준비로만 보고한다.
- SAM 실호출은 하지 않는다. 계수는 모의 어댑터 기준이며 `source`가 `mock`이 아니면 실패로 본다.
