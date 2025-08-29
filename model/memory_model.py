"""Defines a memory data model."""

from typing import MutableMapping, Optional, override

from log import LogManager
from .types import Model, User


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
    def get_user(self, user: User) -> Optional[User]:
        self._logger.debug('Extracting user %r', user)
        result = self._users.get(user.tg_id)
        if result is not None:
            self._logger.debug('User exists %r', result)
        else:
            self._logger.debug('User does not exist %r', user)
        return result

    @override
    def add_user(self, user: User) -> User:
        self._logger.debug('Adding user %r', user)
        result = self._users.setdefault(user.tg_id, user)
        self._logger.debug('Added user %r', result)
        return result

    @override
    def update_user(self, user: User) -> Optional[User]:
        self._logger.debug('Updating user %r', user)
        if result := self.get_user(user):
            result.username = user.username
            result.first_name = user.first_name
            result.last_name = user.last_name
            result = self._users.setdefault(result.tg_id, result)
            self._logger.debug('Updated user %r', user)
        else:
            self._logger.warning('User did not exist, cannot update %r', user)
        return result

    @override
    def delete_user(self, user: User) -> Optional[User]:
        self._logger.debug('Deleting user %r', user)
        result = self._users.pop(user.tg_id, None)
        if result is not None:
            self._logger.debug('User deleted %r', result)
        else:
            self._logger.warning('User did not exist, cannot delete %r', user)
        return result
