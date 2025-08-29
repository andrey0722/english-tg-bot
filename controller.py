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
        self._logger.info('Greeting %s', message.user)
        if user := self._model.update_user(message.user):
            text = f'Приветствую снова, {user.display_name}!'
        else:
            user = self._model.add_user(message.user)
            text = f'Добро пожаловать, {user.display_name}!'
        return OutputMessage(user, text)

    def clear_user(self, message: InputMessage) -> OutputMessage:
        """Erases user data from the bot.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        self._logger.info('Erasing data for %s', message.user)
        if user := self._model.delete_user(message.user):
            text = f'{user.display_name}, ваши данные удалены.'
        else:
            user = message.user
            text = f'{user.display_name}, ваши данные отсутствуют.'
        return OutputMessage(user, text)

    def process_message(self, message: InputMessage) -> OutputMessage:
        """Processes a message from user and forms a response.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        self._logger.info('Responding to %s', message.user)
        if user := self._model.update_user(message.user):
            text = message.text
        else:
            user = message.user
            text = 'Неизвестный пользователь'
        return OutputMessage(user, text)
