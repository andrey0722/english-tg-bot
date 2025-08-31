"""This module defines the main class of the entire application and
all connections between program components.
"""

from bot import Bot, BotError
from config import Config, ConfigError, DatabaseConfig, StorageType
from controller import Controller
from log import LogManager
from model.memory_model import MemoryModel
from model.database_model import DatabaseModel, DatabaseParams
from model.types import Model, ModelError


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
        self._config = self._read_config()
        log.setup(self._config.log_level)
        self._logger = log.create_logger(self)
        self._model = self._create_model(log)
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
            raise ApplicationError(e) from e

    def _create_model(self, log: LogManager) -> Model:
        storage_type = self._config.storage_type
        self._logger.debug('Using storage type "%s"', storage_type)
        try:
            match storage_type:
                case StorageType.DATABASE:
                    db_config = self._read_db_config()
                    db_params = DatabaseParams(**db_config.model_dump())
                    return DatabaseModel(
                        log,
                        db_params,
                        self._config.clear_data,
                    )
                case StorageType.MEMORY:
                    return MemoryModel(log)
                case _:
                    raise ApplicationError(
                        f'Unable to create model for storage "{storage_type}"'
                    )
        except ModelError as e:
            raise ApplicationError(e) from e

    def _read_config(self) -> Config:
        """Internal helper to read application config.

        Args:
            log (LogManager): Log manager to use for logging.

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

        Args:
            log (LogManager): Log manager to use for logging.

        Raises:
            ApplicationError: Error while reading config.

        Returns:
            Config: Application config.
        """
        try:
            return DatabaseConfig()
        except ConfigError as e:
            raise ApplicationError(e) from e
