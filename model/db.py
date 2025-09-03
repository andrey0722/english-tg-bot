"""Defines a database data model."""

import dataclasses
from typing import Callable, Optional

from sqlalchemy import exc
from sqlalchemy import orm
import sqlalchemy as sa
import sqlalchemy.log

import log
import utils

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


SessionFactory = Callable[[], orm.Session]


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

    def user_exists(self, user_id: int) -> bool:
        """Checks whether the model contains user with specified Telegram id.

        Args:
            user_id (int): User Telegram id.

        Returns:
            bool: `True` is the user exists, otherwise `False`.

        Raises:
            ModelError: Model operational error.
        """
        self._logger.debug('Checking if user %s exists', user_id)
        return self.get_user(user_id) is not None

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
        self._logger.debug('Extracting user %s', user_id)
        try:
            with self._create_session() as session:
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

    def add_user(self, user: User):
        """Adds new user into the model. Input object could be
        modified in-place to respect model changes.

        Args:
            user (User): User object.

        Raises:
            ModelError: Model operational error.
        """
        self._logger.debug('Adding user %r', user)
        try:
            with self._create_session() as session, session.begin():
                session.add(user)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Add error: user=%r, error=%s', user, e)
            raise me from e

        self._logger.debug('Added user %r', user)

    def update_user(self, user: User):
        """Updates existing user info in the model.

        Args:
            user (User): User object.

        Raises:
            UserNotFoundError: The user is not found in the model.
            ModelError: Model operational error.
        """
        self._logger.debug('Updating user %r', user)
        try:
            with self._create_session() as session, session.begin():
                if session.get(User, user.id) is None:
                    raise UserNotFoundError(f'User {user!r} does not exist')
                session.merge(user)
        except exc.SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Update error: user=%r, error=%s', user, e)
            raise me from e

        self._logger.debug('Updated user %r', user)

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

        self._logger.debug('Deleting user %r', user_id)
        try:
            with self._create_session() as session, session.begin():
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
