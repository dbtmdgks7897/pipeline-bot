# Pipeline Bot MVP — 구현 순서 (v2)

---

## Phase 1 — 최소 동작: md 전송 → 로컬 저장 (1~2일)

목표: 폰에서 md 보내면 프로젝트 폴더의 mymd/todo에 파일이 생긴다.

### Step 1-1. Telegram Bot 생성 + 그룹 설정

1. @BotFather → `/newbot` → 봇 이름/유저네임 설정 (예: `@imysh_pipeline_bot`)
2. Bot Token 저장
3. Telegram 그룹 생성 (예: "Pipeline Control")
4. 그룹 설정 → Topics 기능 활성화
5. 봇을 그룹에 관리자로 추가
6. 프로젝트별 토픽 생성: kigaru, imysh, atsumaro
7. 각 토픽의 thread_id 확인:
   - 각 토픽에서 아무 메시지 전송
   - `https://api.telegram.org/bot{TOKEN}/getUpdates` 호출
   - 응답에서 `message_thread_id` 값 확인

### Step 1-2. 프로젝트 초기화

```bash
mkdir -p ~/projects/pipeline-bot
cd ~/projects/pipeline-bot

python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn python-telegram-bot pyyaml

# 폴더 구조
mkdir -p src
touch src/__init__.py
touch src/bot.py          # Telegram 봇 핸들러
touch src/file_ops.py     # 파일 저장 함수
touch src/config.py       # 설정 로드
touch config.yaml         # 설정 파일
touch run.py              # 엔트리포인트
```

### Step 1-3. 설정 파일 작성

```yaml
# config.yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  group_id: -100XXXXXXXXXX
  topics:
    kigaru:
      thread_id: 123
      project_path: "/Users/ysh/projects/kigaru"
    imysh:
      thread_id: 456
      project_path: "/Users/ysh/projects/imysh"
    atsumaro:
      thread_id: 789
      project_path: "/Users/ysh/projects/atsumaro"
```

### Step 1-4. config 로더

```python
# src/config.py
import yaml
from pathlib import Path

def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)

def get_project_by_thread_id(config, thread_id):
    """thread_id로 프로젝트 찾기"""
    for name, topic in config["telegram"]["topics"].items():
        if topic["thread_id"] == thread_id:
            return {
                "name": name,
                "path": Path(topic["project_path"]).expanduser()
            }
    return None
```

### Step 1-5. 파일 저장 함수

```python
# src/file_ops.py
from pathlib import Path

def save_md_to_todo(project_path: Path, filename: str, content: str) -> Path:
    """프로젝트의 mymd/todo/에 md 파일 직접 생성"""
    todo_dir = project_path / "mymd" / "todo"
    todo_dir.mkdir(parents=True, exist_ok=True)

    if not filename.endswith(".md"):
        filename += ".md"

    filepath = todo_dir / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath
```

### Step 1-6. /send 핸들러

```python
# src/bot.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from src.config import load_config, get_project_by_thread_id
from src.file_ops import save_md_to_todo

config = load_config()

async def send_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    thread_id = update.message.message_thread_id
    project = get_project_by_thread_id(config, thread_id)

    if not project:
        await update.message.reply_text("❌ 이 토픽에 연결된 프로젝트가 없어.")
        return

    # "/send feature-x" 에서 파일명 추출
    args = context.args
    if not args:
        await update.message.reply_text("사용법: /send 파일명\n(다음 줄부터 md 내용)")
        return

    filename = args[0]

    # /send 파일명 뒤의 나머지 텍스트가 md 내용
    full_text = update.message.text
    # "/send feature-x\n내용..." 에서 첫 줄 제거
    lines = full_text.split("\n", 1)
    content = lines[1] if len(lines) > 1 else ""

    if not content and update.message.document:
        # 파일 첨부인 경우
        file = await update.message.document.get_file()
        content = (await file.download_as_bytearray()).decode("utf-8")

    filepath = save_md_to_todo(project["path"], filename, content)
    await update.message.reply_text(f"✅ {project['name']}/mymd/todo/{filename}.md 저장 완료")

app = ApplicationBuilder().token(config["telegram"]["bot_token"]).build()
app.add_handler(CommandHandler("send", send_handler))
```

### Step 1-7. 엔트리포인트

```python
# run.py
from src.bot import app

if __name__ == "__main__":
    print("Pipeline Bot 시작...")
    app.run_polling()  # Phase 1에서는 polling 방식 (webhook 없이)
```

**참고:** Phase 1에서는 Cloudflare Tunnel 없이 polling 방식으로 먼저 동작 확인.
봇이 Telegram 서버에 주기적으로 "새 메시지 있어?" 물어보는 방식.
Tunnel은 Phase 2에서 webhook 방식으로 전환할 때 설정.

### Step 1-8. 테스트

1. `python run.py` 실행
2. 폰에서 Telegram → kigaru 토픽 → `/send test-feature` + md 내용 전송
3. 노트북에서 확인: `cat ~/projects/kigaru/mymd/todo/test-feature.md`
4. 파일 내용이 보내 내용과 일치하는지 확인
5. imysh 토픽에서도 같은 테스트 → 다른 경로에 저장되는지 확인

**Phase 1 완료 기준:** 폰에서 토픽별로 md 보내면 해당 프로젝트 폴더에 파일이 생긴다.

---

## Phase 2 — Claude Code 연동 (2~3일)

목표: 폰에서 Claude Code 명령 실행 + 결과 수신.

### Step 2-0. 선행 검증 (최우선, Phase 1 끝나자마자)

```bash
# 테스트 1: Claude Code CLI가 non-interactive로 실행 가능한지
cd ~/projects/kigaru
claude -p "prompt_plan.md 파일의 첫 3줄을 읽어줘" --no-input

# 테스트 2: subprocess에서 실행
python3 -c "
import subprocess
result = subprocess.run(
    ['claude', '-p', 'prompt_plan.md 첫 3줄 읽어줘', '--no-input'],
    capture_output=True, text=True, timeout=120,
    cwd='/Users/ysh/projects/kigaru'
)
print('returncode:', result.returncode)
print('stdout:', result.stdout[:500])
print('stderr:', result.stderr[:500])
"
```

**결과별 분기:**
- ✅ 정상 → Step 2-1로
- ❌ 인터랙티브 필요 → `--yes`, `--no-input`, `--dangerously-skip-permissions` 등 플래그 조사
- ❌ 완전 불가 → Plan B: Anthropic API 직접 호출 + 자체 파이프라인 로직

### Step 2-1. Claude Code 실행 함수

```python
# src/claude_runner.py
import asyncio
from pathlib import Path

async def run_claude(project_path: Path, command: str) -> dict:
    """프로젝트 경로에서 Claude Code CLI 실행"""

    # git pull 먼저 (원격 변경사항 반영)
    pull = await asyncio.create_subprocess_exec(
        'git', 'pull', '--rebase',
        cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await pull.communicate()

    # Claude Code 실행
    process = await asyncio.create_subprocess_exec(
        'claude', '-p', command, '--no-input',
        cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=300  # 5분 타임아웃
        )
    except asyncio.TimeoutError:
        process.kill()
        return {"success": False, "error": "타임아웃 (5분 초과)"}

    return {
        "success": process.returncode == 0,
        "stdout": stdout.decode(),
        "stderr": stderr.decode(),
        "returncode": process.returncode
    }
```

### Step 2-2. 결과 파싱 + 요약

```python
# src/result_parser.py

def parse_claude_output(raw_output: str) -> str:
    """Claude Code 출력에서 핵심만 추출하여 Telegram용 요약 생성"""

    # 변경된 파일 목록 추출
    # 에러 여부 확인
    # 요약 메시지 구성

    # Telegram 메시지 길이 제한 (4096자)
    if len(summary) > 4000:
        summary = summary[:4000] + "\n\n... (잘림)"

    return summary
```

### Step 2-3. /run 핸들러 + 인라인 버튼

```python
# src/bot.py에 추가

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def run_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    thread_id = update.message.message_thread_id
    project = get_project_by_thread_id(config, thread_id)

    if not project:
        await update.message.reply_text("❌ 프로젝트 연결 없음")
        return

    command = " ".join(context.args)
    if not command:
        await update.message.reply_text("사용법: /run [명령]\n예: /run plan-sync mymd/todo")
        return

    # 실행 중 알림
    msg = await update.message.reply_text(f"⏳ {project['name']} — {command} 실행 중...")

    # Claude Code 실행
    result = await run_claude(project["path"], command)

    if not result["success"]:
        await msg.edit_text(f"❌ 실행 실패\n\n{result.get('error', result['stderr'][:1000])}")
        return

    summary = parse_claude_output(result["stdout"])

    # 승인/거절 버튼
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 승인", callback_data=f"approve:{project['name']}"),
            InlineKeyboardButton("❌ 거절", callback_data=f"reject:{project['name']}"),
        ],
        [
            InlineKeyboardButton("💬 피드백", callback_data=f"feedback:{project['name']}"),
        ]
    ])

    await msg.edit_text(
        f"🔧 {project['name']} — {command} 완료\n\n{summary}",
        reply_markup=keyboard
    )

app.add_handler(CommandHandler("run", run_handler))
```

### Step 2-4. 콜백 핸들러 (승인/거절)

```python
# src/bot.py에 추가
from telegram.ext import CallbackQueryHandler

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, project_name = query.data.split(":", 1)

    if action == "approve":
        await query.edit_message_text(f"✅ {project_name} — 승인됨")
        # Phase 3에서 다음 스텝 자동 트리거 연결
    elif action == "reject":
        await query.edit_message_text(f"❌ {project_name} — 거절됨. 변경사항 rollback.")
        # Phase 3에서 rollback 로직 연결
    elif action == "feedback":
        await query.edit_message_text(f"💬 {project_name} — 피드백을 입력해주세요:")
        # 다음 메시지를 피드백으로 처리하는 상태 관리 필요

app.add_handler(CallbackQueryHandler(button_callback))
```

### Step 2-5. Cloudflare Tunnel + Webhook 전환

polling → webhook으로 전환 (더 안정적, 더 빠름):

```bash
# 터널 생성
cloudflared tunnel create pipeline-bot

# ~/.cloudflared/config.yml
tunnel: YOUR_TUNNEL_ID
credentials-file: ~/.cloudflared/YOUR_TUNNEL_ID.json
ingress:
  - hostname: pipeline.yourdomain.com
    service: http://localhost:8000
  - service: http_status:404

# 터널 실행
cloudflared tunnel run pipeline-bot

# webhook 등록
curl -X POST "https://api.telegram.org/bot{TOKEN}/setWebhook" \
  -d '{"url": "https://pipeline.yourdomain.com/webhook"}'
```

run.py를 webhook 모드로 변경:
```python
# run.py (webhook 버전)
from fastapi import FastAPI, Request
from src.bot import app as telegram_app
import uvicorn

fastapi_app = FastAPI()

@fastapi_app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
```

### Step 2-6. 테스트

1. Cloudflare Tunnel + 서버 실행
2. 폰 → kigaru 토픽 → `/run plan-sync mymd/todo`
3. "실행 중..." 메시지 확인
4. 완료 후 결과 요약 + 버튼 확인
5. 승인 버튼 동작 확인

**Phase 2 완료 기준:** 폰에서 Claude Code 명령 실행 → 결과 수신 → 승인/거절 가능.

---

## Phase 3 — 자동 체인 (2~3일)

목표: 승인 한 번이면 다음 스텝이 자동으로 이어진다.

### Step 3-1. 파이프라인 상태 관리

```python
# src/pipeline.py

class PipelineSession:
    """프로젝트별 파이프라인 실행 상태"""

    def __init__(self, project_name, project_path, steps):
        self.project_name = project_name
        self.project_path = project_path
        self.steps = steps        # config에서 로드된 단계 목록
        self.current_index = 0
        self.state = {}           # 이전 스텝 결과 저장 (task_id 등)

    @property
    def current_step(self):
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    @property
    def is_complete(self):
        return self.current_index >= len(self.steps)

# 활성 세션 관리 (프로젝트당 최대 1개)
active_sessions: dict[str, PipelineSession] = {}
```

### Step 3-2. 체인 실행 엔진

```python
# src/pipeline.py 계속

async def execute_step(session: PipelineSession, bot, chat_id, thread_id):
    step = session.current_step
    if not step:
        await bot.send_message(chat_id, f"🎉 {session.project_name} — 파이프라인 완료!",
                               message_thread_id=thread_id)
        return

    # 명령어에 변수 치환 (예: {task_id})
    command = step["step"].format(**session.state)

    result = await run_claude(session.project_path, command)
    summary = parse_claude_output(result["stdout"])

    if step["approve"] == "auto":
        # 자동 통과 → 바로 다음
        await bot.send_message(chat_id, f"⚡ {session.project_name} — {command} 자동 완료\n\n{summary}",
                               message_thread_id=thread_id)
        session.current_index += 1
        await execute_step(session, bot, chat_id, thread_id)

    elif step["approve"] == "required":
        # 승인 대기
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ 승인", callback_data=f"pipe_approve:{session.project_name}"),
            InlineKeyboardButton("❌ 거절", callback_data=f"pipe_reject:{session.project_name}"),
            InlineKeyboardButton("💬 피드백", callback_data=f"pipe_feedback:{session.project_name}"),
        ]])
        await bot.send_message(chat_id,
            f"🔧 {session.project_name} — {command} 완료\n\n{summary}",
            reply_markup=keyboard, message_thread_id=thread_id)

    elif step["approve"] == "batch":
        # 배치 큐에 넣고 다음으로
        add_to_batch_queue(session.project_name, command, summary)
        session.current_index += 1
        await execute_step(session, bot, chat_id, thread_id)
```

### Step 3-3. 승인 콜백 → 다음 스텝

```python
async def pipeline_callback(update, context):
    query = update.callback_query
    await query.answer()

    action, project_name = query.data.split(":", 1)
    session = active_sessions.get(project_name)

    if not session:
        await query.edit_message_text("세션 만료됨")
        return

    if action == "pipe_approve":
        session.current_index += 1
        await query.edit_message_text(f"✅ 승인 — 다음 스텝 실행 중...")
        await execute_step(session, context.bot,
                          query.message.chat_id, query.message.message_thread_id)

    elif action == "pipe_reject":
        await rollback(session)
        del active_sessions[project_name]
        await query.edit_message_text(f"❌ 거절 — rollback 완료")

    elif action == "pipe_feedback":
        session.awaiting_feedback = True
        await query.edit_message_text(f"💬 피드백을 입력해주세요:")
```

### Step 3-4. /pipeline 명령 (전체 체인 시작)

```python
async def pipeline_handler(update, context):
    """전체 파이프라인 한 번에 시작"""
    thread_id = update.message.message_thread_id
    project = get_project_by_thread_id(config, thread_id)

    steps = config["pipelines"]["default"]
    session = PipelineSession(project["name"], project["path"], steps)
    active_sessions[project["name"]] = session

    await update.message.reply_text(f"🚀 {project['name']} 파이프라인 시작!")
    await execute_step(session, context.bot,
                      update.message.chat_id, thread_id)

app.add_handler(CommandHandler("pipeline", pipeline_handler))
```

### Step 3-5. 배치 리뷰 (아침 알림)

```python
# src/batch_review.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

batch_queue = []  # [{project, command, summary, timestamp}, ...]

def add_to_batch_queue(project, command, summary):
    batch_queue.append({
        "project": project,
        "command": command,
        "summary": summary,
    })

async def send_morning_review(bot, chat_id):
    if not batch_queue:
        return

    msg = "☀️ 아침 리뷰 대기 항목:\n\n"
    for i, item in enumerate(batch_queue):
        msg += f"{i+1}. {item['project']} — {item['command']}\n"
        msg += f"   {item['summary'][:100]}\n\n"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 전체 승인", callback_data="batch_approve_all"),
        InlineKeyboardButton("📋 하나씩 보기", callback_data="batch_review_one"),
    ]])

    await bot.send_message(chat_id, msg, reply_markup=keyboard)

# 매일 아침 8시
scheduler = AsyncIOScheduler()
scheduler.add_job(send_morning_review, 'cron', hour=8, minute=0)
```

### Step 3-6. 테스트

1. kigaru 토픽에서 `/pipeline` 실행
2. auto 단계 자동 통과 확인
3. required 단계에서 멈추고 버튼 표시 확인
4. 승인 → 다음 단계 자동 실행 확인
5. 거절 → rollback 확인
6. batch 단계 → 큐 쌓임 → 아침 알림 확인

**Phase 3 완료 기준:** `/pipeline` 한 번으로 체인이 돌고, 승인 지점에서만 멈춘다.

---

## Phase 4 — 안정화 (1~2일)

### Step 4-1. 에러 핸들링

```python
# src/error_handler.py

async def error_handler(update, context):
    """전역 에러 핸들러"""
    error = context.error

    error_msg = f"⚠️ 봇 에러 발생\n\n{type(error).__name__}: {str(error)[:500]}"

    # 에러 알림 전송 (그룹 또는 개인 DM)
    await context.bot.send_message(
        chat_id=config["telegram"]["group_id"],
        text=error_msg
    )

app.add_error_handler(error_handler)
```

개별 에러 처리:
```python
# Claude Code 타임아웃
except asyncio.TimeoutError:
    await notify("⏰ 타임아웃 (5분 초과). 명령을 다시 실행하시겠습니까?", retry_button=True)

# Git 충돌
except GitConflictError:
    await notify("⚠️ Git 충돌. 수동 해결 필요.\n\n충돌 파일: ...")

# 파일 경로 없음
except FileNotFoundError:
    await notify("❌ 프로젝트 경로를 찾을 수 없음. config.yaml 확인 필요.")
```

### Step 4-2. 프로세스 자동 시작 (Mac launchd)

```xml
<!-- ~/Library/LaunchAgents/com.imysh.pipeline-bot.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.imysh.pipeline-bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/ysh/projects/pipeline-bot/venv/bin/python</string>
        <string>/Users/ysh/projects/pipeline-bot/run.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/ysh/projects/pipeline-bot</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/ysh/projects/pipeline-bot/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/ysh/projects/pipeline-bot/logs/stderr.log</string>
</dict>
</plist>
```

```bash
# 등록
launchctl load ~/Library/LaunchAgents/com.imysh.pipeline-bot.plist

# 확인
launchctl list | grep pipeline

# 해제
launchctl unload ~/Library/LaunchAgents/com.imysh.pipeline-bot.plist
```

### Step 4-3. Cloudflare Tunnel 자동 시작

```bash
# cloudflared도 launchd로 자동 시작
cloudflared service install
```

또는 별도 plist 작성.

### Step 4-4. 로깅

```python
# src/logger.py
import logging
from pathlib import Path

def setup_logger():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        handlers=[
            logging.FileHandler(log_dir / "pipeline-bot.log"),
            logging.StreamHandler()
        ],
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    return logging.getLogger("pipeline-bot")
```

### Step 4-5. 동시 실행 방지

```python
# src/task_queue.py
import asyncio

class ProjectLock:
    """프로젝트당 동시 실행 1개로 제한"""
    def __init__(self):
        self.locks: dict[str, asyncio.Lock] = {}

    async def acquire(self, project_name: str):
        if project_name not in self.locks:
            self.locks[project_name] = asyncio.Lock()
        await self.locks[project_name].acquire()

    def release(self, project_name: str):
        if project_name in self.locks:
            self.locks[project_name].release()

project_lock = ProjectLock()

# 사용:
async def run_with_lock(project_name, task):
    await project_lock.acquire(project_name)
    try:
        result = await task()
    finally:
        project_lock.release(project_name)
    return result
```

**Phase 4 완료 기준:** 노트북 재시작해도 봇+터널 자동 복구, 에러 시 알림.

---

## 전체 일정

| Phase | 기간 | 산출물 | 의존성 |
|-------|------|--------|--------|
| 1 | 1~2일 | /send → 로컬 파일 생성 | 없음 |
| 2 | 2~3일 | /run → Claude Code 실행 + 결과 수신 | Phase 1 + CLI 검증 |
| 3 | 2~3일 | /pipeline 자동 체인 + 배치 리뷰 | Phase 2 |
| 4 | 1~2일 | 자동 복구 + 에러 핸들링 + 로깅 | Phase 3 |
| **합계** | **6~10일** | **폰에서 전체 파이프라인 제어** | |

## 명령어 정리

| 명령 | 설명 | Phase |
|------|------|-------|
| `/send 파일명` + md 내용 | 프로젝트 mymd/todo에 파일 생성 | 1 |
| `/run 명령` | Claude Code 단일 명령 실행 | 2 |
| `/pipeline` | 전체 파이프라인 체인 시작 | 3 |
| `/status` | 현재 실행 중인 작업 상태 | 4 |

## 킬 스위치

| Phase 2 선행 검증 결과 | 대응 |
|------------------------|------|
| ✅ Claude Code CLI subprocess 정상 | 그대로 진행 |
| ⚠️ 특정 플래그 필요 | 플래그 추가 후 진행 |
| ❌ headless 실행 불가 | Plan B: Anthropic API 직접 호출로 우회 |
