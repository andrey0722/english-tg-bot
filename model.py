"""This module implements all logic to load, save and query
application data.
"""


from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """A class which instance represents one user of the bot."""

    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

    @property
    def display_name(self) -> str:
        """Returns a string representing user name suitable for output."""
        parts = [x for x in (self.first_name, self.last_name) if x]
        result = ' '.join(parts)
        return result or self.username or f'user_{self.tg_id}'


class Model:
    """A class which instance handles all application data."""
