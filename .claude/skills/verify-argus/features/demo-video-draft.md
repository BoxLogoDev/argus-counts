# 데모 영상 초안

데모 영상 초안은 제출 영상의 조립 상태를 미리 확인하는 180초 무음 MP4로, 컷 9개를 슬라이드로 이어 붙인 것이며 최종 제출본이 아니다. 컷 3은 Pi 실촬영이 없어 플레이스홀더 슬라이드임을 화면에 명시한다.

## Sub-features

- `video-render` 렌더 실행이 `demo/assets/argus-demo-draft.mp4`를 만든다.
- `video-duration` 영상 길이가 약 180초(허용 오차 1초 이내)다.
- `video-honesty` 전 컷 하단에 `모의 데이터 · 데모 기준` 표기가 있다.
- `video-placeholder` 컷 3은 Pi 도착 후 실촬영으로 교체한다는 경고 문구가 있는 플레이스홀더 화면이다.
- `video-data-panel` 컷별 데이터 패널 줄을 실제 시뮬레이션 리포트에서 구해 대조한다(컷 5 전체 빈 6줄, 컷 6 불일치만 2줄, 컷 9 `데모 기준` 영향 한 줄).
- `video-assembly-fallback` 조립 매니페스트 컷 3에만 파일 입력 폴백 참조가 있고 `build_fallback_ref`·`validate_assembly`로 대조한다(자산 `demo/assets/fallback.json`, 결정일 2026-11-02, Pi 실촬영이 아니다).

## How to get to it (user POV)

- 터미널에서 렌더 모듈을 실행해 초안을 만든다.
- 만든 MP4를 플레이어로 열어 컷 흐름을 눈으로 확인한다.

## Driving it with verify_argus.py

Preconditions:

- ffmpeg와 ffprobe가 PATH에 있다. 없으면 이 기능은 구동 불가로 보고하고 렌더를 건너뛴 것으로 치지 않는다.
- 헬퍼 doctor가 PASS이고, 자막·캡처·조립 자산이 현재 코드 기준으로 재생성돼 있다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **렌더.** Run `python3 -m demo.render_video`. 종료코드 0이고 `demo/assets/argus-demo-draft.mp4`의 크기가 0보다 크다.
- **길이 확인.** Run `ffprobe -v error -show_entries format=duration -of csv=p=0 demo/assets/argus-demo-draft.mp4`. 값이 179~181초 범위다. 출력과 종료 코드를 transcript에 남긴다.
- **프레임 확인.** Run `ffmpeg -y -v error -ss 5 -i demo/assets/argus-demo-draft.mp4 -frames:v 1 /tmp/argus-verify-evidence/<run-id>/cut1.png`와 `-ss 40`으로 컷 3 프레임을 뽑는다. 컷 1에는 제목과 `모의 데이터 · 데모 기준` 표기가, 컷 3에는 Pi 교체 경고가 보여야 한다.
- **자산 정합.** `demo/assets/narration.json`의 pace_warnings가 빈 배열이고, `demo/assets/assembly.json`의 총 길이가 180초인지 확인한다.
- **데이터 패널.** 헬퍼가 `demo.render_video.build_data_panel_lines`로 컷 1~9 패널을 구동한다. 컷 5는 전체 빈 6줄, 컷 6은 불일치 2줄, 컷 3은 `실촬영 데이터 없음 — Pi 도착 후 교체`만 있어야 하며, 변조 리포트(counted_qty 999)가 `실측 999`로 반영돼 하드코딩이 아님을 증명한다. 증거는 `data-panel.json`에 남는다.
- **조립 폴백.** 헬퍼가 `demo.assemble.build_fallback_ref`와 `validate_assembly`로 조립 매니페스트를 구동한다. 컷 3 세그먼트의 fallback은 자산 `demo/assets/fallback.json`·cut_index 3·결정일 2026-11-02·is_pi_real_capture False·capture_source file·replaces pi-placeholder와 일치하고 다른 컷에는 없어야 하며, fallback을 지우거나 is_pi_real_capture를 True로 바꾸면 `validate_assembly`가 지목해야 한다. 조립 텍스트에는 `fallback: demo/assets/fallback.json`와 `Pi 실촬영 아님`이 있어야 한다. 증거는 `assembly-fallback.json`에 남으며, 이 폴백은 Pi 실촬영이 아니고 컷 3 전환 확정도 아니다.

## Gotchas

- 이 MP4는 조립 초안이다. 최종 제출본이나 실촬영 영상으로 서술하지 않는다.
- 렌더는 자막 컷 구간을 그대로 쓴다. 컷 구간을 바꾸면 자막·나레이션·조립 자산을 먼저 재생성해야 길이가 맞는다.
- 프레임 추출 시각은 컷 경계(컷 1: 0~18초, 컷 3: 30~50초)를 피해서 컷 한가운데로 잡는다.
- ffmpeg가 없으면 이미 있는 MP4를 새 렌더로 치지 않는다. 기존 파일의 존재는 렌더 성공의 증거가 아니다.
