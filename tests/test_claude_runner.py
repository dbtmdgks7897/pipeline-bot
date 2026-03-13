import asyncio
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.claude_runner import run_claude


@pytest.mark.asyncio
class TestRunClaude:
    async def test_successful_run_returns_success_result(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"output here", b""))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await run_claude("echo test", Path("/tmp"))

        assert result.success is True
        assert result.output == "output here"
        assert result.exit_code == 0

    async def test_failed_run_returns_failure_result(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"error here"))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await run_claude("bad-command", Path("/tmp"))

        assert result.success is False
        assert result.error == "error here"
        assert result.exit_code == 1

    async def test_timeout_returns_timeout_result(self):
        mock_proc = MagicMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        async def slow_communicate():
            await asyncio.sleep(10)
            return (b"", b"")

        mock_proc.communicate = slow_communicate

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await run_claude("slow-cmd", Path("/tmp"), timeout=0.01)

        assert result.success is False
        assert "타임아웃" in result.error
        assert result.exit_code == -1

    async def test_claudecode_env_var_not_passed_to_subprocess(self):
        captured = {}

        async def capture_exec(*args, **kwargs):
            captured["env"] = kwargs.get("env", {})
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))
            return mock_proc

        with patch.dict(os.environ, {"CLAUDECODE": "test-session"}):
            with patch("asyncio.create_subprocess_exec", capture_exec):
                await run_claude("test", Path("/tmp"))

        assert "CLAUDECODE" not in captured["env"]

    async def test_result_includes_elapsed_time(self):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await run_claude("test", Path("/tmp"))

        assert isinstance(result.elapsed, float)
        assert result.elapsed >= 0

    async def test_runs_in_project_directory(self):
        captured = {}

        async def capture_exec(*args, **kwargs):
            captured["cwd"] = kwargs.get("cwd")
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"ok", b""))
            return mock_proc

        project_path = Path("/Users/ysh/projects/kigaru")
        with patch("asyncio.create_subprocess_exec", capture_exec):
            await run_claude("plan-sync", project_path)

        assert captured["cwd"] == str(project_path)

    async def test_timeout_kills_subprocess(self):
        mock_proc = MagicMock()
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        async def slow_communicate():
            await asyncio.sleep(10)
            return (b"", b"")

        mock_proc.communicate = slow_communicate

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            await run_claude("slow-cmd", Path("/tmp"), timeout=0.01)

        mock_proc.kill.assert_called_once()
