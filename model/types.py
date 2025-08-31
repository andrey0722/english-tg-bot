"""This module defines basic types that stores application data."""

import abc
import enum
from typing import Optional

from sqlalchemy import String, Enum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column


class ModelBaseType(DeclarativeBase):
    """Base class for all types used by model."""


@enum.unique
class UserState(enum.StrEnum):
    """Current state for a particular user."""
    UNKNOWN_STATE = enum.auto()
    NEW_USER = enum.auto()
    MAIN_MENU = enum.auto()
    LEARNING = enum.auto()


class User(MappedAsDataclass, ModelBaseType):
    """Represents one particular user of the bot."""

    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String(32))
    first_name: Mapped[Optional[str]] = mapped_column(String(64))
    last_name: Mapped[Optional[str]] = mapped_column(String(64))
    state: Mapped = mapped_column(
        Enum(UserState, name='userstate', metadata=ModelBaseType.metadata),
        default=UserState.UNKNOWN_STATE,
    )

    @property
    def display_name(self) -> str:
        """Returns a string representing user name suitable for output."""
        parts = [x for x in (self.first_name, self.last_name) if x]
        result = ' '.join(parts)
        return result or self.username or f'user_{self.id}'

    def __str__(self):
        return self.display_name


class ModelError(Exception):
    """Base type for all model exceptions."""


class UserNotFoundError(ModelError):
    """A specified user is not currently present in the model."""


class Model(abc.ABC):
    """Handles all application data."""

    @abc.abstractmethod
    def user_exists(self, user_id: int) -> bool:
        """Checks whether the model contains user with specified Telegram id.

        Args:
            user_id (int): User Telegram id.

        Returns:
            bool: `True` is the user exists, otherwise `False`.

        Raises:
            ModelError: Model operational error.
        """

    @abc.abstractmethod
    def get_user(self, user_id: int) -> Optional[User]:
        """Extracts a user from the model using user Telegram id.

        Args:
            user_id (int): User Telegram id.

        Returns:
            Optional[User]: Found user object for this Telegram id if any,
                otherwise `None`.

        Raises:
            ModelError: Model operational error.
        """

    @abc.abstractmethod
    def add_user(self, user: User):
        """Adds new user into the model. Input object could be
        modified in-place to respect model changes.

        Args:
            user (User): User object.

        Raises:
            ModelError: Model operational error.
        """

    @abc.abstractmethod
    def update_user(self, user: User):
        """Updates existing user info in the model.

        Args:
            user (User): User object.

        Raises:
            UserNotFoundError: The user is not found in the model.
            ModelError: Model operational error.
        """

    @abc.abstractmethod
    def delete_user(self, user_id: int) -> Optional[User]:
        """Deletes user from the model.

        Args:
            user_id (int): User Telegram id.

        Returns:
            Optional[User]: User object previously stored in the model,
                if any, otherwise `None`.

        Raises:
            ModelError: Model operational error.
        """
