"""This module defines basic types that stores application data."""

import enum
from typing import ClassVar, Final, Optional, TypeVar

import sqlalchemy as sa
from sqlalchemy import orm
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
"""Junction table for User-Card many-to-many relationship."""


class User(ModelBaseType):
    """Represents one particular user of the bot."""

    __tablename__ = 'user'

    id: Mapped[int] = orm.mapped_column(primary_key=True)
    """User unique Telegram ID value."""

    username: Mapped[str | None] = orm.mapped_column(sa.String(32))
    """Username as specified in Telegram profile."""

    first_name: Mapped[str | None] = orm.mapped_column(sa.String(64))
    """User first name as specified in Telegram profile."""

    last_name: Mapped[str | None] = orm.mapped_column(sa.String(64))
    """User last name as specified in Telegram profile."""

    state: Mapped = orm.mapped_column(
        sa.Enum(UserState, name='userstate', metadata=ModelBaseType.metadata),
        default=UserState.UNKNOWN_STATE,
    )
    """Current user state."""

    cards: WriteOnlyMapped['LearningCard'] = orm.relationship(
        secondary=user_card_association,
        passive_deletes=True,
        init=False,
        repr=False,
    )
    """All learning card added to this user."""

    questions: WriteOnlyMapped['LearningQuestion'] = orm.relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True,
        init=False,
        repr=False,
    )
    """All questions for this user during learning session in progress."""

    learning_progress: Mapped[Optional['LearningProgress']] = orm.relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        init=False,
        repr=False,
    )
    """Current user statistics during current learning session."""

    new_card_progress: Mapped[Optional['NewCardProgress']] = orm.relationship(
        back_populates='user',
        cascade='all, delete-orphan',
        init=False,
        repr=False,
    )
    """Word data while user is adding a new learning card."""

    @property
    def display_name(self) -> str:
        """Returns a string representing user name suitable for output."""
        parts = [x for x in (self.first_name, self.last_name) if x]
        result = ' '.join(parts)
        return result or self.username or f'user_{self.id}'

    def __str__(self) -> str:
        """Returns a string representation of the user."""
        return self.display_name


class Language(enum.StrEnum):
    """All allowed languages for words."""
    EN = enum.auto()
    RU = enum.auto()


class BaseWord(ModelBaseType):
    """Represents a word of any language."""

    MAX_LENGTH: ClassVar[Final[int]] = 64

    __tablename__ = 'word'
    __mapper_args__ = {'polymorphic_on': 'language'}
    __table_args__ = (sa.UniqueConstraint('text', 'language'),)

    id: Mapped[int] = orm.mapped_column(primary_key=True, init=False)
    """Surrogate key field of word entity."""

    text: Mapped[str] = orm.mapped_column(sa.String(MAX_LENGTH))
    """Word text in lower case."""

    language: Mapped[str] = orm.mapped_column(
        sa.Enum(Language, name='language', metadata=ModelBaseType.metadata),
        init=False,
    )
    """Language discriminator for polymorphic ORM mapping. Should not
    be assigned directly in any way.
    """


BaseWordT = TypeVar('BaseWordT', bound=BaseWord)


class EnglishWord(BaseWord):
    """Represents an english word for a learning card."""

    __mapper_args__ = {'polymorphic_identity': Language.EN}


class RussianWord(BaseWord):
    """Represents a russian word for a learning card."""

    __mapper_args__ = {'polymorphic_identity': Language.RU}


class LearningCard(ModelBaseType):
    """Represents a learning card for a user."""

    __tablename__ = 'card'
    __table_args__ = (sa.UniqueConstraint('ru_word_id', 'en_word_id'),)

    id: Mapped[int] = orm.mapped_column(primary_key=True, init=False)
    """Surrogate key field of card entity."""

    ru_word_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('word.id', ondelete='CASCADE'),
        init=False,
        repr=False,
    )
    ru_word: Mapped['RussianWord'] = orm.relationship(
        foreign_keys=[ru_word_id],
        lazy='joined',
    )
    """The word to question user about."""

    en_word_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('word.id', ondelete='CASCADE'),
        init=False,
        repr=False,
    )
    en_word: Mapped['EnglishWord'] = orm.relationship(
        foreign_keys=[en_word_id],
        lazy='joined',
    )
    """Translation that user has to guess."""

    questions: Mapped[list['LearningQuestion']] = orm.relationship(
        back_populates='answer_card',
        cascade='all, delete-orphan',
        init=False,
        repr=False,
    )
    """All questions pending with this word."""

    distractors: Mapped[list['LearningDistractor']] = orm.relationship(
        back_populates='card',
        cascade='all, delete-orphan',
        init=False,
        repr=False,
    )
    """All distractors with questions pending with this word."""


class LearningQuestion(ModelBaseType):
    """Holds a learning question for user to answer.

    Holds a learning card pending to be completed by user in current
    learning session. Once the card is completed the question record must
    be deleted. On learning session finish all question records (if any)
    must be deleted.
    """

    CHOICE_COUNT: ClassVar[Final[int]] = 4
    """Number of choices given to a user."""

    __tablename__ = 'learning_question'
    __table_args__ = (sa.UniqueConstraint('user_id', 'order'),)

    id: Mapped[int] = orm.mapped_column(primary_key=True, init=False)
    """Surrogate key field of question entity."""

    user_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        init=False,
    )
    user: Mapped['User'] = orm.relationship(back_populates='questions')
    """Target user for the question."""

    order: Mapped[int] = orm.mapped_column()
    """Field to enforce strict sorting order."""

    answer_card_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('card.id', ondelete='CASCADE'),
        init=False,
    )
    answer_card: Mapped['LearningCard'] = orm.relationship(
        back_populates='questions',
        lazy='joined',
    )
    """Learning card that holds the question and answer words."""

    answer_position: Mapped[int] = orm.mapped_column()
    """Answer's position among the distractors."""

    distractors: Mapped[list['LearningDistractor']] = orm.relationship(
        back_populates='question',
        cascade='all, delete-orphan',
        lazy='joined',
        order_by=lambda: LearningDistractor.order,
    )
    """All distractors for this question."""


class LearningDistractor(ModelBaseType):
    """Holds wrong answer to `LearningQuestion`.

    Used to show along with the correct answer to a user
    when learning a particular learning card.
    """

    __tablename__ = 'learning_distractor'

    question_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('learning_question.id', ondelete='CASCADE'),
        primary_key=True,
        init=False,
    )
    question: Mapped['LearningQuestion'] = orm.relationship(
        back_populates='distractors',
        init=False,
    )
    """Learning question which the distractor belongs to."""

    order: Mapped[int] = orm.mapped_column()
    """Field to enforce strict sorting order."""

    card_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('card.id', ondelete='CASCADE'),
        primary_key=True,
        init=False,
    )
    card: Mapped['LearningCard'] = orm.relationship(
        back_populates='distractors',
        lazy='joined',
    )
    """Learning card where to take the word for the distractor."""


class LearningProgress(ModelBaseType):
    """Holds user statistics during a learning session."""

    __tablename__ = 'learning_progress'

    user_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
        init=False,
    )
    user: Mapped['User'] = orm.relationship(back_populates='learning_progress')
    """User that has these statistics."""

    succeeded_count: Mapped[int] = orm.mapped_column(default=0, init=False)
    """How much times did user answer correctly during learning session."""

    failed_count: Mapped[int] = orm.mapped_column(default=0, init=False)
    """How much times did user answer wrongly during learning session."""

    skipped_count: Mapped[int] = orm.mapped_column(default=0, init=False)
    """How much times did user skip words during learning session."""


class NewCardProgress(ModelBaseType):
    """Holds user input persistently when adding a new learning card."""

    __tablename__ = 'new_card_progress'

    user_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('user.id', ondelete='CASCADE'),
        primary_key=True,
        init=False,
    )
    user: Mapped['User'] = orm.relationship(back_populates='new_card_progress')
    """User that adds a new word."""

    ru_word_id: Mapped[int] = orm.mapped_column(
        sa.ForeignKey('word.id', ondelete='CASCADE'),
        init=False,
    )
    ru_word: Mapped['RussianWord'] = orm.relationship(lazy='joined')
    """The word from user input."""


class ModelError(Exception):
    """Base type for all model exceptions."""


class UserNotFoundError(ModelError):
    """A specified user is not currently present in the model."""

    def __init__(self, user: User) -> None:
        """Initialize an exception object.

        Args:
            user (User): User object.
        """
        super().__init__(f'User {user!r} does not exist')
