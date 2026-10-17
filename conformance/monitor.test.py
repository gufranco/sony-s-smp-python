import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from conformance import monitor

SPIN = bytes((0x2F, 0xFE))

MOV_X_IMMEDIATE = 0xCD


def a_unit(program: bytes = monitor.MONITOR) -> Any:
    return ssmp.Chip("ssmp", boot=program, fill=0x00).reset()


class BootTest(unittest.TestCase):
    def test_a_program_is_padded_to_the_sixty_four_bytes_a_boot_program_is(self) -> None:
        # Arrange
        code = SPIN

        # Act
        image = monitor.boot(code)

        # Assert
        self.assertEqual(len(image), 64)

    def test_and_its_last_two_bytes_send_the_processor_to_the_top_page(self) -> None:
        # Arrange
        code = SPIN

        # Act
        image = monitor.boot(code)

        # Assert
        self.assertEqual(image[:2] + image[-2:], bytes((0x2F, 0xFE, 0xC0, 0xFF)))

    def test_the_monitor_fits_in_front_of_the_vector(self) -> None:
        # Arrange
        program = monitor.PROGRAM

        # Act
        room = 62 - len(program)

        # Assert
        self.assertGreaterEqual(room, 0)


class PeekTest(unittest.TestCase):
    def test_a_byte_the_console_put_in_memory_comes_back(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0x1234, 0x5A)

        # Act
        found = monitor.peek(unit, 0x1234)

        # Assert
        self.assertEqual(found, 0x5A)

    def test_the_top_page_reads_the_monitor_itself(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = monitor.peek(unit, 0xFFC0)

        # Assert
        self.assertEqual(found, MOV_X_IMMEDIATE)

    def test_an_address_aimed_at_once_can_be_read_again_and_again(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0x0400, 0x11)
        monitor.aim(unit, 0x0400)

        # Act
        found = [monitor.fetch(unit) for _ in range(3)]

        # Assert
        self.assertEqual(found, [0x11, 0x11, 0x11])

    def test_and_written_again_without_aiming_twice(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.aim(unit, 0x0400)
        monitor.store(unit, 0x22)

        # Act
        monitor.store(unit, 0x33)

        # Assert
        self.assertEqual(monitor.peek(unit, 0x0400), 0x33)

    def test_a_poke_at_a_port_reaches_the_console(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        monitor.poke(unit, 0xF7, 0x77)

        # Assert
        self.assertEqual(unit.read(3), 0x77)


class GeneratorTest(unittest.TestCase):
    def test_a_generator_register_written_through_the_pair_reads_back(self) -> None:
        # Arrange
        unit = a_unit()
        volume = 0x00

        # Act
        monitor.generator_write(unit, volume, 0x45)

        # Assert
        self.assertEqual(monitor.generator_read(unit, volume), 0x45)


class TallyTest(unittest.TestCase):
    def test_a_byte_that_never_changes_is_summed_once_per_read(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0x0400, 0x03)

        # Act
        _, total = monitor.tally(unit, 0x0400, reads=5, gap=10)

        # Assert
        self.assertEqual(total, 15)

    def test_the_span_covers_every_gap_and_every_read(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        spanned, _ = monitor.tally(unit, 0x0400, reads=5, gap=100)

        # Assert
        self.assertGreaterEqual(spanned, 500)


class SilenceTest(unittest.TestCase):
    def test_a_unit_that_never_answers_is_reported_rather_than_waited_on(self) -> None:
        # Arrange
        unit = a_unit(monitor.boot(SPIN))

        # Act
        with self.assertRaises(monitor.Unanswered) as caught:
            monitor.peek(unit, 0x0000)

        # Assert
        self.assertIn("never acknowledged", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
