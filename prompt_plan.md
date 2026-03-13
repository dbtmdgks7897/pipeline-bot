# pipeline-bot - 구현 계획

## Phase 1: 최소 동작 — md 전송 → 로컬 저장 ✅

목표: 폰에서 md 보내면 프로젝트 폴더의 mymd/todo에 파일이 생긴다.

- [x] Telegram Bot 생성 + 그룹/토픽 설정 (BotFather, thread_id 확인)
- [x] Python 프로젝트 초기화 (requirements.txt, 폴더 구조)
- [x] config.yaml 작성 (bot_token, group_id, topics 매핑)
- [x] src/config.py — 설정 로더 + thread_id → 프로젝트 매핑
- [x] src/file_ops.py — mymd/todo/ 파일 저장 함수
- [x] src/bot.py — /send 핸들러 (텍스트 + 파일 첨부)
- [x] run.py — 엔트리포인트 (polling 모드)
- [x] 테스트 13개 통과 (test_config.py, test_file_ops.py)
- [x] E2E 테스트: 폰 → 토픽별 md 전송 → 로컬 파일 생성 확인

완료 기준: 폰에서 토픽별로 md 보내면 해당 프로젝트 폴더에 파일이 생긴다.

## Phase 2: Claude Code 연동

목표: 폰에서 Claude Code 명령 실행 + 결과 수신.

- [x] **선행 검증**: Claude Code CLI subprocess 실행 가능 여부 확인 (CLAUDECODE 환경변수 제거로 해결)
- [x] src/claude_runner.py — run_claude() 비동기 subprocess (5분 타임아웃)
- [x] src/result_parser.py — 출력 파싱 → Telegram 요약 (4096자 이내, 잘림 처리)
- [x] src/bot.py — /run 핸들러 + 인라인 버튼 (승인/거절/피드백)
- [x] 콜백 핸들러 — 버튼 클릭 처리
- [x] run.py 수정 — WEBHOOK_URL 환경변수로 polling/webhook 모드 전환 (FastAPI + uvicorn)
- [x] Cloudflare Tunnel 설정 — bot.ki-garu.com, tunnel: f377d703, webhook 모드 확인
- [x] 테스트: 폰 → /run 명령 → 결과 수신 → 버튼 동작 확인 — **Bot E2E**

완료 기준: 폰에서 Claude Code 명령 실행 → 결과 수신 → 승인/거절 가능.

## Phase 3: 자동 체인

목표: 승인 한 번이면 다음 스텝이 자동으로 이어진다.

- [x] src/pipeline.py — PipelineSession 상태 관리 (불변 패턴, frozen dataclass)
- [x] execute_next() — trust_level 기반 체인 실행 (auto/required/batch)
- [x] src/bot.py — /pipeline 핸들러 + pipeline_approve/reject 콜백
- [x] src/batch_review.py — BatchReviewQueue (불변 패턴, add/flush/format_summary)
- [ ] 배치 스케줄러 — 아침 8시 일괄 알림 (APScheduler)
- [ ] 테스트: /pipeline → auto 자동 통과, required 멈춤, batch 큐잉 확인 — **Bot E2E**

완료 기준: /pipeline 한 번으로 체인이 돌고 승인 지점에서만 멈춘다.

## Phase 4: 안정화 ✅

목표: 에러 복구 + 자동 시작 + 로깅.

- [x] src/error_handler.py — 전역 에러 핸들러 (format_error_message + telegram_error_handler)
- [x] src/task_queue.py — ProjectLock 동시 실행 방지 (acquire/release/running_projects)
- [x] src/logger.py — 파일(일별 로테이션 7일) + 콘솔 로깅
- [x] launchd plist 작성 — com.pipeline-bot + com.cloudflared-tunnel (자동 재시작)
- [x] /status 명령 — 실행 중 프로젝트 + 파이프라인 + 배치 큐 상태
- [x] bot.py 통합 — error_handler 등록, /run에 ProjectLock 적용
- [x] launchd 등록 + 테스트 — plist 심볼릭 링크 + launchctl load 완료

완료 기준: 노트북 재시작해도 봇+터널 자동 복구, 에러 시 알림.

## 의존성

- Phase 2는 Phase 1 완료 후 진행
- Phase 2 시작 전 Claude Code CLI headless 검증 필수 (킬 스위치)
- Phase 3은 Phase 2 완료 후 진행
- Phase 4는 Phase 3 완료 후 진행

## 킬 스위치

| Phase 2 선행 검증 결과 | 대응 |
|------------------------|------|
| ✅ CLI subprocess 정상 | 그대로 진행 |
| ⚠️ 특정 플래그 필요 | 플래그 추가 후 진행 |
| ❌ headless 실행 불가 | Plan B: Anthropic API 직접 호출로 우회 |

## 전체 일정

| Phase | 기간 | 산출물 |
|-------|------|--------|
| 1 | 1~2일 | /send → 로컬 파일 생성 |
| 2 | 2~3일 | /run → Claude Code 실행 + 결과 수신 |
| 3 | 2~3일 | /pipeline 자동 체인 + 배치 리뷰 |
| 4 | 1~2일 | 자동 복구 + 에러 핸들링 + 로깅 |
| **합계** | **6~10일** | **폰에서 전체 파이프라인 제어** |

## 현재 상태

- [x] 프로젝트 초기화 (CLAUDE.md, spec.md, prompt_plan.md 생성)
- [x] Phase 1 완료 — /send → 로컬 파일 생성 (테스트 13개)
- [x] Phase 2 완료 — /run → Claude Code 실행 + webhook + Cloudflare Tunnel (bot.ki-garu.com)
- [x] Phase 3 코드 구현 완료 — /pipeline 자동 체인 + 배치 큐 (테스트 60개)
- [ ] Phase 3 잔여 — 배치 스케줄러(8시 알림) + /pipeline Bot E2E
- [x] Phase 4 완료 — error_handler + task_queue + logger + /status + launchd 등록 완료 (테스트 78개)
- [ ] 잔여 — 배치 스케줄러(8시 알림) + /pipeline Bot E2E + 전체 E2E
