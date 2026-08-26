"""The audio unit: a processor, sixty four kilobytes, a boot program and four ports.

What this models is the thing around the processor rather than the processor. The
processor is
[sony-spc700-python](https://github.com/gufranco/sony-spc700-python) and the sound
generator beside it is
[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python); both are
members of this family with their own records, and neither is reimplemented here.
What is here is the memory map that makes them one unit: where the registers sit,
what a console can say and hear, how the timers are paced, and the boot program
that covers the top of memory until something switches it away.

The unit has no program of its own. Every cycle it spends is spent inside the
processor it holds, and that member is the one that reports them, so the family's
clocked interface does not appear here. What this offers instead is a way to give
the processor cycles and have everything around it advance by the same amount.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from ssmp import firmware, rates
from ssmp.errors import NoBootRom
from ssmp.ports import COUNT as PORT_COUNT
from ssmp.space import BOOT_BYTES, Space

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "sony-spc700-python"

GENERATOR = ROOT / "sony-s-dsp-python"

PROCESSOR_MODEL = "spc700"
"""Which part the processor member is asked for.

Named here rather than left to a default, because neither half has one. A unit
that let its halves choose for themselves would be a unit whose composition
nobody wrote down.
"""

GENERATOR_MODEL = "s-dsp"
"""Which part the sound generator member is asked for."""

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
    """The two packages this unit is built from, or nothing when either is absent.

    Appended to the import path rather than inserted at the front, because a
    directory placed ahead of the standard library is a directory whose file
    names shadow it.

    The failing path is marked as not measured because the only machine that can
    take it is one without the submodules, which is the machine that cannot run
    a test to prove it. Every caller takes this lookup as an argument instead, so
    what the answer leads to is checked even where the answer itself cannot be.
    """
    for where in (PROCESSOR, GENERATOR):
        if str(where) not in sys.path:
            sys.path.append(str(where))
    try:
        import sdsp
        import spc700
    except ImportError:  # pragma: no cover
        return None
    return spc700, sdsp


def available(
    held: dict[str, tuple[Any, Path]] | None = None,
    members: Callable[[], tuple[Any, Any] | None] = _members,
) -> dict[str, tuple[Any, Path]]:
    """Every unit there is a boot program for, by the name the unit is known as.

    `held` is what was found on disk, passed in so the decision that follows can
    be exercised on a machine holding no image at all. `members` is how the two
    halves are reached, passed in for the same reason: a machine that has them
    cannot otherwise exercise what happens on a machine that does not.
    """
    if held is None:
        if members() is None:
            return {}
        held = {identity.part: (identity, path) for identity, path in firmware.search()}
    return dict(held)


def why_not(
    held: dict[str, tuple[Any, Path]] | None = None,
    members: Callable[[], tuple[Any, Any] | None] = _members,
) -> str | None:
    """Why this unit cannot be built here, or nothing when it can.

    The same sentence the doctor prints, and the one the family's own checks read
    before skipping. A member that runs a file it may not carry has to be able to
    say so in one call.
    """
    if members() is None:
        return WHY_NOT_PROCESSOR
    if not available(held, members):
        return WHY_NOT_BOOT
    return None


class Chip:
    """One audio unit, holding a processor and everything around it."""

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
        members: Callable[[], tuple[Any, Any] | None] = _members,
    ) -> None:
        found = members()
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
        """Build the unit and put it where the rail coming up leaves it.

        The order matters. Memory is built first because both halves reach it:
        the processor runs on it, and the sound generator reads its compressed
        blocks and writes its echo into the same sixty four kilobytes. Handing
        each of them a store of its own would be two memories where the part has
        one, and every sample a program uploaded would go missing.

        The sound generator is reset rather than left as it powered on, because
        the console's reset line reaches it too, and what a reset leaves is a
        part that writes no echo. Without that a unit would come up scribbling
        wherever its scrambled echo registers pointed, which is not what a
        console does and would eat the program a caller just uploaded.
        """
        store = self._processor.Memory(fill=self._fill)
        self.dsp = self._generator.Chip(GENERATOR_MODEL, memory=store).reset()
        self.space = Space(boot=self._boot, memory=store, dsp=self.dsp)
        self.processor = self._processor.Cpu(PROCESSOR_MODEL, memory=self.space)
        self.processor.on_cycle = self._spent
        self.processor.reset()

    def _spent(self) -> None:
        """One cycle, charged to the unit as well as to the processor.

        Every cycle the processor spends passes through here, which is what lets
        the timers and the sound generator run at their own rate rather than
        being stepped once per instruction. An instruction that takes eight
        cycles advances them by eight.

        The sound generator takes one clock per processor cycle, and that is a
        derivation rather than a figure anybody printed. It is in
        `ssmp/rates.py` beside the timer ratios: the same crystal reaches the
        processor at 1,024,000 Hz and the generator at 32,000 samples of thirty
        two clocks each, and those two are the same number.
        """
        self.cycles += 1
        self.space.spend(1)
        for _ in range(rates.GENERATOR_CLOCKS):
            self.dsp.clock()

    def reset(self) -> Chip:
        """Take the unit back to where the console's reset line leaves it.

        The boot program is masked in, so nothing a reset does can reach it, and
        the unit comes back holding what it holds at power on with the same
        program visible at the top of memory. The unit is handed back so a caller
        can build and reset in one expression.
        """
        self._start()
        return self

    def step(self) -> int:
        """One instruction of whatever the unit is running, and what it cost."""
        spent: int = self.processor.step()
        return spent

    def run_for(self, cycles: int) -> int:
        """Instructions until that many cycles are spent, returning what was spent.

        An instruction cannot be cut in half, so this overshoots and says by how
        much. Carrying the overshoot into the next call is what stops a long run
        drifting away from the console it is meant to keep time with.
        """
        spent: int = self.processor.run_for(cycles)
        return spent

    def read(self, index: int) -> int:
        """What the console sees at one of the four addresses it reaches."""
        return self.space.ports.console_reads(index)

    def write(self, index: int, value: int) -> None:
        """A byte the console leaves for the unit."""
        self.space.ports.console_writes(index, value)

    @override
    def __repr__(self) -> str:
        window = "boot" if self.space.boot_visible else "memory"
        return f"<Chip {self.part}, {self.cycles} cycles, top page reads {window}>"


PORTS = PORT_COUNT
