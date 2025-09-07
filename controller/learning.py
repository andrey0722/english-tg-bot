"""This module shows main menu to user and handles user selection in it."""

import random
from typing import Final, List, Optional, override

from messages import LearningMenu
from messages import MainMenu
from messages import Messages
from model import Session
from model.types import LearningCard
from model.types import LearningOption
from model.types import LearningPlan
from model.types import LearningProgress
from model.types import User
from model.types import UserState

from .types import BotKeyboard
from .types import ControllerState
from .types import InputMessage
from .types import OutputMessage


class LearningState(ControllerState):
    """Performs a learning session for user and validates user input
    against learning cards."""

    MENU_TO_STATE: Final = {
        MainMenu.LEARN: UserState.LEARNING,
        MainMenu.ADD_CARD: UserState.ADDING_CARD,
    }

    KEYBOARD: Final = BotKeyboard(
        row_size=1,
        buttons=list(MainMenu.__members__.values()),
    )

    @override
    def start(self, session: Session, message: InputMessage) -> OutputMessage:
        user = message.user
        model = self.model

        model.delete_learning_plan(session, user)
        self._reset_learning_progress(session, user)

        req_count = LearningPlan.OPTIONS_COUNT + 1
        card_number = model.get_card_number(session, user)
        if card_number < req_count:
            # User doesn't have enough cards
            response = self._manager.start_main_menu(session, message)
            text = Messages.NO_LEARNING_CARDS.format(card_number, req_count)
            response.add_paragraph_before(text)
            return response

        # Prepare learning cards in random order
        cards = model.get_random_cards(session, user)
        for index, card in enumerate(cards):
            self._add_plan_for_card(session, user, index, card)
        model.commit(session)

        # Show the first card
        response = self._show_learning_card(session, message)
        text = Messages.PLAN_LEARNING_COUNT.format(card_number)
        response.add_paragraph_before(text)
        return response

    @override
    def respond(
        self,
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        user = message.user
        text = message.text
        model = self.model
        card_mgr = self.card_manager
        self._logger.info('User %s learning input: %s', user, text)

        plan = model.get_next_learning_plan(session, user)
        if plan is None or text == LearningMenu.FINISH:
            return self._finish_learning(session, message)

        card = plan.card
        question = card.ru_word.text
        answer = card.en_word.text
        new_plan = None

        if card_mgr.preprocess_user_word(text) == answer:
            # The card is done, delete it from learning plan
            self._logger.info('"%s" is the correct answer', text)
            model.delete_learning_plan(session, user, plan)
            self._increment_succeeded(session, user)
            text = Messages.CORRECT_TRANSLATION.format(question, answer)
        elif text == LearningMenu.SKIP:
            # Skip the card
            model.delete_learning_plan(session, user, plan)
            self._increment_skipped(session, user)
            text = Messages.SKIPPED_TRANSLATION
        elif text == LearningMenu.DELETE:
            model.delete_learning_plan(session, user, plan)
            model.delete_user_card(user, card)
            text = Messages.DELETED_RU_EN_CARD.format(question, answer)
        else:
            # Just repeat the last card
            self._logger.info('"%s" is wrong', text)
            new_plan = plan
            self._increment_failed(session, user)
            text = Messages.WRONG_TRANSLATION
        model.commit(session)
        response = self._show_learning_card(session, message, new_plan)
        response.add_paragraph_before(text)
        return response

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
            plan = self.model.get_next_learning_plan(session, user)
        if plan is not None:
            text = plan.card.ru_word.text
            self._logger.info('Showing "%s" to %s', text, user)
            text = Messages.SELECT_TRANSLATION.format(text)
            keyboard = self._get_keyboard(plan)
            response = OutputMessage(user=user, text=text, keyboard=keyboard)
        else:
            # No more cards in learning plan, learning is done
            response = self._finish_learning(session, message)
        return response

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
        self._logger.info('User %s finished learning', user)
        self.model.delete_learning_plan(session, user)
        response = self._manager.start_main_menu(session, message)
        progress = self._get_learning_progress(session, user)
        text = Messages.FINISHED_LEARNING.format(
            progress.succeeded_count,
            progress.skipped_count,
            progress.failed_count,
        )
        response.add_paragraph_before(text)
        return response

    def _get_keyboard(self, plan: LearningPlan) -> BotKeyboard:
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

    def _reset_learning_progress(self, session: Session, user: User):
        """Internal helper that resets learning progress for user to zero.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = LearningProgress(user=user)
        self.model.update_learning_progress(session, progress)

    def _increment_succeeded(self, session: Session, user: User):
        """Internal helper that increments the success count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.succeeded_count += 1
        self.model.update_learning_progress(session, progress)

    def _increment_failed(self, session: Session, user: User):
        """Internal helper that increments the fail count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.failed_count += 1
        self.model.update_learning_progress(session, progress)

    def _increment_skipped(self, session: Session, user: User):
        """Internal helper that increments the fail count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.skipped_count += 1
        self.model.update_learning_progress(session, progress)

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
        progress = self.model.get_learning_progress(session, user)
        if progress is None:
            progress = LearningProgress(user=user)
        return progress

    def _add_plan_for_card(
        self,
        session: Session,
        user: User,
        index: int,
        card: LearningCard,
    ):
        """Internal helper that creates and stores new plan record for
        a particular learning card with all the options for user to select.

        Args:
            session (Session): Session object.
            user (User): User object.
            index (int): Positional index of this card in learning session.
            card (LearningCard): Learning card object.
        """
        # Randomize answer location
        answer_position = random.randrange(LearningPlan.OPTIONS_COUNT + 1)
        options = self._get_options_for_card(session, user, card)
        plan = LearningPlan(
            index=index,
            user=user,
            card=card,
            options=options,
            answer_position=answer_position,
        )
        self.model.add_learning_plan(session, plan)

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
            option = self.model.get_random_card(session, user)
            if option and option.en_word.text not in options:
                options[option.en_word.text] = option
        # Delete the original answer, keep only wrong ones
        del options[card.en_word.text]
        return list(map(LearningOption, options.values()))
