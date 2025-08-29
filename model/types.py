"""This module defines basic types that stores application data."""


import abc
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

    def __str__(self):
        return self.display_name


@dataclass
class InputMessage:
    """Input message data from a user to a bot."""
    user: User
    text: str


@dataclass
class OutputMessage:
    """Output message data from a bot to a user."""
    user: User
    text: str


class Model(abc.ABC):
    """Handles all application data."""

    @abc.abstractmethod
    def get_user(self, user: User) -> Optional[User]:
        """Extracts a user from the model using user Telegram id.

        Args:
            user (User): User object.

        Returns:
            Optional[User]: Found user object for this Telegram id if any,
                otherwise `None`.
        """

    @abc.abstractmethod
    def add_user(self, user: User) -> User:
        """Adds new user into the model.

        Args:
            user (User): User object.

        Returns:
            User: User object currently in the model.
        """

    @abc.abstractmethod
    def update_user(self, user: User) -> Optional[User]:
        """Updates existing user data in the model.

        Args:
            user (User): User object.

        Returns:
            User: Updated user object currently in the model, if exists,
                otherwise `None`.
        """

    @abc.abstractmethod
    def delete_user(self, user: User) -> Optional[User]:
        """Deletes user from the model.

        Args:
            user (User): User object.

        Returns:
            Optional[User]: User object previously stored in the model,
                if any, otherwise `None`.
        """
