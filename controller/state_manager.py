"""This module controls controller state transition for users."""


from model import Model
from model import Session
from model.types import User
from model.types import UserState

from .add_card import AddCardState
from .card_manager import CardManager
from .learning import LearningState
from .main_menu import MainMenuState
from .types import ControllerState
from .types import InputMessage
from .types import OutputMessage


class StateManager:
    """Controls controller state transition for users."""

    def __init__(self, model: Model, card_mgr: CardManager) -> None:
        """Initialize state manager object.

        Args:
            model (Model): Model object.
            card_mgr (CardManager): Card manager object.
        """
        self._model = model
        self._card_mgr = card_mgr
        self._states: dict[UserState, ControllerState] = {
            UserState.MAIN_MENU: MainMenuState(self),
            UserState.LEARNING: LearningState(self),
            UserState.ADDING_CARD: AddCardState(self),
        }

    @property
    def model(self) -> Model:
        """Returns managers's model object."""
        return self._model

    @property
    def card_manager(self) -> CardManager:
        """Returns managers's card manager object."""
        return self._card_mgr

    def start(
        self,
        session: Session,
        message: InputMessage,
        state: UserState,
    ) -> OutputMessage:
        """Start a new state for user and respond to them.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.
            state (UserState): New user state.

        Returns:
            OutputMessage: Bot response to the user.
        """
        self._update_user_state(session, message.user, state)
        return self._states[state].start(session, message)

    def start_main_menu(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage:
        """Convenience method to start main menu state.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """
        return self.start(session, message, UserState.MAIN_MENU)

    def respond(
        self,
        session: Session,
        message: InputMessage,
    ) -> OutputMessage | None:
        """Respond to a user depending on user state.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
        state = message.user.state
        if state in self._states:
            return self._states[state].respond(session, message)
        return None

    def _update_user_state(
        self,
        session: Session,
        user: User,
        state: UserState,
    ) -> None:
        """Internal helper to modify user state and reflect it in the model.

        Args:
            session (Session): Session object.
            user (User): A bot user.
            state (UserState): New user state.
        """
        model = self._model
        user.state = state
        model.update_user(session, user)
        model.commit(session)
