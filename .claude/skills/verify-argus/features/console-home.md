# 콘솔 홈

콘솔 홈은 관리자가 브라우저로 여는 첫 화면으로, 최신 실사 세션의 요약 지표(일치율 66.7%), 준비 상태(SAM 실호출 준비·Pi 실촬영 준비의 블로커 분리 표기), 차이 목록, 조치 우선순위, `데모 기준` 영향 한 줄을 한 화면에 보여 주고, 같은 리포트를 `/api/report` JSON으로도 제공한다. 준비 상태는 `/api/readiness` JSON으로도 제공하며 실제 API 호출·촬영은 하지 않는다.

## Sub-features

- `home-summary` 요약 지표: 빈 6, 일치 4, 불일치 2, 일치율 66.7%.
- `home-diff-list` 차이 목록: 부족 1건·초과 1건과 빈별 차이.
- `home-actions` 조치 우선순위: 차이가 큰 빈부터 조치 힌트와 함께 정렬.
- `home-api` `/api/report` JSON: `source: "mock"`, summary 수치 동일.
- `home-readiness` 준비 상태: 기본 환경에서 SAM 블로커 3건·Pi 블로커 2건, `/api/readiness` JSON과 홈 패널이 같은 상태를 보여 준다. 준비 완료는 실호출·실촬영 성공이 아니다.

## How to get to it (user POV)

- 브라우저에서 콘솔 서버 주소의 `/`를 연다.
- 프로그램에서는 같은 서버의 `/api/report`를 GET으로 읽는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다 (`verify_argus.py --doctor` 종료코드 0).
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **홈 구동.** 헬퍼를 실행한다. Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature console-home --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 종료코드 0이고 출력에 `VERIFY: PASS`가 나온다.
- **마커 확인.** 증거의 `home.html`에서 `조치 우선순위`, `모의 데이터`, `66.7%`가 모두 발견됐음을 `summary.json`의 `markers_found`로 확인한다. 셋 다 true여야 한다.
- **JSON 대조.** 증거의 `api-report.json`에서 `source`가 `mock`이고 summary가 counted_bins 6, matched 4, mismatched 2, abs_diff_total 6인지 확인한다. 화면 수치와 JSON 수치가 같아야 증명이 된다.
- **증거 보존 확인.** 헬퍼 종료 뒤에도 증거 디렉터리에 `transcript.txt`, `home.html`, `api-report.json`, `summary.json` 네 파일이 남아 있는지 다시 읽는다.

## Gotchas

- 8765 포트에 떠 있는 상주 서버를 구동하면 내 변경이 아닌 상태를 검증하게 된다. 항상 헬퍼의 임시 포트를 쓴다.
- 전역 urlopen으로 읽으면 환경 프록시가 로컬 응답을 가로챈다. 헬퍼가 쓰는 `ProxyHandler({})` 오프너를 벗어나지 않는다.
- `source`가 `mock`이 아니면 실호출로 전환된 상태다. 수치만 보고 통과시키지 말고 실패로 보고한다.
- 상태 코드 200만으로는 부족하다. 마커와 summary 수치를 함께 확인한다.
