import logging
import sys
from logging.config import dictConfig


def setup_logging() -> None:
    LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    LOG_LEVEL = logging.INFO

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": LOG_FORMAT,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "standard",
                "level": LOG_LEVEL,
            }
        },
        "root": {"handlers": ["console"], "level": LOG_LEVEL},
    }
    dictConfig(config)
