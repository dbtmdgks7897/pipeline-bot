"""배치 스케줄러 — 매일 정해진 시간에 배치 큐를 flush하고 Telegram 알림."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)

_JOB_ID = "batch_flush"


def start_scheduler(
    flush_callback: Callable[[], None],
    hour: int = 8,
    minute: int = 0,
    timezone: str = "Asia/Seoul",
) -> BackgroundScheduler:
    """스케줄러 시작. BackgroundScheduler 객체를 반환."""
    scheduler = BackgroundScheduler()
    trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)
    scheduler.add_job(flush_callback, trigger, id=_JOB_ID)
    scheduler.start()
    logger.info("배치 스케줄러 시작 (매일 %02d:%02d %s)", hour, minute, timezone)
    return scheduler


def shutdown_scheduler(scheduler: BackgroundScheduler) -> None:
    """스케줄러 안전 종료."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("배치 스케줄러 종료")


def get_next_run_time(scheduler: BackgroundScheduler) -> datetime | None:
    """다음 실행 시간 조회. 종료 상태면 None."""
    if not scheduler.running:
        return None
    job = scheduler.get_job(_JOB_ID)
    if job is None:
        return None
    return job.next_run_time
