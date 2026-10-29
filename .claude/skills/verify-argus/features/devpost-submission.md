# 제출 문안 패키지

제출 문안 패키지는 `docs/devpost-submission.md`가 정본인 제출 플랫폼 입력용 문안의 구조와 정직성 표기를 검증하는 절차다. 이 절차는 실제 제출을 하지 않으며 SAM 실호출 미실시와 Pi 실촬영 검증 전 상태를 그대로 둔다. 현재 정답은 `SUBMISSION_READY: false`이며 이 기능이 통과해도 제출 준비 완료가 아니다. 파일 원문을 읽어 절 순서와 데모 기준 수치와 블로커를 대조하고 변조 탐지를 확인하는 `devpost-submission` 구동이 대상이다.

## Sub-features

- `devpost-sections` 절 순서: `validate_devpost_text`가 문안의 프로젝트 이름부터 제출 전 교체할 항목까지 절 11개가 `DEVPOST_SECTIONS` 순서대로 모두 있음을 확인한다.
- `devpost-demo-data` 데모 수치: 데모 기준 빈 6개 중 일치 4건·불일치 2건, 절대 차이 6개·순차이 0·일치율 66.7%가 적혀 있고, 실제 창고 성과가 아니라는 표기가 있음을 확인한다.
- `devpost-honesty` 정직성 표기: 모의 어댑터가 동작 중이고 SAM 실호출은 미실시라는 표기, 가짜 transport로만 검증했다는 표기, 키는 Secure Vault 경유로만 받는다는 표기, 테마 가안 표기, 컷 3은 Pi 실촬영 교체 예정인 플레이스홀더라는 표기가 있음을 확인한다.
- `devpost-blockers-not-ready` 블로커와 미준비: 블로커 `pi_real_capture_pending`와 `sam_real_call_pending`이 이 순서로 있고 `SUBMISSION_READY: false`가 현재 정답으로 남아 있음을 확인한다. `qa.pre_submission --json` 실시간 대조에서도 블로커 id 목록과 `submission_ready` false가 같아야 하며, 공개 저장소 주소와 마감 2026-11-05 11:00 KST가 적혀 있음을 확인한다. `qa.claims_audit`의 `audit_text` 주장 감사 결과도 비어 있어야 한다.
- `devpost-tamper-detection` 변조 탐지: 메모리 사본에서 `SUBMISSION_READY: false`를 true로 바꾼 텍스트를 `validate_devpost_text`로 다시 검증하면 문제가 잡혀야 한다. 원본 파일은 바꾸지 않는다.

## How to get to it (user POV)

- 제출자는 프로젝트 루트의 `docs/devpost-submission.md`를 정본으로 절 순서대로 읽어 제출 플랫폼 입력 칸에 옮긴다. 현재 블로커와 제출 상태 절의 `SUBMISSION_READY: false`가 현재 정답이다.
- 문안의 수치는 전부 데모 기준이며 실제 창고 성과가 아니다. SAM 실호출 결과와 Pi 실촬영 컷 3은 제출 전 교체할 항목으로 남아 있다.
- 개발자가 경계를 점검하는 진입점은 검증 헬퍼다: `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature devpost-submission --evidence-dir /tmp/argus-verify-evidence/<run-id>`.
- 제출 마감은 한국 시간으로 2026-11-05 11:00 KST다. 실제 제출과 SAM 실호출과 Pi 실촬영은 이 절차에서 하지 않으며 미실시와 검증 전 상태로 보고한다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 프로젝트 루트에 `docs/devpost-submission.md`가 있다.
- 실제 제출과 SAM 실호출과 Pi 실촬영은 하지 않으며 미실시와 검증 전 상태다. 실제 키 값은 쓰지 않는다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature devpost-submission --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼는 `drive_devpost_submission`이 파일 원문을 읽어 `validate_devpost_text`로 대조한다.
- **절과 데모 수치 확인.** 헬퍼가 `DEVPOST_SECTIONS` 절 11개 순서와 데모 기준 수치 표기와 66.7%를 대조한다.
- **정직성 확인.** 헬퍼가 모의·미실시·가짜 transport·Secure Vault·가안·플레이스홀더 표기가 남아 있는지를 확인한다.
- **블로커와 마감 확인.** 헬퍼가 `pi_real_capture_pending`와 `sam_real_call_pending` 순서와 `SUBMISSION_READY: false`와 공개 저장소 주소와 마감 2026-11-05 11:00 KST를 대조하고 `audit_text` 주장 감사가 비었는지를 확인한다.
- **변조 탐지 확인.** 헬퍼가 메모리 사본에서 false를 true로 바꾼 텍스트를 `validate_devpost_text`로 다시 검증해 변조가 탐지되는지 확인한다. 원본은 수정하지 않는다.
- **실시간 대조 확인.** 헬퍼가 `python3 -m qa.pre_submission --json`을 서브프로세스로 실행해 블로커 id 목록이 문안과 같고 `submission_ready`가 false인지 대조한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `devpost-submission.json`과 `devpost-submission.md`가 남고 `summary.json`의 `feature`가 `devpost-submission`이며 `section_count`와 `claims_audit_clean`과 `tamper_detected`와 `pre_submission_blockers`를 확인한다.

## Gotchas

- `SUBMISSION_READY: false`를 true로 바꾸면 변조로 탐지된다. 변조 검사는 메모리 사본으로만 하며 원본 파일을 고치지 않는다.
- 문안 통과가 제출 준비 완료를 뜻하지 않는다. 블로커 `pi_real_capture_pending`와 `sam_real_call_pending`이 남아 있어 `SUBMISSION_READY: false`가 현재 정답이다.
- 데모 수치를 실제 성과처럼 고치면 실패다. 수치는 데모 기준으로만 적고 실제 창고 성과가 아니라는 표기를 유지한다.
- 키 값은 문서와 코드와 채팅에 쓰지 않는다. Secure Vault 경로로만 받으며 환경변수 이름만 확인한다.
- 실제 제출과 SAM 실호출과 Pi 실촬영은 하지 않으며 미실시와 검증 전으로 남긴다. 이 절차를 그 실행으로 서술하지 않는다.
- 절과 블로커와 데모 수치의 순서는 결정적이다. 하나라도 빠지거나 순서가 바뀌면 실패로 본다.
