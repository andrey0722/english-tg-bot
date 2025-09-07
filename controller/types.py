"""This module defines basic types for the controller operation."""

import abc
import dataclasses
from typing import List, Optional, TYPE_CHECKING

import log
from model import Model
from model import Session
from model.types import User

from .card_manager import CardManager

if TYPE_CHECKING:
    from .state_manager import StateManager


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


class ControllerState(abc.ABC):
    """Base class of the bot state. Performs all actions that are required
    when bot enters into the state and handles user replies.
    """

    def __init__(self, manager: 'StateManager'):
        """Initialize a controller state object.

        Args:
            manager (StateManager): State manager object.
        """
        super().__init__()
        self._manager = manager
        self._logger = log.create_logger(self)

    @property
    def model(self) -> Model:
        """Returns managers's model object."""
        return self._manager.model

    @property
    def card_manager(self) -> CardManager:
        """Returns managers's card manager object."""
        return self._manager.card_manager

    @abc.abstractmethod
    def start(self, session: Session, message: InputMessage) -> OutputMessage:
        """Start performing actions related to this bot state.

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            OutputMessage: Bot response to the user.
        """

    @abc.abstractmethod
    def respond(
        self,
        session: Session,
        message: InputMessage,
    ) -> Optional[OutputMessage]:
        """_summary_

        Args:
            session (Session): Session object.
            message (InputMessage): A message from user.

        Returns:
            Optional[OutputMessage]: Bot response to the user if any.
        """
