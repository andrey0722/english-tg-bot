"""This module allows user to add a new learning card for them and
handles user input.
"""

from typing import ClassVar, Optional, override

from messages import Messages
from model import Session
from model.types import BaseWord
from model.types import NewCardProgress

from .types import ControllerState
from .types import InputMessage
from .types import OutputMessage


class AddCardState(ControllerState):
    """Allows user to add a new learning card for them and handles
    user input."""

    WORD_TOO_LONG: ClassVar = Messages.WORD_TOO_LONG.format(
        BaseWord.MAX_LENGTH
    )

    @override
    def start(self, session: Session, message: InputMessage) -> OutputMessage:
        model = self.model
        model.delete_new_card_progress(session, message.user)
        model.commit(session)
        return OutputMessage(user=message.user, text=Messages.ENTER_RU_WORD)

    @override
    def respond(
        self,
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        user = message.user
        self._logger.info('User %s word input: %s', user, message.text)

        if progress := self.model.get_new_card_progress(session, user):
            self._logger.debug('Current new card progress: %r', progress)
            return self._process_second_word(session, message, progress)
        else:
            # Save user progress
            return self._process_first_word(session, message)

    def _process_first_word(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage:
        """Processes and saves first word from user.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        text = message.text
        model = self.model

        try:
            ru_word = self.card_manager.add_ru_word(session, text)
        except ValueError:
            response = self.start(session, message)
            response.add_paragraph_before(self.WORD_TOO_LONG)
            return response
        progress = NewCardProgress(user=user, ru_word=ru_word)
        model.add_new_card_progress(session, progress)
        model.commit(session)
        self._logger.debug('Saved new card progress: %r', progress)
        return OutputMessage(user, Messages.ENTER_EN_WORD)

    def _process_second_word(
        self,
        session: Session,
        message: InputMessage,
        progress: NewCardProgress,
    ) -> OutputMessage:
        """Processes and saves second word from user.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.
            progress (NewCardProgress): Progress of the operation.

        Returns:
            OutputMessage: Bot response to the user.
        """
        user = message.user
        text = message.text
        model = self.model

        self._logger.debug('Current new card progress: %r', progress)
        model.delete_new_card_progress(session, user)

        # Add new card for user
        try:
            card = self.card_manager.add_card(session, progress.ru_word, text)
        except ValueError:
            response = OutputMessage(user, Messages.ENTER_EN_WORD)
            response.add_paragraph_before(self.WORD_TOO_LONG)
            return response

        user.cards.add(card)
        model.commit(session)
        self._logger.info(
            'Added card "%s" -> "%s" for %s',
            card.ru_word.text,
            card.en_word.text,
            user,
        )
        text = Messages.ADDED_RU_EN_CARD.format(
            card.ru_word.text,
            card.en_word.text,
        )

        # Count total card count for user
        count = model.get_card_number(session, user)
        text_count = Messages.NEW_LEARNING_COUNT.format(count)

        response = self._manager.start_main_menu(session, message)
        response.add_paragraph_before(text_count)
        response.add_paragraph_before(text)
        return response
