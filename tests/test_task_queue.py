import asyncio
import pytest

from src.task_queue import ProjectLock


class TestProjectLock:
    def test_starts_unlocked(self):
        lock = ProjectLock()
        assert lock.is_locked("kigaru") is False

    @pytest.mark.asyncio
    async def test_acquire_locks_project(self):
        lock = ProjectLock()
        acquired = await lock.acquire("kigaru")

        assert acquired is True
        assert lock.is_locked("kigaru") is True

    @pytest.mark.asyncio
    async def test_second_acquire_fails(self):
        lock = ProjectLock()
        await lock.acquire("kigaru")
        acquired = await lock.acquire("kigaru")

        assert acquired is False

    @pytest.mark.asyncio
    async def test_release_unlocks_project(self):
        lock = ProjectLock()
        await lock.acquire("kigaru")
        lock.release("kigaru")

        assert lock.is_locked("kigaru") is False

    @pytest.mark.asyncio
    async def test_different_projects_independent(self):
        lock = ProjectLock()
        await lock.acquire("kigaru")

        acquired = await lock.acquire("imysh")
        assert acquired is True
        assert lock.is_locked("kigaru") is True
        assert lock.is_locked("imysh") is True

    def test_release_nonexistent_is_noop(self):
        lock = ProjectLock()
        lock.release("nonexistent")  # 크래시 없음

    @pytest.mark.asyncio
    async def test_running_projects_list(self):
        lock = ProjectLock()
        await lock.acquire("kigaru")
        await lock.acquire("imysh")

        running = lock.running_projects()
        assert "kigaru" in running
        assert "imysh" in running
