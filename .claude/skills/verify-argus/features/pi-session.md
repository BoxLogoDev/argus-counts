# Pi 촬영 세션

Pi 촬영 세션은 `terminal.pi_session`의 Pi 캡처→사진 입력→대조 통합 세션을 검증하는 절차다. Pi 실촬영 검증 전이므로 실제 카메라로 찍은 결과를 주장하지 않고, 카메라 명령이 없을 때의 CLI 기대 실패, 프로세스 내 무카메라 차단, 가짜 `which`·`runner` 주입으로 `run_pi_session`을 구동하는 성공 경로만을 확인한다.

## Sub-features

- `pi-session-blocked` CLI 기대 실패: 실제 탐지에서 `available`이 False인 환경에서만 `python3 -m terminal.pi_session --out-dir <임시디렉터리>`를 실행해 종료코드가 1이고 stderr에 'Pi 카메라 명령을 찾을 수 없습니다'가 있으며 캡처 디렉터리가 생기지 않음을 확인한다. 명령이 있는 환경에서는 이 검사를 건너뛰고 그 사실을 노트로 남긴다.
- `pi-session-no-camera` 프로세스 내 무카메라: `which=lambda name: None`으로 `run_pi_session`을 호출하면 `PiCaptureError`가 나고 대상 디렉터리가 생기지 않음을 확인한다.
- `pi-session-fake-success` 가짜 성공: 가짜 `which`(`libcamera-still`만 `/usr/bin/libcamera-still`로 보고)와 `-o` 경로에 `fake-pi-session-jpeg` 바이트를 쓰고 returncode 0을 돌려주는 가짜 `runner`로 `run_pi_session`을 빈 6개 전체 세션으로 호출한다. 세션 ID는 `VERIFY-PI-SESSION-1`이고, `source`가 `mock`, `capture_source`가 `pi-camera`이며, summary가 빈 6·일치 4·불일치 2·절대 차이 6·순 차이 0이다. `A-01-02`는 `short`·diff -3, `B-01-02`는 `over`·diff +3이고, 모든 빈의 사진 `sha256`이 `fake-pi-session-jpeg` 바이트의 SHA-256과 같으며 `image_ref`가 `<bin_id>.jpg`고 실제 파일이 임시 디렉터리에 있다.

## How to get to it (user POV)

- 터미널에서 프로젝트 루트로 이동해 촬영 세션을 시도한다: `python3 -m terminal.pi_session --out-dir <캡처 디렉터리>`. 이 검증 환경에서는 카메라 명령이 없어 디렉터리 없이 실패하는 것이 기대 동작이다.
- Pi 위에서 실제 촬영 세션을 시도하는 사용자 경로도 같은 CLI이며, 필요하면 `--bin <빈 ID>`, `--session-id <세션 ID>`, `--out <리포트 경로>`를 더한다. 이 절차는 그 실행을 실촬영 성공으로 주장하지 않는다.
- 검증 헬퍼를 거치려면 `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-session --evidence-dir /tmp/argus-verify-evidence/<run-id>`를 실행한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다. SAM 실호출은 이 기능의 범위가 아니다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.
- Pi 실촬영 검증 전임을 전제로 한다. 가짜 바이트 `fake-pi-session-jpeg`는 검증 실행이 임시 디렉터리에 직접 만들며, 실제 사진이나 회사 자료를 쓰지 않는다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pi-session --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 먼저 실제 `probe_pi_camera`로 `available`을 확인한다. 실제 `available` 값은 환경에 따라 다르므로 False로 단정하지 않는다.
- **CLI 기대 실패 확인.** `available`이 False일 때만 헬퍼가 `terminal.pi_session` CLI를 `--out-dir` 임시 경로로 실행한다. 종료코드가 1이고 stderr에 'Pi 카메라 명령을 찾을 수 없습니다'가 있으며 캡처 디렉터리가 생기지 않았음을 확인한다. 명령이 있는 환경이면 이 단계는 건너뛰고 summary의 `cli_session_blocked`는 `null`로 남는다.
- **프로세스 내 무카메라 확인.** 헬퍼가 `which=lambda name: None`과 가짜 `runner`로 `run_pi_session`을 호출해 `PiCaptureError`가 나고 디렉터리가 생기지 않음을 확인하며, summary에 `no_camera_blocked`로 남긴다.
- **가짜 성공 확인.** 헬퍼가 `run_pi_session`에 가짜 `which`와 가짜 `runner`를 주입하고 세션 ID `VERIFY-PI-SESSION-1`로 호출한다. `source=mock`, `capture_source=pi-camera`, summary 기준값, 빈 6개, `A-01-02` `short`·-3, `B-01-02` `over`·+3, `probe`의 `available=True`·`command=libcamera-still`, `honesty`의 'Pi 실촬영 검증 전' 포함, 모든 사진의 `sha256`·`image_ref`, 임시 디렉터리 안 실제 캡처 파일 존재를 대조한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pi-session-report.json`(가짜 세션 report 전체)과 `pi-session-blocked.txt`(CLI 기대 실패 stderr, 건너뛴 경우 그 사실)가 남고, `summary.json`의 `fake_capture_sha256`이 `fake-pi-session-jpeg` 해시와 같은지 대조한다.

## Gotchas

- CLI 기대 실패·무카메라 차단·가짜 주입 성공을 Pi 실촬영 성공으로 서술하지 않는다. 증거와 보고 모두 'Pi 실촬영 검증 전'으로 표기한다.
- `available=True`는 카메라 명령이 PATH에 있다는 뜻일 뿐 촬영 성공이 아니다. 명령이 있는 환경에서 CLI 기대 실패 검사를 강제로 돌리면 실제 촬영을 시도하게 되니 건너뛴다.
- 카메라 명령이 없을 때 캡처 디렉터리 없이 실패하는 것이 정답이다. 모의 결과로 조용히 대체해 통과한 것으로 치지 않는다.
- `capture_source=pi-camera`는 `run_pi_session`이 사진 입력 결과를 교체한 표기다. `source=mock`인 계수 결과를 실계수로 서술하지 않는다.
- 가짜 사진 바이트(`fake-pi-session-jpeg`)가 바뀌면 기대 SHA-256도 달라진다. 바이트 내용과 해시 기대값은 함께 유지한다.
