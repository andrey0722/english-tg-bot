"""This module defines basic types that stores application data."""

import enum
from typing import Optional

from sqlalchemy import orm
import sqlalchemy as sa


class ModelBaseType(orm.DeclarativeBase):
    """Base class for all types used by model."""


@enum.unique
class UserState(enum.StrEnum):
    """Current state for a particular user."""
    UNKNOWN_STATE = enum.auto()
    NEW_USER = enum.auto()
    MAIN_MENU = enum.auto()
    LEARNING = enum.auto()


class User(orm.MappedAsDataclass, ModelBaseType):
    """Represents one particular user of the bot."""

    __tablename__ = 'user'

    id: orm.Mapped[int] = orm.mapped_column(primary_key=True)
    username: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(32))
    first_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(64))
    last_name: orm.Mapped[Optional[str]] = orm.mapped_column(sa.String(64))
    state: orm.Mapped = orm.mapped_column(
        sa.Enum(UserState, name='userstate', metadata=ModelBaseType.metadata),
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
