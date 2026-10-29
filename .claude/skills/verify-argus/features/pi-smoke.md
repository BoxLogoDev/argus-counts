# Pi 단일 빈 스모크

Pi 단일 빈 스모크는 `qa.pi_smoke`의 `run_smoke`가 준비 점검(`ready_for_real_capture`가 `true`)을 통과한 뒤에만 단일 빈 1개에 대해 촬영을 시도하는지 검증하는 절차다. 이 검증은 실제로 촬영하지 않는다: 기본 CLI 실행의 차단 보고와 프로세스 안에 주입한 가짜 session, 실제 `pi_session`에 주입한 가짜 runner만으로 구동한다. 성공해도 전체 세션 성공을 뜻하지 않는다. Pi 실촬영 검증 완료도 아니다. 단일 빈 1개의 스모크일 뿐이다. 기본 빈은 `A-01-02`이며 장부 수량은 8이다. 블로커는 결정적 순서로 `pi_device_arrival_not_confirmed`, `pi_camera_command_missing` 두 가지이며, 텍스트 출력의 `SMOKE_PASSED` 줄이 스모크 통과 여부를 나타낸다. 가짜 촬영 바이트는 `fake-pi-smoke-jpeg`이며, 실패하면 가짜 파일이나 모의 결과로 대체하지 않는다.

## Sub-features

- `pi-smoke-blocked-text` 기본 차단 텍스트: CLI `python3 -m qa.pi_smoke`가 종료코드 1을 내고, stdout에 `STATUS: blocked`와 `ATTEMPTED: false`와 `BLOCKERS: 2`와 `SMOKE_PASSED: false`와 블로커 id `pi_device_arrival_not_confirmed`, `pi_camera_command_missing`이 이 순서대로 있음을 확인한다.
- `pi-smoke-blocked-json` 기본 차단 JSON: `python3 -m qa.pi_smoke --json`이 종료코드 1을 내고, `status`가 `blocked`이며 `attempted`와 `ready_for_real_capture`가 모두 `false`이고 blockers id 목록이 위 두 id와 일치하며 `counted_qty`와 `source`, `capture_source`가 `null`임을 확인한다. `honesty`에는 준비 점검을 통과하지 못하면 실제로 촬영하지 않는다는 줄과 실패를 가짜 파일이나 모의 결과로 대체하지 않는다는 줄이 각각 있다.
- `pi-smoke-device-confirmed` CLI 장치 확인 후에도 카메라 차단: 이 VM처럼 카메라 명령이 없는 환경에서 `python3 -m qa.pi_smoke --device-confirmed --json`을 실행하면 종료코드 1과 블로커 `pi_camera_command_missing` 하나만 남음을 확인한다.
- `pi-smoke-fake-passed` 가짜 session 성공: 프로세스 안에서 `run_smoke`에 `libcamera-still`만 찾는 가짜 `which`와 장치 확인, `capture_source`가 `pi-camera`인 결과를 돌려주는 가짜 session을 넘기면 `status`가 `passed`이고 `source`가 `mock`, `counted_qty` 5, `book_qty` 8, `diff` -3, `photo_image_ref`가 `A-01-02.jpg`이며 session 호출이 `A-01-02` 한 번뿐임을 확인한다. 같은 가짜 session으로 준비 안 된 환경을 넘기면 `blocked`이고 session을 호출하지 않으며 `output_dir`이 생기지 않는다.
- `pi-smoke-real-session-fake-runner` 실제 `pi_session`과 가짜 runner 성공: `session_fn` 없이 `-o` 뒤 경로에 `fake-pi-smoke-jpeg` 바이트를 쓰는 가짜 runner를 넘기면 `status`가 `passed`이고 `counted_qty` 5, `diff` -3이며 `photo_sha256`가 그 바이트의 SHA-256과 일치하고 `A-01-02.jpg` 파일이 있음을 확인한다.
- `pi-smoke-unexpected-capture-source` capture_source 차단: `capture_source`가 `file`인 결과를 돌려주는 session을 넘기면 `status`가 `failed`이고 `error_type`이 `unexpected_capture_source`임을 확인한다.
- `pi-smoke-error-blocked` 오류 차단: `PiCaptureError`를 일으키는 session을 넘기면 `status`가 `failed`이고 `error_type`이 `PiCaptureError`이며 `counted_qty`가 `null`임을 확인한다. 일반 예외(`RuntimeError`)를 일으키는 session을 넘겨도 예외 원본 문자열이 보고에 새어 나오지 않는다.
- `pi-smoke-unknown-bin` 알 수 없는 빈 차단: `bin_id`에 `Z-99-99`를 넘기면 `status`가 `failed`이고 `error_type`이 `unknown_bin`이며 `attempted`가 `false`이고 session을 호출하지 않는다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.pi_smoke`를 실행한다. Pi 장치 도착을 외부에서 확인했으면 `--device-confirmed`를, 기계가 읽을 출력이 필요하면 `--json`을, 다른 빈을 보려면 `--bin`을, 캡처 디렉터리를 정하려면 `--out-dir`를 붙인다. 종료코드는 통과 0, 차단 1, 실패 2다.
- 준비가 안 된 기본 실행에서는 실제로 촬영하지 않는다. 차단 보고만 나오고 촬영 세션은 부르지 않는다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-smoke --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 장치와 카메라(`libcamera-still`)로 촬영하는 경로는 이 절차의 범위가 아니다. 성공해도 전체 세션 성공이나 Pi 실촬영 검증 완료가 아니므로, 전체 세션 평가는 실촬영 뒤 별도로 한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제로 촬영하지 않는다. 카메라 명령을 실행하지 않으며, 가짜 session과 가짜 `which`·가짜 runner는 프로세스 안에서만 주입한다.
- 이 VM에는 카메라 명령이 없다는 것이 기본 차단과 `--device-confirmed` 뒤 카메라 블로커 하나만 남는 기대값의 전제다. 카메라 명령이 실제로 있는 환경에서는 기본 차단 기대값이 달라질 수 있다.
- 가짜 촬영 바이트는 헬퍼 상수 `PI_SMOKE_FAKE_CONTENT`(`fake-pi-smoke-jpeg`)뿐이다. 실제 촬영 파일로 증거를 만들지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-smoke --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 실제 촬영 없이 CLI 서브프로세스와 프로세스 내 `run_smoke`만으로 `drive_pi_smoke`를 실행한다.
- **기본 차단 텍스트 확인.** 헬퍼가 `qa.pi_smoke` CLI를 서브프로세스로 실행해 종료코드 1, `STATUS: blocked`, `ATTEMPTED: false`, `BLOCKERS: 2`, `SMOKE_PASSED: false`, 블로커 id 두 개의 순서를 대조한다.
- **기본 차단 JSON 확인.** 헬퍼가 `--json` CLI를 실행해 `status` `blocked`, `attempted`와 `ready_for_real_capture`의 `false`, 블로커 id 목록과 `EXPECTED_PI_READINESS_BLOCKER_IDS`의 일치, `counted_qty`와 `source`·`capture_source`의 `null`, `honesty`의 촬영하지 않는다는 줄과 대체하지 않는다는 줄을 확인한다.
- **CLI 장치 확인 확인.** 헬퍼가 `--device-confirmed --json` CLI를 실행해 이 VM에서는 종료코드 1과 `pi_camera_command_missing` 블로커 하나만 남음을 확인한다.
- **가짜 session 성공 확인.** 헬퍼가 프로세스 안에서 가짜 `which`(`libcamera-still`)와 장치 확인으로 `run_smoke`를 부르면 가짜 session이 `capture_source` `pi-camera`인 결과를 돌려줘 `passed`가 되고, `counted_qty` 5와 `book_qty` 8과 `diff` -3, session 호출 한 번을 확인한다. 준비 안 된 환경에서는 `blocked`이며 session 호출이 0건이고 `output_dir`이 생기지 않는다.
- **실제 `pi_session`과 가짜 runner 확인.** 헬퍼가 `session_fn` 없이 가짜 runner를 넘겨 `passed`와 `photo_sha256`의 `fake-pi-smoke-jpeg` 해시 일치, `A-01-02.jpg` 파일 존재를 확인한다.
- **capture_source 차단 확인.** 헬퍼가 `capture_source` `file`인 결과를 돌려주는 session으로 `failed`와 `error_type` `unexpected_capture_source`를 받는지 확인한다.
- **오류 차단 확인.** 헬퍼가 `PiCaptureError`를 일으키는 session으로 `failed`와 `error_type` `PiCaptureError`를 받고 `counted_qty`가 `null`인지 확인한다. `RuntimeError`를 일으키는 session에서는 예외 원본 문자열이 보고와 CLI 출력 어디에도 없음을 대조한다.
- **알 수 없는 빈 확인.** 헬퍼가 `bin_id` `Z-99-99`로 `failed`와 `error_type` `unknown_bin`, `attempted` `false`, session 호출 0건을 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pi-smoke-blocked.json`(기본 차단 `--json` stdout 원문)과 `pi-smoke-passed.json`(가짜 session 성공 보고)이 남고, `summary.json`의 `feature`가 `pi-smoke`이며 `fake_passed`와 `real_session_passed`가 `true`, `blocked_session_calls`가 0, `sentinel_leaked`가 `false`인지 대조한다.

## Gotchas

- 차단 상태에서 session을 부르면 실패다. 준비 점검이 통과하지 못한 보고는 `attempted`가 `false`여야 하고 session 호출 기록이 비어 있어야 하며 `output_dir`이 생기지 않아야 한다.
- 성공을 전체 세션 성공으로 서술하지 않는다. 단일 빈 스모크의 `passed`는 전체 세션 성공이나 Pi 실촬영 검증 완료를 뜻하지 않으며, 증거와 보고 모두 그렇게 표기한다.
- 실패를 가짜 파일이나 모의 결과로 대체하면 실패다. `PiCaptureError`가 나면 `failed`로 보고하고 `counted_qty`는 `null`이며, `capture_source`가 `pi-camera`가 아닌 결과도 `unexpected_capture_source`로 차단한다.
- 일반 예외의 원본 문자열을 출력하지 않는다. 예외 메시지 원본이 보고 JSON·CLI stdout·증거 파일에 나타나면 실패로 본다.
- 블로커 순서는 결정적이다: `pi_device_arrival_not_confirmed`, `pi_camera_command_missing`. 순서가 바뀌면 실패로 본다.
- 가짜 session과 가짜 `which`·가짜 runner는 프로세스 안에서만 주입한다. 실제 카메라 명령(`libcamera-still`)을 실행하거나 장치 도착을 탐지한 것처럼 증거를 만들지 않는다.
