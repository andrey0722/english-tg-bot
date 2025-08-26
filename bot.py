"""This module defines interaction with the Telegram bot API."""

import json
from typing import Optional
from telebot import TeleBot
from telebot.types import Message
import telebot.apihelper
from config import Config
from controller import Controller
from log import LogManager
from model import User


BotError = telebot.apihelper.ApiException


class Bot:
    """A class which instance incapsulates interaction with
    Telegram bot API. Main logic is handled by a controller.
    """

    def __init__(
        self,
        controller: Controller,
        log: LogManager,
        config: Config,
    ):
        """Initialize bot object.

        Args:
            controller (Controller): Bot controller.
            log (LogManager): Log manager to use for logging.
            config (Config): Application config.
        """
        self._logger = log.create_logger(self)
        self._controller = controller
        self._bot = TeleBot(config.tg_bot_token)

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

    def handle_start(self, message: Message):
        """Process /start command from user.

        Args:
            message (Message): A message from user.
        """
        if user := self._process_user(message):
            response = self._controller.get_welcome_message(user)
            self._bot.send_message(message.chat.id, response)

    def handle_message(self, message: Message):
        """Process any other message from user.

        Args:
            message (Message): A message from user.
        """
        if user := self._process_user(message):
            text = message.text or ''
            response = self._controller.get_response(user, text)
            self._bot.reply_to(message, response)

    def _process_user(self, message: Message) -> Optional[User]:
        """Internal helper to extract user data from a message.

        Args:
            message (Message): A message from user.

        Returns:
            Optional[User]: None when the message doesn't contain valid
                user data. `User` object otherwise.
        """
        from_user = message.from_user
        if from_user is None:
            self._logger.debug('Null user, skipping...')
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
        self._logger.info('message: %s', message.text)
        self._logger.info('user: %s', user.display_name)
        return user
