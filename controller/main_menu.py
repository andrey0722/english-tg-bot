"""This module shows main menu to user and handles user selection in it."""

from typing import Final, Optional, override

from messages import MainMenu
from messages import Messages
from model import Session
from model.types import UserState

from .types import BotKeyboard
from .types import ControllerState
from .types import InputMessage
from .types import OutputMessage


class MainMenuState(ControllerState):
    """Shows bot main menu to user and handles user selection in that menu."""

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
        return OutputMessage(
            user=message.user,
            text=Messages.SELECT_MAIN_MENU,
            keyboard=self.KEYBOARD,
        )

    @override
    def respond(
        self,
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        text = message.text
        self._logger.info(
            'User %s selected in main menu: %s',
            message.user,
            text,
        )
        try:
            state = self.MENU_TO_STATE[MainMenu(text)]
        except (ValueError, KeyError):
            self._logger.info('Unknown main menu option: %s', text)
        else:
            return self._manager.start(session, message, state)
