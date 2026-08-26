"""Which units this package covers, and what each one is.

The S-SMP is one unit with one behaviour. Sony built the processor and the sound
generator onto one part, put sixty four bytes of boot program beside them, and
never sold any of it separately, so there is no family of revisions to model.

The catalogue exists for the same reason it exists in the sibling repositories: a
hardware difference discovered later should mean adding an entry rather than
restructuring the package around it. A caller still names the unit, because
`Chip("ssmp")` reads the same way as every other member of this family and a
constructor that took nothing would be the odd one out.
"""

from typing import override

from ssmp.errors import UnknownModelError

SEPARATORS = ("-", "_", " ", ".")
"""What a reader might put between the letters of a part number."""


class Model:
    """One unit: what it is, what it carries, and how much of it there is."""

    __slots__ = ("boot", "memory", "name", "processor", "summary")

    def __init__(
        self,
        name: str,
        summary: str,
        processor: str,
        memory: int,
        boot: int,
    ) -> None:
        self.name = name
        self.summary = summary
        self.processor = processor
        self.memory = memory
        self.boot = boot

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, {self.processor} and {self.memory // 1024}K>"


MODELS: dict[str, Model] = {
    "ssmp": Model(
        name="ssmp",
        summary=(
            "The audio unit as Sony shipped it: an SPC700 running out of sixty four "
            "kilobytes it shares with a sound generator, four ports the console reaches, "
            "three timers, and a boot program in the top page that hands control over."
        ),
        processor="spc700",
        memory=0x10000,
        boot=0x40,
    )
}

DEFAULT_MODEL = "ssmp"


def _plain(name: str) -> str:
    found = name.strip().lower()
    for one in SEPARATORS:
        found = found.replace(one, "")
    return found


def describe(name: str) -> Model:
    """The unit that goes by that name, however it was written."""
    wanted = _plain(name)
    for known, model in MODELS.items():
        if _plain(known) == wanted:
            return model
    raise UnknownModelError(
        f"{name} is not a unit this package covers; there is {', '.join(sorted(MODELS))}"
    )
