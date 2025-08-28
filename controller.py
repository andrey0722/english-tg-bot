"""This module implements main logic of the bot."""

from log import LogManager
from model.types import Model, OutputMessage, InputMessage


class Controller:
    """A class which instance processes input from the bot and handles it."""

    def __init__(self, model: Model, log: LogManager) -> None:
        """Initialize controller object."""
        self._model = model
        self._logger = log.create_logger(self)

    def welcome_user(self, message: InputMessage) -> OutputMessage:
        """Returns welcome message for a user.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        self._logger.debug('Greeting %s', message.user.display_name)
        return OutputMessage(f'Приветствую, {message.user.display_name}!')

    def process_message(self, message: InputMessage) -> OutputMessage:
        """Processes a message from user and forms a response.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        self._logger.debug('Responding to %s', message.user.display_name)
        return OutputMessage(message.text)
