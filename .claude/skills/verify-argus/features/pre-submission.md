# 제출 전 전수 점검

제출 전 전수 점검은 기존 기계적 점검 25종을 한 번에 구동하는 CLI다. 기계적 점검이 전부 통과해도 제출 블로커 1건이 남아 `submission_ready`는 항상 false이며, 기계적 통과를 제출 가능으로 서술하지 않는다.

## Sub-features

- `pre-run` 기본 실행: `python3 -m qa.pre_submission`으로 기계적 점검 25종을 한 번에 구동해 텍스트 보고를 얻는다.
- `pre-json` `--json` 보고: 같은 점검을 JSON으로 얻어 passed·total·mechanical_pass·checks를 확인한다.
- `pre-blockers` 블로커 1건 분리 보고: `pi_real_capture_pending`을 종료코드와 별도 목록으로 보고한다. SAM 3.1 실호출은 2026-10-30 전체 세션으로 검증해(같은 가상 사진 재사용, 빈별 정확도 아님) 블로커에서 제외했다.
- `pre-not-ready` submission_ready false 확인: 기계적 통과와 무관하게 `submission_ready`가 false인지 확인한다.
- `pre-honesty` honesty 표기: `honesty`에 '모의'를 포함한 줄과 '데모 기준'을 포함한 줄이 있는지 확인한다.
- `pre-readiness` 준비 점검 정합: SAM 실호출 준비 점검과 Pi 실촬영 준비 점검의 보고가 내부적으로 모순되지 않고 전수 점검 블로커 1건과 어긋나지 않는지 확인하며, JSON의 `readiness` 섹션에 두 준비 점검의 블로커가 그대로 기록된다. 준비가 안 된 상태 자체는 기계 점검 실패가 아니다.
- `pre-console-readiness` 콘솔 준비 상태 정합: 콘솔 준비 상태(`console.readiness`)가 같은 조건의 SAM·Pi 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.console`에 blocker_count와 overall_ready가 그대로 기록된다. 콘솔 패널이 준비 점검과 어긋나면 기계 점검 실패다.
- `pre-sam-session` SAM 전체 세션 정합: SAM 전체 세션(`qa.sam_session`) 보고가 SAM 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.sam_session`에 status와 블로커가 그대로 기록된다. 전체 세션 정합은 전수 점검 전용 가짜 counter로만 구동하며 실제 API를 호출하지 않는다. 준비가 안 된 상태에서는 전체 세션이 blocked이고 가짜 counter 호출이 0건이어야 하며, 가짜 성공은 빈별 정확도 검증이 아니다.
- `pre-sam-smoke` SAM 스모크 정합: SAM 단일 빈 스모크(`qa.sam_smoke`) 보고가 SAM 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.smoke`에 status와 블로커가 그대로 기록된다. 스모크 정합은 전수 점검 전용 가짜 counter로만 구동하며 실제 API를 호출하지 않는다. 준비가 안 된 상태에서는 스모크가 blocked이고 가짜 counter 호출이 0건이어야 한다.
- `pre-devpost` 제출 문안 정합: 제출 문안 패키지(`docs/devpost-submission.md`) 원문의 절 11개 순서·블로커 1건·`SUBMISSION_READY: false`·데모 기준 수치가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.devpost`에 section_count와 블로커가 그대로 기록된다. 문안 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-readme` README 정합: README(`README.md`) 원문의 절 5개 순서·블로커 1건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.readme`에 section_count와 블로커가 그대로 기록된다. README 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-demo-script` 데모 대본 정합: 데모 대본(`docs/demo-script.md`) 원문의 절 3개 순서·블로커 1건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.demo_script`에 section_count와 블로커가 그대로 기록된다. 데모 대본 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-en-summary` 영문 제출 요약 정합: 영문 제출 요약(`docs/submission-summary-en.md`) 원문의 절 8개 순서·블로커 1건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.en_summary`에 section_count와 블로커가 그대로 기록된다. 영문 요약 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-story` 제출 스토리 정합: 제출 스토리(`docs/submission-story.md`) 원문의 절 7개 순서·블로커 1건·`SUBMISSION_READY: false`·데모 기준 수치·정직성 표기가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.story`에 section_count와 블로커가 그대로 기록된다. 스토리 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-runbook` 제출 런북 정합: 제출 런북(`docs/submission-runbook.md`) 원문의 절 7개 순서·블로커 1건·`SUBMISSION_READY: false`·최종 점검 명령 8종이 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.runbook`에 section_count와 블로커·final_command_count가 그대로 기록된다. 런북 정합은 파일 원문 대조만 하며 실제로 제출하지 않는다.
- `pre-pi-session` Pi 전체 세션 정합: Pi 전체 촬영 세션(`qa.pi_session`) 보고가 Pi 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.pi_session`에 status와 블로커가 그대로 기록된다. 전체 세션 정합은 전수 점검 전용 가짜 session으로만 구동하며 실제 촬영을 하지 않는다. 준비가 안 된 상태에서는 전체 세션이 blocked이고 가짜 session 호출이 0건이어야 하며, 가짜 성공을 실제 Pi 실촬영 성공으로 주장하지 않는다.
- `pre-pi-smoke` Pi 스모크 정합: Pi 단일 빈 스모크(`qa.pi_smoke`) 보고가 Pi 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.pi_smoke`에 status와 블로커가 그대로 기록된다. 스모크 정합은 전수 점검 전용 가짜 session으로만 구동하며 실제 촬영을 하지 않는다. 준비가 안 된 상태에서는 스모크가 blocked이고 가짜 session 호출이 0건이어야 한다.
- `pre-video-panel` 영상 데이터 패널 정합: `video_draft_present` 체크가 MP4 크기에 더해 컷 1~9 데이터 패널(컷 5 전체 빈 6줄·컷 6 불일치 2줄·컷 3 플레이스홀더 정직 표기·컷 9 '데모 기준')이 현재 시뮬레이션 리포트와 맞는지 확인하고, 통과 detail에 `data_panel_cuts=9`가 포함된다.
- `pre-video-fallback-render` 영상 폴백 렌더 정합: `video_draft_present` 체크가 기본 MP4·데이터 패널에 더해 폴백 MP4(`demo/assets/argus-demo-fallback-draft.mp4`) 크기와 컷 3 폴백 패널 4줄(파일 입력 폴백 — Pi 실촬영 아님·결정일 2026-11-02·capture_source=file·source=mock·요약·A-01-02 사진 해시)이 현재 폴백 매니페스트와 맞는지 확인하고, 통과 detail에 `fallback_render_cut=3`가 포함된다. 폴백 렌더 대조는 저장·생성 자산 대조만이며 Pi 실촬영으로 주장하지 않는다.
- `pre-submission-inventory` 제출물 인벤토리 정합: 제출물 인벤토리(`qa.submission_inventory`) 보고의 제출물 18개·present·missing·합계·블로커 1건·`submission_ready` false가 전수 점검 블로커와 어긋나지 않는지 확인하며, JSON의 `readiness.submission_inventory`에 total_files와 블로커가 그대로 기록된다. 인벤토리 정합은 파일 대조만 하며 실제로 제출하지 않고, 인벤토리 완결을 제출 가능으로 주장하지 않는다.
- `pre-fallback-decision` 폴백 결정 정합: 폴백 결정(`qa.fallback_decision`) 보고의 결정일 2026-11-02·status·fallback_adopted 산식·pi_blockers가 Pi 준비 점검 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.fallback_decision`에 status와 pi_blockers가 그대로 기록된다. 폴백 결정 정합은 날짜·준비 상태 판정만 대조하며 실제 촬영을 하지 않고, 결정일 전 pending은 실패가 아니며, fallback_due(폴백 채택)를 Pi 실촬영 성공으로 주장하지 않는다.
- `pre-final-package` 최종 묶음 정합: 최종 묶음(`qa.final_package`) 보고의 status·inventory_present/total·deadline_status·fallback_status·블로커 1건·`submission_ready` false가 제출물 인벤토리·제출 마감·폴백 결정 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.final_package`에 status와 블로커가 그대로 기록된다. 최종 묶음의 패키지 내보내기 실측(export_copied·export_total·export_missing·export_total_bytes)도 인벤토리의 present_files·total_files·missing·total_bytes와 패키지 내보내기의 missing·total_bytes와 교차 대조하며, 증거 summary에 `readiness_final_package_export_copied`·`readiness_final_package_export_total`·`readiness_final_package_export_missing`·`readiness_final_package_export_total_bytes`로 남는다. 최종 묶음 정합은 보고 대조만 하며 실제로 제출하지 않고, blocked는 실패가 아니며 ready_for_packaging이어도 제출 완료를 뜻하지 않는다.
- `pre-package-export` 패키지 내보내기 정합: 패키지 내보내기(`qa.package_export`) 보고의 제출물 18개·copied_files·missing·합계(total_bytes)·블로커 1건·`submission_ready` false가 제출물 인벤토리 보고와 어긋나지 않는지 확인하며, JSON의 `readiness.package_export`에 total_files·copied_files·missing·total_bytes와 블로커가 그대로 기록되고, missing과 total_bytes는 제출물 인벤토리의 missing·total_bytes와 교차 대조한다. 같은 staging의 재검증(verify) 결과인 verify_verified·verify_copied_files·verify_total_bytes도 필수값으로 검사해 copied_files·total_bytes와 대조하며, 증거 summary에 `readiness_package_export_verify_verified`·`readiness_package_export_verify_copied_files`·`readiness_package_export_verify_total_bytes`로 남는다. 내보내기 정합은 임시 staging 복사·해시 대조만 하며 실제로 제출하지 않고, 내보내기 완결을 제출 가능으로 주장하지 않는다.
- `pre-assembly-fallback` 조립 폴백 정합: `demo_assets_consistent` 체크가 조립 매니페스트 컷 3에만 파일 입력 폴백 참조(asset·cut_index 3·결정일 2026-11-02·is_pi_real_capture false·capture_source file·replaces pi-placeholder)가 있고 정직성 표기가 포함되는지 확인하며, 통과 detail에 `assembly_fallback_cut=3`가 포함되고 증거 summary에 `demo_assembly_fallback_cut`으로 남는다. 조립 폴백 대조는 저장 자산 대조만이며 Pi 실촬영이나 컷 3 전환 확정으로 주장하지 않는다.

## How to get to it (user POV)

- 터미널에서 프로젝트 루트로 이동해 전수 점검 모듈을 실행한다: `python3 -m qa.pre_submission`.
- 기계 판독용 보고가 필요하면 `--json`을 붙여 실행한다: `python3 -m qa.pre_submission --json`.
- 검증 헬퍼로 구동하려면 `--feature pre-submission`을 준다. 헬퍼가 텍스트 실행과 `--json` 실행을 모두 구동하고 증거를 남긴다.

## Driving it with verify_argus.py

Preconditions:

- 헬퍼 doctor가 PASS다.
- 환경변수 `SAM_API_BASE_URL`·`SAM_API_KEY`가 비어 있다. SAM 실호출은 이 기능의 범위가 아니며, 헬퍼의 자식 환경에서도 제거된다.
- 증거 디렉터리 `/tmp/argus-verify-evidence/<run-id>/`를 새로 정했다.

- **기본 실행.** Run `python3 .claude/skills/verify-argus/scripts/verify_argus.py --feature pre-submission --evidence-dir /tmp/argus-verify-evidence/<run-id>`. 헬퍼가 `python3 -m qa.pre_submission`을 CLI 서브프로세스로 구동한다. 종료코드 0이고, stdout에 `PRE_SUBMISSION: 25/25 mechanical passed`, `BLOCKERS: 1`, `SUBMISSION_READY: false`와 블로커 id `pi_real_capture_pending`이 포함되는지, 두 실행의 종료코드를 증거 transcript에 남기는지 확인한다.
- **직접 CLI 확인.** 프로젝트 루트에서 `python3 -m qa.pre_submission`과 `python3 -m qa.pre_submission --json`을 직접 실행해도 같은 수치를 확인한다.
- **JSON 수치 확인.** `--json` 출력에서 passed 25, total 25, 즉 25/25인지, `mechanical_pass`가 true인지, checks가 25개이고 전부 passed true인지 확인한다.
- **준비 점검 확인.** JSON `readiness.sam.blockers`가 `sam_credit_not_confirmed`·`sam_base_url_missing`·`sam_api_key_missing` 3종 순서 그대로이고 `readiness.pi.blockers`가 `pi_device_arrival_not_confirmed`·`pi_camera_command_missing` 2종 순서 그대로이며, 두 ready 플래그가 모두 false인지 확인한다. 증거 summary에도 `readiness_sam_blockers`·`readiness_pi_blockers`로 남는다.
- **콘솔 준비 상태 확인.** JSON `readiness.console`의 sam_blockers·pi_blockers가 위 두 목록과 각각 같고, blocker_count가 5, overall_ready가 false인지 확인한다. 증거 summary에도 `readiness_console_blocker_count`·`readiness_console_overall_ready`로 남는다.
- **제출 문안 확인.** JSON `readiness.devpost`의 section_count가 11, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_devpost_section_count`·`readiness_devpost_blockers`로 남는다. 문안 정합은 원문 대조만이며 실제 제출이 아니다.
- **README 확인.** JSON `readiness.readme`의 section_count가 5, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_readme_section_count`·`readiness_readme_blockers`로 남는다. README 정합은 원문 대조만이며 실제 제출이 아니다.
- **데모 대본 확인.** JSON `readiness.demo_script`의 section_count가 3, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_demo_script_section_count`·`readiness_demo_script_blockers`로 남는다. 데모 대본 정합은 원문 대조만이며 실제 제출이 아니다.
- **영문 제출 요약 확인.** JSON `readiness.en_summary`의 section_count가 8, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_en_summary_section_count`·`readiness_en_summary_blockers`로 남는다. 영문 요약 정합은 원문 대조만이며 실제 제출이 아니다.
- **제출 스토리 확인.** JSON `readiness.story`의 section_count가 7, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true인지 확인한다. 증거 summary에도 `readiness_story_section_count`·`readiness_story_blockers`로 남는다. 스토리 정합은 원문 대조만이며 실제 제출이 아니다.
- **제출 런북 확인.** JSON `readiness.runbook`의 section_count가 7, blockers가 전수 점검 블로커 2종과 같고, submission_ready가 false, claims_audit_clean이 true, final_command_count가 8인지 확인한다. 증거 summary에도 `readiness_runbook_section_count`·`readiness_runbook_blockers`로 남는다. 런북 정합은 원문 대조만이며 실제 제출이 아니다.
- **Pi 전체 세션 확인.** JSON `readiness.pi_session`의 status가 blocked, attempted가 false, blockers가 Pi 준비 점검 블로커 2종과 같고, source·summary가 None인지 확인한다. 증거 summary에도 `readiness_pi_session_status`·`readiness_pi_session_blockers`로 남는다. 전체 세션 정합은 가짜 session으로만 구동하므로 실제 촬영이 아니다.
- **Pi 스모크 확인.** JSON `readiness.pi_smoke`의 status가 blocked, attempted가 false, blockers가 Pi 준비 점검 블로커 2종과 같은지 확인한다. 증거 summary에도 `readiness_pi_smoke_status`·`readiness_pi_smoke_blockers`로 남는다. 스모크 정합은 가짜 session으로만 구동하므로 실제 촬영이 아니다.
- **조립 폴백 확인.** checks에서 `demo_assets_consistent`의 detail에 `assembly_fallback_cut=3`가 포함되는지 확인한다. 증거 summary에도 `demo_assembly_fallback_cut`으로 남는다. 조립 폴백은 파일 입력이며 Pi 실촬영이 아니다.
- **영상 폴백 렌더 확인.** checks에서 `video_draft_present`의 detail에 `fallback_render_cut=3`와 `fallback_bytes=`가 포함되는지 확인한다. 증거 summary에도 `video_fallback_render_cut`으로 남는다. 폴백 렌더는 파일 입력이며 Pi 실촬영이 아니다.
- **SAM 전체 세션 확인.** JSON `readiness.sam_session`의 status가 blocked, attempted가 false, blockers가 SAM 준비 점검 블로커 3종과 같고, source·summary가 None인지 확인한다. 증거 summary에도 `readiness_sam_session_status`·`readiness_sam_session_blockers`로 남는다. 전체 세션 정합은 가짜 counter로만 구동하므로 실제 API 호출이 아니며, 가짜 성공을 실제 전체 세션 실호출 성공으로 주장하지 않는다.
- **SAM 스모크 확인.** JSON `readiness.smoke`의 status가 blocked, attempted가 false, blockers가 SAM 준비 점검 블로커 3종과 같은지 확인한다. 증거 summary에도 `readiness_smoke_status`·`readiness_smoke_blockers`로 남는다. 스모크 정합은 가짜 counter로만 구동하므로 실제 API 호출이 아니다.
- **폴백 결정 확인.** JSON `readiness.fallback_decision`의 decision_date가 2026-11-02, pi_blockers가 Pi 준비 점검 블로커 2종과 같고, is_pi_real_capture가 false이며, status와 fallback_adopted 쌍이 (pending, false)·(fallback_due, true)·(pi_ready, false) 중 하나인지 확인한다. 증거 summary에도 `readiness_fallback_decision_status`·`readiness_fallback_decision_pi_blockers`로 남는다. 폴백 결정은 날짜·준비 상태 판정만이며 실제 촬영이 아니다.
- **제출물 인벤토리 확인.** JSON `readiness.submission_inventory`의 total_files가 18, present_files가 18, missing이 빈 목록, blockers가 전수 점검 블로커 1건과 같고, submission_ready가 false인지 확인한다. 증거 summary에도 `readiness_inventory_total_files`·`readiness_inventory_blockers`로 남는다. 인벤토리 정합은 파일 대조만이며 실제 제출이 아니다.
- **패키지 내보내기 확인.** JSON `readiness.package_export`의 total_files가 18, copied_files가 제출물 인벤토리의 present_files와 같고, missing이 빈 목록, total_bytes가 제출물 인벤토리의 total_bytes와 같고, blockers가 전수 점검 블로커 1건과 같고, submission_ready가 false인지 확인한다. 재검증 필드 verify_verified가 true이고 verify_copied_files·verify_total_bytes가 copied_files·total_bytes와 같은지도 확인한다. 증거 summary에도 `readiness_package_export_total_files`·`readiness_package_export_copied_files`·`readiness_package_export_blockers`·`readiness_package_export_missing`·`readiness_package_export_total_bytes`·`readiness_package_export_submission_ready`·`readiness_package_export_verify_verified`·`readiness_package_export_verify_copied_files`·`readiness_package_export_verify_total_bytes`로 남는다. 패키지 내보내기의 missing·total_bytes는 제출물 인벤토리의 missing·total_bytes와도 교차 대조한다. 내보내기 정합은 임시 staging 대조만이며 실제 제출이 아니다.
- **최종 묶음 확인.** JSON `readiness.final_package`의 status가 blocked, inventory_present가 18, inventory_total이 18, blockers가 전수 점검 블로커 1건과 같고, submission_ready가 false인지 확인한다. 증거 summary에도 `readiness_final_package_status`·`readiness_final_package_blockers`·`readiness_final_package_inventory_present`·`readiness_final_package_inventory_total`·`readiness_final_package_deadline_status`·`readiness_final_package_fallback_status`·`readiness_final_package_submission_ready`·`readiness_final_package_export_copied`·`readiness_final_package_export_total`·`readiness_final_package_export_missing`·`readiness_final_package_export_total_bytes`로 남는다. 최종 묶음의 inventory_present·inventory_total은 제출물 인벤토리의 present_files·total_files와도 교차 대조하고, export_copied·export_total·export_missing·export_total_bytes는 인벤토리의 present_files·total_files·missing·total_bytes와 패키지 내보내기의 missing·total_bytes와도 교차 대조한다. 최종 묶음 정합은 보고 대조만이며 실제 제출이 아니다.
- **블로커 확인.** blockers의 id 목록이 `pi_real_capture_pending` 1건(BLOCKERS: 1)인지 확인한다.
- **제출 가능 아님 확인.** `submission_ready`가 false(SUBMISSION_READY: false)인지 확인한다. true이면 심각한 문제다.
- **표기 확인.** `honesty`에 '모의'를 포함한 줄과 '데모 기준'을 포함한 줄이 있는지 확인한다.
- **증거 확인.** 종료 후 증거 디렉터리에 `pre-submission-stdout.txt`(텍스트 stdout), `pre-submission.json`(JSON stdout), `summary.json`, `transcript.txt`가 남았는지 확인한다.

## Gotchas

- 기계적 통과를 제출 가능으로 오인하지 않는다. `mechanical_pass`가 true여도 `submission_ready`는 false이며, 이를 제출 가능으로 서술하면 검증이 무효다.
- 블로커는 종료코드에 반영되지 않는다. 종료코드 0은 기계적 점검 25종 통과만을 뜻하므로, 블로커 1건은 텍스트의 `BLOCKERS: 1`와 JSON blockers 목록으로 따로 확인한다.
- Pi 실촬영은 아직 하지 않은 일이다. SAM 실호출은 전체 세션으로 검증했지만(같은 가상 사진 재사용, 빈별 정확도 아님) 기본 실행은 모의 어댑터 기준이다. 이 기능은 모의 어댑터 기준 기계적 점검만 구동하며, 실호출·실촬영을 수행하거나 수행한 것으로 서술하지 않는다.
- `pre-deadline`: 마감 점검 정합(deadline_consistent)은 qa.deadline 보고의 마감 상수·블로커·submission_ready false와 남은 시간 산식을 대조하며, 실제로 제출하지 않는다.
- `pre-final-package`: 최종 묶음 정합(final_package_consistent)은 qa.final_package 보고의 status·인벤토리·마감·폴백 필드를 각 원본 보고와 대조하고, export_copied·export_total·export_missing·export_total_bytes를 필수값으로 검사해 None 변조와 인벤토리 total_bytes 불일치도 탐지하며, 실제로 제출하지 않는다. blocked는 실패가 아니다.
- `pre-package-export`: 패키지 내보내기 정합(package_export_consistent)은 qa.package_export 보고의 복사 수치·missing·합계·블로커를 제출물 인벤토리 보고와 대조하며, 임시 staging으로만 복사하고 실제로 제출하지 않는다.
