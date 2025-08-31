"""This module defines interaction with the Telegram bot API."""

import json
from typing import Optional

import telebot
import telebot.apihelper
from telebot.types import KeyboardButton, Message as TelebotMessage
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telebot.types import ReplyParameters

from controller import BotKeyboard, Controller, InputMessage, OutputMessage
from log import LogManager
from model.types import User


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
        self._set_telebot_logger(log)
        self._bot = self._create_bot(token)

        self._bot.register_message_handler(
            self.handle_start,
            commands=['start'],
        )
        self._bot.register_message_handler(
            self.handle_clear,
            commands=['clear'],
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

    def handle_start(self, message: TelebotMessage):
        """Process /start command from user.

        Args:
            message (TelebotMessage): A message from user.
        """
        if in_message := self._convert_message(message):
            if response := self._controller.start_user(in_message):
                self._send_message(message, response)

    def handle_clear(self, message: TelebotMessage):
        """Process /clear command from user.

        Args:
            message (TelebotMessage): A message from user.
        """
        if in_message := self._convert_message(message):
            if response := self._controller.clear_user(in_message):
                self._send_message(message, response)

    def handle_message(self, message: TelebotMessage):
        """Process any other message from user.

        Args:
            message (TelebotMessage): A message from user.
        """
        if in_message := self._convert_message(message):
            if response := self._controller.respond_user(in_message):
                self._send_message(message, response, reply=True)

    def _convert_message(
        self,
        message: TelebotMessage,
    ) -> Optional[InputMessage]:
        """Internal helper to process user message.

        Args:
            message (TelebotMessage): A message from user.

        Returns:
            Optional[InputMessage]: Processed message object if the message
                is valid, otherwise `None`.
        """
        self._logger.debug('Got message: %s', message.text)
        if user := self._extract_user(message):
            return InputMessage(
                user=user,
                text=message.text or '',
            )

    def _extract_user(self, message: TelebotMessage) -> Optional[User]:
        """Internal helper to extract user data from a message.

        Args:
            message (TelebotMessage): A message from user.

        Returns:
            Optional[User]: Extracted user object if the user data
                in message is valid, otherwise `None`.
        """
        from_user = message.from_user
        if from_user is None:
            self._logger.warning('Null user in message')
            return None
        self._logger.debug(
            'Raw user data: %s',
            json.dumps(from_user.to_dict()),
        )

        user = User(
            id=from_user.id,
            username=from_user.username,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
        )
        self._logger.debug('Extracted user from message: %r', user)
        return user

    def _send_message(
        self,
        message: TelebotMessage,
        response: OutputMessage,
        *,
        reply: bool = False,
    ):
        """Internal helper to send response back to the user.

        Args:
            message (TelebotMessage): A message from user.
            response (OutputMessage): Bot response to the user.
            reply (bool, optional): If `True` send the message as a reply
                to the user message. Defaults to `False`.
        """
        self._logger.debug('Sending "%s" to %r', response.text, response.user)

        if reply:
            self._logger.debug('Replying to user')
            reply_parameters = self._get_reply_params(message)
        else:
            reply_parameters = None

        if keyboard := response.keyboard:
            self._logger.debug(f'Keyboard: {keyboard!r}')
            reply_markup = self._get_reply_keyboard(keyboard)
        else:
            reply_markup = ReplyKeyboardRemove()

        self._bot.send_message(
            chat_id=message.chat.id,
            text=response.text,
            reply_parameters=reply_parameters,
            reply_markup=reply_markup,
        )

    @staticmethod
    def _get_reply_params(message: TelebotMessage):
        """Internal helper to calculate reply parameters for bot message.

        Args:
            message (TelebotMessage): A message from user.
        """
        return ReplyParameters(message_id=message.id)

    @staticmethod
    def _get_reply_keyboard(keyboard: BotKeyboard) -> ReplyKeyboardMarkup:
        """Internal helper to calculate keyboard markup for user reply.

        Args:
            keyboard (BotKeyboard): Bot keyboard.
        """
        reply_markup = ReplyKeyboardMarkup(
            row_width=keyboard.row_size,
            resize_keyboard=True,
        )
        buttons = [KeyboardButton(x) for x in keyboard.buttons]
        reply_markup.add(*buttons)
        return reply_markup

    def _create_bot(self, token: str) -> telebot.TeleBot:
        """Internal helper to create and return a bot object.

        Args:
            token (str): Telegram bot API token.
        """
        return telebot.TeleBot(token)

    _is_telebot_logger_set: bool = False

    @staticmethod
    def _set_telebot_logger(log: LogManager):
        """Override logger of the `telebot` library.

        Args:
            log (LogManager): Log manager to use for logging.
        """
        if not Bot._is_telebot_logger_set:
            telebot.logger = log.create_logger(telebot.logger.name)
            Bot._is_telebot_logger_set = True
