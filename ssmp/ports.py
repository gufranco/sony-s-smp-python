from __future__ import annotations

from typing import override

COUNT = 4


class Ports:
    __slots__ = ("from_console", "from_unit")

    def __init__(self, fill: int = 0) -> None:
        self.from_console = bytearray([fill & 0xFF]) * COUNT
        self.from_unit = bytearray([fill & 0xFF]) * COUNT

    def unit_reads(self, index: int) -> int:
        return self.from_console[index & (COUNT - 1)]

    def unit_writes(self, index: int, value: int) -> None:
        self.from_unit[index & (COUNT - 1)] = value & 0xFF

    def console_reads(self, index: int) -> int:
        return self.from_unit[index & (COUNT - 1)]

    def console_writes(self, index: int, value: int) -> None:
        self.from_console[index & (COUNT - 1)] = value & 0xFF

    def clear_from_console(self, lower: bool, upper: bool) -> None:
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
