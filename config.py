"""This module defines all external program parameters which affect
program operation.
"""

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from log import LogLevel


ConfigError = ValidationError


class Config(BaseSettings):
    """Project external parameters loaded from the environment.

    See .env.example file for variable description.
    """

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    log_level: LogLevel = LogLevel.INFO
