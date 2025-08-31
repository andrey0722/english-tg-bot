"""Defines a memory data model."""

from typing import MutableMapping, Optional, override

from log import LogManager
from .types import Model, ModelError, User, UserNotFoundError


class MemoryModel(Model):
    """Stores data in RAM only and does not persist data
    between different runs or instances.
    """

    def __init__(self, log: LogManager):
        """Initialize memory model object.

        Args:
            log (LogManager): Log manager to use for logging.
        """
        super().__init__()
        self._logger = log.create_logger(self)
        self._users: MutableMapping[int, User] = {}

    @override
    def user_exists(self, user_id: int) -> bool:
        self._logger.debug('Checking if user %s exists', user_id)
        user = self._users.get(user_id)
        if result := user is not None:
            self._logger.debug('User exists: %r', user)
        else:
            self._logger.debug('User %s does not exist', user_id)
        return result

    @override
    def get_user(self, user_id: int) -> Optional[User]:
        self._logger.debug('Extracting user %s', user_id)
        result = self._users.get(user_id)
        if result is not None:
            self._logger.debug('User exists: %r', result)
        else:
            self._logger.debug('User %s does not exist', user_id)
        return result

    @override
    def add_user(self, user: User):
        self._logger.debug('Adding user %r', user)
        if user.id in self._users:
            raise ModelError(f'User {user!r} already exists')
        self._users[user.id] = user
        self._logger.debug('Added user %r', user)

    @override
    def update_user(self, user: User):
        self._logger.debug('Updating user %r', user)
        if user.id not in self._users:
            raise UserNotFoundError(f'User {user!r} does not exist')
        self._users[user.id] = user
        self._logger.debug('Updated user %r', user)

    @override
    def delete_user(self, user_id: int) -> Optional[User]:
        self._logger.debug('Deleting user %s', user_id)
        user = self._users.pop(user_id, None)
        if user is not None:
            self._logger.debug('User deleted %r', user)
        else:
            self._logger.warning('No user %s, cannot delete', user_id)
        return user
