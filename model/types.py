"""This module defines basic types that stores application data."""

import enum
from typing import List, Optional, TypeVar

from sqlalchemy import orm
import sqlalchemy as sa
from sqlalchemy.orm import Mapped


class ModelBaseType(orm.MappedAsDataclass, orm.DeclarativeBase):
    """Base class for all types used by model."""


@enum.unique
class UserState(enum.StrEnum):
    """Current state for a particular user."""
    UNKNOWN_STATE = enum.auto()
    NEW_USER = enum.auto()
    MAIN_MENU = enum.auto()
    LEARNING = enum.auto()
    ADDING_CARD = enum.auto()


user_card_association = sa.Table(
    'user_card',
    ModelBaseType.metadata,
    sa.Column(
        'user_id',
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
    ),
    sa.Column(
        'card_id',
        sa.ForeignKey('card.id', ondelete='CASCADE'),
        primary_key=True,
    ),
)


class User(ModelBaseType):
    """Represents one particular user of the bot."""

    __tablename__ = 'user'

    id: Mapped[int] = orm.mapped_column(primary_key=True)
    username: Mapped[Optional[str]] = orm.mapped_column(sa.String(32))
    first_name: Mapped[Optional[str]] = orm.mapped_column(sa.String(64))
    last_name: Mapped[Optional[str]] = orm.mapped_column(sa.String(64))
    state: Mapped = orm.mapped_column(
        sa.Enum(UserState, name='userstate', metadata=ModelBaseType.metadata),
        default=UserState.UNKNOWN_STATE,
    )

    cards: Mapped[List['LearningCard']] = orm.relationship(
        secondary=user_card_association,
        init=False,
        repr=False,
    )

    new_card_progress: Mapped[Optional['NewCardProgress']] = orm.relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        init=False,
        repr=False,
    )

    @property
    def display_name(self) -> str:
        """Returns a string representing user name suitable for output."""
        parts = [x for x in (self.first_name, self.last_name) if x]
        result = ' '.join(parts)
        return result or self.username or f'user_{self.id}'

    def __str__(self):
        return self.display_name


class BaseWord(ModelBaseType):
    """Represents a word of any language."""

    __tablename__ = 'word'
    __mapper_args__ = {'polymorphic_on': 'language'}
    __table_args__ = (sa.UniqueConstraint('text', 'language'),)

    id: Mapped[int] = orm.mapped_column(primary_key=True, init=False)
    text: Mapped[str] = orm.mapped_column(sa.String(64))
    language: Mapped[str] = orm.mapped_column(init=False)


BaseWordT = TypeVar('BaseWordT', bound=BaseWord)


class EnglishWord(BaseWord):
    """Represents an english word for a learning card."""

    __mapper_args__ = {'polymorphic_identity': 'en'}


class RussianWord(BaseWord):
    """Represents a russian word for a learning card."""

    __mapper_args__ = {'polymorphic_identity': 'ru'}


class LearningCard(ModelBaseType):
    """Represents a learning card for a user."""

    __tablename__ = 'card'
    __table_args__ = (sa.UniqueConstraint('ru_word_id', 'en_word_id'),)

    id: Mapped[int] = orm.mapped_column(primary_key=True, init=False)
    ru_word_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('word.id'),
        init=False,
    )
    en_word_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('word.id'),
        init=False,
    )

    ru_word: Mapped['RussianWord'] = orm.relationship(
        foreign_keys=[ru_word_id],
    )
    en_word: Mapped['EnglishWord'] = orm.relationship(
        foreign_keys=[en_word_id],
    )


class NewCardProgress(ModelBaseType):
    """Holds user input persistently when adding a new learning card."""

    __tablename__ = 'new_card_progress'

    user_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('user.id'),
        primary_key=True,
        init=False,
    )
    ru_word_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('word.id'),
        init=False,
    )

    user: Mapped['User'] = orm.relationship(back_populates='new_card_progress')
    ru_word: Mapped['RussianWord'] = orm.relationship()


class ModelError(Exception):
    """Base type for all model exceptions."""


class UserNotFoundError(ModelError):
    """A specified user is not currently present in the model."""
