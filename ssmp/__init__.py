"""A model of the S-SMP, the audio unit a Super Nintendo talks to rather than into.

    from ssmp import Chip

    unit = Chip("ssmp")
    unit.run_for(6300)
    unit.read(0), unit.read(1)          # 0xaa, 0xbb: the unit is ready

The console cannot reach the unit's memory, its processor or its sound generator.
It reaches four bytes, and everything a game has ever done to the audio hardware
went through them. That is why this package exists as a member of its own rather
than as a folder inside either half: the halves are `sony-spc700-python` and
`sony-s-dsp-python`, and what is left over once you have both is the thing
between them, which is the memory they share, the four ports, three timers, and
sixty four bytes of boot program that hand a console's upload into memory.

**It needs a boot program and does not carry one.** Those sixty four bytes are
Sony's. A copy you already own goes in the boot directory of this project or of
the project this one sits inside, or anywhere named by `SSMP_BOOT_DIR`. Nothing
is downloaded. Without one the unit refuses to be built and says why, which is
the honest answer to a request it cannot serve.

**Two crystals, and no ratio between them.** The console and the audio unit are
clocked separately and neither divides the other, so this package publishes no
figure converting one to the other and offers no elapsed time in console cycles.
Inventing that ratio is the one thing a model of this part can do that would look
right and be wrong everywhere.
"""

from typing import Any

from . import models
from .board import Chip as _Chip
from .board import available, why_not
from .errors import Corrupt, NoBootRom, UnknownModelError, Unrecognised, WrongShape
from .models import MODELS, Model
from .version import VERSION

__version__ = VERSION


def Chip(model: str | None = None, **options: Any) -> Any:  # noqa: N802
    """A unit of the named model, sharing one interface across the family.

    The model comes first because it is the thing a caller always knows, and it
    is taken even though there is one of them, so that this reads the way every
    other member of the family reads.
    """
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
