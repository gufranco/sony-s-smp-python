"""An SPC file, and the order a player has to restore it in.

A `.spc` file is a whole audio unit written down: sixty four kilobytes of
memory, the sound generator's registers, and the six processor registers. That
makes it the one artifact that can be handed to this model and simply run, with
no console anywhere in the chain and nothing to emulate on the other side of the
four ports.

The order below is not decoration. Writing the control register clears whichever
pairs of ports its bits ask for, so a player that restores the ports and then the
control register loses two of them, and every check downstream reads zero and
blames the wrong thing. The ports go back last.

Three of these files are checks rather than songs. blargg wrote them to hold a
player to what a console does, and each carries a checksum he took on hardware,
so what they settle is settled at the second rung of the ladder rather than by
agreeing with another implementation.
"""

from __future__ import annotations

import binascii
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from ssmp import space as spacemod

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent

DIRECTORY_VARIABLE = "SSMP_SPC_DIR"

DEFAULT_DIRECTORY = ROOT / "spc"

ALONGSIDE = ROOT.parent / "spc"

SIGNATURE = b"SNES-SPC700 Sound File Data"

HEADER_BYTES = 0x100

RAM_BYTES = 0x10000

GENERATOR_AT = HEADER_BYTES + RAM_BYTES

GENERATOR_BYTES = 0x80

SHORTEST = GENERATOR_AT + GENERATOR_BYTES

PC_AT = 0x25
A_AT = 0x27
X_AT = 0x28
Y_AT = 0x29
PSW_AT = 0x2A
SP_AT = 0x2B

REGISTERS = 0x00F0


class NotAnSpc(ValueError):
    """The file handed over is not one of these."""


class Dump:
    """One audio unit, written down."""

    __slots__ = ("a", "generator", "memory", "pc", "psw", "sp", "x", "y")

    def __init__(self, raw: bytes) -> None:
        if not raw.startswith(SIGNATURE):
            raise NotAnSpc(
                f"this does not begin with {SIGNATURE.decode()!r}, so it is not a"
                " written-down audio unit and there is nothing here to restore"
            )
        if len(raw) < SHORTEST:
            raise NotAnSpc(
                f"an audio unit written down is at least {SHORTEST} bytes and this"
                f" is {len(raw)}, so the sound generator's registers are missing"
            )
        self.pc = raw[PC_AT] | raw[PC_AT + 1] << 8
        self.a = raw[A_AT]
        self.x = raw[X_AT]
        self.y = raw[Y_AT]
        self.psw = raw[PSW_AT]
        self.sp = raw[SP_AT]
        self.memory = bytes(raw[HEADER_BYTES : HEADER_BYTES + RAM_BYTES])
        self.generator = bytes(raw[GENERATOR_AT : GENERATOR_AT + GENERATOR_BYTES])

    @property
    def registers(self) -> bytes:
        """The sixteen addresses that are not memory, as the file holds them."""
        return self.memory[REGISTERS : REGISTERS + 0x10]

    @override
    def __repr__(self) -> str:
        return f"<Dump pc=${self.pc:04x} a=${self.a:02x} sp=${self.sp:02x}>"


def read(path: Path | str) -> Dump:
    """One of these files, off disk."""
    return Dump(Path(path).read_bytes())


def restore(unit: Any, dump: Dump) -> Any:
    """Put a written-down unit back into a real one, in the order that works.

    Memory first, because everything else sits on top of it. The sound
    generator next. The control register before the ports, since it is the write
    that clears them. The processor's own registers last, because the program
    starts the instant a caller steps the unit.
    """
    for at in range(RAM_BYTES):
        unit.space.memory.write8(at, dump.memory[at])
    for at in range(GENERATOR_BYTES):
        unit.space.dsp.write(at, dump.generator[at])
    held = dump.registers
    unit.space.test = held[0x00]
    unit.space.dsp_address = held[0x02]
    for index in range(3):
        unit.space.timers[index].divider = held[0x0A + index]
    unit.space.write8(spacemod.CONTROL, held[0x01])
    for index in range(4):
        unit.space.ports.console_writes(index, held[0x04 + index])
        unit.space.ports.unit_writes(index, held[0x04 + index])
    unit.processor.a = dump.a
    unit.processor.x = dump.x
    unit.processor.y = dump.y
    unit.processor.sp = dump.sp
    unit.processor.psw = dump.psw
    unit.processor.pc = dump.pc
    unit.cycles = 0
    return unit


def checksum(values: Sequence[int] | bytes) -> bytes:
    """The checksum blargg's checks compare against, low byte first.

    Read off his own routine rather than guessed at: a reflected CRC-32 begun at
    all ones with no final inversion. Confirmed against two expectations in
    `initial_regs.spc` that this model already reproduced before anything was
    changed, so the arithmetic was settled before it was used to settle anything
    else.
    """
    held = binascii.crc32(bytes(values)) ^ 0xFFFFFFFF
    return bytes((held >> (8 * index)) & 0xFF for index in range(4))


def directories(environment: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    """Every place these files are looked for, in the order they are looked at."""
    named = (environment if environment is not None else os.environ).get(DIRECTORY_VARIABLE, "")
    wanted = [Path(where) for where in named.split(os.pathsep) if where]
    wanted += [ALONGSIDE, DEFAULT_DIRECTORY]
    seen: list[Path] = []
    for where in wanted:
        if where not in seen:
            seen.append(where)
    return tuple(seen)


def find(name: str, environment: Mapping[str, str] | None = None) -> Path | None:
    """Where one of these files is on this machine, or nothing when it is not."""
    for where in directories(environment):
        candidate = where / name
        if candidate.is_file():
            return candidate
    return None


AGREED = bytes.fromhex("8fffdc8fffdd8fffde8fffdf6f")
"""Blargg's harness setting its four checksum bytes back to all ones.

Every one of his checks calls this before a sub-test and again after one agrees,
so finding it finds both the routine and, in its own operands, the four addresses
the running checksum lives at. The sequence sits at a different address in
different files, which is why it is searched for rather than written down.
"""

DISAGREED = bytes.fromhex("2de4dc2de4dd2de4de2de4df")
"""The harness pushing those same four bytes, which it does only to report them."""


class NoHarness(LookupError):
    """This file is a song rather than one of blargg's checks."""


class Harness:
    """Where the two routines are, and where the running checksum lives."""

    __slots__ = ("agreed", "checksum_at", "disagreed")

    def __init__(self, agreed: int, disagreed: int, checksum_at: int) -> None:
        self.agreed = agreed
        self.disagreed = disagreed
        self.checksum_at = checksum_at

    @override
    def __repr__(self) -> str:
        return f"<Harness agreed=${self.agreed:04x} disagreed=${self.disagreed:04x}>"


def _only(memory: bytes, wanted: bytes, what: str) -> int:
    first = memory.find(wanted)
    if first == -1:
        raise NoHarness(f"nothing in this file {what}, so it carries no checks to run")
    if memory.find(wanted, first + 1) != -1:
        raise NoHarness(
            f"more than one place in this file {what}, so which one the checks use"
            " cannot be decided from the bytes alone"
        )
    return first


def harness(dump: Dump) -> Harness:
    """Blargg's reporting routines, found by what they do rather than by address."""
    agreed = _only(dump.memory, AGREED, "sets four checksum bytes back to all ones")
    disagreed = _only(dump.memory, DISAGREED, "pushes those same four bytes to report them")
    return Harness(agreed, disagreed, dump.memory[agreed + 2])


class Outcome:
    """What a check said, and how far it got before saying it."""

    __slots__ = ("agreements", "cycles", "disagreed_at", "reported")

    def __init__(self, agreements: int, disagreed_at: int | None, reported: bytes, cycles: int):
        self.agreements = agreements
        self.disagreed_at = disagreed_at
        self.reported = reported
        self.cycles = cycles

    @property
    def agreed(self) -> bool:
        return self.disagreed_at is None

    @override
    def __repr__(self) -> str:
        if self.agreed:
            return f"<Outcome agreed, {self.agreements} sub-checks, {self.cycles} cycles>"
        return f"<Outcome disagreed on sub-check {self.disagreed_at}, {self.reported.hex()}>"


def play(unit: Any, dump: Dump, limit: int) -> Outcome:
    """Run one of blargg's checks and report what it decided.

    It reports by beeping, which is no use here, so this watches for the two
    routines it beeps from instead. A sub-check that disagrees stops the run,
    because the harness reports only the first one and everything after it is
    the harness restarting rather than more checking.

    A check that runs to the end hands control back to the boot program, which
    is what blargg's notes mean by re-running the bootloader so the next file
    can be sent without resetting the console. Reaching the boot window is
    therefore the signal that there is nothing left to run, and it is the same
    signal whichever file this is.

    The numbering is the harness's own: sub-check one is it starting up, and the
    codes in blargg's notes begin at two. A disagreement on `n` is therefore the
    failure code `n` he documents.
    """
    restore(unit, dump)
    found = harness(dump)
    agreements = 0
    for _ in range(limit):
        at = unit.processor.pc
        if at == found.agreed:
            agreements += 1
        elif at == found.disagreed:
            reported = bytes(unit.space.read8(found.checksum_at + index) for index in range(4))
            return Outcome(agreements, agreements + 1, reported, unit.cycles)
        elif at >= spacemod.BOOT_AT and unit.space.boot_visible:
            return Outcome(agreements, None, b"", unit.cycles)
        unit.step()
    raise TimeoutError(
        f"the check neither agreed nor disagreed within {limit} instructions,"
        f" reaching ${unit.processor.pc:04x} after {agreements} sub-checks"
    )
