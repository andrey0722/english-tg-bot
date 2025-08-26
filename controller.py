"""This module implements main logic of the bot."""

from log import LogManager
from model import Model


class Controller:
    """A class which instance processes input from the bot and handles it."""

    def __init__(self, model: Model, log: LogManager) -> None:
        """Initialize controller object."""
        self._model = model
        self._logger = log.create_logger(self)
