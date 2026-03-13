import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.bot import build_app


@pytest.fixture
def config():
    return {
        "telegram": {
            "bot_token": "FAKE_TOKEN",
            "group_id": -100123,
            "topics": {
                "kigaru": {
                    "thread_id": 111,
                    "project_path": "/tmp/kigaru",
                }
            },
        },
        "pipelines": {
            "default": [
                {"step": "plan-sync mymd/todo", "approve": "auto"},
                {"step": "next-task", "approve": "required"},
            ]
        },
    }


def _make_update(thread_id=111, text="/pipeline", args=None):
    """테스트용 Update 객체 생성."""
    update = MagicMock()
    update.message.message_thread_id = thread_id
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_context(args=None):
    context = MagicMock()
    context.args = args or []
    return context


class TestPipelineHandler:
    @pytest.mark.asyncio
    async def test_no_project_returns_error(self, config):
        """프로젝트 없는 토픽에서 /pipeline 실행 시 에러."""
        from src.bot import _handle_pipeline

        update = _make_update(thread_id=999)
        context = _make_context()

        await _handle_pipeline(update, context, config)

        update.message.reply_text.assert_called_once()
        msg = update.message.reply_text.call_args[0][0]
        assert "프로젝트가 없습니다" in msg

    @pytest.mark.asyncio
    async def test_pipeline_starts_session(self, config):
        """정상 토픽에서 /pipeline 실행 시 세션이 생성된다."""
        from src.bot import _handle_pipeline, active_sessions

        update = _make_update(thread_id=111)
        context = _make_context()

        with patch("src.bot.asyncio") as mock_asyncio:
            mock_asyncio.create_task = MagicMock()
            await _handle_pipeline(update, context, config)

        # 시작 메시지 전송 확인
        update.message.reply_text.assert_called()
        msg = update.message.reply_text.call_args[0][0]
        assert "파이프라인 시작" in msg


class TestPipelineCallback:
    @pytest.mark.asyncio
    async def test_approve_callback(self):
        """pipeline_approve 콜백이 다음 스텝을 실행한다."""
        from src.bot import _handle_pipeline_callback, active_sessions
        from src.pipeline import PipelineSession, PipelineStep, StepStatus
        from src.claude_runner import ClaudeResult

        session = PipelineSession(
            session_id="test123",
            project={"name": "kigaru", "path": Path("/tmp/kigaru")},
            steps=(PipelineStep(
                command="next-task",
                approve="required",
                status=StepStatus.WAITING_APPROVAL,
            ),),
            current_index=0,
        )
        active_sessions["test123"] = session

        query = MagicMock()
        query.data = "pipeline_approve:test123"
        query.answer = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        query.message.reply_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        mock_result = ClaudeResult(
            success=True, output="task-1", error="", exit_code=0, elapsed=1.0
        )

        with patch("src.pipeline.run_claude", return_value=mock_result):
            await _handle_pipeline_callback(update, MagicMock())

        query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_callback(self):
        """pipeline_reject 콜백이 파이프라인을 중단한다."""
        from src.bot import _handle_pipeline_callback, active_sessions
        from src.pipeline import PipelineSession, PipelineStep, StepStatus

        session = PipelineSession(
            session_id="test456",
            project={"name": "kigaru", "path": Path("/tmp/kigaru")},
            steps=(PipelineStep(
                command="next-task",
                approve="required",
                status=StepStatus.WAITING_APPROVAL,
            ),),
            current_index=0,
        )
        active_sessions["test456"] = session

        query = MagicMock()
        query.data = "pipeline_reject:test456"
        query.answer = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        query.message.reply_text = AsyncMock()

        update = MagicMock()
        update.callback_query = query

        await _handle_pipeline_callback(update, MagicMock())

        query.answer.assert_called_once()
        # 세션 제거 확인
        assert "test456" not in active_sessions
