"""This module defines interaction with the Telegram bot API."""

import json
from typing import Optional
import telebot
import telebot.types
import telebot.apihelper
from controller import Controller
from log import LogManager
from model.types import InputMessage, User


BotError = telebot.apihelper.ApiException


class Bot:
    """A class which instance incapsulates interaction with
    Telegram bot API. Main logic is handled by a controller.
    """

    def __init__(
        self,
        controller: Controller,
        log: LogManager,
        token: str,
    ):
        """Initialize bot object.

        Args:
            controller (Controller): Bot controller.
            log (LogManager): Log manager to use for logging.
            token (str): Telegram bot API token.
        """
        self._logger = log.create_logger(self)
        self._controller = controller
        self._bot = self._create_bot(token)

        self._bot.register_message_handler(
            self.handle_start,
            commands=['start'],
        )
        self._bot.register_message_handler(
            self.handle_message,
            func=lambda _: True,
            content_types=['text'],
        )

    def run(self):
        """Start the bot and handle all incoming messages.

        Raises:
            BotError: Error while interacting with Telegram API.
        """
        self._logger.debug('Bot started')
        try:
            self._bot.infinity_polling(skip_pending=True)
        except:
            self._logger.debug('Bot polling error')
            raise

    def handle_start(self, message: telebot.types.Message):
        """Process /start command from user.

        Args:
            message (telebot.types.Message): A message from user.
        """
        if input_message := self._convert_message(message):
            output_message = self._controller.welcome_user(input_message)
            self._bot.send_message(message.chat.id, output_message.text)

    def handle_message(self, message: telebot.types.Message):
        """Process any other message from user.

        Args:
            message (telebot.types.Message): A message from user.
        """
        if input_message := self._convert_message(message):
            output_message = self._controller.process_message(input_message)
            self._bot.reply_to(message, output_message.text)

    def _convert_message(
        self,
        message: telebot.types.Message,
    ) -> Optional[InputMessage]:
        """Internal helper to process user message.

        Args:
            message (telebot.types.Message): A message from user.

        Returns:
            Optional[InputMessage]: Processed message object if the message
                is valid, otherwise `None`.
        """
        self._logger.info('message: %s', message.text)
        if user := self._extract_user(message):
            return InputMessage(
                user=user,
                text=message.text or '',
            )

    def _extract_user(self, message: telebot.types.Message) -> Optional[User]:
        """Internal helper to extract user data from a message.

        Args:
            message (telebot.types.Message): A message from user.

        Returns:
            Optional[User]: Extracted user object if the user data
                in message is valid, otherwise `None`.
        """
        from_user = message.from_user
        if from_user is None:
            self._logger.warning('Null user, skipping...')
            return None
        self._logger.debug(
            'user = %s',
            json.dumps(from_user.to_dict(), indent=4),
        )

        user = User(
            tg_id=from_user.id,
            username=from_user.username,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
        )
        self._logger.info('user: %s', user.display_name)
        return user

    def _create_bot(self, token: str) -> telebot.TeleBot:
        """Internal helper to create and return a bot object.

        Args:
            token (str): Telegram bot API token.
        """
        return telebot.TeleBot(token)
