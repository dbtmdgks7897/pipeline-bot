import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.claude_runner import ClaudeResult
from src.bot import _handle_run, _handle_callback


@pytest.fixture
def config():
    return {
        "telegram": {
            "bot_token": "test-token",
            "group_id": -100123,
            "topics": {
                "kigaru": {
                    "thread_id": 10,
                    "project_path": "/tmp/kigaru",
                }
            },
        }
    }


def make_update(thread_id=10, args_text="plan-sync"):
    update = MagicMock()
    update.message.message_thread_id = thread_id
    update.message.reply_text = AsyncMock()
    update.message.chat_id = -100123
    return update


def make_context(args=None):
    ctx = MagicMock()
    ctx.args = args if args is not None else ["plan-sync"]
    return ctx


def make_callback_update(data="approve:abc123"):
    update = MagicMock()
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_reply_markup = AsyncMock()
    update.callback_query.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
class TestHandleRun:
    async def test_unknown_topic_replies_error(self, config):
        update = make_update(thread_id=999)
        ctx = make_context()

        await _handle_run(update, ctx, config)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "❌" in call_args

    async def test_no_args_replies_usage(self, config):
        update = make_update()
        ctx = make_context(args=[])

        await _handle_run(update, ctx, config)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "/run" in call_args

    async def test_sends_running_message_immediately(self, config):
        update = make_update()
        ctx = make_context(args=["plan-sync"])

        fake_result = ClaudeResult(
            success=True, output="done", error="", exit_code=0, elapsed=1.0
        )

        with patch("src.bot.run_claude", AsyncMock(return_value=fake_result)):
            with patch("asyncio.create_task") as _mock_task:
                await _handle_run(update, ctx, config)

        # First reply should be "실행 중" message
        first_call = update.message.reply_text.call_args_list[0][0][0]
        assert "⏳" in first_call or "실행 중" in first_call

    async def test_task_created_for_background_execution(self, config):
        update = make_update()
        ctx = make_context(args=["plan-sync"])

        with patch("src.bot.run_claude", AsyncMock()):
            with patch("asyncio.create_task") as mock_task:
                await _handle_run(update, ctx, config)

        mock_task.assert_called_once()


@pytest.mark.asyncio
class TestHandleCallback:
    async def test_approve_callback_replies_approved(self):
        update = make_callback_update("approve:abc123")

        await _handle_callback(update, MagicMock())

        update.callback_query.message.reply_text.assert_called_once()
        msg = update.callback_query.message.reply_text.call_args[0][0]
        assert "✅" in msg

    async def test_reject_callback_replies_rejected(self):
        update = make_callback_update("reject:abc123")

        await _handle_callback(update, MagicMock())

        update.callback_query.message.reply_text.assert_called_once()
        msg = update.callback_query.message.reply_text.call_args[0][0]
        assert "❌" in msg

    async def test_feedback_callback_prompts_for_input(self):
        update = make_callback_update("feedback:abc123")

        await _handle_callback(update, MagicMock())

        update.callback_query.message.reply_text.assert_called_once()
        msg = update.callback_query.message.reply_text.call_args[0][0]
        assert "피드백" in msg

    async def test_callback_answers_query(self):
        update = make_callback_update("approve:abc123")

        await _handle_callback(update, MagicMock())

        update.callback_query.answer.assert_called_once()
