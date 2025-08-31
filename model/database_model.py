"""Defines a database data model."""

from collections.abc import Callable
import dataclasses
from typing import Optional, override

from sqlalchemy import create_engine, delete, Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.log import InstanceLogger
from sqlalchemy.orm import Session, sessionmaker

from log import LogLevel, LogLevelLimitFilter, LogManager
from .types import Model, ModelBaseType, ModelError, User, UserNotFoundError


SessionFactory = Callable[[], Session]


class DatabaseModelError(ModelError):
    """Error while interacting with database."""


@dataclasses.dataclass
class DatabaseParams:
    """Parameters required to establish DB connection."""
    drivername: str
    host: str
    port: int
    database: str
    username: str
    password: str


class DatabaseModel(Model):
    """Stores data in database persistently."""

    def __init__(
        self,
        log: LogManager,
        db_params: DatabaseParams,
        clear_db: bool = False,
    ):
        """Initialize database model object.

        Args:
            log (LogManager): Log manager to use for logging.
            db_params (DatabaseParams): DB connection parameters.
            clear_db (bool): Delete all model data that previously exists.
        """
        super().__init__()
        self._logger = log.create_logger(self)
        self._engine = self._create_engine(log, db_params)
        self._create_session = self._create_session_factory()
        self._test_db_connection()
        if clear_db:
            self._drop_tables()
        self._create_tables()
        self._set_engine_logger(self._engine, log)

    @override
    def user_exists(self, user_id: int) -> bool:
        self._logger.debug('Checking if user %s exists', user_id)
        try:
            with self._create_session() as session:
                user = session.get(User, user_id)
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.error('Check error: user=%r, error=%s', user_id, e)
            raise me from e

        if result := user is not None:
            self._logger.debug('User exists: %r', user)
        else:
            self._logger.debug('User %s does not exist', user_id)
        return result

    @override
    def get_user(self, user_id: int) -> Optional[User]:
        self._logger.debug('Extracting user %s', user_id)
        try:
            with self._create_session() as session:
                user = session.get(User, user_id)
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.error('Get error: user=%r, error=%s', user_id, e)
            raise me from e

        if user is not None:
            self._logger.debug('User exists: %r', user)
        else:
            self._logger.debug('User %s does not exist', user_id)
        return user

    @override
    def add_user(self, user: User):
        self._logger.debug('Adding user %r', user)
        try:
            with self._create_session() as session, session.begin():
                session.add(user)
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.error('Add error: user=%r, error=%s', user, e)
            raise me from e

        self._logger.debug('Added user %r', user)

    @override
    def update_user(self, user: User):
        self._logger.debug('Updating user %r', user)
        try:
            with self._create_session() as session, session.begin():
                if session.get(User, user.id) is None:
                    raise UserNotFoundError(f'User {user!r} does not exist')
                session.merge(user)
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.error('Update error: user=%r, error=%s', user, e)
            raise me from e

        self._logger.debug('Updated user %r', user)

    @override
    def delete_user(self, user_id: int) -> Optional[User]:
        self._logger.debug('Deleting user %r', user_id)
        try:
            with self._create_session() as session, session.begin():
                stmt = delete(User).where(User.id == user_id).returning(User)
                user = session.scalar(stmt)
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.error('Delete error: user=%r, error=%s', user_id, e)
            raise me from e

        if user is not None:
            self._logger.debug('User deleted %r', user)
        else:
            self._logger.warning('No user %s, cannot delete', user_id)
        return user

    def _create_tables(self):
        """Internal helper to create tables for all entities in the DB."""
        try:
            ModelBaseType.metadata.create_all(self._engine)
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Create tables error: %s', e)
            raise me from e

    def _drop_tables(self):
        """Internal helper to delete tables for all entities in the DB."""
        try:
            ModelBaseType.metadata.drop_all(self._engine)
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('Delete tables error: %s', e)
            raise me from e

    def _create_dsn(self, params: DatabaseParams) -> URL:
        """Internal helper to form and return a DSN from `DatabaseParams`.

        Args:
            params (DatabaseParams): DB connection parameters.
        """
        return URL.create(**dataclasses.asdict(params))

    def _create_engine(
        self,
        log: LogManager,
        params: DatabaseParams,
    ) -> Engine:
        """Internal helper to create and return DB engine object.

        Args:
            log (LogManager): Log manager to use for logging.
            params (DatabaseParams): DB connection parameters.
        """
        engine = create_engine(self._create_dsn(params), echo='debug')
        self._set_engine_logger(engine, log)
        return engine

    def _set_engine_logger(self, engine: Engine, log: LogManager):
        """Internal helper to monkey patch engine logger.

        Args:
            engine (Engine): Engine object.
            log (LogManager): Log manager to use for logging.
        """
        logger = engine.logger
        if isinstance(logger, InstanceLogger):
            # Handle engine's internal wrappers for logger
            logger = logger.logger
        logger = log.create_logger(logger.name)
        # Avoid flooding with 'INFO' log level
        logger.addFilter(LogLevelLimitFilter(logger, LogLevel.DEBUG))
        engine.logger = logger

    def _create_session_factory(self) -> SessionFactory:
        """Internal helper to create and return DB session factory
        which creates session objects to perform DB operations.
        """
        return sessionmaker(
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
        except SQLAlchemyError as e:
            me = self._create_model_error(e)
            self._logger.debug('DB connection error: %s', e)
            raise me from e

    @staticmethod
    def _create_model_error(e: SQLAlchemyError) -> DatabaseModelError:
        """Internal helper to create model exception from underlying library.

        Args:
            e (SQLAlchemyError): Underlying library exception.
        """
        # Monkey patch the exception to avoid messages like this:
        # Background on this error at: https://sqlalche.me/e/XX/YYYY
        e.code = None
        return DatabaseModelError(e)
