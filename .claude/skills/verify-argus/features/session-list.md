# 세션 목록

세션 목록은 관리자가 지난 실사 세션들을 한눈에 보는 화면으로, 데모 세션 3개의 목록과 각 세션 상세를 HTML과 JSON으로 제공하고, 없는 세션에는 404를 돌려준다.

## Sub-features

- `sessions-list` 목록: `DEMO-20261027-A`, `DEMO-20261027-B`, `DEMO-20261026-A` 3개와 합계 지표.
- `sessions-detail-ok` 전부 일치 세션 `DEMO-20261027-B` 상세: 일치율 100.0%.
- `sessions-json` `/api/sessions` JSON: total_sessions 3, total_mismatched 5.
- `sessions-404` 없는 세션 id는 HTML·JSON 두 경로 모두 404.

## How to get to it (user POV)

- 브라우저에서 콘솔 홈의 세션 목록 링크를 따라 `/sessions`로 이동한다.
- 목록에서 세션을 눌러 `/sessions/<id>` 상세로 들어간다.
- 프로그램에서는 `/api/sessions`와 `/api/sessions/<id>`를 GET으로 읽는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼가 띄운 임시 포트 서버가 준비됐다 (`verify_argus.py --doctor` PASS).
- HTTP는 `ProxyHandler({})` 오프너로 읽는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **목록 구동.** 헬퍼와 같은 오프너로 GET `/sessions`를 읽는다. 상태 200이고 본문에 세션 id 3개와 `모의 데이터`가 모두 있다.
- **JSON 확인.** GET `/api/sessions`를 읽는다. 상태 200이고 total_sessions가 3, total_mismatched가 5다. 응답 원문을 증거로 남긴다.
- **상세 구동.** GET `/sessions/DEMO-20261027-B`와 GET `/api/sessions/DEMO-20261027-B`를 읽는다. 둘 다 200이고 화면에 `100.0%`가 보인다.
- **404 확인.** GET `/sessions/NOPE`와 GET `/api/sessions/NOPE`를 읽는다. 둘 다 404여야 하며, 이를 실패로 기록하지 않고 기대 동작으로 transcript에 남긴다.

## Gotchas

- 세션 상세 화면은 홈 화면과 같은 렌더를 쓴다. 상세에서 본 수치를 홈의 최신 세션 수치와 혼동하지 않는다.
- 없는 세션 확인에서 HTTP 오류 예외를 그대로 던지면 구동이 중단된다. 상태 코드를 잡아서 404로 단언한다.
- 목록의 합계(total_mismatched 5)는 세션별 불일치의 합이다. 단일 세션 수치와 비교해 실패로 오판하지 않는다.
