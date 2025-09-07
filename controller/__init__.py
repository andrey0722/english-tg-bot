"""This package implements main logic of the bot."""

from typing import Optional

from default_cards import DEFAULT_CARDS
from default_cards import TEST_CARDS
import log
from messages import Messages
from model import Model
from model import Session
from model.types import ModelError
from model.types import User
from model.types import UserState

from .card_manager import CardManager
from .state_manager import StateManager
from .types import InputMessage
from .types import OutputMessage


class Controller:
    """A class which instance processes input from the bot and handles it."""

    def __init__(self, model: Model, test_words: bool = False) -> None:
        """Initialize controller object.

        Args:
            model (Model): Model object.
            test_words (bool): If `True` use only a small subset of
                default words for new users.
        """
        self._model = model
        self._logger = log.create_logger(self)
        self._card_mgr = CardManager(self._model)
        self._state_mgr = StateManager(model, self._card_mgr)
        self._default_cards = TEST_CARDS if test_words else DEFAULT_CARDS

    def start_user(self, message: InputMessage) -> Optional[OutputMessage]:
        """Starts the bot for user and shows main menu.

        Args:
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        self._logger.info('Greeting %s', message.user)
        try:
            with self._model.create_session() as session:
                self._preprocess_user(session, message)
                greeting = self._get_greeting_text(message.user)
                response = self._state_mgr.start_main_menu(session, message)
                response.add_paragraph_before(greeting)
                return response
        except ModelError as e:
            self._logger.error('Model error while greeting: %s', e)
            return OutputMessage(message.user, Messages.BOT_ERROR)

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
            with self._model.create_session() as session:
                if self._delete_user(session, user):
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
        model = self._model
        self._logger.info('Responding to %s', message.user)
        try:
            with model.create_session() as session:
                user = message.user
                if not model.user_exists(session, user.id):
                    return OutputMessage(user, Messages.USER_NOT_STARTED)
                self._preprocess_user(session, message)
                return self._state_mgr.respond(session, message)
        except ModelError as e:
            self._logger.error('Model error while responding: %s', e)
            return OutputMessage(message.user, Messages.BOT_ERROR)

    def _preprocess_user(self, session: Session, message: InputMessage):
        """Internal helper to process input user object using the model.
        Must be called when starting to process new message from a user.
        User object in message is modified in-place.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.
        """
        user = message.user
        model = self._model
        # See if we have this user in the model
        if existing_user := model.get_user(session, user.id):
            # Apply user state from the model
            user.state = existing_user.state
            # Update user info, it could change since last message
            message.user = model.update_user(session, user)
        else:
            # User is now known
            self._logger.info('New user: %s', user)
            user.state = UserState.NEW_USER
            model.add_user(session, user)
            self._add_default_cards(session, user)
        model.commit(session)

    def _add_default_cards(self, session: Session, user: User):
        """Internal helper to add default cards to a user.

        Args:
            session (Session): Session object.
            user (User): A bot user.
        """
        model = self._model
        card_mgr = self._card_mgr
        for ru_word, en_word in self._default_cards:
            card = card_mgr.add_card(session, ru_word, en_word)
            user.cards.add(card)
            model.commit(session)

    def _delete_user(self, session: Session, user: User) -> bool:
        """Internal helper to delete user from the model.

        Args:
            session (Session): Session object.
            user (User): A bot user.

        Returns:
            bool: `True` if existing user was deleted, otherwise `False`.
        """
        model = self._model
        deleted = model.delete_user(session, user.id)
        model.commit(session)
        return deleted is not None

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
