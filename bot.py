"""This module defines interaction with the Telegram bot API."""

from collections.abc import Callable
import enum
import json
from typing import Final

import telebot
import telebot.apihelper
from telebot.types import KeyboardButton
from telebot.types import Message as TelebotMessage
from telebot.types import ReplyKeyboardMarkup
from telebot.types import ReplyKeyboardRemove
from telebot.types import ReplyParameters

from controller import Controller
from controller import InputMessage
from controller import OutputMessage
from controller.types import BotKeyboard
import log
from model.types import User
import utils

BotError = telebot.apihelper.ApiException


class BotCommand(enum.StrEnum):
    """Contains all command supported by the bot."""
    START = enum.auto()
    HELP = enum.auto()
    CLEAR = enum.auto()


Handler = Callable[[Controller, InputMessage], OutputMessage | None]


COMMAND_TO_HANDLER: Final[dict[BotCommand | None, Handler]] = {
    BotCommand.START: Controller.start,
    BotCommand.HELP: Controller.help,
    BotCommand.CLEAR: Controller.clear,
    None: Controller.respond_user,
}


class Bot:
    """Interacts with Telegram bot API.

    A class which instance incapsulates interaction with
    Telegram bot API. Main logic is handled by a controller.
    """

    def __init__(
        self,
        controller: Controller,
        token: str,
    ) -> None:
        """Initialize bot object.

        Args:
            controller (Controller): Bot controller.
            token (str): Telegram bot API token.
        """
        self._logger = log.create_logger(self)
        self._controller = controller
        self._set_telebot_logger()
        self._bot = self._create_bot(token)

        command_to_method = {
            BotCommand.START: self.handle_start,
            BotCommand.HELP: self.handle_help,
            BotCommand.CLEAR: self.handle_clear,
        }
        for command, method in command_to_method.items():
            self._bot.register_message_handler(method, commands=[command])

        self._bot.register_message_handler(
            self.handle_text,
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

    def handle_start(self, message: TelebotMessage) -> None:
        """Process /start command from user.

        Args:
            message (TelebotMessage): A message from user.
        """
        self._handle_message(message, BotCommand.START)

    def handle_help(self, message: TelebotMessage) -> None:
        """Process /help command from user.

        Args:
            message (TelebotMessage): A message from user.
        """
        self._handle_message(message, BotCommand.HELP)

    def handle_clear(self, message: TelebotMessage) -> None:
        """Process /clear command from user.

        Args:
            message (TelebotMessage): A message from user.
        """
        self._handle_message(message, BotCommand.CLEAR)

    def handle_text(self, message: TelebotMessage) -> None:
        """Process any text message from user.

        Args:
            message (TelebotMessage): A message from user.
        """
        self._handle_message(message)

    def _handle_message(
        self,
        message: TelebotMessage,
        command: BotCommand | None = None,
    ) -> None:
        """Internal helper to process a command from user.

        Args:
            message (TelebotMessage): A message from user.
            command (BotCommand | None): Bot command value. Defaults to None.
        """
        in_message = self._convert_message(message)
        if not in_message:
            return

        handler = COMMAND_TO_HANDLER[command]
        response = handler(self._controller, in_message)
        if not response:
            return

        self._send_message(message, response, reply=True)

    def _convert_message(
        self,
        message: TelebotMessage,
    ) -> InputMessage | None:
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
        return None

    def _extract_user(self, message: TelebotMessage) -> User | None:
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
    ) -> None:
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
            self._logger.debug('Keyboard: %r', keyboard)
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
    def _get_reply_params(message: TelebotMessage) -> ReplyParameters:
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

        Returns:
            ReplyKeyboardMarkup: Telebot keyboard.
        """
        reply_markup = ReplyKeyboardMarkup(
            row_width=keyboard.row_size,
            resize_keyboard=True,
        )
        buttons = list(map(KeyboardButton, keyboard.buttons))
        reply_markup.add(*buttons)
        return reply_markup

    def _create_bot(self, token: str) -> telebot.TeleBot:
        """Internal helper to create and return a bot object.

        Args:
            token (str): Telegram bot API token.
        """
        return telebot.TeleBot(token)

    @staticmethod
    @utils.call_once
    def _set_telebot_logger():
        """Override logger of the `telebot` library."""
        telebot.logger = log.create_logger(telebot.logger.name)
