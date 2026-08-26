"""The four bytes each side of the audio unit leaves for the other to read.

This is the whole of what the console and the audio unit can say to each other.
There is no shared memory between them and no interrupt either way: a console
writes a byte where the unit will read it, and the unit writes a byte where the
console will read it, and every protocol either side has ever used is built out
of those two moves.

The part that is easy to model wrongly is that a port is not one byte. It is two,
one per direction, at one address. A write from the console does not change what
the console reads back, and a write from the unit does not change what the unit
reads back. Modelling a port as a single byte makes both sides appear to work
until two writes cross, and then produces an answer neither side sent.
"""

from __future__ import annotations

from typing import override

COUNT = 4
"""How many there are. The console reaches them at four consecutive addresses."""


class Ports:
    """Four ports, each holding a byte per direction."""

    __slots__ = ("from_console", "from_unit")

    def __init__(self, fill: int = 0) -> None:
        self.from_console = bytearray([fill & 0xFF]) * COUNT
        self.from_unit = bytearray([fill & 0xFF]) * COUNT

    def unit_reads(self, index: int) -> int:
        """What the unit's processor sees at one of its four port addresses."""
        return self.from_console[index & (COUNT - 1)]

    def unit_writes(self, index: int, value: int) -> None:
        """A byte the unit leaves for the console."""
        self.from_unit[index & (COUNT - 1)] = value & 0xFF

    def console_reads(self, index: int) -> int:
        """What the console sees at one of the four addresses it reaches."""
        return self.from_unit[index & (COUNT - 1)]

    def console_writes(self, index: int, value: int) -> None:
        """A byte the console leaves for the unit."""
        self.from_console[index & (COUNT - 1)] = value & 0xFF

    def clear_from_console(self, lower: bool, upper: bool) -> None:
        """Drop what the console left, for the pair or pairs named.

        The unit's control register can clear ports zero and one together, or
        two and three together, and it clears only the direction the console
        writes. What the unit already left for the console survives, because a
        console mid-read of an answer would otherwise lose it.
        """
        if lower:
            self.from_console[0:2] = b"\x00\x00"
        if upper:
            self.from_console[2:4] = b"\x00\x00"

    @override
    def __repr__(self) -> str:
        return (
            f"<Ports console->unit {bytes(self.from_console).hex()},"
            f" unit->console {bytes(self.from_unit).hex()}>"
        )
