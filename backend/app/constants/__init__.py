"""
Application-wide constants and configuration values.
"""

from .embedding_models import (
    ALLOWED_MODEL_NAMES,
    DEFAULT_MODEL,
    EMBEDDING_MODELS,
    FORM_OPTIONS_LEGRA,
    FORM_OPTIONS_VECTOR,
    MODELS_FOR_DOWNLOAD,
)

__all__ = [
    "EMBEDDING_MODELS",
    "ALLOWED_MODEL_NAMES",
    "MODELS_FOR_DOWNLOAD",
    "FORM_OPTIONS_VECTOR",
    "FORM_OPTIONS_LEGRA",
    "DEFAULT_MODEL",
]
