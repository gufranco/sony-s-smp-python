import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from conformance import monitor

CONTROL = 0xF1

BOOT_VISIBLE = 0x80

PADDING = 0xFFFD

SPIN = bytes((0x2F, 0xFE))

STOP = 0xFF

WHY_NOT_BOOT_STARTS = "no boot program was found"


def a_unit(fill: int = 0x00) -> Any:
    return monitor.listening(ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=fill))


def without(module: str) -> Any:
    return mock.patch.dict(sys.modules, {module: None})


def a_catalogue(image: bytes) -> dict[str, Any]:
    return {
        "artifacts": [
            {
                "part": "ssmp",
                "processor": "spc700",
                "bytes": len(image),
                "accepted": [{"revision": "made up", "sha256": hashlib.sha256(image).hexdigest()}],
            }
        ]
    }


def with_the_window_off(unit: Any) -> Any:
    for offset, byte in enumerate(monitor.MONITOR):
        monitor.poke(unit, 0xFFC0 + offset, byte)
    monitor.poke(unit, PADDING, 0x5A)
    monitor.poke(unit, CONTROL, 0x00)
    return unit


class AvailabilityTest(unittest.TestCase):
    def test_a_machine_holding_nothing_has_nothing_available(self) -> None:
        # Arrange
        held: dict[str, Any] = {}

        # Act
        found = ssmp.available(held)

        # Assert
        self.assertEqual(found, {})

    def test_and_says_the_boot_program_is_what_is_missing(self) -> None:
        # Arrange
        held: dict[str, Any] = {}

        # Act
        said = ssmp.why_not(held)

        # Assert
        self.assertTrue(str(said).startswith(WHY_NOT_BOOT_STARTS), said)

    def test_the_refusal_names_the_variable_a_reader_can_set(self) -> None:
        # Arrange
        held: dict[str, Any] = {}

        # Act
        said = ssmp.why_not(held)

        # Assert
        self.assertIn("SSMP_BOOT_DIR", str(said))

    def test_a_machine_holding_one_has_it_available(self) -> None:
        # Arrange
        held = {"ssmp": (object(), Path("nowhere"))}

        # Act
        found = ssmp.available(held)

        # Assert
        self.assertEqual(sorted(found), ["ssmp"])

    def test_and_says_nothing_stands_in_the_way(self) -> None:
        # Arrange
        held = {"ssmp": (object(), Path("nowhere"))}

        # Act
        said = ssmp.why_not(held)

        # Assert
        self.assertIsNone(said)


class WithoutTheHalvesTest(unittest.TestCase):
    def test_a_machine_without_the_processor_has_nothing_available(self) -> None:
        # Arrange
        missing = without("spc700")

        # Act
        with missing:
            found = ssmp.available()

        # Assert
        self.assertEqual(found, {})

    def test_and_says_the_submodule_is_what_is_missing(self) -> None:
        # Arrange
        missing = without("spc700")

        # Act
        with missing:
            said = ssmp.why_not()

        # Assert
        self.assertIn("git submodule update --init --recursive", str(said))

    def test_a_machine_without_the_generator_is_refused_the_same_way(self) -> None:
        # Arrange
        missing = without("sdsp")

        # Act
        with missing:
            said = ssmp.why_not()

        # Assert
        self.assertIn("submodule", str(said))

    def test_a_unit_cannot_be_built_when_the_halves_are_not_here(self) -> None:
        # Arrange
        missing = without("spc700")

        # Act
        with missing, self.assertRaises(ssmp.NoBootRom) as caught:
            ssmp.Chip("ssmp", boot=monitor.MONITOR)

        # Assert
        self.assertIn("SPC700", str(caught.exception))


class ConstructionTest(unittest.TestCase):
    def test_a_program_of_the_wrong_length_is_refused(self) -> None:
        # Arrange
        program = monitor.MONITOR[:-1]

        # Act
        with self.assertRaises(ssmp.WrongShape) as caught:
            ssmp.Chip("ssmp", boot=program)

        # Assert
        self.assertIn("63", str(caught.exception))

    def test_a_program_handed_over_without_saying_what_it_is_is_marked_as_supplied(self) -> None:
        # Arrange
        program = monitor.MONITOR

        # Act
        unit = ssmp.Chip("ssmp", boot=program)

        # Assert
        self.assertEqual(
            (unit.identity.part, unit.identity.revision, unit.identity.bytes_long),
            ("ssmp", "supplied", 64),
        )

    def test_a_program_handed_over_with_its_record_carries_that_record(self) -> None:
        # Arrange
        identity = ssmp.identify(monitor.MONITOR, a_catalogue(monitor.MONITOR))

        # Act
        unit = ssmp.Chip("ssmp", boot=monitor.MONITOR, identity=identity)

        # Assert
        self.assertIs(unit.identity, identity)

    def test_a_unit_there_is_no_program_for_is_refused_by_name(self) -> None:
        # Arrange
        images: dict[str, Any] = {}

        # Act
        with self.assertRaises(ssmp.NoBootRom) as caught:
            ssmp.Chip("ssmp", images=images)

        # Assert
        self.assertIn("there is no boot program for ssmp", str(caught.exception))

    def test_a_unit_prints_its_name_its_cycles_and_which_window_is_showing(self) -> None:
        # Arrange
        unit = ssmp.Chip("ssmp", boot=monitor.MONITOR)
        unit.space.write8(CONTROL, BOOT_VISIBLE)

        # Act
        printed = repr(unit)

        # Assert
        self.assertEqual(printed, "<Chip ssmp, 0 cycles, top page reads boot>")

    def test_and_says_so_once_the_window_is_off(self) -> None:
        # Arrange
        unit = with_the_window_off(a_unit())

        # Act
        printed = repr(unit)

        # Assert
        self.assertTrue(printed.endswith("top page reads memory>"), printed)


class FromDiskTest(unittest.TestCase):
    def test_a_unit_runs_the_program_the_catalogue_points_at(self) -> None:
        # Arrange
        where = Path(self.enterContext(tempfile.TemporaryDirectory())) / "made-up.bin"
        where.write_bytes(monitor.MONITOR)
        identity = ssmp.identify(monitor.MONITOR, a_catalogue(monitor.MONITOR))
        unit = ssmp.Chip("ssmp", images={"ssmp": (identity, where)}, fill=0x00).reset()

        # Act
        monitor.poke(unit, 0x0400, 0x42)

        # Assert
        self.assertEqual(monitor.peek(unit, 0x0400), 0x42)

    def test_and_carries_the_identity_the_catalogue_gave_it(self) -> None:
        # Arrange
        where = Path(self.enterContext(tempfile.TemporaryDirectory())) / "made-up.bin"
        where.write_bytes(monitor.MONITOR)
        identity = ssmp.identify(monitor.MONITOR, a_catalogue(monitor.MONITOR))

        # Act
        unit = ssmp.Chip("ssmp", images={"ssmp": (identity, where)})

        # Assert
        self.assertEqual(unit.identity.revision, "made up")


class StartTest(unittest.TestCase):
    def test_the_processor_starts_where_the_program_says(self) -> None:
        # Arrange
        program = (SPIN + monitor.PROGRAM).ljust(62, b"\x00") + b"\xc2\xff"

        # Act
        unit = monitor.listening(ssmp.Chip("ssmp", boot=program, fill=0x00))

        # Assert
        self.assertEqual(monitor.peek(unit, 0xFFC2), monitor.PROGRAM[0])

    def test_building_a_unit_starts_nothing(self) -> None:
        # Arrange
        unit = ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=STOP)

        # Act
        with self.assertRaises(monitor.Unanswered) as caught:
            monitor.peek(unit, 0x1000)

        # Assert
        self.assertIn("never acknowledged", str(caught.exception))

    def test_a_fill_reaches_the_memory_the_unit_runs_on(self) -> None:
        # Arrange
        unit = a_unit(fill=0x5A)

        # Act
        found = monitor.peek(unit, 0x1234)

        # Assert
        self.assertEqual(found, 0x5A)

    def test_resetting_hands_the_same_unit_back(self) -> None:
        # Arrange
        unit = ssmp.Chip("ssmp", boot=monitor.MONITOR)

        # Act
        handed = unit.reset()

        # Assert
        self.assertIs(handed, unit)

    def test_a_byte_written_to_memory_survives_a_reset(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0x1234, 0x77)

        # Act
        unit.reset()

        # Assert
        self.assertEqual(monitor.peek(unit, 0x1234), 0x77)

    def test_a_reset_shows_the_boot_window_the_program_runs_from(self) -> None:
        # Arrange
        unit = with_the_window_off(a_unit())

        # Act
        unit.reset()

        # Assert
        self.assertEqual(monitor.peek(unit, PADDING), 0x00)

    def test_a_reset_stops_a_running_timer(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0xFA, 1)
        monitor.poke(unit, CONTROL, BOOT_VISIBLE | 0x01)

        # Act
        unit.reset()

        # Assert
        monitor.peek(unit, 0xFD)
        self.assertEqual(monitor.tally(unit, 0xFD, reads=4, gap=300)[1], 0)

    def test_a_reset_leaves_the_ports_holding_what_they_held(self) -> None:
        # Arrange
        unit = a_unit()
        unit.write(2, 0x5A)
        monitor.poke(unit, 0xF7, 0xA5)

        # Act
        unit.reset()

        # Assert
        self.assertEqual((unit.read(3), monitor.peek(unit, 0xF6)), (0xA5, 0x5A))


class RunningTest(unittest.TestCase):
    def test_every_cycle_the_processor_spends_is_charged_to_the_unit(self) -> None:
        # Arrange
        unit = a_unit()
        before = unit.cycles

        # Act
        spent = unit.run_for(200)

        # Assert
        self.assertEqual(unit.cycles - before, spent)

    def test_running_overshoots_rather_than_cutting_an_instruction_in_half(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        spent = unit.run_for(1)

        # Assert
        self.assertGreaterEqual(spent, 2)

    def test_one_step_costs_what_it_says_it_costs(self) -> None:
        # Arrange
        unit = a_unit()
        before = unit.cycles

        # Act
        spent = unit.step()

        # Assert
        self.assertEqual(unit.cycles - before, spent)

    def test_a_reset_does_not_clear_the_cycle_count(self) -> None:
        # Arrange
        unit = a_unit()
        spent = unit.run_for(100)

        # Act
        unit.reset()

        # Assert
        self.assertGreaterEqual(unit.cycles, spent)


if __name__ == "__main__":
    unittest.main()
