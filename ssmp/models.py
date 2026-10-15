from typing import override

from ssmp.errors import UnknownModelError

SEPARATORS = ("-", "_", " ", ".")


class Model:
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


def lookup(name: str | None) -> Model:
    if name is None:
        raise UnknownModelError(
            "no model was named, and this package will not choose one for you."
            f" Name one of: {', '.join(sorted(MODELS))}"
        )
    wanted = _plain(name)
    for known, model in MODELS.items():
        if _plain(known) == wanted:
            return model
    raise UnknownModelError(
        f"{name} is not a unit this package covers; there is {', '.join(sorted(MODELS))}"
    )
