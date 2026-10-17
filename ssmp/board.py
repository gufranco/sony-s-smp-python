from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from ssmp import firmware, rates
from ssmp.errors import NoBootRom
from ssmp.ports import COUNT as PORT_COUNT
from ssmp.space import BOOT_BYTES, Space

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "sony-spc700-python"

GENERATOR = ROOT / "sony-s-dsp-python"

PROCESSOR_MODEL = "spc700"

GENERATOR_MODEL = "s-dsp"

WHY_NOT_PROCESSOR = (
    "the processor is not here: this unit runs the SPC700, which is a member of"
    " this family consumed as a submodule, and the submodule is not checked out."
    " Run git submodule update --init --recursive"
)

WHY_NOT_BOOT = (
    "no boot program was found: this unit starts from sixty four bytes Sony wrote,"
    " and those belong to whoever wrote them, so a copy you already own goes in"
    " the boot directory of this project or in any directory named by"
    " SSMP_BOOT_DIR. Nothing is downloaded and nothing is shipped"
)


def _members() -> tuple[Any, Any] | None:
    for where in (PROCESSOR, GENERATOR):
        if str(where) not in sys.path:
            sys.path.append(str(where))
    try:
        import sdsp
        import spc700
    except ImportError:
        return None
    return spc700, sdsp


def available(
    held: dict[str, tuple[Any, Path]] | None = None,
    catalogue: dict[str, Any] | None = None,
) -> dict[str, tuple[Any, Path]]:
    if held is None:
        if _members() is None:
            return {}
        held = {
            identity.part: (identity, path)
            for identity, path in firmware.search(catalogue=catalogue)
        }
    return dict(held)


def why_not(held: dict[str, tuple[Any, Path]] | None = None) -> str | None:
    if _members() is None:
        return WHY_NOT_PROCESSOR
    if not available(held):
        return WHY_NOT_BOOT
    return None


class Chip:
    __slots__ = (
        "_boot",
        "_fill",
        "_generator",
        "_processor",
        "cycles",
        "dsp",
        "identity",
        "model",
        "part",
        "processor",
        "space",
    )

    def __init__(
        self,
        part: str,
        boot: Sequence[int] | None = None,
        identity: Any | None = None,
        images: dict[str, tuple[Any, Path]] | None = None,
        fill: int | None = None,
    ) -> None:
        found = _members()
        if found is None:
            raise NoBootRom(WHY_NOT_PROCESSOR)
        processor, generator = found

        if boot is None:
            catalogue = available(images)
            if part not in catalogue:
                raise NoBootRom(f"there is no boot program for {part}. {WHY_NOT_BOOT}")
            identity, where = catalogue[part]
            boot = Path(where).read_bytes()
        elif identity is None:
            identity = firmware.Identity(part, "spc700", "supplied", BOOT_BYTES)

        firmware.check_shape(boot)

        self.part = part
        self.model = part
        self.identity = identity
        self._boot = bytes(boot)
        self._fill = fill
        self._processor = processor
        self._generator = generator
        self.cycles = 0
        self._start()

    def _start(self) -> None:
        store = self._processor.Memory(fill=self._fill)
        self.dsp = self._generator.Chip(GENERATOR_MODEL, memory=store)
        self.space = Space(boot=self._boot, memory=store, dsp=self.dsp)
        self.processor = self._processor.Cpu(PROCESSOR_MODEL, memory=self.space)
        self.processor.on_cycle = self._spent

    def _spent(self) -> None:
        self.cycles += 1
        self.space.spend(1)
        for _ in range(rates.GENERATOR_CLOCKS):
            self.dsp.clock()

    def reset(self) -> Chip:
        self.space.reset()
        self.dsp.reset()
        self.processor.reset()
        return self

    def step(self) -> int:
        spent: int = self.processor.step()
        return spent

    def run_for(self, cycles: int) -> int:
        spent: int = self.processor.run_for(cycles)
        return spent

    def read(self, index: int) -> int:
        return self.space.ports.console_reads(index)

    def write(self, index: int, value: int) -> None:
        self.space.ports.console_writes(index, value)

    @override
    def __repr__(self) -> str:
        window = "boot" if self.space.boot_visible else "memory"
        return f"<Chip {self.part}, {self.cycles} cycles, top page reads {window}>"


PORTS = PORT_COUNT
