# 단말 시뮬레이터

단말 시뮬레이터는 작업자가 단말로 빈을 촬영하는 흐름(촬영→모의 SAM 계수→장부 대조)을 터미널에서 그대로 재현해, 세션 리포트를 JSON으로 내는 CLI다. Pi 실기가 없어도 전체 흐름을 검증할 수 있는 경로다.

## Sub-features

- `sim-run` 기본 실행: 데모 장부 6개 빈을 계수·대조해 JSON 출력.
- `sim-summary` summary 수치: counted_bins 6, matched 4, mismatched 2, abs_diff_total 6, net_diff 0.
- `sim-out` `--out <경로>`로 같은 리포트를 파일에 저장.
- `sim-source` 리포트의 `source`가 `mock`으로 표기된다.

## How to get to it (user POV)

- 터미널에서 프로젝트 루트로 이동해 시뮬레이터 모듈을 실행한다.
- 파일로 남기려면 `--out` 인자를 붙여 실행한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다. 시뮬레이터는 서버를 쓰지 않지만, 같은 기준값을 공유하므로 먼저 확인한다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 -m terminal.simulator`. 종료코드 0이고 stdout이 JSON이며, 명령·stdout·종료 코드를 증거 transcript에 남긴다.
- **수치 확인.** stdout JSON에서 `source`가 `mock`, summary가 counted_bins 6, matched 4, mismatched 2, abs_diff_total 6, net_diff 0인지 확인한다. bins 배열은 6개이며 verdict가 불일치인 항목이 2개다.
- **파일 저장 확인.** Run `python3 -m terminal.simulator --out /tmp/argus-verify-evidence/<run-id>/simulator.json`. 종료 후 파일이 실재하고, 그 내용을 다시 읽어 summary 수치가 stdout 실행과 같은지 대조한다.
- **콘솔과 교차 확인.** 같은 기준값이 콘솔 `/api/report`의 summary와 일치하는지 `features/console-home.md`의 증거와 비교한다.

## Gotchas

- session_id와 generated_at은 실행마다 달라진다. 이 두 필드는 대조에서 제외하고 수치와 source만 본다.
- `--out` 경로의 상위 디렉터리가 없으면 실패한다. 증거 디렉터리를 먼저 만든다.
- 실호출 환경변수가 남아 있으면 `source`가 달라질 수 있다. mock이 아니면 실패로 보고한다.
- JSON 파싱에 실패한 출력을 수치 확인으로 치지 않는다. 파싱 오류 자체를 실패로 남긴다.
