from __future__ import annotations

from collections.abc import Callable
from typing import Any

WORK_RAM_BANKS = (0x7E, 0x7F)

WORK_RAM_BYTES = 0x20000

SYSTEM_AREA = 0x2000

ROM_FROM = 0x8000

ROM_BANK_BYTES = 0x8000

PORTS = range(0x2140, 0x2180)

PORT_MASK = 3

VIDEO_WORDS = 0x8000

VIDEO_MASK = VIDEO_WORDS - 1

BLANKING = 0x80

VERSION = 0x02

STEPS = (1, 32, 128, 128)

PATTERNS = {0: (0,), 1: (0, 1), 2: (0, 0), 3: (0, 0, 1, 1), 4: (0, 1, 2, 3)}

CHANNELS = 8

CHANNEL_REGISTERS = range(0x4300, 0x4380)

B_BUS = 0x2100

PRINTABLE = range(32, 127)

ROWS = 28

COLUMNS = 32

BYTE = 0xFF

WORD = 0xFFFF


def system_bank(bank: int) -> bool:
    return bank < 0x40 or 0x80 <= bank < 0xC0


def text_of(words: list[int]) -> str:
    return "".join(chr(word & BYTE) if word & BYTE in PRINTABLE else " " for word in words)


class Host:
    def __init__(self, rom: bytes, unit: Any) -> None:
        self.rom = rom
        self.unit = unit
        self.work_ram = bytearray(WORK_RAM_BYTES)
        self.video = [0] * VIDEO_WORDS
        self.address = 0
        self.increment = 0
        self.registers: dict[int, int] = {}
        self.blanking = 0
        self.interrupt = 0
        self.factor = BYTE
        self.product = 0
        self.dividend = 0
        self.quotient = 0
        self.channels = [[0] * 16 for _ in range(CHANNELS)]
        self.last_text = 0

    def read8(self, address: int) -> int:
        bank, offset = address >> 16, address & WORD
        if bank in WORK_RAM_BANKS:
            return self.work_ram[((bank - WORK_RAM_BANKS[0]) << 16) | offset]
        if offset >= ROM_FROM:
            at = (bank & 0x7F) * ROM_BANK_BYTES + offset - ROM_FROM
            return self.rom[at % len(self.rom)]
        if not system_bank(bank):
            return 0
        if offset < SYSTEM_AREA:
            return self.work_ram[offset]
        return self.read_register(offset)

    def read_register(self, offset: int) -> int:
        if offset in PORTS:
            return int(self.unit.read(offset & PORT_MASK))
        if offset in CHANNEL_REGISTERS:
            return self.channels[(offset >> 4) & 7][offset & 15]
        readers: dict[int, Callable[[], int]] = {
            0x4212: self.read_blanking,
            0x4210: self.read_interrupt,
            0x4214: lambda: self.quotient & BYTE,
            0x4215: lambda: self.quotient >> 8,
            0x4216: lambda: self.product & BYTE,
            0x4217: lambda: self.product >> 8,
            0x2139: lambda: self.video[self.address & VIDEO_MASK] & BYTE,
        }
        reader = readers.get(offset)
        return reader() if reader is not None else 0

    def read_blanking(self) -> int:
        self.blanking ^= BLANKING
        return self.blanking

    def read_interrupt(self) -> int:
        self.interrupt ^= BLANKING
        return self.interrupt | VERSION

    def write8(self, address: int, value: int) -> None:
        bank, offset = address >> 16, address & WORD
        if bank in WORK_RAM_BANKS:
            self.work_ram[((bank - WORK_RAM_BANKS[0]) << 16) | offset] = value
            return
        if offset >= ROM_FROM or not system_bank(bank):
            return
        if offset < SYSTEM_AREA:
            self.work_ram[offset] = value
            return
        self.write_register(offset, value)

    def write_register(self, offset: int, value: int) -> None:
        if offset in PORTS:
            self.unit.write(offset & PORT_MASK, value)
            return
        self.registers[offset] = value
        if offset in CHANNEL_REGISTERS:
            self.channels[(offset >> 4) & 7][offset & 15] = value
            return
        writer = self.writers().get(offset)
        if writer is not None:
            writer(value)

    def writers(self) -> dict[int, Any]:
        return {
            0x2115: self.set_increment,
            0x2116: lambda value: self.set_address((self.address & 0xFF00) | value),
            0x2117: lambda value: self.set_address((self.address & BYTE) | (value << 8)),
            0x2118: lambda value: self.write_video(value, high=False),
            0x2119: lambda value: self.write_video(value, high=True),
            0x4202: self.set_factor,
            0x4203: self.multiply,
            0x4204: lambda value: self.set_dividend((self.dividend & 0xFF00) | value),
            0x4205: lambda value: self.set_dividend((self.dividend & BYTE) | (value << 8)),
            0x4206: self.divide,
            0x420B: self.transfer,
        }

    def set_increment(self, value: int) -> None:
        self.increment = value

    def set_address(self, value: int) -> None:
        self.address = value

    def set_factor(self, value: int) -> None:
        self.factor = value

    def set_dividend(self, value: int) -> None:
        self.dividend = value

    def multiply(self, value: int) -> None:
        self.product = self.factor * value

    def divide(self, value: int) -> None:
        if value == 0:
            self.quotient, self.product = WORD, self.dividend
            return
        self.quotient, self.product = divmod(self.dividend, value)

    def write_video(self, value: int, high: bool) -> None:
        at = self.address & VIDEO_MASK
        word = self.video[at]
        self.video[at] = (word & BYTE) | (value << 8) if high else (word & 0xFF00) | value
        if not high and value in PRINTABLE:
            self.last_text = at
        if high == bool(self.increment & BLANKING):
            self.address = (self.address + STEPS[self.increment & 3]) & WORD

    def transfer(self, mask: int) -> None:
        for channel in range(CHANNELS):
            if mask & (1 << channel):
                self.run_channel(channel)

    def run_channel(self, channel: int) -> None:
        held = self.channels[channel]
        control, target = held[0], held[1]
        source, bank = held[2] | (held[3] << 8), held[4]
        count = (held[5] | (held[6] << 8)) or 0x10000
        pattern = PATTERNS.get(control & 7, (0,))
        for index in range(count):
            register = B_BUS + ((target + pattern[index % len(pattern)]) & BYTE)
            if control & 0x80:
                self.write8((bank << 16) | source, self.read8(register))
            else:
                self.write8(register, self.read8((bank << 16) | source))
            if not control & 0x08:
                source = (source + (-1 if control & 0x10 else 1)) & WORD
        self.channels[channel] = [*held[:5], 0, 0, *held[7:]]

    def base(self) -> int:
        return (self.registers.get(0x2107, 0) & 0xFC) << 8

    def row(self, number: int) -> str:
        start = self.base() + number * COLUMNS
        return text_of([self.video[(start + column) & VIDEO_MASK] for column in range(COLUMNS)])

    def screen(self) -> str:
        lines = [self.row(number).rstrip() for number in range(ROWS)]
        return "\n".join(line for line in lines if line)

    def current_line(self) -> str:
        return self.row(((self.last_text - self.base()) & VIDEO_MASK) // COLUMNS).strip()
