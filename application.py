"""Defines initialization logic for application.

This module defines the main class of the entire application and
all connections between program components.
"""

from bot import Bot
from bot import BotError
from config import Config
from config import ConfigError
from config import DatabaseConfig
from controller import Controller
import log
import model
import model.types


class ApplicationError(RuntimeError):
    """Raised when application is stopped on any error."""


class Application:
    """Main class of the bot application."""

    def __init__(self):
        """Initialize application object.

        Raises:
            ApplicationError: Error while initializing application.
        """
        self._config = self._read_config()
        log.setup_logging(self._config.log_level)
        self._logger = log.create_logger(self)
        self._model = self._create_model()
        self._controller = Controller(
            self._model,
            test_words=self._config.test_words,
        )
        self._bot = Bot(self._controller, self._config.tg_bot_token)

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
            self._logger.fatal('Bot running error: %s', e)
            raise ApplicationError(e) from e

    def _create_model(self) -> model.Model:
        try:
            db_config = self._read_db_config()
            db_params = model.ModelConfig(**db_config.model_dump())
            return model.create_model(db_params)
        except model.types.ModelError as e:
            raise ApplicationError(e) from e

    def _read_config(self) -> Config:
        """Internal helper to read application config.

        Raises:
            ApplicationError: Error while reading config.

        Returns:
            Config: Application config.
        """
        try:
            return Config()
        except ConfigError as e:
            raise ApplicationError(e) from e

    def _read_db_config(self) -> DatabaseConfig:
        """Internal helper to read application config.

        Raises:
            ApplicationError: Error while reading config.

        Returns:
            Config: Application config.
        """
        try:
            return DatabaseConfig()
        except ConfigError as e:
            raise ApplicationError(e) from e
