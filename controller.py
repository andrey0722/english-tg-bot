"""This module implements main logic of the bot."""

from log import LogManager
from model.types import Model, ModelError, OutputMessage, InputMessage


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
        user = message.user
        self._logger.info('Greeting %s', user)
        try:
            if self._model.user_exists(user.id):
                self._model.update_user(user)
                text = f'Приветствую снова, {user.display_name}!'
            else:
                self._model.add_user(user)
                text = f'Добро пожаловать, {user.display_name}!'
        except ModelError as e:
            self._logger.error('Model error while greeting: %s', e)
            text = 'Ошибка работы бота'
        return OutputMessage(user, text)

    def clear_user(self, message: InputMessage) -> OutputMessage:
        """Erases user data from the bot.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._logger.info('Erasing data for %s', user)
        try:
            if self._model.delete_user(user.id):
                text = f'{user.display_name}, ваши данные удалены.'
            else:
                text = f'{user.display_name}, ваши данные отсутствуют.'
        except ModelError as e:
            self._logger.error('Model error while erasing: %s', e)
            text = 'Ошибка работы бота'
        return OutputMessage(user, text)

    def process_message(self, message: InputMessage) -> OutputMessage:
        """Processes a message from user and forms a response.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._logger.info('Responding to %s', user)
        try:
            if self._model.user_exists(user.id):
                self._model.update_user(user)
                text = message.text
            else:
                text = 'Неизвестный пользователь'
        except ModelError as e:
            self._logger.error('Model error while responding: %s', e)
            text = 'Ошибка работы бота'
        return OutputMessage(message.user, text)
