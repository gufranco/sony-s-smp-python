import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ssmp
from conformance import monitor

RECORD = Path(__file__).resolve().parent / "hardware.json"

GENERATOR_RECORD = (
    Path(__file__).resolve().parent.parent / "sony-s-dsp-python" / "conformance" / "hardware.json"
)

CLOCKS_PER_SAMPLE = 32

ECHO_START = 0x6D

ECHO_DELAY = 0x7D

ENDED = 0x7C

OUTPUT = 0x09

FULL_GAIN = 0x7F

ENVELOPE_AT_FULL_GAIN = FULL_GAIN << 4

ENVELOPE_SHIFT = 11


def declared() -> dict[str, Any]:
    found: dict[str, Any] = json.loads(RECORD.read_text())
    return found


def a_unit(fill: int = 0x00) -> Any:
    return monitor.listening(ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=fill))


def echoed_into(unit: Any, page: int) -> list[int]:
    monitor.generator_write(unit, ECHO_START, page)
    monitor.generator_write(unit, ECHO_DELAY, 0x00)
    monitor.generator_write(unit, monitor.FLAGS, 0x00)
    unit.run_for(500)
    return [monitor.peek(unit, (page << 8) + offset) for offset in range(4)]


class GeneratorTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["generator"]

    def test_a_sample_lasts_the_cycles_the_recorded_clock_gives(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = monitor.sample_period(unit)

        # Assert
        self.assertAlmostEqual(
            found, CLOCKS_PER_SAMPLE / self.held["clocksPerProcessorCycle"], delta=1
        )

    def test_the_record_says_the_two_halves_share_one_memory(self) -> None:
        # Arrange
        held = self.held

        # Act
        claimed = held["sharesMemoryWithTheProcessor"]

        # Assert
        self.assertIs(claimed, True)

    def test_so_the_generator_writes_its_echo_into_the_memory_the_processor_reads(self) -> None:
        # Arrange
        unit = a_unit(fill=0x5A)

        # Act
        found = echoed_into(unit, 0x20)

        # Assert
        self.assertEqual(found, [0x00] * 4)

    def test_and_reads_its_samples_out_of_the_memory_the_processor_wrote(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.key_on(unit, header=0x01, gain=FULL_GAIN)
        unit.run_for(2000)

        # Act
        found = monitor.generator_read(unit, ENDED)

        # Assert
        self.assertEqual(found, 0x01)

    def test_a_block_written_there_with_no_end_flag_does_not_end(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.key_on(unit, header=0x00, gain=FULL_GAIN)
        unit.run_for(2000)

        # Act
        found = monitor.generator_read(unit, ENDED)

        # Assert
        self.assertEqual(found, 0x00)

    def test_and_that_building_a_unit_leaves_the_generator_scrambled(self) -> None:
        # Arrange
        held = self.held

        # Act
        claimed = held["resetAtConstruction"]

        # Assert
        self.assertIs(claimed, False)

    def test_and_that_the_unit_reset_is_what_resets_it(self) -> None:
        # Arrange
        held = self.held

        # Act
        claimed = held["resetWithTheUnit"]

        # Assert
        self.assertIs(claimed, True)

    def test_a_reset_sets_every_generator_register_its_record_lists(self) -> None:
        # Arrange
        sets = json.loads(GENERATOR_RECORD.read_text())["resetLine"]["sets"]
        expected = [int(sets["registers"], 16)] * 0x80
        expected[monitor.FLAGS] = int(sets["FLG"], 16)
        unit = a_unit()

        # Act
        found = [monitor.generator_read(unit, register) for register in range(0x80)]

        # Assert
        self.assertEqual(found, expected)

    def test_and_starts_its_noise_where_the_record_says(self) -> None:
        # Arrange
        sets = json.loads(GENERATOR_RECORD.read_text())["resetLine"]["sets"]
        sample = ((int(sets["chip"]["noise"], 16) * 2) & 0xFFFF) - 0x10000
        expected = ((sample * ENVELOPE_AT_FULL_GAIN) >> ENVELOPE_SHIFT >> 8) & 0xFF
        unit = a_unit()
        monitor.key_on(unit, header=0x03, gain=FULL_GAIN, noise=True)
        unit.run_for(2000)

        # Act
        found = monitor.generator_read(unit, OUTPUT)

        # Assert
        self.assertEqual(found, expected)

    def test_a_generator_that_was_reset_writes_no_echo(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0xF000, 0x3C)
        unit.run_for(20_000)

        # Act
        found = monitor.peek(unit, 0xF000)

        # Assert
        self.assertEqual(found, 0x3C)

    def test_and_shares_the_same_memory_after_a_reset_as_before_it(self) -> None:
        # Arrange
        unit = a_unit(fill=0x5A)
        unit.reset()

        # Act
        found = echoed_into(unit, 0x30)

        # Assert
        self.assertEqual(found, [0x00] * 4)

    def test_it_does_not_claim_what_the_generator_produces_is_checked(self) -> None:
        # Arrange
        held = self.held

        # Act
        claimed = held["verified"]

        # Assert
        self.assertIs(claimed, False)

    def test_and_names_the_thing_that_would_settle_that(self) -> None:
        # Arrange
        held = self.held

        # Act
        settled_by = held["howToSettleIt"]

        # Assert
        self.assertIn("spc_dsp6", settled_by)


if __name__ == "__main__":
    unittest.main()
