import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from conformance import monitor

CONTROL = 0xF1

BOOT_VISIBLE = 0x80

CLEAR_PORTS_01 = 0x10

CLEAR_PORTS_23 = 0x20


def a_unit() -> Any:
    return ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=0x00).reset()


def clearing_then_copying(control: int) -> bytes:
    return monitor.boot(
        bytes(
            (
                *(0x8F, control, 0xF1),
                *(0xE4, 0xF4, 0xC4, 0xF4),
                *(0xE4, 0xF5, 0xC4, 0xF5),
                *(0xE4, 0xF6, 0xC4, 0xF6),
                *(0xE4, 0xF7, 0xC4, 0xF7),
                *(0x2F, 0xEE),
            )
        )
    )


def after_a_clear(control: int) -> list[int]:
    unit = ssmp.Chip("ssmp", boot=clearing_then_copying(control), fill=0x00)
    for index in range(4):
        unit.write(index, 0xFF)
    unit.reset().run_for(200)
    return [unit.read(index) for index in range(4)]


class ShapeTest(unittest.TestCase):
    def test_there_are_four_of_them_and_a_fifth_index_is_the_first_again(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0xF7, 0x3C)

        # Act
        found = unit.read(7)

        # Assert
        self.assertEqual(found, 0x3C)

    def test_and_a_console_write_past_the_fourth_lands_on_the_four(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.aim(unit, 0xF6)
        unit.write(6, 0x4B)

        # Act
        found = monitor.fetch(unit)

        # Assert
        self.assertEqual(found, 0x4B)


class DirectionTest(unittest.TestCase):
    def test_the_unit_reads_what_the_console_wrote(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.aim(unit, 0xF5)
        unit.write(1, 0x42)

        # Act
        found = monitor.fetch(unit)

        # Assert
        self.assertEqual(found, 0x42)

    def test_the_console_reads_what_the_unit_wrote(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        monitor.poke(unit, 0xF6, 0x42)

        # Assert
        self.assertEqual(unit.read(2), 0x42)

    def test_a_console_write_does_not_change_what_the_console_reads(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0xF7, 0x11)

        # Act
        unit.write(3, 0x99)

        # Assert
        self.assertEqual(unit.read(3), 0x11)

    def test_a_unit_write_does_not_change_what_the_unit_reads(self) -> None:
        # Arrange
        unit = a_unit()
        unit.write(3, 0x11)
        monitor.poke(unit, 0xF7, 0x99)

        # Act
        found = monitor.fetch(unit)

        # Assert
        self.assertEqual(found, 0x11)

    def test_two_writes_that_cross_leave_each_side_holding_its_own(self) -> None:
        # Arrange
        unit = a_unit()
        unit.write(2, 0x01)

        # Act
        monitor.poke(unit, 0xF6, 0x02)

        # Assert
        self.assertEqual((monitor.fetch(unit), unit.read(2)), (0x01, 0x02))

    def test_only_the_low_byte_of_a_console_write_is_kept(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.aim(unit, 0xF6)
        unit.write(2, 0x1FF)

        # Act
        found = monitor.fetch(unit)

        # Assert
        self.assertEqual(found, 0xFF)


class ClearTest(unittest.TestCase):
    def test_clearing_the_lower_pair_drops_what_the_console_left_there(self) -> None:
        # Arrange
        control = BOOT_VISIBLE | CLEAR_PORTS_01

        # Act
        found = after_a_clear(control)

        # Assert
        self.assertEqual(found, [0, 0, 0xFF, 0xFF])

    def test_clearing_the_upper_pair_drops_the_other_two(self) -> None:
        # Arrange
        control = BOOT_VISIBLE | CLEAR_PORTS_23

        # Act
        found = after_a_clear(control)

        # Assert
        self.assertEqual(found, [0xFF, 0xFF, 0, 0])

    def test_clearing_both_drops_all_four(self) -> None:
        # Arrange
        control = BOOT_VISIBLE | CLEAR_PORTS_01 | CLEAR_PORTS_23

        # Act
        found = after_a_clear(control)

        # Assert
        self.assertEqual(found, [0, 0, 0, 0])

    def test_clearing_neither_drops_nothing(self) -> None:
        # Arrange
        control = BOOT_VISIBLE

        # Act
        found = after_a_clear(control)

        # Assert
        self.assertEqual(found, [0xFF, 0xFF, 0xFF, 0xFF])

    def test_clearing_happens_on_the_write_rather_than_while_the_bit_is_held(self) -> None:
        # Arrange
        unit = ssmp.Chip("ssmp", boot=clearing_then_copying(0x90), fill=0x00).reset()
        unit.run_for(200)
        unit.write(0, 0x77)

        # Act
        unit.run_for(100)

        # Assert
        self.assertEqual(unit.read(0), 0x77)

    def test_what_the_unit_left_for_the_console_survives_a_clear(self) -> None:
        # Arrange
        program = monitor.boot(bytes((0x8F, 0xAB, 0xF4, 0x8F, 0xB0, 0xF1, 0x2F, 0xFE)))
        unit = ssmp.Chip("ssmp", boot=program, fill=0x00).reset()

        # Act
        unit.run_for(100)

        # Assert
        self.assertEqual(unit.read(0), 0xAB)


if __name__ == "__main__":
    unittest.main()
