"""Four ports, two bytes each, and what keeps the two directions apart."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import ports


class ShapeTest(unittest.TestCase):
    def test_there_are_four_of_them(self) -> None:
        self.assertEqual(ports.COUNT, 4)

    def test_a_fresh_set_holds_what_it_was_filled_with(self) -> None:
        held = ports.Ports(fill=0x5A)

        self.assertEqual(held.console_reads(0), 0x5A)

    def test_and_holds_it_in_both_directions(self) -> None:
        held = ports.Ports(fill=0x5A)

        self.assertEqual(held.unit_reads(0), 0x5A)

    def test_it_prints_both_directions(self) -> None:
        held = ports.Ports()
        held.unit_writes(0, 0xAA)

        self.assertIn("aa", repr(held))


class DirectionTest(unittest.TestCase):
    def test_the_unit_reads_what_the_console_wrote(self) -> None:
        held = ports.Ports()

        held.console_writes(1, 0x42)

        self.assertEqual(held.unit_reads(1), 0x42)

    def test_the_console_reads_what_the_unit_wrote(self) -> None:
        held = ports.Ports()

        held.unit_writes(1, 0x42)

        self.assertEqual(held.console_reads(1), 0x42)

    def test_a_console_write_does_not_change_what_the_console_reads(self) -> None:
        held = ports.Ports()
        held.unit_writes(2, 0x11)

        held.console_writes(2, 0x99)

        self.assertEqual(held.console_reads(2), 0x11)

    def test_a_unit_write_does_not_change_what_the_unit_reads(self) -> None:
        held = ports.Ports()
        held.console_writes(2, 0x11)

        held.unit_writes(2, 0x99)

        self.assertEqual(held.unit_reads(2), 0x11)

    def test_two_writes_that_cross_leave_each_side_holding_its_own(self) -> None:
        held = ports.Ports()

        held.console_writes(3, 0x01)
        held.unit_writes(3, 0x02)

        self.assertEqual((held.unit_reads(3), held.console_reads(3)), (0x01, 0x02))

    def test_only_the_low_byte_of_a_value_is_kept(self) -> None:
        held = ports.Ports()

        held.unit_writes(0, 0x1FF)

        self.assertEqual(held.console_reads(0), 0xFF)

    def test_an_index_past_the_fourth_wraps_onto_the_four(self) -> None:
        held = ports.Ports()

        held.unit_writes(4, 0x7E)

        self.assertEqual(held.console_reads(0), 0x7E)


class ClearTest(unittest.TestCase):
    def test_clearing_the_lower_pair_drops_what_the_console_left_there(self) -> None:
        held = ports.Ports()
        for at in range(4):
            held.console_writes(at, 0xFF)

        held.clear_from_console(lower=True, upper=False)

        self.assertEqual([held.unit_reads(at) for at in range(4)], [0, 0, 0xFF, 0xFF])

    def test_clearing_the_upper_pair_drops_the_other_two(self) -> None:
        held = ports.Ports()
        for at in range(4):
            held.console_writes(at, 0xFF)

        held.clear_from_console(lower=False, upper=True)

        self.assertEqual([held.unit_reads(at) for at in range(4)], [0xFF, 0xFF, 0, 0])

    def test_clearing_both_drops_all_four(self) -> None:
        held = ports.Ports()
        for at in range(4):
            held.console_writes(at, 0xFF)

        held.clear_from_console(lower=True, upper=True)

        self.assertEqual([held.unit_reads(at) for at in range(4)], [0, 0, 0, 0])

    def test_clearing_neither_drops_nothing(self) -> None:
        held = ports.Ports()
        held.console_writes(0, 0xFF)

        held.clear_from_console(lower=False, upper=False)

        self.assertEqual(held.unit_reads(0), 0xFF)

    def test_what_the_unit_left_for_the_console_survives_a_clear(self) -> None:
        held = ports.Ports()
        held.unit_writes(0, 0xAB)

        held.clear_from_console(lower=True, upper=True)

        self.assertEqual(held.console_reads(0), 0xAB)


if __name__ == "__main__":
    unittest.main()
