"""This module contains all messages that bot can send to a user."""

import enum


@enum.unique
class MainMenu(enum.StrEnum):
    """Commands in main menu."""

    LEARN = 'Учиться'


@enum.unique
class LearningMenu(enum.StrEnum):
    """Commands in learning mode."""

    FINISH = 'Завершить'


class Messages(enum.StrEnum):
    """Messages from the bot to a user."""

    USER_NOT_STARTED = 'Отправьте команду /start, чтобы начать.'
    BOT_ERROR = 'Ошибка работы бота'
    GREETING_NEW_USER = 'Добро пожаловать, {}!'
    GREETING_OLD_USER = 'Приветствую снова, {}!'
    DELETED_USER = '{}, ваши данные удалены.'
    DELETED_NOT_EXISTING = '{}, ваши данные отсутствуют.'
    SELECT_MAIN_MENU = 'Выберите вариант из меню ниже:'
    SELECT_LEARNING = 'Ну и что будем делать?'
    FINISHED_LEARNING = 'Обучение завершено.'
