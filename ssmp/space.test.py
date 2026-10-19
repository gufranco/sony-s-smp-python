import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from conformance import monitor

TEST = 0xF0

CONTROL = 0xF1

GENERATOR_ADDRESS = 0xF2

GENERATOR_DATA = 0xF3

FIRST_DIVIDER = 0xFA

FIRST_COUNTER = 0xFD

BOOT_VISIBLE = 0x80

ALL_THREE_TIMERS = 0x07

BOOT_AT = 0xFFC0

PADDING = 0xFFFD

MAIN_VOLUME_LEFT = 0x0C

WRITE_ONLY = (TEST, CONTROL, FIRST_DIVIDER, FIRST_DIVIDER + 1, FIRST_DIVIDER + 2)

SLOW = 128

ONE_SEED = 1

ANOTHER_SEED = 2


def a_unit(fill: int = 0x00) -> Any:
    return monitor.listening(ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=fill))


def powered_on(seed: int) -> Any:
    return ssmp.Chip("ssmp", boot=monitor.MONITOR, seed=seed)


def what_power_on_left(seed: int) -> tuple[list[int], list[int], int, int]:
    space = powered_on(seed).space
    return (
        [powered_on(seed).read(index) for index in range(4)],
        [space.read8(FIRST_COUNTER + timer) for timer in range(3)],
        space.read8(BOOT_AT),
        monitor.first_tick(powered_on(seed), 0, SLOW),
    )


def counting(unit: Any) -> list[bool]:
    held = []
    for timer in range(3):
        _, counted = monitor.tally(unit, FIRST_COUNTER + timer, reads=4, gap=300)
        held.append(counted > 0)
    return held


def with_the_window_off(marker: int) -> Any:
    unit = a_unit()
    for offset, byte in enumerate(monitor.MONITOR):
        monitor.poke(unit, BOOT_AT + offset, byte)
    monitor.poke(unit, PADDING, marker)
    monitor.poke(unit, CONTROL, 0x00)
    return unit


class MemoryTest(unittest.TestCase):
    def test_an_ordinary_address_reads_what_was_written_there(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0x1234, 0x5A)

        # Act
        found = monitor.peek(unit, 0x1234)

        # Assert
        self.assertEqual(found, 0x5A)

    def test_the_two_spare_registers_read_back_what_was_written(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0xF8, 0x11)
        monitor.poke(unit, 0xF9, 0x22)

        # Act
        found = (monitor.peek(unit, 0xF8), monitor.peek(unit, 0xF9))

        # Assert
        self.assertEqual(found, (0x11, 0x22))

    def test_even_after_the_memory_beneath_them_changes(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0xF8, 0x11)
        unit.dsp.memory.write8(0xF8, 0x99)

        # Act
        found = monitor.peek(unit, 0xF8)

        # Assert
        self.assertEqual(found, 0x11)

    def test_a_write_to_a_register_also_reaches_the_memory_beneath_it(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        monitor.poke(unit, FIRST_DIVIDER, 0x33)

        # Assert
        self.assertEqual(unit.dsp.memory.read8(FIRST_DIVIDER), 0x33)

    def test_and_so_does_a_write_to_a_counter_nothing_else_takes(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        monitor.poke(unit, FIRST_COUNTER, 0x55)

        # Assert
        self.assertEqual(unit.dsp.memory.read8(FIRST_COUNTER), 0x55)


class BootWindowTest(unittest.TestCase):
    def test_the_top_page_reads_the_boot_program_while_it_is_visible(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = (monitor.peek(unit, 0xFFFE), monitor.peek(unit, 0xFFFF))

        # Assert
        self.assertEqual(found, (0xC0, 0xFF))

    def test_a_write_under_the_window_does_not_show_through_it(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, PADDING, 0x5A)

        # Act
        found = monitor.peek(unit, PADDING)

        # Assert
        self.assertEqual(found, 0x00)

    def test_but_reaches_the_memory_beneath_once_the_window_is_off(self) -> None:
        # Arrange
        unit = with_the_window_off(marker=0x5A)

        # Act
        found = monitor.peek(unit, PADDING)

        # Assert
        self.assertEqual(found, 0x5A)

    def test_switching_it_off_hands_the_top_page_back_to_memory_entirely(self) -> None:
        # Arrange
        unit = with_the_window_off(marker=0x5A)
        monitor.poke(unit, 0xFFFF, 0x77)

        # Act
        found = monitor.peek(unit, 0xFFFF)

        # Assert
        self.assertEqual(found, 0x77)


class ControlTest(unittest.TestCase):
    def test_the_control_register_cannot_be_read_and_answers_zero(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, CONTROL, BOOT_VISIBLE | ALL_THREE_TIMERS)

        # Act
        found = monitor.peek(unit, CONTROL)

        # Assert
        self.assertEqual(found, 0x00)

    def test_each_timer_bit_turns_its_own_timer_on(self) -> None:
        # Arrange
        unit = a_unit()
        for timer in range(3):
            monitor.poke(unit, FIRST_DIVIDER + timer, 1)
        monitor.poke(unit, CONTROL, BOOT_VISIBLE | ALL_THREE_TIMERS)

        # Act
        found = counting(unit)

        # Assert
        self.assertEqual(found, [True, True, True])

    def test_clearing_a_bit_turns_that_timer_off(self) -> None:
        # Arrange
        unit = a_unit()
        for timer in range(3):
            monitor.poke(unit, FIRST_DIVIDER + timer, 1)
        monitor.poke(unit, CONTROL, BOOT_VISIBLE | ALL_THREE_TIMERS)
        monitor.poke(unit, CONTROL, BOOT_VISIBLE | 0x02)
        counting(unit)

        # Act
        found = counting(unit)

        # Assert
        self.assertEqual(found, [False, True, False])


class TimerRegisterTest(unittest.TestCase):
    def test_each_divider_reaches_its_own_timer(self) -> None:
        # Arrange
        unit = a_unit()
        for timer, divider in enumerate((1, 2, 4)):
            monitor.poke(unit, FIRST_DIVIDER + timer, divider)
        monitor.poke(unit, CONTROL, BOOT_VISIBLE | ALL_THREE_TIMERS)

        # Act
        found = [
            monitor.tally(unit, FIRST_COUNTER + timer, reads=40, gap=900) for timer in range(3)
        ]

        # Assert
        self.assertEqual(
            [
                abs(spanned / period - counted) < 1
                for (spanned, counted), period in zip(found, (128, 256, 64), strict=True)
            ],
            [True, True, True],
        )


class GeneratorTest(unittest.TestCase):
    def test_a_write_to_the_data_register_reaches_the_generator(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, GENERATOR_ADDRESS, MAIN_VOLUME_LEFT)
        monitor.poke(unit, GENERATOR_DATA, 0x34)

        # Act
        found = monitor.peek(unit, GENERATOR_DATA)

        # Assert
        self.assertEqual(found, 0x34)

    def test_the_address_register_reads_back_what_was_written(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, GENERATOR_ADDRESS, 0x91)

        # Act
        found = monitor.peek(unit, GENERATOR_ADDRESS)

        # Assert
        self.assertEqual(found, 0x91)

    def test_a_write_with_the_top_bit_of_the_address_set_is_dropped(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.generator_write(unit, MAIN_VOLUME_LEFT, 0x77)
        monitor.generator_write(unit, 0x80 | MAIN_VOLUME_LEFT, 0x34)

        # Act
        found = monitor.generator_read(unit, MAIN_VOLUME_LEFT)

        # Assert
        self.assertEqual(found, 0x77)

    def test_a_read_with_the_top_bit_set_still_folds_onto_the_register(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.generator_write(unit, MAIN_VOLUME_LEFT, 0x77)

        # Act
        found = monitor.generator_read(unit, 0x80 | MAIN_VOLUME_LEFT)

        # Assert
        self.assertEqual(found, 0x77)


class WriteOnlyTest(unittest.TestCase):
    def test_every_write_only_register_answers_zero_rather_than_what_was_written(self) -> None:
        # Arrange
        unit = a_unit()
        for address in WRITE_ONLY:
            monitor.poke(unit, address, BOOT_VISIBLE if address == CONTROL else 0x5A)

        # Act
        found = [monitor.peek(unit, address) for address in WRITE_ONLY]

        # Assert
        self.assertEqual(found, [0x00] * 5)

    def test_or_what_the_memory_underneath_holds(self) -> None:
        # Arrange
        unit = a_unit(fill=0xA5)

        # Act
        found = [monitor.peek(unit, address) for address in WRITE_ONLY]

        # Assert
        self.assertEqual(found, [0x00] * 5)


class PowerOnTest(unittest.TestCase):
    def test_one_seed_powers_on_the_same_unit_every_time(self) -> None:
        # Arrange
        first = what_power_on_left(ONE_SEED)

        # Act
        second = what_power_on_left(ONE_SEED)

        # Assert
        self.assertEqual(first, second)

    def test_another_seed_leaves_other_ports_counters_window_and_prescaler(self) -> None:
        # Arrange
        one = what_power_on_left(ONE_SEED)

        # Act
        another = what_power_on_left(ANOTHER_SEED)

        # Assert
        self.assertEqual([a != b for a, b in zip(one, another, strict=True)], [True] * 4)

    def test_a_reset_leaves_the_counters_power_on_left_while_it_stops_the_timers(self) -> None:
        # Arrange
        before = what_power_on_left(ONE_SEED)[1]
        unit = powered_on(ONE_SEED)

        # Act
        unit.reset()
        unit.space.spend(SLOW * 0x100 * 2)

        # Assert
        self.assertEqual(
            ([unit.space.read8(FIRST_COUNTER + timer) for timer in range(3)], before == [0] * 3),
            (before, False),
        )


if __name__ == "__main__":
    unittest.main()
