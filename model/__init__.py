"""This package defines basic types that stores application data."""

from . import db


class Model(db.DatabaseModel):
    """Stores all application data."""


class ModelConfig(db.DatabaseConfig):
    """Model parameters."""


def create_model(config: ModelConfig) -> Model:
    """Create model object.

    Args:
        config (ModelConfig): Model parameters.

    Returns:
        Model: Model object.

    Raises:
        ModelError: Model creation error.
    """
    return Model(config)
