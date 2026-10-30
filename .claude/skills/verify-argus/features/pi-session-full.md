# Pi 전체 촬영 세션

Pi 전체 촬영 세션은 `qa.pi_session`의 `run_pi_full_session`이 준비 점검을 통과한 뒤에만 데모 빈 6개 전체의 촬영 세션을 시도하는지 검증하는 절차다. 이 검증은 실제 촬영을 하지 않는다: 기본 CLI 실행의 차단 보고와 프로세스 안에 주입한 가짜 session, 실제 `terminal.pi_session`에 가짜 runner를 주입한 경로만으로 구동한다. 가짜 성공은 데모 기준 수량의 대조 검증일 뿐이며, 전체 세션을 시도하거나 통과해도 Pi 실촬영 검증 완료를 뜻하지 않는다. 세션 ID 예시는 `VERIFY-PI-FULL-1`이다. 블로커는 결정적 순서로 `pi_device_arrival_not_confirmed`, `pi_camera_command_missing` 두 가지이며, 텍스트 출력의 `SESSION_PASSED` 줄이 세션 통과 여부를 나타낸다.

## Sub-features

- `pi-full-session-blocked-text` 기본 차단 텍스트: CLI `python3 -m qa.pi_session`가 종료코드 1을 내고, stdout에 `STATUS: blocked`와 `ATTEMPTED: false`와 `BLOCKERS: 2`와 `SESSION_PASSED: false`와 블로커 id 두 개가 이 순서대로 있음을 확인한다.
- `pi-full-session-blocked-json` 기본 차단 JSON: `python3 -m qa.pi_session --json`이 종료코드 1을 내고, `status`가 `blocked`이며 `attempted`와 `ready_for_real_capture`가 모두 `false`이고 blockers id 목록이 위 두 id와 일치하며 `source`와 `capture_source`가 `null`, `bins`가 빈 목록, `summary`가 `null`임을 확인한다. `honesty`에는 준비 점검을 통과하지 못하면 실제로 촬영하지 않는다는 줄과 실패를 가짜 파일이나 모의 결과로 대체하지 않는다는 줄, 전체 세션을 시도하거나 통과해도 Pi 실촬영 검증 완료를 뜻하지 않는다는 줄이 각각 있다.
- `pi-full-session-device-confirmed` 장치 확인 시 카메라 블로커만: `python3 -m qa.pi_session --device-confirmed --json`은 이 검증 환경(카메라 명령 없음)에서 종료코드 1을 내고 blockers가 `pi_camera_command_missing` 하나만 남음을 확인한다.
- `pi-full-session-fake-passed` 가짜 session 성공: 프로세스 안에서 `run_pi_full_session`에 장치 확인과 가짜 `which`(`libcamera-still`), 데모 기준 결과를 돌려주는 가짜 session을 넘기면 `status`가 `passed`이고 `source`가 `mock`, `capture_source`가 `pi-camera`, session 호출이 데모 빈 6개 순서와 세션 ID `VERIFY-PI-FULL-1`로 1회이며, 요약이 빈 6·일치 4·불일치 2·절대 차이 6·순 차이 0이고 A-01-02가 장부 8·실측 5·diff -3·short·사진 sha가 가짜 sha, B-01-02가 diff 3·over임을 확인한다.
- `pi-full-session-blocked-session` 차단 시 session 무호출: 준비 안 된 환경에서는 `blocked`이고 session을 호출하지 않는다.
- `pi-full-session-real-runner` 실제 pi_session+가짜 runner 성공: session을 주입하지 않고 가짜 `runner`(`fake-pi-full-session-jpeg` 바이트 기록)만 주입하면 실제 `terminal.pi_session` 경로로 `passed`가 되고, 전 빈 사진 `sha256`이 그 바이트의 SHA-256과 같으며 빈별 캡처 파일이 실제로 있음을 확인한다.
- `pi-full-session-capture-source-blocked` capture_source 차단: 결과의 `capture_source`가 `file`이면 세션 전체가 `failed`이고 `error_type`이 `unexpected_capture_source`이며 `summary`가 `null`임을 확인한다. 한 빈이라도 어긋나면 부분 성공으로 보이지 않는다.
- `pi-full-session-error-blocked` 오류 차단: `PiCaptureError`를 일으키는 session을 넘기면 `failed`이고 `error_type`이 `PiCaptureError`이며, 일반 `RuntimeError`를 일으키는 session은 `error_type`이 `RuntimeError`이고 예외 원본 문자열이 보고에 새지 않음을 확인한다. 실패를 가짜 파일이나 모의 결과로 대체하지 않는다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.pi_session`를 실행한다. 장치 도착을 외부에서 확인했으면 `--device-confirmed`를, 기계가 읽을 출력이 필요하면 `--json`을, 캡처 디렉터리는 `--out-dir`를, 세션 이름은 `--session-id`를 붙인다. 종료코드는 통과 0, 차단 1, 실패 2다.
- 준비가 안 된 기본 실행에서는 실제로 촬영하지 않는다. 차단 보고만 나오고 어떤 빈도 촬영하지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-session-full --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 Pi 장치에서 촬영하는 경로는 이 절차의 범위가 아니다. 이 절차의 가짜 성공을 Pi 실촬영 성공이나 Pi 실촬영 검증 완료로 서술하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제 촬영을 하지 않는다. 실제 카메라 명령을 실행하지 않으며, 헬퍼의 기본 CLI 실행은 이 환경에 카메라 명령이 없다는 전제로 차단 보고를 기대한다.
- 가짜 session 결과의 사진 sha는 헬퍼 상수 `PI_FULL_FAKE_SHA`, 가짜 runner 바이트는 `PI_FULL_FAKE_CONTENT`(`fake-pi-full-session-jpeg`)로만 만들며, 실제 사진이나 회사 자료를 쓰지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-session-full --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 실제 촬영 없이 CLI 서브프로세스와 프로세스 내 `run_pi_full_session`만으로 `drive_pi_session_full`를 실행한다.
- **기본 차단 텍스트 확인.** 헬퍼가 `qa.pi_session` CLI를 서브프로세스로 실행해 종료코드 1, `STATUS: blocked`, `ATTEMPTED: false`, `BLOCKERS: 2`, `SESSION_PASSED: false`, 블로커 id 두 개의 순서를 대조한다.
- **기본 차단 JSON 확인.** 헬퍼가 `--json` CLI를 실행해 `status` `blocked`, `attempted`와 `ready_for_real_capture`의 `false`, 블로커 id 목록과 `EXPECTED_PI_READINESS_BLOCKER_IDS`의 일치, `source`와 `capture_source`의 `null`, `bins`의 빈 목록, `summary`의 `null`, `honesty`의 촬영하지 않는다는 줄과 대체하지 않는다는 줄과 검증 완료를 뜻하지 않는다는 줄을 확인한다.
- **장치 확인 확인.** 헬퍼가 `--device-confirmed --json` CLI를 실행해 블로커가 `pi_camera_command_missing` 하나만 남음을 확인한다.
- **가짜 session 성공 확인.** 헬퍼가 프로세스 안에서 장치 확인과 가짜 `which`로 `run_pi_full_session`를 부르면 가짜 session이 데모 기준 결과를 돌려줘 `passed`가 되고, session 호출 1회와 빈별 대조, 요약 수치를 확인한다. 준비 안 된 환경에서는 `blocked`이며 session 호출이 0건이다.
- **실제 pi_session+가짜 runner 확인.** 헬퍼가 session 주입 없이 가짜 `runner`로 실제 `terminal.pi_session` 경로를 구동해 `passed`와 전 빈 사진 해시, 빈별 캡처 파일 존재를 확인한다.
- **capture_source 차단 확인.** 헬퍼가 `capture_source` `file`인 결과를 돌려주는 session으로 세션 전체 `failed`와 `error_type` `unexpected_capture_source`를 받는지 확인한다.
- **오류 차단 확인.** 헬퍼가 `PiCaptureError`와 일반 예외를 일으키는 session으로 각각 `failed`와 해당 `error_type`을 받고, 예외 원본 문자열이 보고에 없는지 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pi-full-session-blocked.json`(기본 차단 `--json` stdout 원문)과 `pi-full-session-passed.json`(가짜 session 성공 보고)이 남고, `summary.json`의 `feature`가 `pi-session-full`이며 `fake_passed`가 `true`, `blocked_session_calls`가 0, `real_session_passed`가 `true`, `sentinel_leaked`가 `false`인지 대조한다.

## Gotchas

- 차단 상태에서 session을 부르면 실패다. 준비 점검이 통과하지 못한 보고는 `attempted`가 `false`여야 하고 session 호출 기록이 비어 있어야 한다.
- 가짜 성공을 Pi 실촬영 성공으로 서술하지 않는다. 이 절차의 `passed`는 가짜 session·가짜 runner와 데모 기준 수량의 대조 검증이며, Pi 실촬영 검증 완료와 섞지 않는다.
- 전체 세션을 시도하거나 통과해도 Pi 실촬영 검증 완료를 뜻하지 않는다. 실제 장치에서 통과한 기록이 별도로 필요하다.
- 실패를 가짜 파일이나 모의 결과로 대체하면 실패다. 한 빈이라도 `PiCaptureError`가 나거나 `capture_source`가 `pi-camera`가 아니면 세션 전체를 `failed`로 보고하고 `summary`는 `null`이다.
- 블로커 순서는 결정적이다: `pi_device_arrival_not_confirmed`, `pi_camera_command_missing`. 순서가 바뀌면 실패로 본다.
- 예외 원본 문자열이 보고 JSON·CLI stdout·증거 파일에 나타나면 실패로 본다. 오류는 `error_type`으로만 보고한다.
- 가짜 사진 바이트(`fake-pi-full-session-jpeg`)가 바뀌면 기대 SHA-256도 달라진다. 바이트 내용과 해시 기대값은 함께 유지한다.
