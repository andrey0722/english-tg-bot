"""This module defines basic types that stores application data."""

import enum
from typing import ClassVar, Final, List, Optional, TypeVar

from sqlalchemy import orm
import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import WriteOnlyMapped


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

    cards: WriteOnlyMapped['LearningCard'] = orm.relationship(
        secondary=user_card_association,
        init=False,
        repr=False,
    )

    learning_plan: WriteOnlyMapped['LearningPlan'] = orm.relationship(
        back_populates='user',
        cascade='all, delete-orphan',
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
        repr=False,
    )
    en_word_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('word.id'),
        init=False,
        repr=False,
    )

    ru_word: Mapped['RussianWord'] = orm.relationship(
        foreign_keys=[ru_word_id],
        lazy='joined',
    )
    en_word: Mapped['EnglishWord'] = orm.relationship(
        foreign_keys=[en_word_id],
        lazy='joined',
    )


class LearningPlan(ModelBaseType):
    """Holds a learning card pending to be completed by user in current
    learning session. Once the card is completed the plan record must
    be deleted. On learning session finish all plan records (if any)
    must be deleted.
    """

    __tablename__ = 'learning_plan'

    id: Mapped[int] = orm.mapped_column(primary_key=True, init=False)
    user_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('user.id'),
        init=False,
    )
    card_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('card.id'),
        init=False,
    )
    answer_position: Mapped[int] = orm.mapped_column()

    user: Mapped['User'] = orm.relationship(back_populates='learning_plan')
    card: Mapped['LearningCard'] = orm.relationship(lazy='joined')
    options: Mapped[List['LearningOption']] = orm.relationship(
        back_populates='plan',
        cascade='all, delete-orphan',
        lazy='joined',
    )

    OPTIONS_COUNT: ClassVar[Final[int]] = 3
    """Number of additional options besides the actual card."""


class LearningOption(ModelBaseType):
    """Holds options to show to a user when learning a particular
    learning card.
    """

    __tablename__ = 'learning_option'

    plan_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('learning_plan.id'),
        primary_key=True,
        init=False,
    )
    card_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('card.id'),
        primary_key=True,
        init=False,
    )

    plan: Mapped['LearningPlan'] = orm.relationship(
        back_populates='options',
        init=False,
    )
    card: Mapped['LearningCard'] = orm.relationship()


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
