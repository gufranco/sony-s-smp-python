"""The console's side of the conversation, so a check can play it.

A Super Nintendo cannot reach the audio unit's memory. It reaches four bytes, and
every audio program any cartridge ever ran arrived through them, one byte at a
time, in the sequence below. That sequence is not something this repository
invented and not something it copied from an implementation: it is what the boot
program in the unit's top page requires, and it can be read off those sixty four
bytes.

    wait until ports 0 and 1 read 0xaa and 0xbb
    put the destination in ports 2 and 3
    put a non-zero byte in port 1, meaning a transfer follows
    put 0xcc in port 0, and wait for it to come back
    for each byte:
        put the byte in port 1
        put the running count in port 0, and wait for it to come back
    put the destination in ports 2 and 3 again
    put zero in port 1, meaning jump rather than transfer
    put the count plus two in port 0

Nothing here needs a boot program: it is the console half. What it is played at
decides whether a boot program is needed, and `boot.test.py` plays it at the real
unit while this file's own tests play it at a stand-in.
"""

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

READY_LOW = 0xAA

READY_HIGH = 0xBB

START = 0xCC

WAITING = (0xFFCF, 0xFFD1, 0xFFD2)
"""Where the boot program sits while it waits for the console to say something."""

SOMEWHERE = 0x0200
"""Somewhere to upload to that no part of the boot program uses."""

A_PROGRAM = bytes((0xE8, 0x42, 0x8F, 0x5A, 0x10, 0xFF))
"""`mov a,#$42` `mov $10,#$5a` `stop`, which is enough to prove it ran."""

ANOTHER_PROGRAM = bytes((0xE8, 0x99, 0xFF))
"""`mov a,#$99` `stop`, for checking that a second block can follow the first."""

PATIENCE = 400
"""How many times to let the unit run before giving up on an answer.

Generous rather than tuned. What is being checked is that the unit answers at
all, and a check that failed because a limit was tight would be reporting on the
limit.
"""

SLICE = 64
"""Cycles to run between looking at the ports again."""


class NeverAnswered(Exception):
    """The unit did not say what the protocol says it says."""


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
    """Run the unit until its boot program says it is listening."""
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
    """Move a block in through the four ports, the way a cartridge does.

    Returns what the unit acknowledged for each byte, which is the running count
    coming back.

    `after` is how many bytes the previous block held, and passing it is what
    makes this a second block rather than a first. The boot program is past the
    handshake by then, so what starts the next transfer is not `0xcc` but that
    count plus two, which is the same value that would have made it jump had
    port 1 held zero. One byte decides between another block and a jump, which is
    the whole of how a cartridge uploads a driver in pieces.
    """
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
