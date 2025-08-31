"""This module defines infrastructure for application logging."""


import enum
import logging
from typing import Any, Optional, override

import coloredlogs


@enum.unique
class LogLevel(enum.IntEnum):
    """Defines all valid log levels for the application."""

    FATAL = logging.FATAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG


Logger = logging.Logger


class LogLevelLimitFilter(logging.Filter):
    """Reduces log level of all log records to a specified level. Helps
    to avoid flooding with logs on high log level.
    """

    def __init__(self, logger: Logger, level: LogLevel):
        """Initialize filer object.

        Args:
            logger (Logger): A logger to measure effective log level.
            level (LogLevel): Target log level for limit.
        """
        super().__init__()
        self.logger = logger
        self.level = level

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        if self.logger.getEffectiveLevel() > self.level:
            # Discard record when log level is above
            return False
        # Reduce log level
        record.levelno = self.level
        record.levelname = self.level.name
        return True


class LogManager:
    """Provides interface for creating and configuring loggers."""

    def setup(self, level: LogLevel = LogLevel.INFO):
        """Initialize logging infrastructure for future logging.

        Args:
            level (LogLevel, optional): Desired log level to apply.
                Defaults to LogLevel.INFO.
        """
        logging.basicConfig(level=level, force=True)
        coloredlogs.install(level=level)

    def create_logger(
        self,
        obj: Any,
        level: Optional[LogLevel] = None,
    ) -> Logger:
        """Initialize logging infrastructure for future logging.

        Args:
            obj (Any): Object to use for name calculation.
            level (LogLevel, optional): Desired log level to apply.
                Defaults to LogLevel.INFO.
        """
        logger_name = self._get_logger_name(obj)
        # Delete logger if it exists
        Logger.manager.loggerDict.pop(logger_name, None)
        logger = logging.getLogger(logger_name)
        if level is not None:
            logger.setLevel(level.value)
        return logger

    def _get_logger_name(self, obj: Any) -> str:
        """Internal helper to calculate desired logger name.

        Args:
            obj (Any): Object to use for name calculation.
        """
        if isinstance(obj, str):
            # User specified a concrete logger name
            return obj
        if not hasattr(obj, '__qualname__'):
            # For plain objects use their types
            # Functions already have names
            obj = type(obj)
        # Use fully-qualified name with module path
        return f'{obj.__module__}.{obj.__qualname__}'
