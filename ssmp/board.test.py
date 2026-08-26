"""Building the unit, refusing to when it cannot be built, and saying why.

The cases that need a real boot program say so and skip without one. The rest
build their own sixty four bytes, so most of this file runs anywhere.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import board, firmware, space
from ssmp.errors import NoBootRom, WrongShape

MADE_UP = bytes(range(space.BOOT_BYTES))


def _an_identity() -> firmware.Identity:
    return firmware.Identity("ssmp", "spc700", "made up", space.BOOT_BYTES)


def _a_unit(fill: int | None = None) -> board.Chip:
    return board.Chip("ssmp", boot=MADE_UP, identity=_an_identity(), fill=fill)


class AvailabilityTest(unittest.TestCase):
    def test_a_machine_holding_nothing_has_nothing_available(self) -> None:
        self.assertEqual(board.available({}), {})

    def test_and_says_why_the_unit_cannot_be_built(self) -> None:
        self.assertEqual(board.why_not({}), board.WHY_NOT_BOOT)

    def test_a_machine_holding_one_has_it_available(self) -> None:
        held = {"ssmp": (_an_identity(), Path("nowhere"))}

        self.assertEqual(sorted(board.available(held)), ["ssmp"])

    def test_and_says_nothing_stands_in_the_way(self) -> None:
        held = {"ssmp": (_an_identity(), Path("nowhere"))}

        self.assertIsNone(board.why_not(held))

    def test_the_refusal_names_the_variable_a_reader_can_set(self) -> None:
        self.assertIn(firmware.DIRECTORY_VARIABLE, board.WHY_NOT_BOOT)

    def test_a_machine_without_the_two_halves_has_nothing_available(self) -> None:
        self.assertEqual(board.available(members=lambda: None), {})

    def test_and_says_the_halves_are_what_is_missing(self) -> None:
        self.assertEqual(board.why_not(members=lambda: None), board.WHY_NOT_PROCESSOR)

    def test_the_refusal_says_how_to_fetch_them(self) -> None:
        self.assertIn("submodule", board.WHY_NOT_PROCESSOR)

    def test_the_two_halves_are_the_processor_and_the_generator(self) -> None:
        found = board._members()

        self.assertEqual([one.__name__ for one in found] if found else [], ["spc700", "sdsp"])


class ConstructionTest(unittest.TestCase):
    def test_a_unit_can_be_built_from_a_program_handed_straight_to_it(self) -> None:
        unit = _a_unit()

        self.assertEqual(unit.part, "ssmp")

    def test_a_program_of_the_wrong_length_is_refused(self) -> None:
        with self.assertRaises(WrongShape):
            board.Chip("ssmp", boot=MADE_UP[:-1], identity=_an_identity())

    def test_a_program_handed_over_without_saying_what_it_is_is_marked_as_supplied(self) -> None:
        unit = board.Chip("ssmp", boot=MADE_UP)

        self.assertEqual(unit.identity.revision, "supplied")

    def test_a_unit_there_is_no_program_for_is_refused(self) -> None:
        with self.assertRaises(NoBootRom):
            board.Chip("nosuchunit", images={})

    def test_the_refusal_names_the_unit_that_was_asked_for(self) -> None:
        with self.assertRaises(NoBootRom) as caught:
            board.Chip("nosuchunit", images={})

        self.assertIn("nosuchunit", str(caught.exception))

    def test_a_unit_prints_the_name_and_which_window_is_showing(self) -> None:
        self.assertIn("boot", repr(_a_unit()))


class WithoutTheHalvesTest(unittest.TestCase):
    def test_a_unit_cannot_be_built_when_the_halves_are_not_here(self) -> None:
        with self.assertRaises(NoBootRom):
            board.Chip("ssmp", boot=MADE_UP, identity=_an_identity(), members=lambda: None)

    def test_the_refusal_says_which_half_is_missing(self) -> None:
        with self.assertRaises(NoBootRom) as caught:
            board.Chip("ssmp", boot=MADE_UP, identity=_an_identity(), members=lambda: None)

        self.assertIn("SPC700", str(caught.exception))


class FromDiskTest(unittest.TestCase):
    """Reading the program off disk, without needing the real one to do it."""

    def test_a_unit_reads_the_program_from_where_the_catalogue_points(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "made-up.bin"
            path.write_bytes(MADE_UP)

            unit = board.Chip("ssmp", images={"ssmp": (_an_identity(), path)})

            self.assertEqual(unit.processor.pc, MADE_UP[62] | MADE_UP[63] << 8)

    def test_and_carries_the_identity_the_catalogue_gave_it(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "made-up.bin"
            path.write_bytes(MADE_UP)

            unit = board.Chip("ssmp", images={"ssmp": (_an_identity(), path)})

            self.assertEqual(unit.identity.revision, "made up")


class StartTest(unittest.TestCase):
    def test_the_processor_starts_where_the_program_says(self) -> None:
        unit = _a_unit()

        self.assertEqual(unit.processor.pc, MADE_UP[62] | MADE_UP[63] << 8)

    def test_the_top_page_reads_the_program_rather_than_memory(self) -> None:
        unit = _a_unit()

        self.assertTrue(unit.space.boot_visible)

    def test_a_fill_reaches_the_memory_the_unit_runs_on(self) -> None:
        unit = _a_unit(fill=0x5A)

        self.assertEqual(unit.space.memory.read8(0x1234), 0x5A)

    def test_resetting_takes_it_back_and_hands_it_over(self) -> None:
        unit = _a_unit()

        self.assertIs(unit.reset(), unit)

    def test_and_the_memory_it_ran_on_is_gone(self) -> None:
        unit = _a_unit(fill=0x00)
        unit.space.memory.write8(0x1234, 0x77)

        unit.reset()

        self.assertEqual(unit.space.memory.read8(0x1234), 0x00)


class RunningTest(unittest.TestCase):
    def test_every_cycle_the_processor_spends_is_charged_to_the_unit(self) -> None:
        unit = _a_unit()
        before = unit.cycles

        spent = unit.run_for(200)

        self.assertEqual(unit.cycles - before, spent)

    def test_running_overshoots_rather_than_cutting_an_instruction_in_half(self) -> None:
        unit = _a_unit()

        spent = unit.run_for(1)

        self.assertGreaterEqual(spent, 1)

    def test_one_step_costs_what_it_says_it_costs(self) -> None:
        unit = _a_unit()
        before = unit.cycles

        spent = unit.step()

        self.assertEqual(unit.cycles - before, spent)

    def test_the_timers_advance_with_the_processor(self) -> None:
        unit = _a_unit()
        unit.space.write8(0xFA, 1)
        unit.space.write8(0xF1, 0x01)

        unit.run_for(unit.space.timers[0].ticks_every * 4)

        self.assertGreater(unit.space.timers[0].counter, 0)


class PortTest(unittest.TestCase):
    def test_a_byte_the_console_writes_reaches_the_unit(self) -> None:
        unit = _a_unit()

        unit.write(2, 0x42)

        self.assertEqual(unit.space.ports.unit_reads(2), 0x42)

    def test_a_byte_the_unit_writes_reaches_the_console(self) -> None:
        unit = _a_unit()

        unit.space.ports.unit_writes(3, 0x99)

        self.assertEqual(unit.read(3), 0x99)


if __name__ == "__main__":
    unittest.main()
