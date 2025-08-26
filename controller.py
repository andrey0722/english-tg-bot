"""This module implements main logic of the bot."""

from log import LogManager
from model import Model, User


class Controller:
    """A class which instance processes input from the bot and handles it."""

    def __init__(self, model: Model, log: LogManager) -> None:
        """Initialize controller object."""
        self._model = model
        self._logger = log.create_logger(self)

    def get_welcome_message(self, user: User) -> str:
        """Returns welcome message for a user.

        Args:
            user (User): Bot user, a new one or an old one.

        Returns:
            str: Bot response to the user.
        """
        self._logger.debug('Greeting %s', user.display_name)
        return f'Приветствую, {user.display_name}!'

    def get_response(self, user: User, message: str) -> str:
        """Returns response message for a user.

        Args:
            user (User): Bot user.
            message (User): User message to the bot.

        Returns:
            str: Bot response to the user.
        """
        self._logger.debug('Responding to %s', user.display_name)
        return message
