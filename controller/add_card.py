"""This module allows user to add a new learning card for them and
handles user input.
"""

from typing import Optional, override

from messages import Messages
from model import Session
from model.types import NewCardProgress

from .types import ControllerState
from .types import InputMessage
from .types import OutputMessage


class AddCardState(ControllerState):
    """Allows user to add a new learning card for them and handles
    user input."""

    @override
    def start(self, session: Session, message: InputMessage) -> OutputMessage:
        return OutputMessage(user=message.user, text=Messages.ENTER_RU_WORD)

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
        self._logger.info('User %s word input: %s', user, text)

        if progress := model.get_new_card_progress(session, user):
            self._logger.debug('Current new card progress: %r', progress)
            model.delete_new_card_progress(session, user)

            # Add new card for user
            card = card_mgr.add_card(session, progress.ru_word, text)
            user.cards.add(card)
            model.commit(session)
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
        else:
            # Save user progress
            ru_word = card_mgr.add_ru_word(session, text)
            progress = NewCardProgress(user=user, ru_word=ru_word)
            model.add_new_card_progress(session, progress)
            model.commit(session)
            self._logger.debug('Saved new card progress: %r', progress)
            response = OutputMessage(user=user, text=Messages.ENTER_EN_WORD)

        return response
