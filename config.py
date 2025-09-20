"""Program configuration parameters.

This module defines all external program parameters which affect
program operation.
"""

from typing import ClassVar, Final, TypeVar

from pydantic import Field
from pydantic import ValidationError
from pydantic import field_validator
from pydantic_core import PydanticKnownError
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

import log

ConfigError = ValidationError

T = TypeVar('T')


class ConfigBase(BaseSettings):
    """Base class for other settings classes."""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


class Config(ConfigBase):
    """Project external parameters loaded from the environment.

    See .env.example file for variable description.
    """
    log_level: log.LogLevel = log.LogLevel.INFO
    tg_bot_token: str = '1234567890:TG_BOT_EXAMPLE_TOKEN'
    test_words: bool = False

    @field_validator('log_level', mode='before')
    @classmethod
    def _log_level_from_str(cls, value: T) -> T | log.LogLevel:
        """If environment value if a string, try to convert it to `LogLevel`.

        Args:
            value (Any): Environment value.

        Returns:
            Any: Environment value after conversion.
        """
        if not isinstance(value, str):
            # Pass the value through for further validation
            return value

        # Process only strings
        members = log.LogLevel.__members__.keys()
        if value in members:
            # Convert exact enum member names
            return log.LogLevel[value]

        # Show member string values in error message
        formatted_members = cls._format_log_level_members()
        raise PydanticKnownError('enum', {'expected': formatted_members})

    @classmethod
    def _format_log_level_members(cls) -> str:
        """Format `log.LogLevel` members in Pydantic's style.

        Returns:
            str: Formatted list of `log.LogLevel` members.
        """
        members = log.LogLevel.__members__.keys()
        members = list(map(repr, members))
        return ' or '.join(
            [', '.join(members[:-1]), members[-1]]
            if len(members) > cls.MIN_PYDANTIC_ENUM_COUNT
            else members,
        )

    MIN_PYDANTIC_ENUM_COUNT: ClassVar[Final] = 2


class DatabaseConfig(ConfigBase):
    """External parameters for DB connection loaded from the environment.

    See .env.example file for variable description.
    """
    driver: str = Field(alias='DB_DRIVER', default='postgresql+psycopg2')
    host: str = Field(alias='DB_HOST', default='localhost')
    port: int = Field(alias='DB_PORT', default=5432)
    database: str = Field(alias='DB_NAME', default='english_tg_bot')
    user: str = Field(alias='DB_USER', default='postgres')
    password: str = Field(alias='DB_PASS', default='postgres')
    clear_data: bool = False
