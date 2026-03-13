import asyncio
import logging
import uuid
from pathlib import Path
from typing import cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import get_project_by_thread_id
from src.claude_runner import run_claude
from src.file_ops import save_md_to_todo
from src.result_parser import parse_claude_output

logger = logging.getLogger(__name__)

# run_id → {"project": ..., "command": ...}  (Phase 3에서 pipeline.py로 이관)
pending_runs: dict[str, dict] = {}


async def _handle_run(update: Update, context: ContextTypes.DEFAULT_TYPE, config: dict) -> None:
    """Core logic for /run command. Separated for testability."""
    assert update.message is not None
    thread_id = update.message.message_thread_id
    project = get_project_by_thread_id(config, thread_id)

    if not project:
        await update.message.reply_text(
            "❌ 이 토픽에 연결된 프로젝트가 없습니다.\n"
            "config.yaml에서 thread_id를 확인하세요."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "사용법:\n  /run [claude-code-명령]\n\n"
            "예: /run plan-sync mymd/todo\n"
            "    /run next-task"
        )
        return

    command = " ".join(context.args)
    await update.message.reply_text(f"⏳ {project['name']} — {command} 실행 중...")
    asyncio.create_task(_execute_and_report(update, project, command))


async def _execute_and_report(update: Update, project: dict, command: str) -> None:
    """Claude Code 실행 후 결과를 Telegram으로 전송."""
    assert update.message is not None
    try:
        result = await run_claude(command, project["path"])
        message = parse_claude_output(result, command, project["name"])

        run_id = uuid.uuid4().hex[:8]
        pending_runs[run_id] = {"project": project, "command": command}

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ 승인", callback_data=f"approve:{run_id}"),
                InlineKeyboardButton("❌ 거절", callback_data=f"reject:{run_id}"),
                InlineKeyboardButton("💬 피드백", callback_data=f"feedback:{run_id}"),
            ]
        ])

        await update.message.reply_text(message, reply_markup=keyboard)

    except Exception as e:
        logger.error("실행 중 오류: %s", e)
        await update.message.reply_text(f"❌ 실행 중 오류 발생: {e}")


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """인라인 버튼 콜백 처리."""
    query = update.callback_query
    assert query is not None
    assert query.data is not None
    await query.answer()

    parts = query.data.split(":", 1)
    if len(parts) != 2:
        return

    action, run_id = parts
    await query.edit_message_reply_markup(reply_markup=None)

    assert query.message is not None
    msg = cast(Message, query.message)
    if action == "approve":
        await msg.reply_text("✅ 승인됨")
    elif action == "reject":
        await msg.reply_text("❌ 거절됨")
    elif action == "feedback":
        await msg.reply_text("💬 피드백을 입력하세요:\n(다음 메시지로 보내주세요)")


def build_app(config: dict):
    """config을 받아 Telegram Application을 생성한다."""
    token = config["telegram"]["bot_token"]
    app = ApplicationBuilder().token(token).build()

    async def send_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /send 파일명
        (md 내용)

        또는 .md 파일 직접 첨부
        """
        assert update.message is not None
        thread_id = update.message.message_thread_id
        project = get_project_by_thread_id(config, thread_id)

        if not project:
            await update.message.reply_text(
                "❌ 이 토픽에 연결된 프로젝트가 없습니다.\n"
                "config.yaml에서 thread_id를 확인하세요."
            )
            return

        args = context.args
        if not args:
            await update.message.reply_text(
                "사용법:\n"
                "  /send 파일명\n"
                "  (다음 줄부터 md 내용)\n\n"
                "또는 .md 파일을 캡션으로 파일명과 함께 첨부하세요."
            )
            return

        filename = args[0]
        content = _extract_content(update)

        if not content:
            await update.message.reply_text(
                "❌ 내용이 비어 있습니다.\n"
                "/send 파일명 다음 줄에 md 내용을 입력하거나 .md 파일을 첨부하세요."
            )
            return

        try:
            filepath = save_md_to_todo(project["path"], filename, content)
            rel = Path(filename) if filename.endswith(".md") else Path(filename + ".md")
            await update.message.reply_text(
                f"✅ {project['name']}/mymd/todo/{rel.name} 저장 완료"
            )
            logger.info("Saved %s for project %s", filepath, project["name"])
        except OSError as e:
            logger.error("파일 저장 실패: %s", e)
            await update.message.reply_text(f"❌ 파일 저장 실패: {e}")

    async def send_document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """.md 파일 첨부 처리. /send 커맨드 없이 파일만 보낸 경우."""
        assert update.message is not None
        if not update.message.document:
            return

        doc = update.message.document
        if not doc.file_name or not doc.file_name.endswith(".md"):
            return

        thread_id = update.message.message_thread_id
        project = get_project_by_thread_id(config, thread_id)

        if not project:
            await update.message.reply_text("❌ 이 토픽에 연결된 프로젝트가 없습니다.")
            return

        try:
            file = await doc.get_file()
            raw = await file.download_as_bytearray()
            content = raw.decode("utf-8")
            filename = doc.file_name

            filepath = save_md_to_todo(project["path"], filename, content)
            await update.message.reply_text(
                f"✅ {project['name']}/mymd/todo/{filename} 저장 완료"
            )
            logger.info("Saved attachment %s for project %s", filepath, project["name"])
        except Exception as e:
            logger.error("파일 첨부 처리 실패: %s", e)
            await update.message.reply_text(f"❌ 파일 처리 실패: {e}")

    app.add_handler(CommandHandler("send", send_handler))
    app.add_handler(
        MessageHandler(
            filters.Document.MimeType("text/plain") & filters.Document.FileExtension("md"),
            send_document_handler,
        )
    )
    app.add_handler(CommandHandler("run", lambda u, c: _handle_run(u, c, config)))
    app.add_handler(CallbackQueryHandler(_handle_callback))

    return app


def _extract_content(update: Update) -> str:
    """메시지에서 md 내용을 추출한다.

    '/send 파일명\\n내용...' 형태에서 첫 줄(커맨드)을 제거하고 반환.
    """
    assert update.message is not None
    full_text = update.message.text or ""
    parts = full_text.split("\n", 1)
    return parts[1].strip() if len(parts) > 1 else ""
