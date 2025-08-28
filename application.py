"""This module defines the main class of the entire application and
all connections between program components.
"""

from bot import Bot, BotError
from config import Config, ConfigError
from controller import Controller
from log import LogLevel, LogManager
from model import Model


class ApplicationError(RuntimeError):
    """Raised when application is stopped on any error."""


class Application:
    """Main class of the bot application."""

    def __init__(self, log: LogManager):
        """Initialize application object.

        Args:
            log (LogManager): Log manager to use for logging.

        Raises:
            ApplicationError: Error while initializing application.
        """
        self._config = self._read_config(log)
        log.setup(self._config.log_level)
        self._logger = log.create_logger(self)
        self._model = Model()
        self._controller = Controller(self._model, log)
        self._bot = Bot(self._controller, log, self._config.tg_bot_token)

    def run(self):
        """Start the bot and keep running until stopped.

        Raises:
            ApplicationError: Error while running application.
        """
        self._logger.info('Starting the bot')
        try:
            self._bot.run()
            self._logger.info('Bot exited normally')
        except BotError as e:
            self._logger.critical('Bot running error: %s', e)
            raise ApplicationError from e

    def _read_config(self, log: LogManager) -> Config:
        """Internal helper to read application config.

        Args:
            log (LogManager): Log manager to use for logging.

        Raises:
            ApplicationError: Error while reading config.

        Returns:
            Config: Application config.
        """
        logger = log.create_logger(Application._read_config, LogLevel.INFO)
        try:
            return Config()
        except ConfigError as e:
            logger.critical('Failed to read application config: %s', e)
            raise ApplicationError from e
