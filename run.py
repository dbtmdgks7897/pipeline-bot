import logging
import os

from src.config import load_config
from src.bot import build_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _run_webhook(tg_app, webhook_url: str, port: int = 8000):
    """FastAPI + Cloudflare Tunnel webhook 모드로 실행."""
    import uvicorn
    from contextlib import asynccontextmanager
    from fastapi import FastAPI, Request

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await tg_app.initialize()
        await tg_app.bot.set_webhook(webhook_url + "/webhook")
        logger.info("Webhook 등록 완료: %s/webhook", webhook_url)
        yield
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
        logger.info("Pipeline Bot 시작 (polling 모드)...")
        app.run_polling()
