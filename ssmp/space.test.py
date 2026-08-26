"""The sixty four kilobytes as the processor sees them, registers included."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import space
from ssmp.errors import NoBootRom


class Memory:
    """Sixty four kilobytes and nothing else, which is all a space needs of one."""

    def __init__(self, fill: int = 0) -> None:
        self.held = bytearray([fill & 0xFF]) * space.SPACE

    def read8(self, address: int) -> int:
        return self.held[address & (space.SPACE - 1)]

    def write8(self, address: int, value: int) -> None:
        self.held[address & (space.SPACE - 1)] = value & 0xFF


class Generator:
    """A sound generator that remembers what it was told."""

    def __init__(self) -> None:
        self.held = bytearray(0x80)
        self.written: list[tuple[int, int]] = []

    def read(self, address: int) -> int:
        return self.held[address & 0x7F]

    def write(self, address: int, value: int) -> None:
        self.written.append((address, value))
        self.held[address & 0x7F] = value & 0xFF


def _a_space(boot: bytes | None = None, fill: int = 0) -> space.Space:
    return space.Space(
        boot=bytes(range(space.BOOT_BYTES)) if boot is None else boot,
        memory=Memory(fill=fill),
        dsp=Generator(),
    )


class MemoryTest(unittest.TestCase):
    def test_an_ordinary_address_reads_what_was_written_there(self) -> None:
        held = _a_space()

        held.write8(0x1234, 0x5A)

        self.assertEqual(held.read8(0x1234), 0x5A)

    def test_an_address_past_the_end_wraps_into_the_space(self) -> None:
        held = _a_space()

        held.write8(space.SPACE + 0x10, 0x77)

        self.assertEqual(held.read8(0x10), 0x77)

    def test_only_the_low_byte_of_a_value_is_kept(self) -> None:
        held = _a_space()

        held.write8(0x1000, 0x1FF)

        self.assertEqual(held.read8(0x1000), 0xFF)

    def test_filling_the_whole_space_reaches_every_address(self) -> None:
        held = _a_space()

        held.write_all(0x3C)

        self.assertEqual({held.read8(at) for at in (0x0000, 0x1234, 0xEFFF)}, {0x3C})

    def test_a_space_asked_for_a_fill_puts_it_everywhere(self) -> None:
        held = space.Space(boot=bytes(space.BOOT_BYTES), memory=Memory(), dsp=None, fill=0x7E)

        self.assertEqual(held.memory.read8(0x2000), 0x7E)

    def test_a_space_asked_for_none_leaves_the_memory_as_it_found_it(self) -> None:
        held = space.Space(boot=bytes(space.BOOT_BYTES), memory=Memory(fill=0x11), dsp=None)

        self.assertEqual(held.memory.read8(0x2000), 0x11)

    def test_a_space_prints_which_window_is_showing(self) -> None:
        self.assertIn("boot", repr(_a_space()))


class BootWindowTest(unittest.TestCase):
    def test_the_top_page_reads_the_boot_program_when_it_is_visible(self) -> None:
        held = _a_space()

        self.assertEqual(held.read8(space.BOOT_AT), 0x00)

    def test_and_reads_memory_once_it_is_not(self) -> None:
        held = _a_space()
        held.write8(space.BOOT_AT, 0x5A)

        held.write8(space.CONTROL, 0x00)

        self.assertEqual(held.read8(space.BOOT_AT), 0x5A)

    def test_a_write_under_the_window_reaches_the_memory_beneath(self) -> None:
        held = _a_space()

        held.write8(space.BOOT_AT + 4, 0x5A)

        self.assertEqual(held.memory.read8(space.BOOT_AT + 4), 0x5A)

    def test_the_window_covers_the_whole_top_page(self) -> None:
        held = _a_space()

        self.assertEqual(held.read8(0xFFFF), space.BOOT_BYTES - 1)

    def test_a_visible_window_with_no_program_behind_it_is_refused(self) -> None:
        held = space.Space(boot=None, memory=Memory(), dsp=None)
        held.write8(space.CONTROL, space.CONTROL_BOOT_VISIBLE)

        with self.assertRaises(NoBootRom):
            held.read8(space.BOOT_AT)


class PortTest(unittest.TestCase):
    def test_a_write_to_a_port_leaves_it_for_the_console(self) -> None:
        held = _a_space()

        held.write8(space.PORT_0 + 1, 0x42)

        self.assertEqual(held.ports.console_reads(1), 0x42)

    def test_a_read_of_a_port_gives_what_the_console_left(self) -> None:
        held = _a_space()
        held.ports.console_writes(2, 0x99)

        self.assertEqual(held.read8(space.PORT_0 + 2), 0x99)

    def test_a_write_does_not_change_what_the_unit_reads_back(self) -> None:
        held = _a_space()
        held.ports.console_writes(0, 0x11)

        held.write8(space.PORT_0, 0x99)

        self.assertEqual(held.read8(space.PORT_0), 0x11)


class ControlTest(unittest.TestCase):
    def test_the_control_register_reads_back_what_was_written(self) -> None:
        held = _a_space()

        held.write8(space.CONTROL, 0x87)

        self.assertEqual(held.read8(space.CONTROL), 0x87)

    def test_each_timer_bit_turns_its_own_timer_on(self) -> None:
        held = _a_space()

        held.write8(space.CONTROL, 0x07)

        self.assertEqual([one.enabled for one in held.timers], [True, True, True])

    def test_clearing_a_bit_turns_that_timer_off(self) -> None:
        held = _a_space()
        held.write8(space.CONTROL, 0x07)

        held.write8(space.CONTROL, 0x02)

        self.assertEqual([one.enabled for one in held.timers], [False, True, False])

    def test_the_lower_clear_bit_drops_the_first_two_ports(self) -> None:
        held = _a_space()
        for at in range(4):
            held.ports.console_writes(at, 0xFF)

        held.write8(space.CONTROL, space.CONTROL_CLEAR_PORTS_01)

        self.assertEqual([held.read8(space.PORT_0 + at) for at in range(4)], [0, 0, 0xFF, 0xFF])

    def test_the_upper_clear_bit_drops_the_other_two(self) -> None:
        held = _a_space()
        for at in range(4):
            held.ports.console_writes(at, 0xFF)

        held.write8(space.CONTROL, space.CONTROL_CLEAR_PORTS_23)

        self.assertEqual([held.read8(space.PORT_0 + at) for at in range(4)], [0xFF, 0xFF, 0, 0])

    def test_clearing_happens_on_the_write_rather_than_while_the_bit_is_held(self) -> None:
        held = _a_space()
        held.write8(space.CONTROL, space.CONTROL_CLEAR_PORTS_01)

        held.ports.console_writes(0, 0x77)

        self.assertEqual(held.read8(space.PORT_0), 0x77)


class TimerRegisterTest(unittest.TestCase):
    def test_a_divider_goes_to_its_own_timer(self) -> None:
        held = _a_space()

        held.write8(space.TIMER_0_DIVIDER + 2, 0x20)

        self.assertEqual(held.timers[2].divider, 0x20)

    def test_a_counter_reads_what_its_timer_counted(self) -> None:
        held = _a_space()
        held.write8(space.TIMER_0_DIVIDER, 1)
        held.write8(space.CONTROL, space.CONTROL_TIMER_0)

        held.spend(held.timers[0].ticks_every * 3)

        self.assertEqual(held.read8(space.COUNTER_0), 3)

    def test_reading_a_counter_empties_it(self) -> None:
        held = _a_space()
        held.write8(space.TIMER_0_DIVIDER, 1)
        held.write8(space.CONTROL, space.CONTROL_TIMER_0)
        held.spend(held.timers[0].ticks_every * 3)
        held.read8(space.COUNTER_0)

        self.assertEqual(held.read8(space.COUNTER_0), 0)

    def test_spending_cycles_advances_every_timer_at_its_own_rate(self) -> None:
        held = _a_space()
        for at in range(3):
            held.write8(space.TIMER_0_DIVIDER + at, 1)
        held.write8(space.CONTROL, 0x07)

        held.spend(384)

        self.assertEqual([one.counter for one in held.timers], [3, 3, 8])

    def test_the_third_timer_runs_eight_times_faster_than_the_other_two(self) -> None:
        held = _a_space()

        self.assertEqual(held.timers[0].ticks_every, held.timers[2].ticks_every * 8)


class GeneratorTest(unittest.TestCase):
    def test_a_write_to_the_data_register_reaches_the_generator(self) -> None:
        held = _a_space()
        held.write8(space.DSP_ADDRESS, 0x12)

        held.write8(space.DSP_DATA, 0x34)

        self.assertEqual(held.dsp.written, [(0x12, 0x34)])

    def test_a_read_of_the_data_register_comes_from_the_generator(self) -> None:
        held = _a_space()
        held.dsp.held[0x12] = 0x56
        held.write8(space.DSP_ADDRESS, 0x12)

        self.assertEqual(held.read8(space.DSP_DATA), 0x56)

    def test_the_address_register_reads_back_what_was_written(self) -> None:
        held = _a_space()

        held.write8(space.DSP_ADDRESS, 0x91)

        self.assertEqual(held.read8(space.DSP_ADDRESS), 0x91)

    def test_a_write_with_the_top_bit_of_the_address_set_is_dropped(self) -> None:
        held = _a_space()
        held.write8(space.DSP_ADDRESS, 0x91)

        held.write8(space.DSP_DATA, 0x34)

        self.assertEqual(held.dsp.written, [])

    def test_a_read_with_the_top_bit_set_still_folds_onto_the_register(self) -> None:
        held = _a_space()
        held.dsp.held[0x11] = 0x77
        held.write8(space.DSP_ADDRESS, 0x91)

        self.assertEqual(held.read8(space.DSP_DATA), 0x77)

    def test_a_space_with_no_generator_answers_nothing_and_drops_writes(self) -> None:
        held = space.Space(boot=bytes(space.BOOT_BYTES), memory=Memory(), dsp=None)
        held.write8(space.DSP_ADDRESS, 0x12)

        held.write8(space.DSP_DATA, 0x34)

        self.assertEqual(held.read8(space.DSP_DATA), 0)


class WriteOnlyTest(unittest.TestCase):
    def test_the_test_register_keeps_what_it_was_given(self) -> None:
        held = _a_space()

        held.write8(space.TEST, 0x5A)

        self.assertEqual(held.test, 0x5A)

    def test_reading_it_answers_the_memory_underneath_rather_than_inventing(self) -> None:
        held = _a_space()
        held.memory.write8(space.TEST, 0x3C)

        held.write8(space.TEST, 0x5A)

        self.assertEqual(held.read8(space.TEST), 0x3C)

    def test_a_divider_reads_the_memory_underneath_too(self) -> None:
        held = _a_space()
        held.memory.write8(space.TIMER_0_DIVIDER, 0x21)

        held.write8(space.TIMER_0_DIVIDER, 0x99)

        self.assertEqual(held.read8(space.TIMER_0_DIVIDER), 0x21)

    def test_the_two_spare_registers_are_ordinary_memory(self) -> None:
        held = _a_space()

        held.write8(space.SPARE_0, 0x11)
        held.write8(space.SPARE_0 + 1, 0x22)

        self.assertEqual((held.read8(space.SPARE_0), held.read8(space.SPARE_0 + 1)), (0x11, 0x22))


if __name__ == "__main__":
    unittest.main()
