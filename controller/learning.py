"""This module performs a learning session for user.

Also validates user input against learning cards.
"""

import random
from typing import override

from controller.card_manager import WordTooLongError
from messages import LearningMenu
from messages import Messages
from model import Session
from model.types import LearningCard
from model.types import LearningDistractor
from model.types import LearningProgress
from model.types import LearningQuestion
from model.types import User

from .types import BotKeyboard
from .types import ControllerState
from .types import InputMessage
from .types import OutputMessage


class LearningState(ControllerState):
    """In this state user answers questions during learning session."""

    @override
    def start(self, session: Session, message: InputMessage) -> OutputMessage:
        user = message.user
        model = self.model

        model.delete_learning_question(session, user)
        self._reset_learning_progress(session, user)

        req_count = LearningQuestion.CHOICE_COUNT
        card_number = model.get_card_number(session, user)
        if card_number < req_count:
            # User doesn't have enough cards
            response = self._manager.start_main_menu(session, message)
            text = Messages.NO_LEARNING_CARDS.format(card_number, req_count)
            response.add_paragraph_before(text)
            return response

        # Prepare learning cards in random order
        cards = model.get_random_cards(session, user)
        for order, card in enumerate(cards):
            self._add_question_for_card(session, user, order, card)
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
    ) -> OutputMessage | None:
        user = message.user
        text = message.text
        model = self.model
        self._logger.info('User %s learning input: %s', user, text)

        question = model.get_next_learning_question(session, user)
        if question is None or text == LearningMenu.FINISH:
            return self._finish_learning(session, message)

        card = question.answer_card
        asked = card.ru_word.text
        answer = card.en_word.text
        cached_question = None

        if self._preprocess_word(text) == answer:
            # The card is done, delete it from learning plan
            self._logger.info('"%s" is the correct answer', text)
            model.delete_learning_question(session, user, question)
            self._increment_succeeded(session, user)
            text = Messages.CORRECT_TRANSLATION.format(asked, answer)
        elif text == LearningMenu.SKIP:
            # Skip the card
            model.delete_learning_question(session, user, question)
            self._increment_skipped(session, user)
            text = Messages.SKIPPED_TRANSLATION
        elif text == LearningMenu.DELETE:
            model.delete_learning_question(session, user, question)
            model.delete_user_card(user, card)
            text = Messages.DELETED_RU_EN_CARD.format(asked, answer)
        else:
            # Just repeat the last card
            self._logger.info('"%s" is wrong', text)
            cached_question = question
            self._increment_failed(session, user)
            text = Messages.WRONG_TRANSLATION
        model.commit(session)
        response = self._show_learning_card(session, message, cached_question)
        response.add_paragraph_before(text)
        return response

    def _preprocess_word(self, text: str) -> str:
        """Internal helper to process user input for word matching.

        Args:
            text (str): User input text.

        Returns:
            str: Preprocessed text.
        """
        try:
            return self.card_manager.preprocess_user_word(text)
        except WordTooLongError:
            # Just return the word, because we use it simply for matching
            return text

    def _show_learning_card(
        self,
        session: Session,
        message: InputMessage,
        question: LearningQuestion | None = None,
    ) -> OutputMessage:
        """Internal helper that shows next learning card to a user.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.
            question (Optional[LearningQuestion]): Learning question
                object to use. If set to `None` then extract next question
                record from the model and use it. Defaults to `None`.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        if question is None:
            question = self.model.get_next_learning_question(session, user)
        if question is not None:
            text = question.answer_card.ru_word.text
            self._logger.info('Showing "%s" to %s', text, user)
            text = Messages.SELECT_TRANSLATION.format(text)
            keyboard = self._get_keyboard(question)
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
        self.model.delete_learning_question(session, user)
        response = self._manager.start_main_menu(session, message)
        progress = self._get_learning_progress(session, user)
        text = Messages.FINISHED_LEARNING.format(
            progress.succeeded_count,
            progress.skipped_count,
            progress.failed_count,
        )
        response.add_paragraph_before(text)
        return response

    def _get_keyboard(self, question: LearningQuestion) -> BotKeyboard:
        """Internal helper to construct bot keyboard for learning card.

        Args:
            question (LearningQuestion): Learning question object.

        Returns:
            BotKeyboard: Bot keyboard object.
        """
        # Prepare possible answers
        cards = [distractor.card for distractor in question.distractors]
        cards.insert(question.answer_position, question.answer_card)
        # Prepare other buttons too
        buttons = [card.en_word.text for card in cards]
        buttons.extend(LearningMenu.__members__.values())
        return BotKeyboard(row_size=2, buttons=buttons)

    def _reset_learning_progress(self, session: Session, user: User) -> None:
        """Internal helper that resets learning progress for user to zero.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = LearningProgress(user=user)
        self.model.update_learning_progress(session, progress)

    def _increment_succeeded(self, session: Session, user: User) -> None:
        """Internal helper that increments the success count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.succeeded_count += 1
        self.model.update_learning_progress(session, progress)

    def _increment_failed(self, session: Session, user: User) -> None:
        """Internal helper that increments the fail count for user.

        Args:
            session (Session): Session object.
            user (User): User object.
        """
        progress = self._get_learning_progress(session, user)
        progress.failed_count += 1
        self.model.update_learning_progress(session, progress)

    def _increment_skipped(self, session: Session, user: User) -> None:
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

    def _add_question_for_card(
        self,
        session: Session,
        user: User,
        order: int,
        card: LearningCard,
    ) -> None:
        """Internal helper that creates and stores new question record.

        Creates a new question record for a particular with the given card.
        Distractors are also prepared in advance.

        Args:
            session (Session): Session object.
            user (User): User object.
            order (int): Positional index of this card in learning session.
            card (LearningCard): Learning card object.
        """
        # Randomize answer location
        answer_position = random.randrange(LearningQuestion.CHOICE_COUNT)
        distractors = self._get_distractors_for_card(session, user, card)
        question = LearningQuestion(
            order=order,
            user=user,
            answer_card=card,
            distractors=distractors,
            answer_position=answer_position,
        )
        self.model.add_learning_question(session, question)

    def _get_distractors_for_card(
        self,
        session: Session,
        user: User,
        card: LearningCard,
    ) -> list[LearningDistractor]:
        """Internal helper that collects list of random distractors.

        Collects a list of random distractors for user to select from
        when studying a learning.

        Args:
            session (Session): Session object.
            user (User): User object.
            card (LearningCard): Learning card object.

        Returns:
            List[LearningDistractor]: Distractors for the learning card.
        """
        # Put correct answer first to exclude the same words
        choices: dict[str, LearningCard] = {card.en_word.text: card}
        # Look for the rest unique choices
        while len(choices) < LearningQuestion.CHOICE_COUNT:
            choice = self.model.get_random_card(session, user)
            if choice and choice.en_word.text not in choices:
                choices[choice.en_word.text] = choice
        # Delete the original answer, keep only wrong ones
        del choices[card.en_word.text]
        return [LearningDistractor(*x) for x in enumerate(choices.values())]
