"""로깅 설정 — 콘솔 + 파일 로그 (일별 로테이션)."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: str = "logs", level: int = logging.INFO) -> None:
    """콘솔 + 파일 로그를 설정한다.

    - 콘솔: INFO
    - 파일: DEBUG, 일별 로테이션, 7일 보관
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # 콘솔 핸들러 (기존 것 제거 후 추가)
    for handler in root.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.FileHandler
        ):
            root.removeHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # 파일 핸들러 (일별 로테이션)
    file_handler = TimedRotatingFileHandler(
        filename=str(log_path / "pipeline-bot.log"),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
