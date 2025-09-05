"""This module implements main logic of the bot."""

import dataclasses
from typing import List, Optional

from default_cards import DEFAULT_CARDS
import log
from messages import LearningMenu
from messages import MainMenu
from messages import Messages
from model import Model
from model import Session
from model.types import AddWordProgress
from model.types import EnglishWord
from model.types import LearningCard
from model.types import ModelError
from model.types import RussianWord
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

    def add_paragraph_before(self, paragraph: str, *, separator: str = '\n\n'):
        """Add a paragraph before current message text.

        Args:
            paragraph (str): Text paragraph to add.
            separator (str, optional): Optional separator value between
                paragraphs. Defaults to `'\n\n'`.
        """
        self.text = separator.join([paragraph, self.text])

    def add_paragraph_after(self, paragraph: str, *, separator: str = '\n\n'):
        """Add a paragraph after current message text.

        Args:
            paragraph (str): Text paragraph to add.
            separator (str, optional): Optional separator value between
                paragraphs. Defaults to `'\n\n'`.
        """
        self.text = separator.join([self.text, paragraph])


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
            with self._model.create_session() as session:
                message.user = self._preprocess_user(session, user)
                user = message.user
                greeting = self._get_greeting_text(user)
                response = self._start_main_menu(session, message)
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
        user = message.user
        self._logger.info('Responding to %s', user)
        try:
            with self._model.create_session() as session:
                if not self._model.user_exists(session, user.id):
                    return OutputMessage(user, Messages.USER_NOT_STARTED)
                message.user = self._preprocess_user(session, user)
                user = message.user
                match user.state:
                    case UserState.MAIN_MENU:
                        return self._respond_main_menu(session, message)
                    case UserState.LEARNING:
                        return self._respond_learning(session, message)
                    case UserState.ADDING_WORD:
                        return self._respond_add_word(session, message)
        except ModelError as e:
            self._logger.error('Model error while responding: %s', e)
            return OutputMessage(user, Messages.BOT_ERROR)

    def _start_main_menu(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage:
        """Internal helper that shows main menu to a user with
        keyboard selection.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._update_user_state(session, user, UserState.MAIN_MENU)
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
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """Internal helper that checks and processes user input from main menu.

        Args:
            session (Session): Session object.
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
                return self._start_learning(session, message)
            case MainMenu.ADD_WORD:
                return self._start_add_word(session, message)
            case _:
                self._logger.info('Unknown main menu option: %s', text)

    def _start_learning(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage:
        """Internal helper that shows learning cards to a user.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._update_user_state(session, user, UserState.LEARNING)
        response = OutputMessage(
            user=user,
            text=Messages.SELECT_LEARNING,
            keyboard=self._get_learning_keyboard(),
        )

        lines = []
        for card in self._model.get_cards(session, user):
            lines.append(f'{card.ru_word.text} -> {card.en_word.text}')
        text = '\n'.join(lines)
        response.add_paragraph_before(text)
        response.add_paragraph_before('Cards:')

        return response

    @staticmethod
    def _get_learning_keyboard() -> BotKeyboard:
        """Internal helper to construct bot keyboard for learning menu."""
        return BotKeyboard(
            row_size=1,
            buttons=list(LearningMenu.__members__.values()),
        )

    def _respond_learning(
        self,
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """Internal helper that checks and processes user input in
        learning mode.

        Args:
            session (Session): Session object.
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
                response = self._start_main_menu(session, message)
                response.add_paragraph_before(Messages.FINISHED_LEARNING)
                return response
            case _:
                self._logger.info('Unknown learning menu option: %s', text)

    def _start_add_word(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage:
        """Internal helper that starts add word procedure.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._update_user_state(session, user, UserState.ADDING_WORD)
        return OutputMessage(
            user=user,
            text=Messages.ENTER_RU_WORD,
        )

    def _respond_add_word(
        self,
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """Internal helper that checks and processes user input when adding
        new words.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        user = message.user
        text = message.text
        self._logger.info('User %s word input: %s', user, text)

        if progress := self._model.get_add_word_progress(session, user):
            self._logger.debug('Current word progress: %r', progress)

            # Delete user progress
            user.add_word_progress = None

            # Add new card for user
            card = self._add_card(session, progress.ru_word, text)
            user.cards.append(card)
            self._model.commit(session)
            text = Messages.ADDED_RU_EN_CARD.format(
                card.ru_word.text,
                card.en_word.text,
            )

            response = self._start_main_menu(session, message)
            response.add_paragraph_before(text)
        else:
            # Save user progress
            ru_word = self._model.add_word(session, RussianWord(text=text))
            progress = AddWordProgress(user=user, ru_word=ru_word)
            session.add(progress)
            self._model.commit(session)
            self._logger.debug('Saved add word progress: %r', progress)
            response = OutputMessage(user=user, text=Messages.ENTER_EN_WORD)

        return response

    def _preprocess_user(self, session: Session, user: User) -> User:
        """Internal helper to process input user object using the model.
        Must be called when starting to process new message from a user.

        Args:
            session (Session): Session object.
            user (User): A bot user.

        Returns:
            User: User object now associated with `session`.
        """
        # See if we have this user in the model
        if existing_user := self._model.get_user(session, user.id):
            # Apply user state from the model
            user.state = existing_user.state
            # Update user info, it could change since last massage
            user = self._model.update_user(session, user)
        else:
            # User is now known
            user.state = UserState.NEW_USER
            self._model.add_user(session, user)
            self._add_default_cards(session, user)
        self._model.commit(session)
        return user

    def _add_default_cards(self, session: Session, user: User):
        """Internal helper to add default cards to a user.

        Args:
            session (Session): Session object.
            user (User): A bot user.
        """
        for ru_word, en_word in DEFAULT_CARDS:
            card = self._add_card(session, ru_word, en_word)
            user.cards.append(card)
            self._model.commit(session)

    def _add_card(
        self,
        session: Session,
        ru_word: str | RussianWord,
        en_word: str | EnglishWord,
    ) -> LearningCard:
        """Internal helper to add a new word card of use existing one.

        Args:
            session (Session): Session object.
            ru_word (str | RussianWord): Russian word object or text.
            en_word (str | EnglishWord): English word object or text.

        Returns:
            RussianWord: Word object from the model.
        """
        if not isinstance(ru_word, RussianWord):
            ru_word = self._add_ru_word(session, ru_word)
        if not isinstance(en_word, EnglishWord):
            en_word = self._add_en_word(session, en_word)
        card = LearningCard(ru_word=ru_word, en_word=en_word)
        return self._model.add_card(session, card)

    def _add_ru_word(self, session: Session, text: str) -> RussianWord:
        """Internal helper to add a new russian word of use existing one.

        Args:
            session (Session): Session object.
            text (str): Word text.

        Returns:
            RussianWord: Word object from the model.
        """
        return self._model.add_word(session, RussianWord(text=text))

    def _add_en_word(self, session: Session, text: str) -> EnglishWord:
        """Internal helper to add a new english word of use existing one.

        Args:
            session (Session): Session object.
            text (str): Word text.

        Returns:
            EnglishWord: Word object from the model.
        """
        return self._model.add_word(session, EnglishWord(text=text))

    def _delete_user(self, session: Session, user: User) -> bool:
        """Internal helper to delete user from the model.

        Args:
            session (Session): Session object.
            user (User): A bot user.

        Returns:
            bool: `True` if existing user was deleted, otherwise `False`.
        """
        deleted = self._model.delete_user(session, user.id)
        self._model.commit(session)
        return deleted is not None

    def _update_user_state(
        self,
        session: Session,
        user: User,
        state: UserState,
    ):
        """Internal helper to modify user state and reflect it in the model.

        Args:
            session (Session): Session object.
            user (User): A bot user.
            state (UserState): New user state.
        """
        user.state = state
        self._model.update_user(session, user)
        self._model.commit(session)

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
