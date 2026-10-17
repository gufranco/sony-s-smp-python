from typing import Any

BOOT_BYTES = 0x40

BOOT_AT = 0xFFC0

READ = 0x00

WRITE = 0x40

LOW = 0x80

HIGH = 0xC0

SEQUENCE = 0x3F

PATIENCE = 64

POINTER = 0x00

GENERATOR_ADDRESS = 0xF2

GENERATOR_DATA = 0xF3

CONTROL = 0xF1

BOOT_VISIBLE = 0x80

FIRST_DIVIDER = 0xFA

FIRST_COUNTER = 0xFD

FLAGS = 0x6C

ECHO_WRITES_OFF = 0x20

DIRECTORY_PAGE = 0x5D

PITCH_HIGH = 0x03

UNIT_PITCH = 0x10

SOURCE = 0x04

ATTACK_DECAY = 0x05

GAIN = 0x07

ENVELOPE = 0x08

KEY_ON = 0x4C

NOISE_ON = 0x3D

DIRECTORY = 0x0400

SAMPLE = 0x0500

LINEAR_RISE_EVERY_SAMPLE = 0xDF

ENVELOPE_LEVELS = 128

SAMPLES_TO_RISE = 64

TALLY_READS = 120

RISING_FOR = 1500

WRITE_LEAD = 8

READ_LAG = 28

PROGRAM = bytes(
    (
        *(0xCD, 0x00),
        *(0xD8, 0xF4),
        *(0x8D, 0x00),
        *(0x3E, 0xF4),
        *(0xF0, 0xFC),
        *(0xF8, 0xF4),
        *(0xD8, 0x02),
        *(0xE3, 0x02, 0x0F),
        *(0xC3, 0x02, 0x06),
        *(0xF7, POINTER),
        *(0xC4, 0xF5),
        *(0x2F, 0x11),
        *(0xE4, 0xF5),
        *(0xD7, POINTER),
        *(0x2F, 0x0B),
        *(0xC3, 0x02, 0x05),
        *(0xFA, 0xF5, POINTER),
        *(0x2F, 0x03),
        *(0xFA, 0xF5, POINTER + 1),
        *(0xD8, 0xF4),
        *(0x2F, 0xD7),
    )
)


class Unanswered(Exception): ...


def boot(code: bytes) -> bytes:
    return code.ljust(BOOT_BYTES - 2, b"\x00") + BOOT_AT.to_bytes(2, "little")


MONITOR = boot(PROGRAM)


def say(unit: Any, op: int, argument: int | None = None) -> int:
    command = op | (unit.read(0) & SEQUENCE) % SEQUENCE + 1
    if argument is not None:
        unit.write(1, argument)
    unit.write(0, command)
    for _ in range(PATIENCE):
        if unit.read(0) == command:
            answer: int = unit.read(1)
            return answer
        unit.step()
    raise Unanswered(
        f"the unit never acknowledged {command:#04x}; port 0 reads {unit.read(0):#04x}"
        f" after {PATIENCE} instructions"
    )


def aim(unit: Any, address: int) -> None:
    say(unit, LOW, address & 0xFF)
    say(unit, HIGH, (address >> 8) & 0xFF)


def fetch(unit: Any) -> int:
    return say(unit, READ)


def store(unit: Any, value: int) -> None:
    say(unit, WRITE, value)


def peek(unit: Any, address: int) -> int:
    aim(unit, address)
    return fetch(unit)


def poke(unit: Any, address: int, value: int) -> None:
    aim(unit, address)
    store(unit, value)


def generator_write(unit: Any, register: int, value: int) -> None:
    poke(unit, GENERATOR_ADDRESS, register)
    poke(unit, GENERATOR_DATA, value)


def generator_read(unit: Any, register: int) -> int:
    poke(unit, GENERATOR_ADDRESS, register)
    return peek(unit, GENERATOR_DATA)


def tally(unit: Any, address: int, reads: int, gap: int) -> tuple[int, int]:
    aim(unit, address)
    fetch(unit)
    started = unit.cycles
    total = 0
    for _ in range(reads):
        unit.run_for(gap)
        total += fetch(unit)
    return unit.cycles - started, total


def timer_period(unit: Any, timer: int, divider: int, gap: int) -> float:
    poke(unit, FIRST_DIVIDER + timer, divider)
    poke(unit, CONTROL, BOOT_VISIBLE | 1 << timer)
    spanned, counted = tally(unit, FIRST_COUNTER + timer, reads=TALLY_READS, gap=gap)
    return spanned / counted


def key_on(unit: Any, header: int, gain: int, noise: bool = False) -> None:
    generator_write(unit, FLAGS, ECHO_WRITES_OFF)
    generator_write(unit, DIRECTORY_PAGE, DIRECTORY >> 8)
    poke(unit, DIRECTORY + 1, SAMPLE >> 8)
    poke(unit, DIRECTORY + 3, SAMPLE >> 8)
    poke(unit, SAMPLE, header)
    generator_write(unit, PITCH_HIGH, UNIT_PITCH)
    generator_write(unit, SOURCE, 0x00)
    generator_write(unit, ATTACK_DECAY, 0x00)
    generator_write(unit, GAIN, gain)
    generator_write(unit, NOISE_ON, 0x01 if noise else 0x00)
    generator_write(unit, KEY_ON, 0x01)


def sample_period(unit: Any) -> float:
    key_on(unit, header=0x03, gain=LINEAR_RISE_EVERY_SAMPLE)
    poke(unit, GENERATOR_ADDRESS, ENVELOPE)
    aim(unit, GENERATOR_DATA)
    first, started = fetch(unit), unit.cycles
    unit.run_for(RISING_FOR)
    last, ended = fetch(unit), unit.cycles
    period: float = (ended - started) / ((last - first) * SAMPLES_TO_RISE / ENVELOPE_LEVELS)
    return period


def switch(unit: Any, timer: int, on: bool) -> int:
    poke(unit, CONTROL, BOOT_VISIBLE | (1 << timer if on else 0))
    written: int = unit.cycles - WRITE_LEAD
    return written


def start(unit: Any, timer: int, divider: int) -> int:
    poke(unit, FIRST_DIVIDER + timer, divider)
    return switch(unit, timer, on=True)


def counter_at(unit: Any, timer: int, at: int) -> int:
    aim(unit, FIRST_COUNTER + timer)
    unit.run_for(max(1, at - unit.cycles - READ_LAG))
    return fetch(unit)
