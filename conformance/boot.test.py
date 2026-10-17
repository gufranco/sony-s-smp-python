import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ssmp
from conformance import console, monitor

PRESENT = ssmp.why_not() is None

MONITOR_AT = 0x0300

CONTROL = 0xF1

PUSHING = bytes((0xE8, 0x5A, 0x2D, 0x5F, MONITOR_AT & 0xFF, MONITOR_AT >> 8))


def a_unit(fill: int = 0x00) -> Any:
    return ssmp.Chip("ssmp", fill=fill).reset()


def watched(unit: Any, after: int | None = None) -> Any:
    console.upload(unit, monitor.PROGRAM, MONITOR_AT, after=after)
    return unit


def the_boot_program() -> bytes:
    _, where = ssmp.available()["ssmp"]
    return Path(where).read_bytes()


@unittest.skipUnless(PRESENT, ssmp.why_not() or "")
class HandshakeTest(unittest.TestCase):
    def test_it_answers_the_two_bytes_a_console_waits_for(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        console.wait_for_ready(unit)

        # Assert
        self.assertEqual((unit.read(0), unit.read(1)), (console.READY_LOW, console.READY_HIGH))

    def test_it_says_nothing_on_the_other_two_ports(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        console.wait_for_ready(unit)

        # Assert
        self.assertEqual((unit.read(2), unit.read(3)), (0x00, 0x00))

    def test_it_then_waits_for_the_start_byte_and_echoes_it(self) -> None:
        # Arrange
        unit = a_unit()
        console.wait_for_ready(unit)
        unit.write(0, console.START)

        # Act
        unit.run_for(console.SLICE)

        # Assert
        self.assertEqual(unit.read(0), console.START)

    def test_and_goes_on_waiting_while_nothing_is_said_to_it(self) -> None:
        # Arrange
        unit = a_unit()
        console.wait_for_ready(unit)
        unit.run_for(50_000)
        still = (unit.read(0), unit.read(1))
        unit.write(0, console.START)

        # Act
        unit.run_for(console.SLICE)

        # Assert
        self.assertEqual(
            (still, unit.read(0)), ((console.READY_LOW, console.READY_HIGH), console.START)
        )


@unittest.skipUnless(PRESENT, ssmp.why_not() or "")
class UploadTest(unittest.TestCase):
    def test_a_program_uploaded_through_the_ports_runs(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)

        # Assert
        self.assertEqual(unit.read(3), 0x42)

    def test_it_leaves_what_it_wrote_where_it_wrote_it(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)

        # Assert
        self.assertEqual(unit.read(2), 0x5A)

    def test_the_uploaded_bytes_are_the_bytes_that_arrived(self) -> None:
        # Arrange
        unit = watched(a_unit())

        # Act
        held = bytes(monitor.peek(unit, MONITOR_AT + at) for at in range(len(monitor.PROGRAM)))

        # Assert
        self.assertEqual(held, monitor.PROGRAM)

    def test_a_program_uploaded_somewhere_else_runs_there(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        console.upload(unit, console.A_PROGRAM, 0x0400)

        # Assert
        self.assertEqual(unit.read(3), 0x42)

    def test_the_unit_acknowledges_every_byte_as_it_arrives(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        said = console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)

        # Assert
        self.assertEqual(said, list(range(len(console.A_PROGRAM))))

    def test_a_second_block_can_follow_the_first(self) -> None:
        # Arrange
        unit = a_unit()
        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE, jump=False)

        # Act
        console.upload(unit, console.ANOTHER_PROGRAM, 0x0400, after=len(console.A_PROGRAM))

        # Assert
        self.assertEqual(unit.read(3), 0x99)

    def test_and_the_first_block_is_still_where_it_was_put(self) -> None:
        # Arrange
        unit = a_unit()
        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE, jump=False)
        watched(unit, after=len(console.A_PROGRAM))

        # Act
        held = bytes(
            monitor.peek(unit, console.SOMEWHERE + at) for at in range(len(console.A_PROGRAM))
        )

        # Assert
        self.assertEqual(held, console.A_PROGRAM)


@unittest.skipUnless(PRESENT, ssmp.why_not() or "")
class MemoryTest(unittest.TestCase):
    def test_the_boot_program_clears_the_zero_page_before_the_handshake(self) -> None:
        # Arrange
        unit = watched(a_unit(fill=0xFF))

        # Act
        held = {monitor.peek(unit, at) for at in range(0x03, 0xF0)}

        # Assert
        self.assertEqual(held, {0x00})

    def test_and_clears_nothing_past_it(self) -> None:
        # Arrange
        unit = watched(a_unit(fill=0xFF))

        # Act
        held = {monitor.peek(unit, at) for at in range(0x0100, 0x0200)}

        # Assert
        self.assertEqual(held, {0xFF})

    def test_the_boot_window_covers_memory_rather_than_replacing_it(self) -> None:
        # Arrange
        unit = watched(a_unit())
        monitor.poke(unit, 0xFFC0, 0x5A)
        covered = monitor.peek(unit, 0xFFC0)
        monitor.poke(unit, CONTROL, 0x00)

        # Act
        under = monitor.peek(unit, 0xFFC0)

        # Assert
        self.assertEqual((covered, under), (the_boot_program()[0], 0x5A))

    def test_the_stack_pointer_is_where_the_boot_program_put_it(self) -> None:
        # Arrange
        unit = a_unit()
        console.upload(unit, monitor.PROGRAM, MONITOR_AT, jump=False)

        # Act
        console.upload(unit, PUSHING, console.SOMEWHERE, after=len(monitor.PROGRAM))

        # Assert
        self.assertEqual(monitor.peek(unit, 0x01EF), 0x5A)


@unittest.skipUnless(PRESENT, ssmp.why_not() or "")
class FoundOnThisMachineTest(unittest.TestCase):
    def test_a_unit_built_with_no_program_named_finds_one(self) -> None:
        # Arrange
        model = "ssmp"

        # Act
        unit = ssmp.Chip(model)

        # Assert
        self.assertEqual(unit.identity.part, "ssmp")

    def test_a_reset_starts_the_program_it_found_over_again(self) -> None:
        # Arrange
        unit = a_unit()
        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)
        unit.reset()

        # Act
        unit.run_for(6300)

        # Assert
        self.assertEqual((unit.read(0), unit.read(1)), (console.READY_LOW, console.READY_HIGH))


if __name__ == "__main__":
    unittest.main()
