import logging
import os

from src.config import load_config
from src.bot import build_app, set_batch_scheduler
from src.batch_scheduler import start_scheduler, shutdown_scheduler
from src.batch_review import flush_queue, get_summary, is_empty
from src.logger import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


_scheduler = None


def _start_batch_scheduler() -> None:
    """배치 스케줄러를 시작하고 bot에 등록."""
    global _scheduler

    def _flush_callback() -> None:
        if is_empty():
            return
        summary = get_summary()
        flush_queue()
        logger.info("배치 큐 flush: %s", summary[:100])

    _scheduler = start_scheduler(_flush_callback, hour=8, minute=0)
    set_batch_scheduler(_scheduler)


def _stop_batch_scheduler() -> None:
    """배치 스케줄러를 종료."""
    global _scheduler
    if _scheduler is not None:
        shutdown_scheduler(_scheduler)
        _scheduler = None


def _run_webhook(tg_app, webhook_url: str, port: int = 8000):
    """FastAPI + Cloudflare Tunnel webhook 모드로 실행."""
    import uvicorn
    from contextlib import asynccontextmanager
    from fastapi import FastAPI, Request

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _start_batch_scheduler()
        await tg_app.initialize()
        await tg_app.bot.set_webhook(webhook_url + "/webhook")
        logger.info("Webhook 등록 완료: %s/webhook", webhook_url)
        yield
        _stop_batch_scheduler()
        await tg_app.bot.delete_webhook()
        await tg_app.shutdown()

    fastapi_app = FastAPI(lifespan=lifespan)

    @fastapi_app.post("/webhook")
    async def webhook(request: Request):
        from telegram import Update

        data = await request.json()
        update = Update.de_json(data, tg_app.bot)
        await tg_app.process_update(update)
        return {"ok": True}

    @fastapi_app.get("/health")
    async def health():
        return {"status": "ok"}

    logger.info("Pipeline Bot 시작 (webhook 모드, port=%d)...", port)
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    config = load_config("config.yaml")
    app = build_app(config)

    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()
    if webhook_url:
        port = int(os.environ.get("PORT", "8000"))
        _run_webhook(app, webhook_url, port)
    else:
        _start_batch_scheduler()
        logger.info("Pipeline Bot 시작 (polling 모드)...")
        try:
            app.run_polling()
        finally:
            _stop_batch_scheduler()
