"""Defines a database data model."""

import dataclasses
from typing import Callable, Iterable, Optional

from sqlalchemy import exc
from sqlalchemy import orm
import sqlalchemy as sa
import sqlalchemy.log
from sqlalchemy.sql import functions as func

import log
import utils

from .types import AddWordProgress
from .types import BaseWord
from .types import BaseWordT
from .types import LearningCard
from .types import ModelBaseType
from .types import ModelError
from .types import User
from .types import UserNotFoundError


@dataclasses.dataclass
class DatabaseConfig:
    """Parameters required to establish DB connection."""
    driver: str
    host: str
    port: int
    database: str
    user: str
    password: str
    clear_data: bool


Session = orm.Session
SessionFactory = Callable[[], Session]


class DatabaseModelError(ModelError):
    """Error while interacting with database."""


class DatabaseModel:
    """Stores data in database persistently."""

    def __init__(self, db_params: DatabaseConfig):
        """Initialize database model object.

        Args:
            db_params (DatabaseConfig): DB connection parameters.
            clear_db (bool): Delete all model data that previously exists.

        Raises:
            ModelError: Model creation error.
        """
        super().__init__()
        self._set_sqlalchemy_logger()
        self._logger = log.create_logger(self)
        self._engine = self._create_engine(db_params)
        self._create_session = self._create_session_factory()
        self._test_db_connection()
        if db_params.clear_data:
            self._drop_tables()
        self._create_tables()
        self._set_engine_logger(self._engine)

    def create_session(self) -> Session:
        """Create session to interact with objects in the model.

        Returns:
            Session: Session object.
        """
        return self._create_session()

    def commit(self, session: Session):
        """Saves pending changes into the model.

        Args:
            session (Session): Session object.

        Raises:
            ModelError: Model operational error.
        """
        try:
            session.commit()
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Commit error: %s', e)
            raise me from e

    def user_exists(self, session: Session, user_id: int) -> bool:
        """Checks whether the model contains user with specified Telegram id.

        Args:
            session (Session): Session object.
            user_id (int): User Telegram id.

        Returns:
            bool: `True` is the user exists, otherwise `False`.

        Raises:
            ModelError: Model operational error.
        """
        self._logger.debug('Checking if user %s exists', user_id)
        return self.get_user(session, user_id) is not None

    def get_user(self, session: Session, user_id: int) -> Optional[User]:
        """Extracts a user from the model using user Telegram id.

        Args:
            session (Session): Session object.
            user_id (int): User Telegram id.

        Returns:
            Optional[User]: Found user object for this Telegram id if any,
                otherwise `None`.

        Raises:
            ModelError: Model operational error.
        """
        self._logger.debug('Extracting user %s', user_id)
        try:
            user = session.get(User, user_id)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Get error: user=%r, error=%s', user_id, e)
            raise me from e

        if user is not None:
            self._logger.debug('User exists: %r', user)
        else:
            self._logger.debug('User %s does not exist', user_id)
        return user

    def add_user(self, session: Session, user: User):
        """Adds new user into the model. Input object could be
        modified in-place to respect current model state.

        Args:
            session (Session): Session object.
            user (User): User object.

        Raises:
            ModelError: Model operational error.
        """
        self._logger.debug('Adding user %r', user)
        try:
            session.add(user)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Add error: user=%r, error=%s', user, e)
            raise me from e

        self._logger.debug('Added user %r', user)

    def update_user(self, session: Session, user: User) -> User:
        """Updates existing user info in the model.

        Args:
            session (Session): Session object.
            user (User): User object.

        Returns:
            User: User object now associated with `session`.

        Raises:
            UserNotFoundError: The user is not found in the model.
            ModelError: Model operational error.
        """
        self._logger.debug('Updating user %r', user)
        try:
            if session.get(User, user.id) is None:
                raise UserNotFoundError(f'User {user!r} does not exist')
            result = session.merge(user)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Update error: user=%r, error=%s', user, e)
            raise me from e

        self._logger.debug('Updated user %r', result)
        return result

    def delete_user(self, session: Session, user_id: int) -> Optional[User]:
        """Deletes user from the model.

        Args:
            session (Session): Session object.
            user_id (int): User Telegram id.

        Returns:
            Optional[User]: User object previously stored in the model,
                if any, otherwise `None`.

        Raises:
            ModelError: Model operational error.
        """

        self._logger.debug('Deleting user %r', user_id)
        try:
            stmt = sa.delete(User).where(User.id == user_id).returning(User)
            user = session.scalar(stmt)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Delete error: user=%r, error=%s', user_id, e)
            raise me from e

        if user is not None:
            self._logger.debug('User deleted %r', user)
        else:
            self._logger.warning('No user %s, cannot delete', user_id)
        return user

    def add_word(self, session: Session, word: BaseWordT) -> BaseWordT:
        """Adds new word into the model or extracts an existing one. Input
        object could be modified in-place to respect current model state.

        Args:
            session (Session): Session object.
            word (BaseWordT): Word object.

        Returns:
            BaseWordT: Word object now associated with `session`.

        Raises:
            ModelError: Model operational error.
        """
        self._logger.debug('Adding word %r', word)
        try:
            # Extract existing word if any
            stmt = sa.select(BaseWord).where(
                BaseWord.text == word.text,
                BaseWord.language == word.language,
            )
            if existing := session.scalar(stmt):
                self._logger.debug('Word exists: %r', word)
                # Update input object with data from DB
                word.id = existing.id
                return session.merge(word)
            else:
                # Word doesn't exist, create it
                session.add(word)
                self._logger.debug('Added word %r', word)
                return word
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Add error: word=%r, error=%s', word, e)
            raise me from e

    def add_card(self, session: Session, card: LearningCard) -> LearningCard:
        """Adds new card into the model or extracts an existing one. Input
        object could be modified in-place to respect current model state.

        Args:
            session (Session): Session object.
            card (LearningCard): Card object.

        Returns:
            LearningCard: Card object now associated with `session`.

        Raises:
            ModelError: Model operational error.
        """
        self._logger.debug('Adding card %r', card)
        try:
            # Extract existing card if any
            stmt = sa.select(LearningCard).where(
                LearningCard.ru_word_id == card.ru_word.id,
                LearningCard.en_word_id == card.en_word.id,
            )
            if existing := session.scalar(stmt):
                self._logger.debug('Card exists: %r', card)
                # Update input object with data from DB
                card.id = existing.id
                card.ru_word_id = existing.ru_word_id
                card.en_word_id = existing.en_word_id
                return session.merge(card)
            else:
                # Card doesn't exist, create it
                session.add(card)
                self._logger.debug('Added card %r', card)
                return card
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Add error: card=%r, error=%s', card, e)
            raise me from e

    def get_cards(
        self,
        session: Session,
        user: User,
    ) -> Iterable[LearningCard]:
        """Extracts a list of all learning cards for a user.

        Args:
            session (Session): Session object.
            user (User): User object.

        Returns:
            Iterable[LearningCard]: Learning cards for the user.
        """
        self._logger.debug('Extracting cards for %r', user)
        try:
            # Get card number first
            stmt = (
                sa.select(func.count())
                .join(User.cards)
                .where(User.id == user.id)
            )
            count = session.scalar(stmt) or 0

            # Now extract user cards in batches
            stmt = (
                sa.select(LearningCard)
                .join(User.cards)
                .where(User.id == user.id)
                .options(
                    orm.joinedload(LearningCard.ru_word),
                    orm.joinedload(LearningCard.en_word),
                )
                .execution_options(yield_per=20)
            )
            cards = session.scalars(stmt)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Get cards error: user=%r, error=%s', user, e)
            raise me from e

        self._logger.debug('Extracted %d cards for %r', count, user)
        return cards

    def get_add_word_progress(
        self,
        session: Session,
        user: User,
    ) -> Optional[AddWordProgress]:
        """For given user return theirs add word progress.

        Args:
            session (Session): Session object.
            user (User): User object.

        Returns:
            Optional[AddWordProgress]: Add word progress if any.
        """
        self._logger.debug('Extracting add word progress for %r', user)
        try:
            stmt = (
                sa.select(AddWordProgress)
                .where(AddWordProgress.user_id == user.id)
                .options(orm.joinedload(AddWordProgress.ru_word))
            )
            progress = session.scalar(stmt)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug(
                'Get add progress error: user=%r, error=%s',
                user,
                e,
            )
            raise me from e

        self._logger.debug('Extracted: %r', progress)
        return progress

    def _create_tables(self):
        """Internal helper to create tables for all entities in the DB."""
        try:
            self._logger.debug('Creating tables')
            ModelBaseType.metadata.create_all(self._engine)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Create tables error: %s', e)
            raise me from e

    def _drop_tables(self):
        """Internal helper to delete tables for all entities in the DB."""
        try:
            self._logger.debug('Deleting tables')
            ModelBaseType.metadata.drop_all(self._engine)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Delete tables error: %s', e)
            raise me from e

    def _create_dsn(self, params: DatabaseConfig) -> sa.URL:
        """Internal helper to form and return a DSN from `DatabaseConfig`.

        Args:
            params (DatabaseConfig): DB connection parameters.
        """
        return sa.URL.create(
            drivername=params.driver,
            host=params.host,
            port=params.port,
            database=params.database,
            username=params.user,
            password=params.password,
        )

    def _create_engine(self, params: DatabaseConfig) -> sa.Engine:
        """Internal helper to create and return DB engine object.

        Args:
            params (DatabaseConfig): DB connection parameters.
        """
        engine = sa.create_engine(self._create_dsn(params), echo='debug')
        self._set_engine_logger(engine)
        return engine

    def _set_engine_logger(self, engine: sa.Engine):
        """Internal helper to monkey patch engine logger.

        Args:
            engine (sa.Engine): Engine object.
        """
        logger = engine.logger
        if isinstance(logger, sqlalchemy.log.InstanceLogger):
            # Handle engine's internal wrappers for logger
            logger = logger.logger
        logger = log.create_logger(logger.name)
        # Avoid flooding with 'INFO' log level
        logger.addFilter(log.LogLevelLimitFilter(logger, log.LogLevel.DEBUG))
        engine.logger = logger

    def _create_session_factory(self) -> SessionFactory:
        """Internal helper to create and return DB session factory
        which creates session objects to perform DB operations.
        """
        return orm.sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
        )

    def _test_db_connection(self):
        """Internal helper to create a test connection to the DB.

        Raises:
            DatabaseModelError: Failed to connect to DB.
        """
        try:
            with self._engine.connect():
                self._logger.debug('DB connection is OK')
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('DB connection error: %s', e)
            raise me from e

    @staticmethod
    def _create_model_error(e: exc.SQLAlchemyError) -> DatabaseModelError:
        """Internal helper to create model exception from underlying library.

        Args:
            e (SQLAlchemyError): Underlying library exception.
        """
        # Monkey patch the exception to avoid messages like this:
        # Background on this error at: https://sqlalche.me/e/XX/YYYY
        e.code = None
        return DatabaseModelError(e)

    @staticmethod
    @utils.call_once
    def _set_sqlalchemy_logger():
        """Override logger of the `sqlalchemy` library."""
        sqlalchemy.log.rootlogger = log.create_logger(
            sqlalchemy.log.rootlogger.name
        )
