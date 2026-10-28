# 차이 리포트

차이 리포트는 실사 결과를 후속 조치로 바꾸는 산출물로, 차이 큰 빈부터 조치 힌트와 함께 정렬한 우선순위와, 수치가 데모 데이터 기준임을 밝히는 영향 한 줄을 텍스트와 JSON으로 제공한다.

## Sub-features

- `report-actions` 조치 우선순위: 1순위 A-01-02 부족(-3), 2순위 B-01-02 초과(+3).
- `report-impact` 영향 한 줄: `데모 기준: 빈 6개 중 불일치 2건, 절대 차이 6개, 일치율 66.7%`.
- `report-json` `--json` payload: actions 2건과 impact_line 포함.
- `report-out` `--out <경로>`로 리포트를 파일에 저장.

## How to get to it (user POV)

- 터미널에서 리포트 모듈을 실행해 화면에서 바로 읽는다.
- 파일이나 다른 도구에 넘길 때는 `--out` 또는 `--json`으로 얻는다.
- 콘솔 홈 화면에서도 같은 우선순위를 `조치 우선순위` 섹션으로 본다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있어 리포트가 모의 기준으로 만들어진다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **텍스트 리포트.** Run `python3 -m terminal.report`. 종료코드 0이고 출력에 조치 1순위 `A-01-02`, 2순위 `B-01-02`가 순서대로 있으며, 말미에 `데모 기준`으로 시작하는 영향 한 줄이 있다. 출력을 증거 transcript에 남긴다.
- **JSON 리포트.** Run `python3 -m terminal.report --json`. payload의 actions가 2건이고 impact_line에 `데모 기준`이 포함되며 source 표기가 모의 기준과 어긋나지 않는다.
- **파일 저장 확인.** Run `python3 -m terminal.report --out /tmp/argus-verify-evidence/<run-id>/report.txt`. 파일을 다시 읽어 우선순위 순서와 영향 한 줄이 stdout과 같은지 확인한다.
- **콘솔 교차 확인.** 콘솔 홈 증거(`home.html`)의 조치 우선순위 섹션 순서가 리포트와 같은지 대조한다.

## Gotchas

- 영향 한 줄의 `데모 기준` 접두어를 빠뜨리면 실측 성과로 오독된다. 이 문구가 없으면 실패다.
- 우선순위는 절대 차이 내림차순이다. 빈 id 순으로 정렬된 목록과 혼동하지 않는다.
- 동률(둘 다 절대 차이 3)인 경우에도 현재 데모 데이터의 순서는 A-01-02, B-01-02로 고정돼 있다. 순서가 바뀌면 회귀로 보고한다.
