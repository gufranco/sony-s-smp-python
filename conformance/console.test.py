"""The console's side of the protocol, checked against a unit that is not one.

Every case here uses a stand-in, so the file runs on a machine holding no boot
program. What it checks is that the sequence written down is the sequence played:
which ports, in which order, and what it does when nothing answers.

Whether the real part answers it is `boot.test.py`, which needs the real thing
and skips without it.
"""

import sys
import unittest
from pathlib import Path
from typing import override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import console


class Deaf:
    """A unit that never answers, which is what a wrong image looks like."""

    def __init__(self) -> None:
        self.written: list[tuple[int, int]] = []
        self.ran = 0

    def read(self, index: int) -> int:
        return 0x00

    def write(self, index: int, value: int) -> None:
        self.written.append((index, value))

    def run_for(self, cycles: int) -> int:
        self.ran += cycles
        return cycles


class Echoing(Deaf):
    """A unit that hands back whatever was last put in a port, and is ready."""

    def __init__(self) -> None:
        super().__init__()
        self.held = {0: console.READY_LOW, 1: console.READY_HIGH, 2: 0x00, 3: 0x00}

    @override
    def read(self, index: int) -> int:
        return self.held[index]

    @override
    def write(self, index: int, value: int) -> None:
        super().write(index, value)
        self.held[index] = value


class ReadyTest(unittest.TestCase):
    def test_a_unit_that_is_ready_is_waited_for_and_no_more(self) -> None:
        unit = Echoing()

        console.wait_for_ready(unit)

        self.assertEqual(unit.written, [])

    def test_a_unit_that_never_answers_is_reported_rather_than_waited_for_ever(self) -> None:
        with self.assertRaises(console.NeverAnswered):
            console.wait_for_ready(Deaf())

    def test_the_refusal_says_what_the_ports_held_instead(self) -> None:
        with self.assertRaises(console.NeverAnswered) as caught:
            console.wait_for_ready(Deaf())

        self.assertIn("0x0", str(caught.exception))

    def test_waiting_gives_the_unit_cycles_to_run_in(self) -> None:
        unit = Deaf()

        with self.assertRaises(console.NeverAnswered):
            console.wait_for_ready(unit)

        self.assertEqual(unit.ran, console.PATIENCE * console.SLICE)


class UploadTest(unittest.TestCase):
    def test_the_destination_goes_into_the_upper_two_ports(self) -> None:
        unit = Echoing()

        console.upload(unit, b"\x00", where=0x1234, jump=False)

        self.assertIn((2, 0x34), unit.written)
        self.assertIn((3, 0x12), unit.written)

    def test_the_start_byte_goes_into_port_zero(self) -> None:
        unit = Echoing()

        console.upload(unit, b"", jump=False)

        self.assertIn((0, console.START), unit.written)

    def test_each_byte_goes_in_through_port_one(self) -> None:
        unit = Echoing()

        console.upload(unit, b"\x11\x22", jump=False)

        self.assertEqual([value for at, value in unit.written if at == 1], [0x01, 0x11, 0x22])

    def test_each_byte_is_counted_off_through_port_zero(self) -> None:
        unit = Echoing()

        console.upload(unit, b"\x11\x22", jump=False)

        counted = [value for at, value in unit.written if at == 0]
        self.assertEqual(counted, [console.START, 0x00, 0x01])

    def test_what_the_unit_said_back_comes_back(self) -> None:
        unit = Echoing()

        said = console.upload(unit, b"\x11\x22", jump=False)

        self.assertEqual(said, [0x00, 0x01])

    def test_the_jump_puts_zero_in_port_one_and_the_count_in_port_zero(self) -> None:
        unit = Echoing()

        console.upload(unit, b"\x11\x22")

        self.assertEqual(unit.written[-2:], [(1, 0x00), (0, 0x04)])

    def test_a_block_that_follows_another_starts_with_the_running_count(self) -> None:
        unit = Echoing()

        console.upload(unit, b"\x11", after=4, jump=False)

        self.assertNotIn((0, console.START), unit.written)
        self.assertIn((0, 0x06), unit.written)

    def test_a_unit_that_stops_answering_mid_upload_is_reported(self) -> None:
        class Stops(Echoing):
            @override
            def read(self, index: int) -> int:
                if index == 0 and len(self.written) > 4:
                    return 0xFF
                return super().read(index)

        with self.assertRaises(console.NeverAnswered):
            console.upload(Stops(), b"\x11\x22\x33", jump=False)


class ConstantTest(unittest.TestCase):
    def test_the_two_ready_bytes_are_the_ones_a_console_waits_for(self) -> None:
        self.assertEqual((console.READY_LOW, console.READY_HIGH), (0xAA, 0xBB))

    def test_the_start_byte_is_the_one_the_boot_program_compares_against(self) -> None:
        self.assertEqual(console.START, 0xCC)

    def test_the_sample_program_ends_by_stopping(self) -> None:
        self.assertEqual(console.A_PROGRAM[-1], 0xFF)


if __name__ == "__main__":
    unittest.main()
