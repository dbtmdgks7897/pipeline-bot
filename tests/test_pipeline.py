import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path

from src.pipeline import PipelineSession, PipelineStep, StepStatus, create_session


@pytest.fixture
def sample_config():
    return {
        "pipelines": {
            "default": [
                {"step": "plan-sync mymd/todo", "approve": "auto"},
                {"step": "next-task", "approve": "required"},
                {"step": "tdd", "approve": "batch"},
            ]
        }
    }


@pytest.fixture
def sample_project():
    return {"name": "kigaru", "path": Path("/tmp/test-project")}


class TestCreateSession:
    def test_creates_session_with_steps(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)

        assert session.project == sample_project
        assert len(session.steps) == 3
        assert session.current_index == 0
        assert session.session_id  # non-empty

    def test_steps_have_correct_command_and_approve(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)

        assert session.steps[0].command == "plan-sync mymd/todo"
        assert session.steps[0].approve == "auto"
        assert session.steps[1].command == "next-task"
        assert session.steps[1].approve == "required"

    def test_all_steps_start_pending(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)

        for step in session.steps:
            assert step.status == StepStatus.PENDING

    def test_is_complete_false_at_start(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)
        assert session.is_complete is False

    def test_is_complete_true_when_index_exceeds_steps(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)
        session = PipelineSession(
            session_id=session.session_id,
            project=session.project,
            steps=session.steps,
            current_index=3,
        )
        assert session.is_complete is True


class TestCurrentStep:
    def test_returns_first_step_at_start(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)
        assert session.current_step is not None
        assert session.current_step.command == "plan-sync mymd/todo"

    def test_returns_none_when_complete(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)
        session = PipelineSession(
            session_id=session.session_id,
            project=session.project,
            steps=session.steps,
            current_index=3,
        )
        assert session.current_step is None


class TestAdvance:
    def test_advance_increments_index(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)
        advanced = session.advance()

        assert advanced.current_index == 1
        assert session.current_index == 0  # 원본 불변

    def test_advance_preserves_other_fields(self, sample_config, sample_project):
        session = create_session(sample_config, sample_project)
        advanced = session.advance()

        assert advanced.session_id == session.session_id
        assert advanced.project == session.project
        assert advanced.steps == session.steps


class TestExecuteNext:
    @pytest.mark.asyncio
    async def test_auto_step_runs_and_advances(self, sample_config, sample_project):
        """auto 스텝은 즉시 실행 후 다음 스텝으로 넘어간다."""
        from src.claude_runner import ClaudeResult

        mock_result = ClaudeResult(
            success=True, output="done", error="", exit_code=0, elapsed=1.0
        )
        send_fn = AsyncMock()

        session = create_session(sample_config, sample_project)
        # 스텝 1개만 auto로 테스트
        session = PipelineSession(
            session_id=session.session_id,
            project=session.project,
            steps=[PipelineStep(command="plan-sync", approve="auto")],
            current_index=0,
        )

        with patch("src.pipeline.run_claude", return_value=mock_result):
            result_session = await session.execute_next(send_fn)

        assert result_session.is_complete
        send_fn.assert_called()  # 완료 메시지 전송

    @pytest.mark.asyncio
    async def test_required_step_pauses(self, sample_config, sample_project):
        """required 스텝은 승인 버튼을 보내고 멈춘다."""
        send_fn = AsyncMock()

        session = create_session(sample_config, sample_project)
        session = PipelineSession(
            session_id=session.session_id,
            project=session.project,
            steps=[PipelineStep(command="next-task", approve="required")],
            current_index=0,
        )

        result_session = await session.execute_next(send_fn)

        assert result_session.current_index == 0  # 안 넘어감
        assert result_session.steps[0].status == StepStatus.WAITING_APPROVAL
        send_fn.assert_called()  # 승인 요청 메시지 전송

    @pytest.mark.asyncio
    async def test_failed_step_stops_pipeline(self, sample_config, sample_project):
        """실패하면 파이프라인이 멈춘다."""
        from src.claude_runner import ClaudeResult

        mock_result = ClaudeResult(
            success=False, output="", error="build failed", exit_code=1, elapsed=1.0
        )
        send_fn = AsyncMock()

        session = PipelineSession(
            session_id="test",
            project=sample_project,
            steps=[PipelineStep(command="tdd", approve="auto")],
            current_index=0,
        )

        with patch("src.pipeline.run_claude", return_value=mock_result):
            result_session = await session.execute_next(send_fn)

        assert result_session.steps[0].status == StepStatus.FAILED
        assert result_session.current_index == 0  # 안 넘어감
