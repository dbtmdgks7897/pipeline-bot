"""배치 스케줄러 테스트."""

from unittest.mock import MagicMock, patch

import pytest

from src.batch_scheduler import (
    get_next_run_time,
    shutdown_scheduler,
    start_scheduler,
)


class TestStartScheduler:
    """start_scheduler 테스트."""

    def test_returns_scheduler_object(self):
        """스케줄러 객체를 반환해야 한다."""
        callback = MagicMock()
        scheduler = start_scheduler(callback, hour=9, minute=0)
        assert scheduler is not None
        shutdown_scheduler(scheduler)

    def test_scheduler_is_running_after_start(self):
        """시작 후 running 상태여야 한다."""
        callback = MagicMock()
        scheduler = start_scheduler(callback, hour=9, minute=0)
        assert scheduler.running is True
        shutdown_scheduler(scheduler)

    def test_uses_provided_timezone(self):
        """지정한 timezone이 적용되어야 한다."""
        callback = MagicMock()
        scheduler = start_scheduler(
            callback, hour=9, minute=0, timezone="Asia/Seoul"
        )
        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        assert str(jobs[0].trigger.timezone) == "Asia/Seoul"
        shutdown_scheduler(scheduler)

    def test_uses_provided_hour_and_minute(self):
        """지정한 시/분이 cron 트리거에 반영되어야 한다."""
        callback = MagicMock()
        scheduler = start_scheduler(callback, hour=14, minute=30)
        jobs = scheduler.get_jobs()
        trigger_str = str(jobs[0].trigger)
        assert "14" in trigger_str
        assert "30" in trigger_str
        shutdown_scheduler(scheduler)


class TestShutdownScheduler:
    """shutdown_scheduler 테스트."""

    def test_scheduler_stops_after_shutdown(self):
        """종료 후 running이 False여야 한다."""
        callback = MagicMock()
        scheduler = start_scheduler(callback, hour=9, minute=0)
        shutdown_scheduler(scheduler)
        assert scheduler.running is False

    def test_shutdown_idempotent(self):
        """이미 종료된 스케줄러를 다시 종료해도 에러 없어야 한다."""
        callback = MagicMock()
        scheduler = start_scheduler(callback, hour=9, minute=0)
        shutdown_scheduler(scheduler)
        shutdown_scheduler(scheduler)  # 두 번째 호출 — 에러 없어야 함


class TestGetNextRunTime:
    """get_next_run_time 테스트."""

    def test_returns_datetime_after_start(self):
        """시작된 스케줄러는 다음 실행 시간을 반환해야 한다."""
        from datetime import datetime

        callback = MagicMock()
        scheduler = start_scheduler(callback, hour=9, minute=0)
        next_time = get_next_run_time(scheduler)
        assert isinstance(next_time, datetime)
        shutdown_scheduler(scheduler)

    def test_returns_none_after_shutdown(self):
        """종료된 스케줄러는 None을 반환해야 한다."""
        callback = MagicMock()
        scheduler = start_scheduler(callback, hour=9, minute=0)
        shutdown_scheduler(scheduler)
        next_time = get_next_run_time(scheduler)
        assert next_time is None
