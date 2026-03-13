# pipeline-bot - 기능 명세

## 해결하는 문제

- 노트북 앞에 없으면 파이프라인 사이클이 멈춤
- md 추출 → mymd/todo 전달이 수동
- Claude Code 명령 실행 → 결과 확인 → 승인이 전부 터미널 의존

## 아키텍처

```
[폰/Telegram] ←→ [Telegram Bot API]
                        ↕ (Cloudflare Tunnel)
              [로컬 노트북 서버]
              ├── Bot Server (FastAPI)
              ├── Claude Code CLI
              └── 프로젝트 폴더들 (~/projects/*)
```

---

## Feature 1: md 파일 수신 → 프로젝트 폴더에 직접 저장

### 요구사항
1. 해당 프로젝트 토픽에서 md 내용 전송 시 로컬 `mymd/todo/`에 파일 생성
2. `.md` 파일 직접 첨부도 지원
3. git 안 탐. 로컬 파일 쓰기만.

### 입력 형식
```
/send 파일명
(md 내용)
```
또는 .md 파일 직접 첨부

### 동작
```
사용자 (kigaru 토픽): /send feature-x + md 내용
→ 봇: ~/projects/kigaru/mymd/todo/feature-x.md 생성
→ 봇: "✅ feature-x.md 저장 완료" 회신
```

### 핵심 모듈
- `src/bot.py` — `/send` 커맨드 핸들러
- `src/file_ops.py` — `save_md_to_todo()` 파일 쓰기
- `src/config.py` — `get_project_by_thread_id()` 프로젝트 매핑

---

## Feature 2: Claude Code 작업 실행 + 결과 알림

### 요구사항
1. 프로젝트 토픽에서 `/run` 명령 → Claude Code CLI subprocess 실행
2. 실행 완료 시 결과 요약을 Telegram으로 전송
3. 승인/거절/피드백 인라인 버튼 표시

### 선행 검증 (CRITICAL)
- Claude Code CLI가 non-interactive (subprocess)로 실행 가능한지 확인
- `claude -p "prompt" --no-input` 방식
- 불가 시 Plan B: Anthropic API 직접 호출

### 입력 형식
```
/run [claude-code-명령]
  예: /run plan-sync mymd/todo
      /run next-task
      /run plan E8-P2-2
```

### 결과 알림 형식
```
🔧 kigaru — plan-sync 완료

변경사항:
- prompt_plan.md에 3개 항목 추가
- E9-P1 ~ E9-P3 생성

[✅ 승인] [❌ 거절] [💬 피드백]
```

### 핵심 모듈
- `src/claude_runner.py` — `run_claude()` subprocess 실행 (5분 타임아웃)
- `src/result_parser.py` — `parse_claude_output()` 출력 파싱 → 4000자 이내 요약
- `src/bot.py` — `/run` 핸들러 + 인라인 버튼 콜백

---

## Feature 3: 승인 → 다음 스텝 자동 실행 (파이프라인 체인)

### 요구사항
1. `/pipeline` 한 번으로 전체 체인 시작
2. trust_level 설정으로 단계별 자동/수동 승인 제어
3. 거절 시 rollback
4. 피드백 시 피드백 반영하여 재실행

### 자동 체인 (승인 시)
```
plan-sync → next-task 제안 → [승인] → plan → [승인] → tdd → code-review → handoff-verify → commit 전 보고 → [승인] → commit-push-pr
```

### Trust Levels
| 레벨 | 동작 | 예시 |
|------|------|------|
| `auto` | 자동 통과 | lint-fix, plan-sync |
| `batch` | 큐에 쌓고 다음으로 | tdd, code-review, handoff-verify |
| `required` | 승인 대기 (필수) | commit-push-pr, new-feature |

### 핵심 모듈
- `src/pipeline.py` — `PipelineSession` 상태 관리 + `execute_step()` 체인 엔진
- `src/batch_review.py` — 배치 큐 + 아침 8시 일괄 알림

---

## Feature 4: 안정화 + 자동 복구

### 요구사항
1. 전역 에러 핸들링 → Telegram 에러 알림
2. launchd로 노트북 재시작 시 자동 복구
3. 프로젝트당 순차 실행 (동시 실행 방지)
4. 로깅 (파일 + 콘솔)

### 핵심 모듈
- `src/error_handler.py` — 전역 에러 핸들러
- `src/task_queue.py` — `ProjectLock` 동시 실행 방지
- `src/logger.py` — 로깅 설정

---

## 비기능 요구사항

- **보안**: config.yaml gitignore, bot_token 환경변수화, Cloudflare Tunnel + webhook secret
- **신뢰성**: 에러 시 Telegram 알림, launchd KeepAlive
- **동시성**: 프로젝트당 1작업 순차 실행 (asyncio.Lock)
- **제한**: Telegram 메시지 4096자 제한 → 초과 시 잘림 처리
- **로깅**: 모든 파이프라인 실행 이력 기록

## 제약사항 / 리스크

- **노트북 종속**: 꺼지면 멈춤. 필요 시 Fly.io 이전 검토
- **Claude Code headless 실행**: Phase 2 선행 검증 필수. 안 되면 Anthropic API 직접 호출
- **동시 실행**: 프로젝트당 순차 실행 (큐잉)

## 성공 기준

- 폰에서 md 전송 → 로컬 프로젝트 폴더에 파일 생성 확인
- 폰에서 Claude Code 명령 → 자동 실행 → 결과 수신
- 노트북 앞에 안 앉고 1사이클 (plan-sync → plan → tdd → commit) 완주
