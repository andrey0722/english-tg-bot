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

    USER_NOT_STARTED = (
        'Вы новый пользователь! Отправьте команду /start, '
        'чтобы познакомиться с ботом и начать его использовать.'
    )
    BOT_ERROR = 'Ошибка работы бота'
    GREETING_NEW_USER = (
        '🎉🎉🎉 Добро пожаловать, {}! 🎉🎉🎉\n'
        'Данный бот предназначен для помощи в обучении английскому языку и '
        'расширению словарного запаса.'
    )
    GREETING_OLD_USER = 'Приветствую снова, {}! 👋'
    DELETED_USER = '{}, ваши данные удалены.'
    DELETED_NOT_EXISTING = '{}, ваши данные отсутствуют.'
    SELECT_MAIN_MENU = 'Выберите вариант из меню ниже:'
    NO_LEARNING_CARDS = (
        'У вас сейчас {} карточек, а для обучения необходимо как минимум {}! '
        'Сперва добавьте больше новых слов, затем повторите попытку!'
    )
    PLAN_LEARNING_COUNT = 'Вы будете изучать {} слов, приступим 🤓'
    SELECT_TRANSLATION = 'Выберите перевод слова:\n🇷🇺 {}'
    CORRECT_TRANSLATION = 'Верно!\n🇷🇺 {} → 🇬🇧 {}'
    WRONG_TRANSLATION = '😢 Ответ неверный! Попробуйте отгадать снова 🙏'
    SKIPPED_TRANSLATION = 'Пропускаем слово, бежим дальше 🏃‍♂️‍➡️'
    FINISHED_LEARNING = (
        'Обучение завершено. Вот ваши результаты:\n'
        'Изучено слов: {} ✅\n'
        'Пропущено слов: {} ⏩\n'
        'Количество ошибок: {} ❌'
    )
    ENTER_RU_WORD = 'Введите новое слово 🇷🇺:'
    ENTER_EN_WORD = 'Введите его перевод 🇬🇧:'
    ADDED_RU_EN_CARD = 'Добавлена новая карточка:\n🇷🇺 {} → 🇬🇧 {}'
    DELETED_RU_EN_CARD = 'Удалена карточка:\n🇷🇺 {} → 🇬🇧 {}'
    NEW_LEARNING_COUNT = 'Теперь вы изучаете {} слов!'
