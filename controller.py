"""This module implements main logic of the bot."""

import dataclasses
import random
from typing import List, Optional

from default_cards import DEFAULT_CARDS
import log
from messages import LearningMenu
from messages import MainMenu
from messages import Messages
from model import Model
from model import Session
from model.types import EnglishWord
from model.types import LearningCard
from model.types import LearningOption
from model.types import LearningPlan
from model.types import LearningProgress
from model.types import ModelError
from model.types import NewCardProgress
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
                    case UserState.ADDING_CARD:
                        return self._respond_new_card(session, message)
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
            case MainMenu.ADD_CARD:
                return self._start_new_card(session, message)
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
        self._model.delete_learning_plan(session, user)
        self._reset_learning_progress(session, user)

        req_count = LearningPlan.OPTIONS_COUNT + 1
        card_number = self._model.get_card_number(session, user)
        if card_number < req_count:
            # User doesn't have enough cards
            response = self._start_main_menu(session, message)
            text = Messages.NO_LEARNING_CARDS.format(card_number, req_count)
            response.add_paragraph_before(text)
            return response

        text = Messages.PLAN_LEARNING_COUNT.format(card_number)
        self._update_user_state(session, user, UserState.LEARNING)

        # Prepare learning cards in random order
        for card in self._model.get_random_cards(session, user):
            self._add_plan_for_card(session, user, card)
        self._model.commit(session)

        # Show the first card
        response = self._show_learning_card(session, message)
        response.add_paragraph_before(text)
        return response

    def _add_plan_for_card(
        self,
        session: Session,
        user: User,
        card: LearningCard,
    ):
        """Internal helper that creates and stores new plan record for
        a particular learning card with all the options for user to select.

        Args:
            session (Session): Session object.
            user (User): User object.
            card (LearningCard): Learning card object.
        """
        # Randomize answer location
        position = random.randrange(LearningPlan.OPTIONS_COUNT + 1)
        options = self._get_options_for_card(session, user, card)
        plan = LearningPlan(
            user=user,
            card=card,
            options=options,
            answer_position=position,
        )
        self._model.add_learning_plan(session, plan)

    def _get_options_for_card(
        self,
        session: Session,
        user: User,
        card: LearningCard,
    ) -> List[LearningOption]:
        """Internal helper that collects a list of random options for user
        to respond to when studying a learning.

        Args:
            session (Session): Session object.
            user (User): User object.
            card (LearningCard): Learning card object.

        Returns:
            List[LearningOption]: Options for the learning card.
        """
        # Put correct answer first to exclude the same words
        options: dict[str, LearningCard] = {card.en_word.text: card}
        # Look for the rest unique options
        while len(options) <= LearningPlan.OPTIONS_COUNT:
            option = self._model.get_random_card(session, user)
            if option and option.en_word.text not in options:
                options[option.en_word.text] = option
        # Delete the original answer, keep only wrong ones
        del options[card.en_word.text]
        return list(map(LearningOption, options.values()))

    def _show_learning_card(
        self,
        session: Session,
        message: InputMessage,
        plan: Optional[LearningPlan] = None,
    ) -> OutputMessage:
        """Internal helper that shows next learning card to a user.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.
            plan (Optional[LearningPlan]): Learning plan object to use. If
                set to `None` then extract next plan record from the model
                and use it. Defaults to `None`.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        if plan is None:
            plan = self._model.get_next_learning_plan(session, user)
        if plan is not None:
            text = Messages.SELECT_TRANSLATION.format(plan.card.ru_word.text)
            keyboard = self._get_learning_keyboard(plan)
            response = OutputMessage(user=user, text=text, keyboard=keyboard)
        else:
            # No more cards in learning plan, learning is done
            response = self._finish_learning(session, message)
        return response

    def _get_learning_keyboard(self, plan: LearningPlan) -> BotKeyboard:
        """Internal helper to construct bot keyboard for learning card.

        Args:
            plan (LearningPlan): Learning plan object.

        Returns:
            BotKeyboard: Bot keyboard object.
        """
        # Prepare possible answers
        cards = [option.card for option in plan.options]
        cards.insert(plan.answer_position, plan.card)
        # Prepare other buttons too
        buttons = [card.en_word.text for card in cards]
        buttons.extend(LearningMenu.__members__.values())
        return BotKeyboard(row_size=2, buttons=buttons)

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
        user = message.user
        text = message.text
        self._logger.info('User %s learning input: %s', user, text)

        plan = self._model.get_next_learning_plan(session, user)
        if plan is None or text == LearningMenu.FINISH:
            return self._finish_learning(session, message)

        card = plan.card
        question = card.ru_word.text
        answer = card.en_word.text
        new_plan = None

        if text == answer:
            # The card is done, delete it from learning plan
            self._model.delete_learning_plan(session, user, plan)
            self._increment_succeeded(session, user)
            text = Messages.CORRECT_TRANSLATION.format(question, answer)
        elif text == LearningMenu.SKIP:
            # Skip the card
            self._model.delete_learning_plan(session, user, plan)
            self._increment_skipped(session, user)
            text = Messages.SKIPPED_TRANSLATION
        elif text == LearningMenu.DELETE:
            self._model.delete_learning_plan(session, user, plan)
            self._model.delete_user_card(user, card)
            text = Messages.DELETED_RU_EN_CARD.format(question, answer)
        else:
            # Just repeat the last card
            new_plan = plan
            self._increment_failed(session, user)
            text = Messages.WRONG_TRANSLATION
        self._model.commit(session)
        response = self._show_learning_card(session, message, new_plan)
        response.add_paragraph_before(text)
        return response

    def _get_learning_progress(
        self,
        session: Session,
        user: User,
    ) -> LearningProgress:
        """Internal helper that retrieves learning progress for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._model.get_learning_progress(session, user)
        if progress is None:
            progress = LearningProgress(user=user)
        return progress

    def _increment_succeeded(self, session: Session, user: User):
        """Internal helper that increments the success count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.succeeded_count += 1
        self._model.update_learning_progress(session, progress)

    def _increment_failed(self, session: Session, user: User):
        """Internal helper that increments the fail count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.failed_count += 1
        self._model.update_learning_progress(session, progress)

    def _increment_skipped(self, session: Session, user: User):
        """Internal helper that increments the fail count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.skipped_count += 1
        self._model.update_learning_progress(session, progress)

    def _reset_learning_progress(self, session: Session, user: User):
        """Internal helper that resets learning progress for user to zero.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = LearningProgress(user=user)
        self._model.update_learning_progress(session, progress)

    def _finish_learning(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage:
        """Internal helper that stops learning process and skips to main menu.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._model.delete_learning_plan(session, user)
        response = self._start_main_menu(session, message)
        progress = self._get_learning_progress(session, user)
        text = Messages.FINISHED_LEARNING.format(
            progress.succeeded_count,
            progress.skipped_count,
            progress.failed_count,
        )
        response.add_paragraph_before(text)
        return response

    def _start_new_card(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage:
        """Internal helper that starts add new learning card procedure.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        self._update_user_state(session, user, UserState.ADDING_CARD)
        return OutputMessage(user=user, text=Messages.ENTER_RU_WORD)

    def _respond_new_card(
        self,
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """Internal helper that checks and processes user input when adding
        new learning card.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        user = message.user
        text = message.text
        self._logger.info('User %s word input: %s', user, text)

        if progress := self._model.get_new_card_progress(session, user):
            self._logger.debug('Current new card progress: %r', progress)
            self._model.delete_new_card_progress(session, user)

            # Add new card for user
            card = self._add_card(session, progress.ru_word, text)
            user.cards.add(card)
            self._model.commit(session)
            text = Messages.ADDED_RU_EN_CARD.format(
                card.ru_word.text,
                card.en_word.text,
            )

            # Count total card count for user
            count = self._model.get_card_number(session, user)
            text_count = Messages.NEW_LEARNING_COUNT.format(count)

            response = self._start_main_menu(session, message)
            response.add_paragraph_before(text_count)
            response.add_paragraph_before(text)
        else:
            # Save user progress
            ru_word = self._model.add_word(session, RussianWord(text=text))
            progress = NewCardProgress(user=user, ru_word=ru_word)
            self._model.add_new_card_progress(session, progress)
            self._model.commit(session)
            self._logger.debug('Saved new card progress: %r', progress)
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
            user.cards.add(card)
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
