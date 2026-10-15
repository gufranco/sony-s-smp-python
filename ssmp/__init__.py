from typing import Any

from . import models
from .board import Chip as _Chip
from .board import available, why_not
from .errors import Corrupt, NoBootRom, UnknownModelError, Unrecognised, WrongShape
from .models import MODELS, Model
from .version import VERSION

__version__ = VERSION


def Chip(model: str | None = None, **options: Any) -> Any:  # noqa: N802
    return _Chip(models.lookup(model).name, **options)


__all__ = [
    "MODELS",
    "VERSION",
    "Chip",
    "Corrupt",
    "Model",
    "NoBootRom",
    "UnknownModelError",
    "Unrecognised",
    "WrongShape",
    "__version__",
    "available",
    "why_not",
]
