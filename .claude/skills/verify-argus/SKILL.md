---
name: verify-argus
description: "Argus(창고 재고실사 코파일럿)의 웹 콘솔과 단말 CLI를 사용자처럼 구동해 검증하는 프로젝트 로컬 스킬. 콘솔 화면·세션·리포트·데모 영상의 동작을 실제 서버 응답과 CLI 출력으로 증명할 때 사용한다."
---

# Argus 검증 스킬

이 스킬은 Argus를 내부 함수가 아니라 사용자가 닿는 표면으로 검증한다: 웹 콘솔은 HTTP로, 단말 흐름은 CLI로 직접 구동하고, 응답 원문과 종료 코드를 증거로 남긴다. 헬퍼는 `scripts/verify_argus.py`이며 표준 라이브러리만 쓴다.

기준 상태: 상태가 없는(stateless) 앱이다. 데이터 디렉터리·마이그레이션·인증·시드 절차가 없다. 데모 데이터는 코드 안의 가상 데이터이며, 계수는 모의 어댑터라 응답의 `source`는 항상 `mock`이어야 한다.

## Launch

- 프로젝트 루트에서 헬퍼가 서버를 띄우는 것이 기본 경로다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `console.server.create_handler`로 `ThreadingHTTPServer`를 127.0.0.1 포트 0(OS 배정 임시 포트)에 띄운다.
- 손으로 띄울 때는 `python3 -m console.server --host 127.0.0.1 --port <빈 포트>`를 쓴다. 기본값은 127.0.0.1:8765이지만, 검증에서 8765의 상주 인스턴스를 구동 대상으로 삼지 않는다. 그 포트를 이미 다른 과정이 쓰고 있을 수 있고, 내가 띄운 서버가 아니면 종료할 권한도 없다.
- 준비 완료 판정: 프로세스가 살아 있는 것이 아니라, `GET /api/report`가 200을 주고 JSON의 `source`가 `mock`이며 summary가 빈 6·일치 4·불일치 2일 때만 usable이다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 설정돼 있으면 실호출로 전환될 수 있어 검증이 오염된다. 검증 실행에서는 두 변수를 비우고, 응답 `source=mock`을 반드시 확인한다. 실호출은 이 스킬의 범위가 아니다.

## Doctor

- 한 번의 읽기 전용 점검: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor`
- 이 명령은 임시 포트로 서버를 띄워 `GET /api/report`의 상태 200, `source == "mock"`, summary matched 4·mismatched 2·counted_bins 6을 확인하고 `DOCTOR: PASS`와 종료코드 0을 낸다. 모듈 import 실패, 포트 바인드 실패, 수치 불일치가 있으면 `DOCTOR: FAIL`과 종료코드 1이다.
- 무언가 이상해 보이면 기능 검증 전에 항상 doctor부터 돌린다. doctor가 실패하면 기능을 구동하지 말고 실패 지점을 그대로 보고한다.

## Drive

- 기본 구동은 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature console-home --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `GET /`에서 마커 `조치 우선순위`·`모의 데이터`·`66.7%`를, `GET /api/report`에서 source와 요약 수치를 확인한다.
- 헬퍼는 기능 17종을 모두 구동한다: `--feature`에 `console-home`·`terminal-simulator`·`session-list`·`difference-report`·`demo-video-draft`·`photo-intake`·`pre-submission`·`pi-capture`·`pi-session`·`sam-live`·`sam-readiness`·`submission-runbook`·`pi-readiness`·`console-readiness`·`sam-smoke`·`pi-smoke`·`devpost-submission` 중 하나를 주거나, `all`을 주면 17종을 순서대로 구동해 증거를 기능별 하위 디렉터리에 남기고 최상위 `summary.json`에 기능별 `all_ok`를 모은다. 시뮬레이터와 리포트는 CLI 서브프로세스로(자식 환경에서도 SAM 환경변수를 제거), 세션은 임시 포트 HTTP로, 영상 초안은 ffprobe 탐침(렌더 아님)과 `demo.render_video.build_data_panel_lines`로 구한 컷별 데이터 패널 대조(컷 5 전체 빈 6줄·컷 6 불일치만·컷 3 `실촬영 데이터 없음`, 증거 `data-panel.json`)로, 사진 입력은 임시 디렉터리에 만든 가짜 사진 6장을 CLI 서브프로세스에 `--capture`로 넘겨 구동한다(파일 기반 입력이며 Pi 실촬영이 아니다. `capture_source=file`와 `honesty`의 'Pi 실촬영이 아닙니다' 표기, 사진 SHA-256 기록을 확인한다).
- 콘솔 라우트(전부 GET): `/` 홈 화면, `/api/report` JSON 리포트, `/api/readiness` 준비 상태 JSON(SAM 실호출 준비·Pi 실촬영 준비의 블로커를 분리해 돌려주며 실제 API 호출·촬영은 하지 않고 환경변수 값은 포함하지 않는다), `/sessions` 세션 목록 화면, `/api/sessions` 세션 목록 JSON(세션 3개), `/sessions/<id>` 세션 상세, `/api/sessions/<id>` 세션 상세 JSON. 없는 세션 id는 두 경로 모두 404가 정답이다. 세션 id는 `DEMO-20261027-A`, `DEMO-20261027-B`(전부 일치, 일치율 100.0%), `DEMO-20261026-A`다.
- 로컬 서버를 HTTP로 읽을 때는 환경 프록시를 우회해야 한다. urllib에 `ProxyHandler({})`를 명시한 전용 오프너를 쓴다. 전역 urlopen은 프록시 캐시 때문에 로컬 응답을 놓치거나 이후 테스트를 오염시킨다(`demo/capture.py`가 이미 겪은 결함이다).
- 단말 CLI 구동: `python3 -m terminal.simulator`는 촬영→계수→대조 흐름의 JSON을 stdout으로 내고 종료코드 0이다. `python3 -m terminal.report`는 텍스트 리포트를 내며 말미에 `데모 기준` 영향 한 줄이 있고, `--json`이면 조치 우선순위 payload를 낸다.
- pre-submission 구동: 제출 전 전수 점검은 CLI 서브프로세스로 구동하며, `mechanical_pass`와 `submission_ready`(false)를 분리해 확인한다. 전수 점검은 기계 점검 12종이며 SAM·Pi 준비 점검 정합과 콘솔 준비 상태 정합, SAM 스모크 정합(가짜 counter로만 구동, 실제 API 호출 없음), Pi 스모크 정합(가짜 session으로만 구동, 실제 촬영 없음), 제출 문안 정합(문안 원문 대조만 하며 실제로 제출하지 않음)이 포함되고, 증거 summary에 readiness 블로커(SAM 3종·Pi 2종)와 콘솔 blocker_count·overall_ready, SAM·Pi 스모크 status·블로커, 제출 문안 section_count·블로커도 남긴다.
- pi-capture 구동: Pi 캡처 경계는 CLI `--probe` 정직 보고, 카메라 명령 부재 시 CLI `--capture` 기대 실패, 가짜 `which`/`runner` 주입 성공으로 구동하며 증거 `pi-capture-probe.json`·`pi-capture-fake.json`을 남긴다(Pi 실촬영 검증 전).
- pi-session 구동: Pi 촬영 세션은 카메라 명령 부재 시 CLI `--out-dir` 기대 실패, 가짜 `which`/`runner` 주입 성공으로 구동하며 증거 `pi-session-report.json`·`pi-session-blocked.txt`를 남긴다(Pi 실촬영 검증 전).
- sam-live 구동: SAM 실호출 준비 경계는 가짜 transport로만 구동하며 실제 API 호출은 하지 않고 증거 `sam-live-fake.json`·`sam-live-errors.json`을 남긴다(SAM 실호출 검증 전).
- sam-readiness 구동: SAM 실호출 전환 준비 점검은 CLI 서브프로세스(기본 차단 3건·종료코드 1)와 프로세스 내 check_readiness(가짜 환경+크레딧 확인 시 준비 완료, 값 누출 없음)로 구동하며 증거 `sam-readiness-blocked.json`·`sam-readiness-ready.json`을 남긴다(준비 완료는 실호출 성공이 아니다).
- pi-readiness 구동: Pi 실촬영 준비 점검은 CLI 서브프로세스(기본 차단 2건·종료코드 1)와 프로세스 내 check_readiness(가짜 probe 준비 완료)로 구동하며 증거 `pi-readiness-blocked.json`·`pi-readiness-ready.json`을 남긴다(준비 완료는 실촬영 성공이 아니다).
- console-readiness 구동: 콘솔 준비 상태는 임시 포트 HTTP `GET /api/readiness`와 `GET /` 홈 패널로 구동하며, 프로세스 내 `build_readiness` 가짜 환경·가짜 probe 준비 완료와 SAM/Pi 분리, 환경변수 값 누출 없음을 확인하고 증거 `console-readiness.json`·`console-readiness-ready.json`을 남긴다(준비 완료는 실호출·실촬영 성공이 아니다).
- sam-smoke 구동: SAM 단일 빈 스모크는 CLI 서브프로세스(기본 차단 3건·종료코드 1·호출 시도 없음)와 프로세스 내 run_smoke 가짜 counter 주입(성공·모의 source 차단·SamCountingError 차단·알 수 없는 빈 차단)으로 구동하며 증거 sam-smoke-blocked.json·sam-smoke-passed.json을 남긴다(실제 API 호출 없음, 성공해도 전체 세션 성공이 아니다).
- pi-smoke 구동: Pi 단일 빈 스모크는 CLI 서브프로세스(기본 차단 2건·종료코드 1·촬영 시도 없음)와 프로세스 내 run_smoke 가짜 session 주입(성공·capture_source 차단·PiCaptureError 차단·알 수 없는 빈 차단), 실제 pi_session+가짜 runner 성공으로 구동하며 증거 pi-smoke-blocked.json·pi-smoke-passed.json을 남긴다(실제 촬영 없음, 성공해도 전체 세션 성공이나 Pi 실촬영 검증 완료가 아니다).
- devpost-submission 구동: 제출 문안 패키지는 파일 원문을 읽어 절 11개 순서·데모 기준 수치·블로커 2건을 대조하고 변조 탐지를 확인하며 증거 devpost-submission.json·devpost-submission.md를 남긴다(제출 준비 완료가 아니다).
- submission-runbook 구동: 제출 런북은 파일 원문을 읽어 절 순서·블로커·최종 점검 명령·주장 감사를 대조하고 변조 탐지를 확인하며 증거 submission-runbook.json·submission-runbook.md를 남긴다(제출 준비 완료가 아니다).
- 회귀 확인: `python3 -m unittest discover -s tests`, `python3 -m qa`(체크 17개), `python3 -m qa.standalone`(체크 6개, 현재형 주장 감사 통합). 셋 다 종료코드 0이어야 한다.
- 기능별 상세 절차는 `features/` 아래 파일이 정본이다. 검증 전에 색인 `features/README.md`를 읽고 해당 기능 파일을 따른다.

## Evidence

- 증거 위치: `/tmp/argus-verify-evidence/<run-id>/` (run-id는 실행마다 새로 만든다).
- 헬퍼 구동 증거: `transcript.txt`(명령·상태·마커 확인 과정), `home.html`(GET / 응답 원문), `api-report.json`(GET /api/report 응답 원문), `summary.json`(feature·상태 코드·markers_found·source·all_ok). 다른 기능은 기능별 원문(예: `simulator-stdout.json`, `sessions.json`, `report.json`, `video-probe.json`)을 같은 방식으로 남기고, `all` 구동에서는 기능별 하위 디렉터리마다 이 증거가 쌓인다.
- CLI 구동 증거: 명령, stdout, stderr, 종료 코드를 transcript에 함께 남긴다. 화면만 보지 말고 부수 결과(생성 파일, JSON 필드)를 두 번째 경로로 확인한다. 예: 시뮬레이터 JSON의 summary와 콘솔 `/api/report`의 summary가 같은 수치인지 대조한다.
- 증거에서도 모의인 것을 구분한다: `source: "mock"`과 화면의 `모의 데이터` 표기가 증거에 그대로 있어야 하며, 이를 실호출 결과처럼 서술하지 않는다.
- 증명 기준: 내부 setter나 테스트 전용 경로가 아니라 실제 사용자 경로(라우트·CLI 진입점)로 구동한다. 최종 화면만 캡처하지 말고 행동과 그 결과 상태를 같이 남긴다.

## Cleanup

- 종료는 헬퍼가 맡는다: 자기가 띄운 `ThreadingHTTPServer`만 `shutdown`/`server_close` 한다. 프로세스 이름으로 죽이지 않는다.
- 손으로 띄운 서버는 그 터미널 세션에서 Ctrl+C로만 종료한다. 8765의 상주 인스턴스나 남이 띄운 서버는 건드리지 않는다.
- 정리 뒤에도 증거 디렉터리(`/tmp/argus-verify-evidence/<run-id>/`)는 지우지 않는다. 종료 후 증거 파일이 그대로 있는지 확인하는 것까지가 cleanup이다.

## Helpers

- `scripts/verify_argus.py --doctor` — 구동 가능성 점검(종료코드 0/1).
- `scripts/verify_argus.py --feature console-home --evidence-dir <dir>` — 콘솔 홈 기능을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature <terminal-simulator|session-list|difference-report|demo-video-draft> --evidence-dir <dir>` — 해당 기능을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature photo-intake --evidence-dir <dir>` — 가짜 사진 6장으로 파일 기반 사진 입력을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature pre-submission --evidence-dir <dir>` — 제출 전 전수 점검을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature pi-capture --evidence-dir <dir>` — Pi 캡처 경계(탐지·부재 시 기대 실패·가짜 runner 성공)를 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature pi-session --evidence-dir <dir>` — Pi 촬영 세션(기대 실패·가짜 주입 성공)을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature sam-live --evidence-dir <dir>` — SAM 실호출 준비 경계(가짜 transport 성공·해석 변형·실패 차단)를 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature sam-readiness --evidence-dir <dir>` — SAM 실호출 전환 준비 점검(기본 차단 3건·가짜 환경 준비 완료, 실제 API 호출 없음)을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature pi-readiness --evidence-dir <dir>` — Pi 실촬영 준비 점검(기본 차단 2건·가짜 probe 준비 완료, 실제 촬영 없음)을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature console-readiness --evidence-dir <dir>` — 콘솔 준비 상태(/api/readiness·홈 패널·가짜 준비 완료, 실제 API 호출·촬영 없음)를 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature submission-runbook --evidence-dir <dir>` — 제출 런북(절 순서·블로커·최종 점검 명령·변조 탐지)을 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature sam-smoke --evidence-dir <dir>` — SAM 단일 빈 스모크(기본 차단·가짜 counter 성공·오류 차단, 실제 API 호출 없음)를 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature pi-smoke --evidence-dir <dir>` — Pi 단일 빈 스모크(기본 차단·가짜 session 성공·오류 차단, 실제 촬영 없음)를 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature devpost-submission --evidence-dir <dir>` — 제출 문안 패키지(절 순서·데모 수치·블로커·변조 탐지)를 구동하고 증거를 남긴다.
- `scripts/verify_argus.py --feature all --evidence-dir <dir>` — 기능 17종을 전부 구동하고 기능별 하위 디렉터리와 최상위 요약을 남긴다.
- 유지보수는 pstack `maintain-verification-skill` 절차를 따른다: 라우트·마커·수치가 바뀌면 이 스킬과 `features/`를 같은 변경에서 함께 고친다.
