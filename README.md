# Argus (신규 제작)

창고 재고실사 코파일럿. 단말로 빈(bin)을 촬영하면 SAM 3.1이 수량을 세고 장부와 대조해 차이 리포트를 만든다. Meta Global AI Developer Hackathon(2026) 출품작으로, 이 저장소의 모든 코드는 행사 기간 안에 새로 작성했다.

## 구성 (계획)

- `terminal/` — 단말 플로우: 촬영 → SAM 3.1 계수 → 장부 대조 → 차이 리포트. Pi 5 + 카메라 실기 기준, 도착 전에는 시뮬레이터로 개발한다.
- `console/` — 관리자 웹 콘솔: 실사 세션 목록, 차이 목록, 요약 지표(실사 완료 수·일치율·불일치 내역).
- `qa/` — 기준값 대조 하네스: 데모 빈 6개의 장부·실측 시나리오를 단언으로 검증한다.
- `docs/` — 제출 스토리와 데모 영상 대본.

## SAM 3.1 연동

- 연동 지점은 Meta Model API다.
- 개발은 모의 어댑터로 진행한다. 환경변수 `SAM_API_BASE_URL`과 `SAM_API_KEY`를 설정하면 실호출 어댑터가 선택되도록 코드 경로는 준비돼 있으나, 실제 API로 검증하지 않았고 실호출은 아직 하지 않았다. 공식 규격과 크레딧 입금을 확인한 뒤에만 실사용한다. 규격 의존 부분은 어댑터의 요청 구성·응답 해석 두 지점에 격리돼 있고, 가짜 전송(fake transport) 테스트로만 검증했다.
- 모의 결과는 화면에서 '모의'로 구분해 표기한다.

## 실행법 (초안)

아직 골격 단계라 실행 명령은 구성 요소가 들어오는 대로 이 문서에 확정해 적는다.

- 콘솔: 프로젝트 루트에서 `python3 -m console.server` (기본 http://127.0.0.1:8765, `/`는 화면 — 요약 지표·준비 상태(SAM 실호출 준비와 Pi 실촬영 준비의 블로커를 분리 표기하며, 준비 완료는 실호출·실촬영 성공을 뜻하지 않는다)·차이 목록·조치 우선순위·영향 수치 포함, `/api/report`는 JSON, `/api/readiness`는 준비 상태 JSON(실제 API 호출·촬영 없음, 환경변수 값 미포함), `/sessions`는 데모 세션 3개 목록 화면, `/sessions/<id>`는 세션 상세, `/api/sessions`·`/api/sessions/<id>`는 JSON)
- 단말 시뮬레이터: 프로젝트 루트에서 `python3 -m terminal.simulator` (JSON 리포트 출력, `--out <경로>`로 저장 가능)
- 차이 리포트: 프로젝트 루트에서 `python3 -m terminal.report` (텍스트 리포트, `--json`으로 조치 우선순위 payload, `--out <경로>`로 저장 가능)
- 사진 입력 파이프라인: 프로젝트 루트에서 `python3 -m terminal.photo_intake --capture A-01-02=<사진경로> [--capture <빈>=<사진경로> ...]` (파일 기반 입력이며 Pi 실촬영이 아니다. 사진 파일의 크기·SHA-256을 기록하고 기존 계수→대조 흐름에 태우며, 계수는 어댑터 경유·모의 기준이다. Pi 도착 후에는 카메라가 만든 사진 파일을 같은 형식으로 넘긴다)
- Pi 카메라 캡처: 프로젝트 루트에서 `python3 -m terminal.pi_capture --probe` (libcamera-still·raspistill 명령 존재만 탐지하며 명령을 실행하지 않는다. `--capture <빈>=<출력경로>`로 캡처를 시도할 수 있으나 Pi 실촬영 검증 전이며, 이 VM처럼 카메라 명령이 없는 환경에서는 available=false로 보고하고 캡처는 PiCaptureError로 실패한다. 가짜 파일로 대체하지 않는다)
- Pi 촬영 세션: 프로젝트 루트에서 `python3 -m terminal.pi_session --out-dir <캡처 디렉터리> [--bin <빈> ...] [--session-id <id>] [--out <경로>]` (Pi 캡처 경계와 사진 입력 파이프라인을 이어 한 번의 호출로 촬영→계수→대조→리포트를 수행한다. 카메라 명령이 없으면 PiCaptureError로 실패하고 종료코드 1이며 가짜 파일로 대체하지 않는다. Pi 실촬영 검증 전이며 계수는 모의 어댑터 기준이고 리포트의 capture_source는 pi-camera, probe와 honesty에 검증 전임이 기록된다)
- 단위 테스트: 프로젝트 루트에서 `python3 -m unittest discover -s tests` (현재 304개)
- QA 하네스: 프로젝트 루트에서 `python3 -m qa` (기준값 대조 체크 17개, 전부 통과 시 종료코드 0·실패 시 1)
- standalone 점검: 프로젝트 루트에서 `python3 -m qa.standalone` (필수 파일·회사 식별자/비밀 패턴·정직성 표기·현재형 주장 감사 체크 6개 — 주장 감사는 qa.claims_audit를 재사용해 통합했다)
- 현재형 주장 감사: 프로젝트 루트에서 `python3 -m qa.claims_audit` (README·제출 문서에서 SAM 실호출·Pi 실촬영 같은 미실시 사항을 이미 한 것처럼 단정하는 문장을 감사. 정직성 표기가 없는 단정만 위반으로 잡으며, 전부 통과 시 종료코드 0)
- SAM 실호출 전환 준비 점검: 프로젝트 루트에서 `python3 -m qa.sam_readiness [--credit-confirmed] [--json]` (실제 API를 호출하지 않고 크레딧 입금 확인 여부와 SAM_API_BASE_URL·SAM_API_KEY 존재 여부만 점검한다. 환경변수 값은 출력하지 않는다. 준비 완료는 실호출 성공을 뜻하지 않으며, 현재 기본 환경에서는 블로커 3건으로 READY_FOR_LIVE_CALL: false다)
- SAM 단일 빈 스모크: 프로젝트 루트에서 `python3 -m qa.sam_smoke [--credit-confirmed] [--json] [--bin <빈>]` (준비 점검을 통과하지 못하면 실제 API를 호출하지 않고 차단 보고만 낸다. 통과한 경우에만 빈 1개를 시도하며, 성공해도 전체 세션 성공을 뜻하지 않고 실패하면 모의로 대체하지 않는다. 현재 기본 환경에서는 블로커 3건으로 차단되고 종료코드 1이다)
- Pi 실촬영 준비 점검: 프로젝트 루트에서 `python3 -m qa.pi_readiness [--device-confirmed] [--json]` (실제 촬영을 하지 않고 Pi 장치 도착의 외부 확인 여부와 카메라 명령(libcamera-still·raspistill) 존재만 점검한다. 카메라 명령을 실행하지 않고 존재만 탐지하며, 준비 완료는 Pi 실촬영 성공을 뜻하지 않는다. Pi 실촬영 검증 전이며, 현재 이 환경에서는 블로커 2건으로 READY_FOR_REAL_CAPTURE: false다)
- 제출 전 전수 점검: 프로젝트 루트에서 `python3 -m qa.pre_submission` (QA 17개·standalone 6개·주장 감사·SAM 실호출 준비 점검 정합·Pi 실촬영 준비 점검 정합·콘솔 준비 상태 정합(콘솔이 같은 조건의 두 준비 점검과 어긋나지 않는지)·데모 자산 존재/정합·영상 초안(크기와 컷 1~9 데이터 패널 정합)의 기계 점검 9종을 한 번에 확인하고, JSON 보고에는 readiness 섹션(SAM 블로커·Pi 블로커·콘솔 blocker_count와 overall_ready, 환경변수 값은 포함하지 않음)이 들어가며, Pi 실촬영 미실시·SAM 실호출 미실시 블로커 2건을 분리해 보고한다. 기계적 체크가 전부 통과해도 블로커가 남아 있으면 SUBMISSION_READY: false이며, `--json`으로 같은 내용을 JSON 출력)
- 데모 영상 자산: 프로젝트 루트에서 `python3 -m demo.captions` (대본 컷 표 9개를 `demo/assets/`에 captions.srt·captions.vtt·shot-list.json으로 생성)
- 콘솔 캡처 자산: 프로젝트 루트에서 `python3 -m demo.capture` (실제 콘솔 서버 응답 4종 — 홈·세션 목록·세션 상세 HTML과 리포트 JSON 원문 — 을 `demo/assets/captures/`에 저장하고 capture-manifest.json으로 상태·마커를 검증. PNG 스크린샷이 아닌 서버 응답 원문 캡처다)
- 데모 영상 조립: 프로젝트 루트에서 `python3 -m demo.assemble` (자막 컷 9개와 캡처 자산을 컷별 소스로 묶은 조립 매니페스트를 `demo/assets/`에 assembly.json·assembly.txt로 생성. 실제 영상 파일이 아닌 편집 결정 목록이며, Pi 컷은 플레이스홀더로 표기)
- 데모 나레이션 대본: 프로젝트 루트에서 `python3 -m demo.narration` (자막 컷 9개의 나레이션 문장을 `demo/assets/`에 narration.json·narration.txt·narration-full.txt로 생성. 실제 음성 파일이 아닌 대본 텍스트 자산이며, 컷 구간 재조정으로 전 컷이 공백 제외 글자수/초 4.0 이하라 속도 경고가 없다)
- 데모 영상 초안 렌더: 프로젝트 루트에서 `python3 -m demo.render_video` (자막 컷 9개를 슬라이드로 만들어 ffmpeg로 이어 붙인 180초 MP4 초안을 `demo/assets/argus-demo-draft.mp4`로 생성. 슬라이드 하단 데이터 패널은 시뮬레이션 리포트에서 가져온 빈별 대조·차이·조치·요약 수치를 보여 주며 하드코딩이 아니다. 최종 제출본이 아닌 조립 초안이며, 컷 3은 Pi 도착 후 실촬영으로 교체할 플레이스홀더 슬라이드이고 전 컷에 '모의 데이터 · 데모 기준' 표기가 들어간다)
- 제출 문서: `docs/submission-story.md`(제출 스토리 초안), `docs/submission-summary-en.md`(영문 제출 요약), `docs/demo-script.md`(3분 데모 대본 초안), `docs/submission-runbook.md`(제출 런북 — 크레딧 확인·키·SAM 전환·Pi 촬영·최종 점검·제출 순서, 현재 블로커 2건 기준이며 모의·검증 전·미실시 표기를 유지한다)
- 검증 스킬: `.claude/skills/verify-argus/` — 콘솔·단말을 사용자처럼 구동해 검증하는 프로젝트 로컬 스킬. 점검은 `python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor`, 구동·증거 수집은 같은 스크립트에 `--evidence-dir /tmp/argus-verify-evidence/<run-id>`를 붙여 실행한다. `--feature`로 기능 14종(console-home·terminal-simulator·session-list·difference-report·demo-video-draft·photo-intake·pre-submission·pi-capture·pi-session·sam-live·sam-readiness·submission-runbook·pi-readiness·console-readiness)을 개별 구동하거나 `all`로 전부 구동할 수 있다. pi-capture는 Pi 캡처 경계를 탐지·기대 실패·가짜 runner 성공으로 구동하며 Pi 실촬영 검증 전이다. pi-session은 Pi 촬영 세션을 CLI 기대 실패와 가짜 which/runner 주입 성공으로 구동하며 Pi 실촬영 검증 전이다. sam-live는 SAM 실호출 경계를 가짜 transport 주입으로만 구동하며 실제 API 호출은 하지 않고 SAM 실호출 검증 전이다. sam-readiness는 SAM 실호출 전환 준비 점검을 CLI 기본 차단 3건과 가짜 환경 준비 완료로 구동하며 실제 API를 호출하지 않고, 준비 완료는 실호출 성공이 아니다. pi-readiness는 Pi 실촬영 준비 점검을 CLI 기본 차단 2건과 가짜 probe 준비 완료로 구동하며 실제 촬영을 하지 않고, 준비 완료는 실촬영 성공이 아니다. submission-runbook은 제출 런북 원문을 읽어 절 순서·블로커 2건·최종 점검 명령 8종을 대조하고 SUBMISSION_READY: false 변조를 탐지하며, 런북 통과가 제출 준비 완료를 뜻하지 않는다. console-readiness는 콘솔 준비 상태를 /api/readiness와 홈 패널로 구동하며 가짜 환경·가짜 probe 준비 완료와 SAM/Pi 분리, 환경변수 값 누출 없음을 확인하고, 준비 완료는 실호출·실촬영 성공이 아니다

## 일정

- 10/28 골격·데이터 모델
- 10/29~31 Pi 실기·카메라
- 11/01~02 SAM 실호출·리포트
- 11/03 제출 패키지(공개 repo standalone·데모 영상 3분)
- 11/04 제출
