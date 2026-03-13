import logging
import pytest
from pathlib import Path

from src.logger import setup_logging


class TestSetupLogging:
    def test_creates_log_directory(self, tmp_path):
        log_dir = tmp_path / "logs"
        setup_logging(log_dir=str(log_dir))

        assert log_dir.exists()

    def test_adds_file_handler(self, tmp_path):
        log_dir = tmp_path / "logs"
        setup_logging(log_dir=str(log_dir))

        root = logging.getLogger()
        file_handlers = [
            h for h in root.handlers
            if isinstance(h, logging.FileHandler)
        ]
        assert len(file_handlers) >= 1

    def test_log_file_created_on_write(self, tmp_path):
        log_dir = tmp_path / "logs"
        setup_logging(log_dir=str(log_dir))

        test_logger = logging.getLogger("test.logger.write")
        test_logger.info("test message")

        log_files = list(log_dir.glob("*.log"))
        assert len(log_files) >= 1

    def teardown_method(self):
        """각 테스트 후 핸들러 정리."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root.removeHandler(handler)
