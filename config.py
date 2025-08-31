"""This module defines all external program parameters which affect
program operation.
"""

import enum
from typing import Any

from pydantic import Field
from pydantic import field_validator
from pydantic import ValidationError
from pydantic_core import PydanticKnownError
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from log import LogLevel


ConfigError = ValidationError


class StorageType(enum.StrEnum):
    """Depicts storage type that the application will use to store data."""
    DATABASE = 'DATABASE'
    MEMORY = 'MEMORY'


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
    log_level: LogLevel = LogLevel.INFO
    tg_bot_token: str = '1234567890:TG_BOT_EXAMPLE_TOKEN'
    storage_type: StorageType = StorageType.DATABASE
    clear_data: bool = False

    @field_validator('log_level', mode='before')
    @classmethod
    def _log_level_from_str(cls, value: Any) -> Any:
        """If environment value if a string, try to convert it to `LogLevel`.

        Args:
            value (Any): Environment value.

        Returns:
            Any: Environment value after conversion.
        """
        if isinstance(value, str):
            # Process only strings
            members = LogLevel.__members__.keys()
            if value in members:
                # Convert exact enum member names
                return LogLevel[value]
            else:
                # Show member string values in error message
                # Mimic the pydantic's way of formatting
                members = list(map(repr, members))
                members_str = ' or '.join(
                    [', '.join(members[:-1]), members[-1]]
                    if len(members) > 2
                    else members
                )
                raise PydanticKnownError('enum', {'expected': members_str})
        # Pass the value through for further validation
        return value


class DatabaseConfig(ConfigBase):
    """External parameters for DB connection loaded from the environment.

    See .env.example file for variable description.
    """
    drivername: str = Field(alias='DB_DRIVER', default='postgresql+psycopg2')
    host: str = Field(alias='DB_HOST', default='localhost')
    port: int = Field(alias='DB_PORT', default=5432)
    database: str = Field(alias='DB_NAME', default='english_tg_bot')
    username: str = Field(alias='DB_USER', default='postgres')
    password: str = Field(alias='DB_PASS', default='postgres')
