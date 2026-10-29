# 콘솔 준비 상태

콘솔 준비 상태는 `console.readiness.build_readiness`가 묶은 SAM 실호출 준비와 Pi 실촬영 준비를 콘솔 홈의 `준비 상태` 패널과 `GET /api/readiness` JSON으로 같은 값으로 보여 주는지 검증하는 절차다. 이 절차는 임시 포트 서버를 구동하며 실제 API를 호출하지 않고 실제 촬영을 하지 않는다. 기본 환경에서는 SAM 블로커 `sam_credit_not_confirmed`를 포함한 3건과 Pi 블로커 `pi_camera_command_missing`를 포함한 2건이 분리돼 보여야 하고, 준비 완료는 실호출·실촬영 성공을 뜻하지 않는다.

## Sub-features

- `console-readiness-api` 준비 상태 JSON: 임시 포트에서 `GET /api/readiness`가 200을 주고 `sam_blockers` 3건, `pi_blockers` 2건, `blocker_count` 5, `sam_ready`·`pi_ready`·`overall_ready`가 모두 `false`이며 `sam.ready_for_live_call`과 `pi.ready_for_real_capture`도 `false`임을 확인한다.
- `console-readiness-home-panel` 홈 패널: `GET /` 홈 화면에서 `준비 상태` 섹션이 실사 세션 정보 뒤·차이 목록 앞에 있고, `SAM 실호출 준비: 준비 안 됨`·`Pi 실촬영 준비: 준비 안 됨`·블로커 id·정직성 문구가 모두 발견됨을 확인한다.
- `console-readiness-fake-ready` 가짜 준비 완료: 프로세스 안에서 `build_readiness`에 가짜 환경과 가짜 probe, 크레딧·장치 확인을 넘기면 `overall_ready`가 `true`이고 블로커가 0건임을 확인한다.
- `console-readiness-sam-pi-separation` SAM·Pi 분리: 가짜 SAM만 준비하면 `sam_ready`만 `true`이고, 가짜 Pi만 준비하면 `pi_ready`만 `true`이며, 어느 경우에도 `overall_ready`는 `false`임을 확인한다.
- `console-readiness-no-leak` 값 누출 없음: 가짜 환경변수 값(sentinel)은 `build_readiness` 결과와 증거 어디에도 새지 않는다. 환경변수 값은 증거에 새지 않는다.

## How to get to it (user POV)

- 사용자가 닿는 진입점은 브라우저 콘솔 홈 `/`의 `준비 상태` 섹션과 프로그램이 읽는 `GET /api/readiness` JSON이다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature console-readiness --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 실제 SAM API 호출과 실제 Pi 촬영은 이 절차의 범위가 아니다. 준비 완료는 실호출·실촬영 성공을 뜻하지 않으므로, 실제 성공은 크레딧·키·장치가 갖춰진 뒤 별도로 확인한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다. 기본 블로커 기대값은 이 전제에서만 성립한다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.
- 서버는 헬퍼가 띄운 임시 포트 서버만 쓴다. 8765 상주 인스턴스는 구동하지 않는다.

- **기본 구동.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature console-readiness --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `drive_console_readiness`로 임시 포트 HTTP와 프로세스 내 `build_readiness`만 구동한다.
- **API 대조.** 헬퍼가 `GET /api/readiness` 응답에서 SAM 블로커 순서 `sam_credit_not_confirmed`, `sam_base_url_missing`, `sam_api_key_missing`와 Pi 블로커 순서 `pi_device_arrival_not_confirmed`, `pi_camera_command_missing`, `blocker_count` 5를 대조한다.
- **홈 패널 대조.** 헬퍼가 `GET /` 응답에서 준비 상태 마커 6종과 섹션 순서(실사 세션 정보 → 준비 상태 → 차이 목록)를 대조한다.
- **가짜 준비 완료 대조.** 헬퍼가 가짜 환경·가짜 probe로 `overall_ready` `true`를, SAM만·Pi만 준비한 경우의 분리 결과를 대조하고 sentinel 누출이 없음을 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `console-readiness.json`(/api/readiness 응답 원문), `console-readiness-ready.json`(가짜 준비 완료 결과, sentinel 값 없음), `console-readiness-home.html`(홈 응답 원문)이 남고, `summary.json`의 `feature`가 `console-readiness`이며 `fake_overall_ready`가 `true`, `sentinel_leaked`가 `false`인지 대조한다.

## Gotchas

- 준비 완료를 실호출·실촬영 성공으로 서술하지 않는다. 준비 완료는 실호출·실촬영 성공을 뜻하지 않으며, 증거와 보고 모두 그렇게 표기한다.
- 이 절차에서 실제 API를 호출하거나 실제 촬영을 하면 검증이 무효가 된다.
- 환경변수 값이 설정된 환경에서는 기본 블로커 기대값이 달라진다. 전제를 먼저 확인하고, 가짜 값은 프로세스 안에서만 주입한다.
- 블로커 순서는 결정적이다: SAM은 `sam_credit_not_confirmed`부터, Pi는 `pi_device_arrival_not_confirmed`부터다. 순서가 바뀌면 실패로 본다.
- 홈 패널만 보고 통과시키지 않는다. `/api/readiness` JSON과 홈 패널이 같은 블로커를 보여야 증명이 된다.
