import pytest
from unittest.mock import AsyncMock, MagicMock

from src.bot import _handle_status


class TestStatusHandler:
    @pytest.mark.asyncio
    async def test_shows_idle_when_nothing_running(self):
        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await _handle_status(update, context)

        msg = update.message.reply_text.call_args[0][0]
        assert "상태" in msg

    @pytest.mark.asyncio
    async def test_shows_running_projects(self):
        from src.bot import project_lock
        await project_lock.acquire("kigaru")

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await _handle_status(update, context)

        msg = update.message.reply_text.call_args[0][0]
        assert "kigaru" in msg

        project_lock.release("kigaru")

    @pytest.mark.asyncio
    async def test_shows_active_pipelines(self):
        from src.bot import active_sessions
        from src.pipeline import PipelineSession, PipelineStep, StepStatus
        from pathlib import Path

        session = PipelineSession(
            session_id="abc123",
            project={"name": "kigaru", "path": Path("/tmp")},
            steps=(PipelineStep(command="tdd", approve="batch", status=StepStatus.RUNNING),),
            current_index=0,
        )
        active_sessions["abc123"] = session

        update = MagicMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await _handle_status(update, context)

        msg = update.message.reply_text.call_args[0][0]
        assert "kigaru" in msg
        assert "tdd" in msg

        del active_sessions["abc123"]
