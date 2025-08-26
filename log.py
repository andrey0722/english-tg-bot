"""This module defines infrastructure for application logging."""


from enum import Enum
import logging
from typing import Any, Optional


class LogLevel(Enum):
    """Defines all valid log levels for the application."""

    CRITICAL = 'CRITICAL'
    FATAL = 'FATAL'
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'


Logger = logging.Logger


class LogManager:
    """Provides interface for creating and configuring loggers."""

    def setup(self, level: LogLevel = LogLevel.INFO):
        """Initialize logging infrastructure for future logging.

        Args:
            level (LogLevel, optional): Desired log level to apply.
                Defaults to LogLevel.INFO.
        """
        logging.basicConfig(level=level.value, force=True)

    def create_logger(
        self,
        obj: Any,
        level: Optional[LogLevel] = None,
    ) -> Logger:
        """Initialize logging infrastructure for future logging.

        Args:
            level (LogLevel, optional): Desired log level to apply.
                Defaults to LogLevel.INFO.
        """
        if not hasattr(obj, '__name__'):
            obj = type(obj)
        logger_name = obj.__name__
        logger = logging.getLogger(logger_name)
        if level is not None:
            logger.setLevel(level.value)
        return logger
