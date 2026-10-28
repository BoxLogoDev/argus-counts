# Pi 캡처

Pi 캡처는 `terminal.pi_capture`의 Pi 카메라 캡처 경계를 검증하는 절차다. Pi 실촬영 검증 전이므로 실제 카메라로 찍은 결과를 주장하지 않고, 명령 탐지(`--probe`)의 정직한 보고, 카메라 명령이 없을 때의 기대 실패, 가짜 `which`·`runner` 주입 성공 경로만을 구동한다.

## Sub-features

- `pi-probe` 명령 탐지: `python3 -m terminal.pi_capture --probe`가 종료코드 0으로 JSON을 내고, `available`이 bool이며 `command`가 `None` 또는 `libcamera-still`·`raspistill` 중 하나이고, `honesty`에 'Pi 실촬영 검증 전'이 포함된다. `probe_pi_camera`의 탐지는 명령을 실행하지 않는다.
- `pi-blocked` 부재 시 기대 실패: `available`이 False인 환경에서만 `--capture A-01-02=<임시경로>`를 실행해 종료코드가 0이 아니고 출력 파일이 생기지 않음을 확인한다. 명령이 있는 환경에서는 이 검사를 건너뛰고 그 사실을 노트로 남긴다.
- `pi-fake-success` 가짜 성공: 가짜 `which`(`libcamera-still`만 `/usr/bin/libcamera-still`로 보고)와 `-o` 경로에 `fake-pi-jpeg` 바이트를 쓰고 returncode 0을 돌려주는 가짜 `runner`로 `capture_photo`를 호출해 `CaptureRecord`를 얻는다. `sha256`이 `fake-pi-jpeg` 바이트의 SHA-256과 일치하고, `suffix`가 `.jpg`, `bin_id`가 `A-01-02`다.
- `pi-fake-failure` 가짜 실패: returncode 2와 `stderr` `sensitive-detail`인 runner로 `capture_photo`를 호출하면 `PiCaptureError`가 나고, 예외 문자열에 `sensitive-detail`이 포함되지 않는다.
- `pi-command-shape` 명령 모양: `build_capture_command("libcamera-still", "/tmp/x.jpg")`의 첫 원소가 `libcamera-still`이고 `-o` 다음 원소가 `/tmp/x.jpg`다.

## How to get to it (user POV)

- 터미널에서 프로젝트 루트로 이동해 캡처 명령 존재만 탐지한다: `python3 -m terminal.pi_capture --probe`. 명령을 실행하지 않으므로 Pi가 없는 환경에서도 안전하다.
- Pi 위에서 실제 캡처를 시도하는 사용자 경로는 `python3 -m terminal.pi_capture --capture A-01-02=<사진경로>`다. 이 검증 환경에서는 카메라 명령이 없어 파일 없이 실패하는 것이 기대 동작이다.
- 검증 헬퍼를 거치려면 `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-capture --evidence-dir /tmp/argus-verify-evidence/<run-id>`를 실행한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다. SAM 실호출은 이 기능의 범위가 아니다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.
- Pi 실촬영 검증 전임을 전제로 한다. 가짜 바이트 `fake-pi-jpeg`는 검증 실행이 임시 디렉터리에 직접 만들며, 실제 사진이나 회사 자료를 쓰지 않는다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-capture --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 먼저 CLI `--probe`를 구동해 종료코드 0과 stdout JSON을 확인하고, `available`의 bool 여부, `command`의 허용 값, `honesty`의 'Pi 실촬영 검증 전' 포함을 대조한다. 실제 `available` 값은 환경에 따라 다르므로 False로 단정하지 않는다.
- **기대 실패 확인.** `available`이 False일 때만 헬퍼가 임시 경로로 CLI `--capture A-01-02=<임시경로>`를 실행한다. 종료코드가 0이 아니고 출력 파일이 생기지 않았음을 확인한다. 명령이 있는 환경이면 이 단계는 건너뛰고 summary의 `cli_capture_blocked`는 `null`로 남는다.
- **가짜 성공 확인.** 헬퍼가 `capture_photo`와 `probe_pi_camera`, `build_capture_command`를 불러와 가짜 `which`와 가짜 `runner`를 주입한다. 얻은 기록의 `sha256`·`suffix`·`bin_id`와 `libcamera-still` 명령 모양(`-o` 다음 경로)을 확인한다.
- **가짜 실패 확인.** returncode 2인 runner로 `capture_photo`를 다시 호출해 `PiCaptureError`가 나는지, 예외에 `sensitive-detail`이 새지 않는지 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pi-capture-probe.json`(probe stdout 원문)과 `pi-capture-fake.json`(가짜 기록의 `bin_id`·`image_ref`·`size_bytes`·`sha256`·`suffix`)이 남고, `summary.json`의 `fake_capture_sha256`이 `fake-pi-jpeg` 해시와 같은지 대조한다.

## Gotchas

- 탐지·기대 실패·가짜 주입 성공을 Pi 실촬영 성공으로 서술하지 않는다. 증거와 보고 모두 'Pi 실촬영 검증 전'으로 표기한다.
- `available=True`는 카메라 명령이 PATH에 있다는 뜻일 뿐 촬영 성공이 아니다. 명령이 있는 환경에서 기대 실패 검사를 강제로 돌리면 실제 촬영을 시도하게 되니 건너뛴다.
- 명령 부재 시 `--capture`가 파일 없이 실패하는 것이 정답이다. 모의 결과로 조용히 대체해 통과한 것으로 치지 않는다.
- `PiCaptureError` 메시지에는 runner의 stderr 원문이 들어가면 안 된다. 민감한 세부정보가 예외나 증거에 남지 않는지 확인한다.
- 가짜 사진 바이트(`fake-pi-jpeg`)가 바뀌면 기대 SHA-256도 달라진다. 바이트 내용과 해시 기대값은 함께 유지한다.
