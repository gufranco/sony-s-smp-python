import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

READY_LOW = 0xAA

READY_HIGH = 0xBB

START = 0xCC

WAITING = (0xFFCF, 0xFFD1, 0xFFD2)

SOMEWHERE = 0x0200

A_PROGRAM = bytes((0xE8, 0x42, 0x8F, 0x5A, 0x10, 0xFF))

ANOTHER_PROGRAM = bytes((0xE8, 0x99, 0xFF))

PATIENCE = 400

SLICE = 64


class NeverAnswered(Exception): ...


def _until(unit: Any, port: int, value: int) -> None:
    for _ in range(PATIENCE):
        unit.run_for(SLICE)
        if unit.read(port) == value:
            return
    raise NeverAnswered(
        f"port {port} never read {value:#04x}; it holds {unit.read(port):#04x} after"
        f" {PATIENCE * SLICE} cycles"
    )


def wait_for_ready(unit: Any) -> None:
    for _ in range(PATIENCE):
        if (unit.read(0), unit.read(1)) == (READY_LOW, READY_HIGH):
            return
        unit.run_for(SLICE)
    raise NeverAnswered(
        f"the unit never answered {READY_LOW:#04x} {READY_HIGH:#04x};"
        f" its ports read {[hex(unit.read(at)) for at in range(4)]}"
    )


def upload(
    unit: Any,
    program: Sequence[int],
    where: int = SOMEWHERE,
    jump: bool = True,
    after: int | None = None,
) -> list[int]:
    if after is None:
        wait_for_ready(unit)
    unit.write(2, where & 0xFF)
    unit.write(3, (where >> 8) & 0xFF)
    unit.write(1, 0x01)
    kick = START if after is None else (after + 2) & 0xFF
    unit.write(0, kick)
    _until(unit, 0, kick)

    said = []
    for at, byte in enumerate(program):
        unit.write(1, byte & 0xFF)
        unit.write(0, at & 0xFF)
        _until(unit, 0, at & 0xFF)
        said.append(unit.read(0))

    if jump:
        unit.write(2, where & 0xFF)
        unit.write(3, (where >> 8) & 0xFF)
        unit.write(1, 0x00)
        unit.write(0, (len(program) + 2) & 0xFF)
        unit.run_for(SLICE * 8)
    return said
