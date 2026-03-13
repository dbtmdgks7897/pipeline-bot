# Pipeline Bot MVP — Spec (v2)

## 개요

Telegram 봇으로 개발 파이프라인을 폰에서 제어.
노트북이 서버 역할. 노트북 앞에 앉아있지 않아도 사이클이 돌아간다.

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

## 핵심 원리

봇 = 노트북 터미널의 원격 리모컨.
폰에서 명령 → 봇이 노트북에서 대신 실행 → 결과를 폰으로 전달.

## Telegram 구조

- **1개 봇** + **1개 그룹** + **프로젝트별 Topics**
- Topics = Telegram 그룹 내 스레드. 슬랙 채널과 유사.
- 프로젝트별 토픽: kigaru, imysh, atsumaro, ...
- **프로젝트 판별 방식:** 너가 어느 토픽에서 메시지를 보내느냐로 자동 결정. 별도 태그 불필요.

```
너가 "kigaru" 토픽에서 메시지 전송
→ Telegram이 메시지에 thread_id: 123 자동 부여
→ 봇이 thread_id 123 → config에서 kigaru → ~/projects/kigaru 매핑
→ 해당 경로에서 작업 실행
```

- 새 프로젝트 추가 = 토픽 하나 생성 + config에 thread_id와 경로 등록

## 핵심 기능 (MVP)

### F1. md 파일 수신 → 프로젝트 폴더에 직접 저장

**흐름:**
1. Claude.ai에서 기획 구체화 → md 추출
2. 해당 프로젝트 토픽에서 md 내용 전송
3. 봇이 로컬 프로젝트 폴더의 `mymd/todo/`에 파일 직접 생성
4. git 안 탐. 로컬 파일 쓰기만.

**입력 형식:**
```
/send 파일명
(md 내용)
```
또는 .md 파일 직접 첨부

**동작:**
```
너 (kigaru 토픽에서): /send feature-x + md 내용
→ 봇: ~/projects/kigaru/mymd/todo/feature-x.md 생성
→ 봇: "✅ feature-x.md 저장 완료" 회신
```

### F2. Claude Code 작업 실행 + 결과 알림

**흐름:**
1. 프로젝트 토픽에서 명령 전송
2. 봇이 해당 프로젝트 경로에서 Claude Code CLI 실행 (= 네가 터미널에서 직접 치는 것과 동일)
3. 실행 완료 시 결과 요약을 Telegram으로 전송
4. 승인/거절 인라인 버튼 표시

**입력 형식:**
```
/run [claude-code-명령]
  예: /run plan-sync mymd/todo
      /run next-task
      /run plan E8-P2-2
```

프로젝트명 불필요 — 토픽이 곧 프로젝트.

**결과 알림 형식:**
```
🔧 kigaru — plan-sync 완료

변경사항:
- prompt_plan.md에 3개 항목 추가
- E9-P1 ~ E9-P3 생성

[✅ 승인] [❌ 거절] [💬 피드백]
```

### F3. 승인 → 다음 스텝 자동 실행

**흐름:**
1. 승인 버튼 → 다음 스텝 자동 트리거
2. 거절 → 작업 취소, 변경사항 rollback
3. 피드백 → 텍스트 입력 → 피드백 반영하여 재실행

**자동 체인 (승인 시):**
```
plan-sync → next-task 제안 → [승인] → plan → [승인] → tdd → code-review → handoff-verify → commit 전 보고 → [승인] → commit-push-pr
```

각 단계 사이에 승인 지점. trust_level 설정으로 특정 단계는 자동 통과 가능.

**git이 개입하는 시점:** commit-push-pr 딱 한 번뿐. 나머지는 전부 로컬 파일 조작.

## 전체 플로우 요약

```
1. 아이디어 발상 (너, 어디서든)
   → 메모 앱에 한두 줄

2. 기획 구체화 (Claude.ai, 폰/노트북)
   → 메모 던짐 → 기획 초안 → 판단 → md 추출

3. md 전송 (폰 Telegram, kigaru 토픽)
   → /send feature-x + md 내용
   → 봇이 ~/projects/kigaru/mymd/todo/feature-x.md 직접 생성

4. 작업 실행 (폰 Telegram)
   → /run plan-sync mymd/todo → 결과 알림 → 승인
   → /run next-task → task 선택 → 승인
   → tdd → code-review → handoff-verify (trust level에 따라 자동/승인)
   → commit 전 보고 → 승인 → commit-push-pr ← 여기서만 git

5. 피드백 (폰 Telegram)
   → 결과 확인 → 피드백 또는 다음 작업 → 4번으로

너가 하는 일: 아이디어, 기획 판단, 승인/거절, 피드백. 전부 폰.
노트북이 하는 일: 켜져있기.
```

## 기술 스택

- **Bot Server:** Python FastAPI
- **Telegram SDK:** python-telegram-bot
- **외부 접근:** Cloudflare Tunnel (무료)
- **프로세스 관리:** launchd (Mac) 또는 systemd (Linux) — 노트북 재시작 시 자동 복구
- **Claude Code 호출:** subprocess로 CLI 실행
- **파일 조작:** Python 기본 파일 I/O

## 설정 파일

```yaml
# ~/.pipeline-bot/config.yaml
telegram:
  bot_token: "xxx"
  group_id: -100xxx
  topics:
    kigaru:
      thread_id: 123
      project_path: ~/projects/kigaru
    imysh:
      thread_id: 456
      project_path: ~/projects/imysh
    atsumaro:
      thread_id: 789
      project_path: ~/projects/atsumaro

pipelines:
  default:
    - step: plan-sync mymd/todo
      approve: auto
    - step: next-task
      approve: required
    - step: plan {task_id}
      approve: required
    - step: tdd
      approve: batch
    - step: code-review
      approve: batch
    - step: handoff-verify
      approve: batch
    - step: commit-push-pr
      approve: required

trust_levels:
  auto: ["lint-fix", "simple-refactor", "plan-sync"]
  batch: ["tdd", "code-review", "handoff-verify"]
  required: ["commit-push-pr", "new-feature", "ux-change"]
```

## 구현 순서

### Phase 1 — 최소 동작 (1~2일)
- Telegram Bot 생성 + 그룹/토픽 설정
- FastAPI 서버 + Cloudflare Tunnel
- `/send` → 로컬 프로젝트 폴더에 md 파일 직접 생성
- 테스트: 폰에서 md 보내면 로컬에 파일 생김

### Phase 2 — Claude Code 연동 (2~3일)
- **선행 검증: Claude Code CLI subprocess 실행 가능 여부**
- `/run` → subprocess로 Claude Code CLI 실행
- 결과 파싱 → Telegram 메시지 전송
- 인라인 버튼 (승인/거절/피드백)

### Phase 3 — 자동 체인 (2~3일)
- 승인 시 다음 스텝 자동 트리거
- trust_levels 기반 자동 승인
- 거절 시 rollback
- 배치 리뷰 (아침 일괄 알림)

### Phase 4 — 안정화 (1~2일)
- 에러 핸들링 + Telegram 에러 알림
- launchd/systemd 서비스 등록
- 로깅
- 동시 실행 방지 큐잉

**총 예상: 6~10일**

## 제약사항 / 리스크

- **노트북 종속:** 꺼지면 멈춤. 필요 시 Fly.io 이전 검토
- **Claude Code headless 실행:** Phase 2 선행 검증 필수. 안 되면 설계 변경
- **보안:** Cloudflare Tunnel + bot token + webhook secret. 로컬 전용이므로 위험 낮음
- **동시 실행:** 프로젝트당 순차 실행 (큐잉)

## 성공 기준

- 폰에서 md 전송 → 로컬 프로젝트 폴더에 파일 생성 확인
- 폰에서 Claude Code 명령 → 자동 실행 → 결과 수신
- 노트북 앞에 안 앉고 1사이클 (plan-sync → plan → tdd → commit) 완주
