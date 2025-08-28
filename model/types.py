"""This module defines basic types that stores application data."""


from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Represents one particular user of the bot."""

    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

    @property
    def display_name(self) -> str:
        """Returns a string representing user name suitable for output."""
        parts = [x for x in (self.first_name, self.last_name) if x]
        result = ' '.join(parts)
        return result or self.username or f'user_{self.tg_id}'


@dataclass
class InputMessage:
    """Input message data from a user to a bot."""
    user: User
    text: str


@dataclass
class OutputMessage:
    """Output message data from a bot to a user."""
    text: str


class Model:
    """Handles all application data."""
