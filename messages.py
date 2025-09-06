"""This module contains all messages that bot can send to a user."""

import enum


@enum.unique
class MainMenu(enum.StrEnum):
    """Commands in main menu."""

    LEARN = '📖 Учиться'
    ADD_CARD = '✍🏻 Добавить новое слово'


@enum.unique
class LearningMenu(enum.StrEnum):
    """Commands in learning mode."""

    SKIP = '⏩ Пропустить слово'
    DELETE = '❌ Удалить слово'
    FINISH = '🏁 Завершить'


class Messages(enum.StrEnum):
    """Messages from the bot to a user."""

    USER_NOT_STARTED = 'Отправьте команду /start, чтобы начать.'
    BOT_ERROR = 'Ошибка работы бота'
    GREETING_NEW_USER = 'Добро пожаловать, {}!'
    GREETING_OLD_USER = 'Приветствую снова, {}!'
    DELETED_USER = '{}, ваши данные удалены.'
    DELETED_NOT_EXISTING = '{}, ваши данные отсутствуют.'
    SELECT_MAIN_MENU = 'Выберите вариант из меню ниже:'
    NO_LEARNING_CARDS = (
        'У вас не хватает карточек для обучения! '
        'Сперва добавьте новые слова, затем повторите попытку!'
    )
    SELECT_TRANSLATION = 'Выберите перевод слова:\n🇷🇺 {}'
    CORRECT_TRANSLATION = 'Верно!\n🇷🇺 {} → 🇬🇧 {}'
    WRONG_TRANSLATION = 'Ответ неверный! Попробуйте отгадать снова.'
    SKIPPED_TRANSLATION = 'Пропускаем слово, идём дальше.'
    FINISHED_LEARNING = 'Обучение завершено.'
    ENTER_RU_WORD = 'Введите новое слово 🇷🇺:'
    ENTER_EN_WORD = 'Введите его перевод 🇬🇧:'
    ADDED_RU_EN_CARD = 'Добавлена новая карточка:\n🇷🇺 {} → 🇬🇧 {}'
    DELETED_RU_EN_CARD = 'Удалена карточка:\n🇷🇺 {} → 🇬🇧 {}'
