# Pi 실촬영 준비 점검

Pi 실촬영 준비 점검은 `qa.pi_readiness`의 `check_readiness`가 실촬영을 시작하기 전에 필요한 조건만 점검하는지 검증하는 절차다. 이 하네스는 실제 촬영을 하지 않는다(실제 촬영 없음). 카메라 명령은 실행하지 않고 존재만 탐지한다. 장치 도착은 이 하네스가 확인할 수 없어 외부 확인 플래그로만 받는다. 준비 완료는 Pi 실촬영 성공을 뜻하지 않는다. 블로커는 결정적 순서로 `pi_device_arrival_not_confirmed`, `pi_camera_command_missing` 두 가지이며, 텍스트 출력의 `READY_FOR_REAL_CAPTURE` 줄과 JSON의 `ready_for_real_capture`가 준비 판정을 나타낸다.

## Sub-features

- `pi-readiness-blocked-text` 기본 차단 텍스트: CLI `python3 -m qa.pi_readiness`가 종료코드 1을 내고, stdout에 `BLOCKERS: 2`와 `READY_FOR_REAL_CAPTURE: false`와 블로커 id `pi_device_arrival_not_confirmed`, `pi_camera_command_missing`이 이 순서대로 있음을 확인한다.
- `pi-readiness-blocked-json` 기본 차단 JSON: `python3 -m qa.pi_readiness --json`이 종료코드 1을 내고, `ready_for_real_capture`이 `false`이며 blockers id 목록이 위 두 id와 일치하고 `device_confirmed`·`camera_available`이 모두 `false`, `camera_command`가 `null`, `candidates_checked`가 `libcamera-still`·`raspistill`임을 확인한다. `honesty`에는 촬영을 하지 않는다는 줄과 성공을 뜻하지 않는다는 줄이 있다.
- `pi-readiness-fake-ready` 가짜 probe 준비 완료: 프로세스 안에서 `check_readiness`에 가짜 ready probe(`libcamera-still` 존재)와 `device_confirmed=True`를 넘기면 `ready_for_real_capture`이 `true`이고 blockers가 비어 있음을 확인한다.
- `pi-readiness-device-only` 장치만 남은 차단: 가짜 ready probe에 `device_confirmed=False`를 넘기면 블로커가 `pi_device_arrival_not_confirmed` 하나만 남음을 확인한다.
- `pi-readiness-camera-only` 카메라만 남은 차단: 가짜 missing probe에 `device_confirmed=True`를 넘기면 블로커가 `pi_camera_command_missing` 하나만 남음을 확인한다.
- `pi-readiness-which-injected` which 주입 탐지: `which`를 주입해 `raspistill`만 찾히게 하면 `camera_command`가 `raspistill`이고 준비 완료가 됨을 확인한다. 명령을 실행하지 않고 존재만 탐지한다.
- `pi-readiness-cli-device-confirmed` CLI 장치 확인 후에도 카메라 차단: 이 VM처럼 카메라 명령이 없는 환경에서 `python3 -m qa.pi_readiness --device-confirmed --json`을 실행하면 종료코드 1과 블로커 `pi_camera_command_missing` 하나만 남음을 확인한다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 단말 CLI다: 프로젝트 루트에서 `python3 -m qa.pi_readiness`를 실행한다. Pi 장치 도착을 외부에서 확인했으면 `--device-confirmed`를, 기계가 읽을 출력이 필요하면 `--json`을 붙인다. 준비 완료이면 종료코드 0, 아니면 1이다.
- 이 CLI는 실제 촬영을 하지 않는다. 카메라 명령(`libcamera-still`·`raspistill`)은 실행하지 않고 존재만 탐지한다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-readiness --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 장치와 카메라로 촬영하는 경로는 이 절차의 범위가 아니다. 준비 완료는 Pi 실촬영 성공을 뜻하지 않으므로, 실제 촬영 성공은 장치 도착 뒤 별도로 확인한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 실제 촬영을 하지 않는다. 카메라 명령을 실행하지 않으며, 가짜 probe와 가짜 `which`는 프로세스 안에서만 주입한다.
- 이 VM에는 카메라 명령이 없다는 것이 기본 차단 기대값의 전제다. 카메라 명령이 실제로 있는 환경에서는 기본 차단 기대값이 달라질 수 있다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-readiness --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 실제 촬영 없이 CLI 서브프로세스와 프로세스 내 `check_readiness`만으로 `drive_pi_readiness`를 실행한다.
- **기본 차단 텍스트 확인.** 헬퍼가 `qa.pi_readiness` CLI를 서브프로세스로 실행해 종료코드 1, `BLOCKERS: 2`, `READY_FOR_REAL_CAPTURE: false`, 블로커 id 두 개의 순서를 대조한다.
- **기본 차단 JSON 확인.** 헬퍼가 `--json` CLI를 실행해 `ready_for_real_capture` `false`, 블로커 id 목록과 `EXPECTED_PI_READINESS_BLOCKER_IDS`의 일치, 존재 플래그와 `candidates_checked`, `honesty`의 촬영을 하지 않는다는 줄을 확인한다.
- **가짜 probe 준비 완료 확인.** 헬퍼가 프로세스 안에서 `qa.pi_readiness`의 `check_readiness`를 가져와 가짜 ready probe와 장치 확인으로 준비 완료를 확인한다.
- **장치만·카메라만 남은 차단 확인.** 헬퍼가 가짜 probe 조합을 바꿔 블로커가 각각 하나만 남는지 확인하고, `which` 주입으로 `raspistill` 탐지도 확인한다.
- **CLI 장치 확인 확인.** 헬퍼가 `--device-confirmed --json` CLI를 실행해 이 VM에서는 종료코드 1과 카메라 블로커 하나만 남음을 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pi-readiness-blocked.json`(기본 차단 `--json` stdout 원문)과 `pi-readiness-ready.json`(가짜 probe `check_readiness` 결과)이 남고, `summary.json`의 `feature`가 `pi-readiness`이며 `ready_with_fake_probe`가 `true`인지 대조한다.

## Gotchas

- 준비 완료를 실촬영 성공으로 서술하지 않는다. 준비 완료는 Pi 실촬영 성공을 뜻하지 않으며, 증거와 보고 모두 그렇게 표기한다.
- 이 절차에서 실제 촬영을 하지 않는다. 카메라 명령을 실행하는 호출을 하면 검증이 무효가 된다.
- 장치 도착은 이 하네스가 확인할 수 없다. `--device-confirmed`는 외부 확인을 받았다는 표기일 뿐, 하네스 자체의 탐지 결과가 아니다.
- 블로커 순서는 결정적이다: `pi_device_arrival_not_confirmed`, `pi_camera_command_missing`. 순서가 바뀌면 실패로 본다.
- 기본 차단 상태에서 종료코드 0이거나 `READY_FOR_REAL_CAPTURE: true`면 실패로 본다. 카메라 명령이 있는 환경에서는 기본 기대값 자체가 달라지므로, 전제를 먼저 확인한다.
- 가짜 probe와 가짜 `which`는 프로세스 안에서만 주입한다. 실제 장치나 실제 카메라 명령이 있는 것처럼 증거를 만들지 않는다.
