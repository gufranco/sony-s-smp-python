from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

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

TIMER_COUNT = 3


class Space:
    __slots__ = (
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

    def __init__(
        self,
        boot: Sequence[int] | None = None,
        memory: Any = None,
        dsp: Any = None,
        fill: int | None = None,
    ) -> None:
        self.boot = bytes(boot) if boot is not None else None
        self.memory = memory
        self.dsp = dsp
        self.ports = Ports()
        self.timers = [
            Timer(rates.SLOW_TIMER_CYCLES),
            Timer(rates.SLOW_TIMER_CYCLES),
            Timer(rates.FAST_TIMER_CYCLES),
        ]
        self.test = 0
        self.control = CONTROL_BOOT_VISIBLE
        self.boot_visible = True
        self.dsp_address = 0
        if fill is not None:
            self.write_all(fill)

    def reset(self) -> None:
        self.control |= CONTROL_BOOT_VISIBLE
        self.boot_visible = True

    def write_all(self, value: int) -> None:
        for address in range(SPACE):
            self.memory.write8(address, value & 0xFF)

    def read8(self, address: int) -> int:
        address &= SPACE - 1
        if REGISTERS_AT <= address < REGISTERS_AT + REGISTER_COUNT:
            return self._read_register(address)
        if self.boot_visible and address >= BOOT_AT:
            return self._read_boot(address)
        held: int = self.memory.read8(address)
        return held

    def write8(self, address: int, value: int) -> None:
        address &= SPACE - 1
        value &= 0xFF
        if REGISTERS_AT <= address < REGISTERS_AT + REGISTER_COUNT:
            self._write_register(address, value)
            return
        self.memory.write8(address, value)

    def _read_boot(self, address: int) -> int:
        if self.boot is None:
            from ssmp.errors import NoBootRom

            raise NoBootRom(
                "the boot window is visible and no boot program was supplied, so"
                " there is nothing at this address to read"
            )
        return self.boot[address - BOOT_AT]

    def _read_register(self, address: int) -> int:
        if PORT_0 <= address < PORT_0 + PORT_COUNT:
            return self.ports.unit_reads(address - PORT_0)
        if COUNTER_0 <= address < COUNTER_0 + TIMER_COUNT:
            return self.timers[address - COUNTER_0].read()
        if address == DSP_DATA:
            return self._read_dsp()
        if address == DSP_ADDRESS:
            return self.dsp_address
        if address in (SPARE_0, SPARE_0 + 1):
            held: int = self.memory.read8(address)
            return held
        return self._read_write_only(address)

    def _read_write_only(self, address: int) -> int:
        del address
        return 0x00

    def _read_dsp(self) -> int:
        if self.dsp is None:
            return 0
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
        self.memory.write8(address, value)

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
        if self.dsp is None:
            return
        if self.dsp_address & 0x80:
            return
        self.dsp.write(self.dsp_address & 0x7F, value)

    def spend(self, cycles: int) -> None:
        for one in self.timers:
            one.spend(cycles)

    @override
    def __repr__(self) -> str:
        window = "boot" if self.boot_visible else "memory"
        return f"<Space, top page reads {window}, control ${self.control:02X}>"
