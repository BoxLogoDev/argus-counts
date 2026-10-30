# SAM 실호출 준비

SAM 실호출 준비는 `terminal.sam_adapter`의 실호출 경계가 실제 호출 없이도 계약을 지키는지 검증하는 절차다. 이 절차에서는 실제 API 호출 없음이 전제이며(실호출 자체는 2026-10-30 전체 세션으로 검증했다(같은 가상 사진 재사용, 빈별 정확도 아님)), `LiveSamCounter`에는 fake transport만 주입한다. 가짜 주소 `https://example.invalid/sam`과 가짜 키 `test-key-not-real`을 쓰며, 키는 Authorization 헤더로만 키 전송되고 본문에 키 없음 상태를 확인한다. 실패 시 모의 폴백 없음 원칙대로 `SamCountingError`가 나야 한다.

## Sub-features

- `sam-live-fake-success` 가짜 성공: 호출 인자를 기록하고 `(200, {"counted_qty": 5})`를 돌려주는 fake transport로 `LiveSamCounter("https://example.invalid/sam/", "test-key-not-real", transport=fake)`를 만들어 `A-01-02`를 `image_ref="photo-1.jpg"`로 센다. 결과는 `counted_qty` 5이며 `source`가 `sam`이다. 기록된 url은 끝 슬래시가 제거된 `https://example.invalid/sam`이고, Authorization 헤더로만 키 전송되므로 헤더 값은 `Bearer test-key-not-real`이다. `build_payload`가 만든 body를 JSON으로 풀면 `model`이 `sam-3.1`이고, `input`의 user 메시지에 `input_text` "cardboard box"와 `input_image`의 `image_url` `photo-1.jpg`가 들어 있으며, 본문에 키 없음 상태를 확인한다. 본문 규격 자체는 2026-10-30에 커넥터 경유 실호출 탐침으로 검증했지만, 이 절차 안에서는 여전히 fake transport만 쓴다.
- `sam-live-parse-variants` 해석 변형: `parse_response`가 `{"counted_qty": 7}`을 7로, `{"result": {"quantity": 4}}`를 4로, `{"detections": [1, 2]}`를 2로 해석함을 확인한다.
- `sam-live-http-error` HTTP 실패 차단: `(503, {...})`를 돌려주는 fake transport로 `LiveSamCounter.count`를 호출하면 `SamCountingError`가 나고 모의 폴백 없음 상태를 확인한다. 예외가 나야 통과다.
- `sam-live-transport-error` 전송 예외 감싸기: `OSError("sensitive-detail")`를 던지는 fake transport로 호출하면 `SamCountingError`로 감싸지고, 예외 문자열에 `sensitive-detail`과 `test-key-not-real`이 모두 없음을 확인한다.
- `sam-live-mock-selection` 모의 선택 경계: 환경변수 `SAM_API_BASE_URL`과 `SAM_API_KEY`를 `os.environ`에서 잠시 제거했다가 정확히 복원한 상태에서 `build_counter`가 `MockSamCounter`를 고르고, 그 `count` 결과의 `source`가 `mock`이며 수량이 5임을 확인한다.

## How to get to it (user POV)

- 사용자에게 닿는 SAM 실호출 진입점은 아직 없다. 실호출은 전체 세션으로 검증했지만(같은 가상 사진 재사용, 빈별 정확도 아님) 이 절차에서는 실제 API 호출 없음 상태이므로, 콘솔과 단말 CLI의 기본 계수는 모의 어댑터 기준이다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-live --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 API 주소와 실제 키를 넣고 호출하는 경로는 이 절차의 범위가 아니다. 크레딧과 공식 규격이 확인되기 전까지 `LiveSamCounter`의 기본 transport로 `count`를 실행하지 않는다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 이 절차에서는 실제 API를 호출하지 않음을 전제로 한다. 실제 API 호출 없음 조건을 지키며, 모든 `LiveSamCounter` 호출에는 fake transport만 주입한다.
- 가짜 주소는 `https://example.invalid/sam`이며 가짜 키는 `test-key-not-real`이다. `example.invalid`는 도달 대상이 아니라 기록용 가짜 주소다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature sam-live --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 네트워크를 쓰지 않고 fake transport 주입만으로 `drive_sam_live`를 실행한다.
- **가짜 성공 확인.** 헬퍼가 `LiveSamCounter`에 fake transport를 주입해 `counted_qty` 5와 `source=sam`을 받고, 끝 슬래시가 제거된 url, Authorization 헤더로만 키 전송된 상태, `build_payload` 본문의 `model`·`input_text`·`image_url`, 본문에 키 없음을 대조한다.
- **해석 변형 확인.** 헬퍼가 `parse_response`의 세 형태를 확인한다. 최상위 수량 키, `result` 안의 수량 키, `detections` 리스트 길이가 각각 7·4·2가 된다.
- **실패 차단 확인.** 헬퍼가 HTTP 503 fake transport와 `OSError` fake transport를 각각 호출한다. 두 경우 모두 `SamCountingError`가 나야 하며, 모의 폴백 없음 상태와 예외 문자열에 원본 상세와 키가 없음을 확인한다.
- **모의 선택 확인.** 헬퍼가 두 환경변수를 잠시 제거하고 정확히 복원하면서 `build_counter`의 모의 선택을 확인한다. 결과는 `MockSamCounter`이며 `source=mock`이고 수량은 5다.
- **증거 확인.** 종료 후 증거 디렉터리에 `sam-live-fake.json`(url·model·input_text·image_url·counted_qty·source, 키 원문 없음)과 `sam-live-errors.json`(`http_error_blocked`·`transport_error_wrapped`·`mock_selection_ok`)이 남고, `summary.json`의 `feature`가 `sam-live`이며 `fake_url`이 `https://example.invalid/sam`인지 대조한다.

## Gotchas

- 가짜 성공을 SAM 실호출 성공으로 서술하지 않는다. 증거와 보고 모두 이 절차 안에서는 fake transport 구동으로 표기한다.
- 기본 transport를 쓰는 `LiveSamCounter.count`를 이 절차에서 실행하지 않는다. 실제 API 호출 없음 조건이 깨진다.
- HTTP 실패와 전송 실패에서 모의 폴백 없음이 정답이다. 예외 없이 모의 숫자가 돌아오면 실패로 본다.
- 키는 Authorization 헤더로만 키 전송된다. 본문에 키 없음 상태를 깨거나 증거 파일에 `test-key-not-real` 원문을 남기면 실패로 본다.
- 전송 예외를 `SamCountingError`로 바꿀 때 원본 메시지(`sensitive-detail`)와 키가 예외 문자열에 섞이면 실패로 본다.
- 환경변수 제거와 복원은 한 쌍이다. 복원하지 않으면 이후 검증이 오염되므로 `try/finally` 경계를 유지한다.
