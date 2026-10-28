# 사진 입력

사진 입력은 이미 존재하는 이미지 파일을 빈(bin)별로 받아 기존 실사 흐름(모의 SAM 계수→장부 대조→차이 리포트)에 태우는 파일 기반 입력 경계다. Pi 카메라 실촬영이 아니며, 검증에서는 임시 디렉터리에 만든 가짜 사진 바이트로 전체 흐름을 구동한다.

## Sub-features

- `photo-run` 기본 실행: 가짜 사진 6장을 `--capture BIN=PATH`로 넘겨 JSON 리포트를 얻는다.
- `photo-source` 리포트의 `source`가 `mock`, `capture_source`가 `file`로 표기된다.
- `photo-honesty` `honesty`에 '파일 기반 입력이며 Pi 실촬영이 아닙니다' 표기가 포함된다.
- `photo-record` 각 빈의 사진 메타데이터(이름·크기·SHA-256·확장자)가 리포트에 기록된다.
- `photo-summary` summary 수치: counted_bins 6, matched 4, mismatched 2, abs_diff_total 6, net_diff 0. A-01-02는 short·-3, B-01-02는 over·+3이다.
- `photo-out` `--out <경로>`로 같은 리포트를 파일에 저장한다.

## How to get to it (user POV)

- 터미널에서 프로젝트 루트로 이동해 사진 입력 모듈을 실행한다: `python3 -m terminal.photo_intake --capture A-01-02=<사진경로> [--capture <빈>=<사진경로> ...]`.
- Pi 도착 후에는 카메라가 만든 사진 파일을 같은 형식으로 넘기는 것이 사용자 경로이며, 지금은 파일 기반 입력만으로 검증한다.
- 파일로 남기려면 `--out` 인자를 붙여 실행한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다. 실호출은 이 기능의 범위가 아니다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.
- 가짜 사진은 검증 실행이 임시 디렉터리에 직접 만든다: 빈 6개 각각 내용 `fake-photo-<빈ID>`인 `<빈ID>.jpg` 파일이다. 실제 사진이나 회사 자료를 쓰지 않는다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature photo-intake --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼가 가짜 사진 6장으로 `python3 -m terminal.photo_intake --capture ... --session-id VERIFY-PHOTO-1`을 구동한다. 종료코드 0이고 stdout이 JSON이며, 명령·종료 코드를 증거 transcript에 남긴다.
- **표기 확인.** stdout JSON에서 `source`가 `mock`, `capture_source`가 `file`, `session_id`가 `VERIFY-PHOTO-1`, `honesty`에 'Pi 실촬영이 아닙니다'가 포함되는지 확인한다.
- **수치 확인.** summary가 counted_bins 6, matched 4, mismatched 2, abs_diff_total 6, net_diff 0인지, bins가 6개이며 A-01-02가 short·-3, B-01-02가 over·+3인지 확인한다.
- **사진 기록 확인.** A-01-02의 `photo.sha256`이 `fake-photo-A-01-02` 바이트의 SHA-256과 일치하고 `photo.image_ref`가 `A-01-02.jpg`인지 확인한다.
- **파일 저장 확인.** 헬퍼가 같은 입력으로 `--out`을 붙여 재실행한다. 종료 후 증거 디렉터리의 `photo-intake.json`이 실재하고, 그 summary와 capture_source가 stdout 실행과 같은지 대조한다.

## Gotchas

- 파일 기반 입력을 Pi 실촬영으로 서술하지 않는다. 증거와 보고 모두 '파일 기반·모의 계수'로 표기한다.
- 지원 확장자는 jpg·jpeg·png·webp뿐이다. 미지원 확장자, 없는 파일, 빈 파일은 모듈이 거부하는 것이 정답이며, 이를 우회해 통과한 것으로 치지 않는다.
- session_id를 고정하지 않으면 실행마다 달라진다. 검증에서는 `VERIFY-PHOTO-1`로 고정하고 generated_at은 대조에서 제외한다.
- 실호출 환경변수가 남아 있으면 `source`가 달라질 수 있다. mock이 아니면 실패로 보고한다.
- 가짜 사진 바이트가 바뀌면 기대 SHA-256도 달라진다. 사진 내용(`fake-photo-<빈ID>`)과 해시 기대값은 함께 유지한다.
