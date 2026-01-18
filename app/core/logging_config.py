"""
Logging configuration for the application.
"""
import logging
import sys
from logging.config import dictConfig


def setup_logging():
    """Initialize logging configuration."""
    from app.core.config import settings
    
    # Build logging config dynamically to ensure settings are loaded
    log_level = "DEBUG" if settings.DEBUG else "INFO"
    
    LOGGING_CONFIG = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout,
            },
            "detailed": {
                "class": "logging.StreamHandler",
                "formatter": "detailed",
                "stream": sys.stdout,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["default"],
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["default"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["default"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["default"],
                "propagate": False,
            },
        },
    }
    
    dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger("app")
    logger.info("Logging configured successfully")
    return logger
