import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.error_handler import telegram_error_handler, format_error_message


class TestFormatErrorMessage:
    def test_includes_error_type_and_message(self):
        error = ValueError("invalid input")
        msg = format_error_message(error)

        assert "ValueError" in msg
        assert "invalid input" in msg

    def test_truncates_to_4096_chars(self):
        error = RuntimeError("x" * 5000)
        msg = format_error_message(error)

        assert len(msg) <= 4096

    def test_includes_traceback_when_available(self):
        try:
            raise RuntimeError("test error")
        except RuntimeError as e:
            msg = format_error_message(e)

        assert "Traceback" in msg or "RuntimeError" in msg


class TestTelegramErrorHandler:
    @pytest.mark.asyncio
    async def test_sends_error_to_log(self):
        update = MagicMock()
        context = MagicMock()
        context.error = RuntimeError("something broke")

        with patch("src.error_handler.logger") as mock_logger:
            await telegram_error_handler(update, context)
            mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_handles_none_update(self):
        """update가 None이어도 크래시하지 않는다."""
        context = MagicMock()
        context.error = RuntimeError("no update")

        await telegram_error_handler(None, context)
