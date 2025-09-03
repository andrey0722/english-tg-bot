"""This module implements main logic of the bot."""

import dataclasses
from typing import List, Optional

import log
from messages import LearningMenu
from messages import MainMenu
from messages import Messages
from model import Model
from model.types import ModelError
from model.types import User
from model.types import UserState


@dataclasses.dataclass
class InputMessage:
    """Input message data from a user to a bot."""

    user: User
    text: str


@dataclasses.dataclass
class BotKeyboard:
    """Contents of bot keyboard shown to user."""

    row_size: int
    buttons: List[str]


@dataclasses.dataclass
class OutputMessage:
    """Output message data from a bot to a user."""

    user: User
    text: str
    keyboard: Optional[BotKeyboard] = None

    def add_paragraph_before(self, paragraph: str):
        """Add a paragraph before current message text.

        Args:
            paragraph (str): Text paragraph to add.
        """
        self.text = '\n\n'.join([paragraph, self.text])


class Controller:
    """A class which instance processes input from the bot and handles it."""

    def __init__(self, model: Model) -> None:
        """Initialize controller object."""
        self._model = model
        self._logger = log.create_logger(self)

    def start_user(self, message: InputMessage) -> Optional[OutputMessage]:
        """Starts the bot for user and shows main menu.

        Args:
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        user = message.user
        self._logger.info('Greeting %s', user)
        try:
            self._preprocess_user(user)
            greeting = self._get_greeting_text(user)
            response = self._start_main_menu(message)
            response.add_paragraph_before(greeting)
            return response
        except ModelError as e:
            self._logger.error('Model error while greeting: %s', e)
            return OutputMessage(user, Messages.BOT_ERROR)

    def clear_user(self, message: InputMessage) -> Optional[OutputMessage]:
        """Erases user data from the bot.

        Args:
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        user = message.user
        self._logger.info('Erasing data for %s', user)
        try:
            if self._model.delete_user(user.id):
                template = Messages.DELETED_USER
            else:
                template = Messages.DELETED_NOT_EXISTING
            return OutputMessage(user, template.format(user.display_name))
        except ModelError as e:
            self._logger.error('Model error while erasing: %s', e)
            return OutputMessage(user, Messages.BOT_ERROR)

    def respond_user(
        self,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """Processes a message from user and forms a response.

        Args:
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        user = message.user
        self._logger.info('Responding to %s', user)
        try:
            if not self._model.user_exists(user.id):
                return OutputMessage(user, Messages.USER_NOT_STARTED)
            self._preprocess_user(user)
            match user.state:
                case UserState.MAIN_MENU:
                    return self._respond_main_menu(message)
                case UserState.LEARNING:
                    return self._respond_learning(message)
        except ModelError as e:
            self._logger.error('Model error while responding: %s', e)
            return OutputMessage(user, Messages.BOT_ERROR)

    def _start_main_menu(self, message: InputMessage) -> OutputMessage:
        """Internal helper that shows main menu to a user with
        keyboard selection.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._update_user_state(user, UserState.MAIN_MENU)
        return OutputMessage(
            user=user,
            text=Messages.SELECT_MAIN_MENU,
            keyboard=self._get_main_menu_keyboard(),
        )

    @staticmethod
    def _get_main_menu_keyboard() -> BotKeyboard:
        """Internal helper to construct bot keyboard for main menu."""
        return BotKeyboard(
            row_size=1,
            buttons=list(MainMenu.__members__.values()),
        )

    def _respond_main_menu(
        self,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """Internal helper that checks and processes user input from main menu.

        Args:
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        text = message.text
        self._logger.info(
            'User %s selected in main menu: %s',
            message.user,
            text,
        )
        match text:
            case MainMenu.LEARN:
                return self._start_learning(message)
            case _:
                self._logger.info('Unknown main menu option: %s', text)

    def _start_learning(self, message: InputMessage) -> OutputMessage:
        """Internal helper that shows learning cards to a user.

        Args:
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._update_user_state(user, UserState.LEARNING)
        return OutputMessage(
            user=user,
            text=Messages.SELECT_LEARNING,
            keyboard=self._get_learning_keyboard(),
        )

    @staticmethod
    def _get_learning_keyboard() -> BotKeyboard:
        """Internal helper to construct bot keyboard for learning menu."""
        return BotKeyboard(
            row_size=1,
            buttons=list(LearningMenu.__members__.values()),
        )

    def _respond_learning(
        self,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """Internal helper that checks and processes user input in
        learning mode.

        Args:
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        text = message.text
        self._logger.info(
            'User %s selected in learning menu: %s',
            message.user,
            text,
        )
        match text:
            case LearningMenu.FINISH:
                response = self._start_main_menu(message)
                response.add_paragraph_before(Messages.FINISHED_LEARNING)
                return response
            case _:
                self._logger.info('Unknown learning menu option: %s', text)

    def _preprocess_user(self, user: User):
        """Internal helper to process input user object using the model.
        Must be called when starting to process new message from a user.

        Args:
            user (User): A bot user.
        """
        if user.state != UserState.UNKNOWN_STATE:
            # User has already been processed
            return
        # See if we have this user in the model
        if existing_user := self._model.get_user(user.id):
            # Apply user state from the model
            user.state = existing_user.state
            # Update user info, it could change since last massage
            self._model.update_user(user)
        else:
            # User is now known
            user.state = UserState.NEW_USER
            self._model.add_user(user)

    def _update_user_state(self, user: User, state: UserState):
        """Internel helper to modify user state and reflect it in the model.

        Args:
            user (User): A bot user.
            state (UserState): New user state.
        """
        user.state = state
        self._model.update_user(user)

    @staticmethod
    def _get_greeting_text(user: User) -> str:
        """Returns greeting text for a user.

        Args:
            user (User): A bot user.
        """
        if user.state == UserState.NEW_USER:
            template = Messages.GREETING_NEW_USER
        else:
            template = Messages.GREETING_OLD_USER
        return template.format(user.display_name)
