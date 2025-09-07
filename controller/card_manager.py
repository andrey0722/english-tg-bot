"""This module provides methods for various operations with learning cards."""

from model import Model
from model import Session
from model.types import EnglishWord
from model.types import LearningCard
from model.types import RussianWord


class CardManager:
    """Provides methods for various operations with learning cards."""

    def __init__(self, model: Model):
        """Initialize a card manager object.

        Args:
            model (Model): Model object.
        """
        self._model = model

    def add_card(
        self,
        session: Session,
        ru_word: str | RussianWord,
        en_word: str | EnglishWord,
    ) -> LearningCard:
        """Adds a new word card or gets an existing one.

        Args:
            session (Session): Session object.
            ru_word (str | RussianWord): Russian word object or plain text.
            en_word (str | EnglishWord): English word object or plain text.

        Returns:
            RussianWord: Word object from the model.
        """
        if not isinstance(ru_word, RussianWord):
            ru_word = self.add_ru_word(session, ru_word)
        if not isinstance(en_word, EnglishWord):
            en_word = self.add_en_word(session, en_word)
        card = LearningCard(ru_word=ru_word, en_word=en_word)
        return self._model.add_card(session, card)

    def add_ru_word(self, session: Session, text: str) -> RussianWord:
        """Add a new russian word of gets an existing one.

        Args:
            session (Session): Session object.
            text (str): Word text.

        Returns:
            RussianWord: Word object from the model.
        """
        text = self.preprocess_user_word(text)
        return self._model.add_word(session, RussianWord(text=text))

    def add_en_word(self, session: Session, text: str) -> EnglishWord:
        """Adds a new english word of gets an existing one.

        Args:
            session (Session): Session object.
            text (str): Word text.

        Returns:
            EnglishWord: Word object from the model.
        """
        text = self.preprocess_user_word(text)
        return self._model.add_word(session, EnglishWord(text=text))

    @staticmethod
    def preprocess_user_word(text: str) -> str:
        """Processes text from user input to match it later against
        words in learning cards.

        Args:
            text (str): User input text.

        Returns:
            str: Preprocessed text.
        """
        return text.strip().lower()
