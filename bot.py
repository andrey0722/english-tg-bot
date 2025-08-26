"""This module defines interaction with the Telegram bot API."""

from controller import Controller
from log import LogManager


class Bot:
    """A class which instance incapsulates interaction with
    Telegram bot API. Main logic is handled by a controller.
    """

    def __init__(self, controller: Controller, log: LogManager):
        """Initialize bot object."""
        self._logger = log.create_logger(self)
        self._controller = controller

    def run(self):
        """Start the bot and handle all incoming messages."""
        self._logger.debug('Bot started')
