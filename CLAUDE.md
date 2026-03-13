# pipeline-bot

## 개요

Telegram 봇으로 개발 파이프라인을 폰에서 원격 제어.
노트북이 서버 역할. 노트북 앞에 앉아있지 않아도 개발 사이클이 돌아간다.

봇 = 노트북 터미널의 원격 리모컨.
폰에서 명령 → 봇이 노트북에서 대신 실행 → 결과를 폰으로 전달.

## 기술 스택

- **런타임**: Python 3.11+
- **웹 프레임워크**: FastAPI + uvicorn
- **Telegram SDK**: python-telegram-bot
- **외부 접근**: Cloudflare Tunnel (무료)
- **Claude Code 호출**: subprocess로 CLI 실행
- **프로세스 관리**: launchd (macOS)
- **설정 파일**: YAML (PyYAML)

## 빌드 & 테스트

```bash
# 가상환경 활성화
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (개발 - polling 모드)
python run.py

# 서버 실행 (프로덕션 - webhook 모드)
uvicorn run:fastapi_app --host 0.0.0.0 --port 8000

# 테스트
pytest tests/ -v

# 린트
ruff check src/

# 타입 체크
mypy src/
```

## 디렉토리 구조

```
pipeline-bot/
├── src/
│   ├── __init__.py
│   ├── bot.py              # Telegram 봇 핸들러 (/send, /run, /pipeline)
│   ├── config.py            # config.yaml 로더 + thread_id → 프로젝트 매핑
│   ├── file_ops.py          # 파일 저장 (mymd/todo/ 쓰기)
│   ├── claude_runner.py     # Claude Code CLI subprocess 실행
│   ├── result_parser.py     # Claude 출력 파싱 → Telegram용 요약
│   ├── pipeline.py          # 파이프라인 세션 + 체인 실행 엔진
│   ├── task_queue.py        # 프로젝트별 동시 실행 방지 (Lock)
│   ├── batch_review.py      # 배치 큐 + 아침 일괄 알림
│   ├── error_handler.py     # 전역 에러 핸들링 + Telegram 에러 알림
│   └── logger.py            # 로깅 설정
├── tests/                   # 테스트 파일
├── logs/                    # 로그 파일 (gitignore)
├── config.yaml              # 프로젝트별 토픽/경로 매핑 (gitignore)
├── run.py                   # 엔트리포인트
├── requirements.txt
├── .env.example
├── CLAUDE.md
├── spec.md
└── prompt_plan.md
```

## 환경 변수 / 설정

```yaml
# config.yaml (gitignore 대상 - 토큰 포함)
telegram:
  bot_token: "BOT_TOKEN"
  group_id: -100XXXXXXXXXX
  topics:
    kigaru:
      thread_id: 123
      project_path: ~/projects/kigaru
    imysh:
      thread_id: 456
      project_path: ~/projects/imysh

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

## Telegram 구조

- 1개 봇 + 1개 그룹 + 프로젝트별 Topics
- 토픽(thread_id)으로 프로젝트 자동 판별. 별도 태그 불필요.
- 새 프로젝트 추가 = 토픽 생성 + config.yaml에 thread_id/경로 등록

## 코딩 컨벤션

- 불변성 패턴 (dict 직접 수정 대신 새 dict 생성)
- 함수 50줄 이하, 파일 800줄 이하
- 시스템 경계(Telegram 입력, config 파일)에서 검증
- 시크릿은 config.yaml + gitignore (절대 하드코딩 금지)
- 에러 핸들링 필수 — 에러 시 Telegram으로 알림
- async/await 기반 비동기 처리

## 주요 명령어

| 명령 | 설명 | Phase |
|------|------|-------|
| `/send 파일명` + md 내용 | 프로젝트 mymd/todo에 파일 생성 | 1 |
| `/run 명령` | Claude Code 단일 명령 실행 | 2 |
| `/pipeline` | 전체 파이프라인 체인 시작 | 3 |
| `/status` | 현재 실행 중인 작업 상태 | 4 |
