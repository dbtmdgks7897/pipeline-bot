"""전역 에러 핸들링 — 미처리 에러를 로깅 + Telegram 알림."""

import logging
import traceback

from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

MAX_MSG_LEN = 4096
_TRUNCATION_SUFFIX = "\n...(잘림)"


def format_error_message(error: BaseException) -> str:
    """에러를 Telegram 메시지 형식으로 변환. 4096자 이내."""
    tb = traceback.format_exception(type(error), error, error.__traceback__)
    tb_text = "".join(tb)

    header = f"🚨 에러 발생: {type(error).__name__}\n\n"
    body = f"{error}\n\n{tb_text}" if tb_text.strip() else str(error)
    message = header + body

    if len(message) > MAX_MSG_LEN:
        available = MAX_MSG_LEN - len(header) - len(_TRUNCATION_SUFFIX)
        message = header + body[-max(available, 0):] + _TRUNCATION_SUFFIX

    return message


async def telegram_error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """python-telegram-bot 전역 에러 핸들러.

    build_app()에서 app.add_error_handler()로 등록한다.
    """
    error = context.error
    if error is None:
        return

    logger.error("Unhandled exception: %s", error, exc_info=error)
