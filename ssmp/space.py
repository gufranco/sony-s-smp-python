from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

from ssmp import rates
from ssmp.ports import COUNT as PORT_COUNT
from ssmp.ports import Ports
from ssmp.timers import Timer

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Sequence

SPACE = 0x10000

REGISTERS_AT = 0x00F0

REGISTER_COUNT = 0x10

TEST = 0xF0
CONTROL = 0xF1
DSP_ADDRESS = 0xF2
DSP_DATA = 0xF3
PORT_0 = 0xF4
SPARE_0 = 0xF8
SPARE_COUNT = 2
TIMER_0_DIVIDER = 0xFA
COUNTER_0 = 0xFD

BOOT_AT = 0xFFC0

BOOT_BYTES = 0x40

CONTROL_TIMER_0 = 0x01
CONTROL_TIMER_1 = 0x02
CONTROL_TIMER_2 = 0x04
CONTROL_CLEAR_PORTS_01 = 0x10
CONTROL_CLEAR_PORTS_23 = 0x20
CONTROL_BOOT_VISIBLE = 0x80
CONTROL_CLEARED_BY_RESET = 0x37
CONTROL_TIMERS = (CONTROL_TIMER_0, CONTROL_TIMER_1, CONTROL_TIMER_2)

TIMER_COUNT = 3

BYTE = 0x100

STREAM = "ssmp.space"


class Space:
    __slots__ = (
        "auxiliary",
        "boot",
        "boot_visible",
        "control",
        "dsp",
        "dsp_address",
        "memory",
        "ports",
        "test",
        "timers",
    )

    def __init__(self, boot: Sequence[int], memory: Any, dsp: Any, seed: int) -> None:
        self.boot = bytes(boot)
        self.memory = memory
        self.dsp = dsp
        scrambled = random.Random(f"{STREAM}:{seed}")
        self.control = scrambled.randrange(BYTE)
        self.boot_visible = bool(self.control & CONTROL_BOOT_VISIBLE)
        self.test = scrambled.randrange(BYTE)
        self.dsp_address = scrambled.randrange(BYTE)
        self.auxiliary = bytearray(scrambled.randbytes(SPARE_COUNT))
        self.ports = Ports(scrambled)
        self.timers = _power_on_timers(scrambled, self.control)

    def reset(self) -> None:
        self.control = (self.control & ~CONTROL_CLEARED_BY_RESET) | CONTROL_BOOT_VISIBLE
        self.boot_visible = True
        for one in self.timers:
            one.enable(False)

    def read8(self, address: int) -> int:
        address &= SPACE - 1
        if REGISTERS_AT <= address < REGISTERS_AT + REGISTER_COUNT:
            return self._read_register(address)
        if self.boot_visible and address >= BOOT_AT:
            return self.boot[address - BOOT_AT]
        held: int = self.memory.read8(address)
        return held

    def write8(self, address: int, value: int) -> None:
        address &= SPACE - 1
        value &= 0xFF
        self.memory.write8(address, value)
        if REGISTERS_AT <= address < REGISTERS_AT + REGISTER_COUNT:
            self._write_register(address, value)

    def _read_register(self, address: int) -> int:
        if PORT_0 <= address < PORT_0 + PORT_COUNT:
            return self.ports.unit_reads(address - PORT_0)
        if COUNTER_0 <= address < COUNTER_0 + TIMER_COUNT:
            return self.timers[address - COUNTER_0].read()
        if address == DSP_DATA:
            return self._read_dsp()
        if address == DSP_ADDRESS:
            return self.dsp_address
        if SPARE_0 <= address < SPARE_0 + SPARE_COUNT:
            return self.auxiliary[address - SPARE_0]
        return self._read_write_only(address)

    def _read_write_only(self, address: int) -> int:
        del address
        return 0x00

    def _read_dsp(self) -> int:
        held: int = self.dsp.read(self.dsp_address & 0x7F)
        return held

    def _write_register(self, address: int, value: int) -> None:
        if PORT_0 <= address < PORT_0 + PORT_COUNT:
            self.ports.unit_writes(address - PORT_0, value)
            return
        if TIMER_0_DIVIDER <= address < TIMER_0_DIVIDER + TIMER_COUNT:
            self.timers[address - TIMER_0_DIVIDER].divider = value
            return
        if address == CONTROL:
            self._write_control(value)
            return
        if address == DSP_ADDRESS:
            self.dsp_address = value
            return
        if address == DSP_DATA:
            self._write_dsp(value)
            return
        if address == TEST:
            self.test = value
            return
        if SPARE_0 <= address < SPARE_0 + SPARE_COUNT:
            self.auxiliary[address - SPARE_0] = value

    def _write_control(self, value: int) -> None:
        self.control = value
        self.boot_visible = bool(value & CONTROL_BOOT_VISIBLE)
        self.timers[0].enable(bool(value & CONTROL_TIMER_0))
        self.timers[1].enable(bool(value & CONTROL_TIMER_1))
        self.timers[2].enable(bool(value & CONTROL_TIMER_2))
        self.ports.clear_from_console(
            bool(value & CONTROL_CLEAR_PORTS_01), bool(value & CONTROL_CLEAR_PORTS_23)
        )

    def _write_dsp(self, value: int) -> None:
        if self.dsp_address & 0x80:
            return
        self.dsp.write(self.dsp_address & 0x7F, value)

    def spend(self, cycles: int) -> None:
        for one in self.timers:
            one.spend(cycles)


def _power_on_timers(scrambled: random.Random, control: int) -> list[Timer]:
    prescaler = scrambled.randrange(rates.SLOW_TIMER_CYCLES)
    every = (rates.SLOW_TIMER_CYCLES, rates.SLOW_TIMER_CYCLES, rates.FAST_TIMER_CYCLES)
    return [
        Timer(ticks, scrambled, prescaler, bool(control & bit))
        for ticks, bit in zip(every, CONTROL_TIMERS, strict=True)
    ]
