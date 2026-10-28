# Argus (신규 제작)

창고 재고실사 코파일럿. 단말로 빈(bin)을 촬영하면 SAM 3.1이 수량을 세고 장부와 대조해 차이 리포트를 만든다. Meta Global AI Developer Hackathon(2026) 출품작으로, 이 저장소의 모든 코드는 행사 기간 안에 새로 작성했다.

## 구성 (계획)

- `terminal/` — 단말 플로우: 촬영 → SAM 3.1 계수 → 장부 대조 → 차이 리포트. Pi 5 + 카메라 실기 기준, 도착 전에는 시뮬레이터로 개발한다.
- `console/` — 관리자 웹 콘솔: 실사 세션 목록, 차이 목록, 요약 지표(실사 완료 수·일치율·불일치 내역).
- `qa/` — 기준값 대조 하네스: 데모 빈 6개의 장부·실측 시나리오를 단언으로 검증한다.
- `docs/` — 제출 스토리와 데모 영상 대본.

## SAM 3.1 연동

- 연동 지점은 Meta Model API다.
- 개발은 모의 어댑터로 진행하고, 환경변수 `SAM_API_BASE_URL`과 `SAM_API_KEY`를 설정하면 실호출로 전환된다.
- 모의 결과는 화면에서 '모의'로 구분해 표기한다.

## 실행법 (초안)

아직 골격 단계라 실행 명령은 구성 요소가 들어오는 대로 이 문서에 확정해 적는다.

- 콘솔: 프로젝트 루트에서 `python3 -m console.server` (기본 http://127.0.0.1:8765, `/`는 화면 — 요약 지표·차이 목록·조치 우선순위·영향 수치 포함, `/api/report`는 JSON, `/sessions`는 데모 세션 3개 목록 화면, `/sessions/<id>`는 세션 상세, `/api/sessions`·`/api/sessions/<id>`는 JSON)
- 단말 시뮬레이터: 프로젝트 루트에서 `python3 -m terminal.simulator` (JSON 리포트 출력, `--out <경로>`로 저장 가능)
- 차이 리포트: 프로젝트 루트에서 `python3 -m terminal.report` (텍스트 리포트, `--json`으로 조치 우선순위 payload, `--out <경로>`로 저장 가능)
- 단위 테스트: 프로젝트 루트에서 `python3 -m unittest discover -s tests` (현재 142개)
- QA 하네스: 프로젝트 루트에서 `python3 -m qa` (기준값 대조 체크 17개, 전부 통과 시 종료코드 0·실패 시 1)
- standalone 점검: 프로젝트 루트에서 `python3 -m qa.standalone` (필수 파일·회사 식별자/비밀 패턴·정직성 표기 체크 5개)
- 데모 영상 자산: 프로젝트 루트에서 `python3 -m demo.captions` (대본 컷 표 9개를 `demo/assets/`에 captions.srt·captions.vtt·shot-list.json으로 생성)
- 콘솔 캡처 자산: 프로젝트 루트에서 `python3 -m demo.capture` (실제 콘솔 서버 응답 4종 — 홈·세션 목록·세션 상세 HTML과 리포트 JSON 원문 — 을 `demo/assets/captures/`에 저장하고 capture-manifest.json으로 상태·마커를 검증. PNG 스크린샷이 아닌 서버 응답 원문 캡처다)
- 데모 영상 조립: 프로젝트 루트에서 `python3 -m demo.assemble` (자막 컷 9개와 캡처 자산을 컷별 소스로 묶은 조립 매니페스트를 `demo/assets/`에 assembly.json·assembly.txt로 생성. 실제 영상 파일이 아닌 편집 결정 목록이며, Pi 컷은 플레이스홀더로 표기)
- 데모 나레이션 대본: 프로젝트 루트에서 `python3 -m demo.narration` (자막 컷 9개의 나레이션 문장을 `demo/assets/`에 narration.json·narration.txt·narration-full.txt로 생성. 실제 음성 파일이 아닌 대본 텍스트 자산이며, 컷 구간 재조정으로 전 컷이 공백 제외 글자수/초 4.0 이하라 속도 경고가 없다)
- 데모 영상 초안 렌더: 프로젝트 루트에서 `python3 -m demo.render_video` (자막 컷 9개를 슬라이드로 만들어 ffmpeg로 이어 붙인 180초 MP4 초안을 `demo/assets/argus-demo-draft.mp4`로 생성. 최종 제출본이 아닌 조립 초안이며, 컷 3은 Pi 도착 후 실촬영으로 교체할 플레이스홀더 슬라이드이고 전 컷에 '모의 데이터 · 데모 기준' 표기가 들어간다)
- 제출 문서: `docs/submission-story.md`(제출 스토리 초안), `docs/submission-summary-en.md`(영문 제출 요약), `docs/demo-script.md`(3분 데모 대본 초안)
- 검증 스킬: `.claude/skills/verify-argus/` — 콘솔·단말을 사용자처럼 구동해 검증하는 프로젝트 로컬 스킬. 점검은 `python3 .claude/skills/verify-argus/scripts/verify_argus.py --doctor`, 구동·증거 수집은 같은 스크립트에 `--evidence-dir /tmp/argus-verify-evidence/<run-id>`를 붙여 실행한다. `--feature`로 기능 5종(console-home·terminal-simulator·session-list·difference-report·demo-video-draft)을 개별 구동하거나 `all`로 전부 구동할 수 있다

## 일정

- 10/28 골격·데이터 모델
- 10/29~31 Pi 실기·카메라
- 11/01~02 SAM 실호출·리포트
- 11/03 제출 패키지(공개 repo standalone·데모 영상 3분)
- 11/04 제출
