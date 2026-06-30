"""
logger.py

Application logging for the Davison Financial Model.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

import logging

from src.config.settings import settings


def _create_logger() -> logging.Logger:
    """
    Create and configure the application logger.
    """

    settings.logs_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    app_logger = logging.getLogger("financial_model")

    if app_logger.handlers:
        return app_logger

    app_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        settings.log_file,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    app_logger.addHandler(file_handler)

    return app_logger


logger = _create_logger()
