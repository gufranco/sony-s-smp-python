import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from conformance import monitor

PROCESSOR_HZ = 24_576_000 // 24

SAMPLE_HZ = 24_576_000 // 768


def a_unit() -> Any:
    return ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=0x00).reset()


class TimerCostTest(unittest.TestCase):
    def test_timer_0_ticks_every_128_processor_cycles(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = monitor.timer_period(unit, 0, divider=1, gap=1500)

        # Assert
        self.assertAlmostEqual(found, PROCESSOR_HZ / 8_000, delta=1)

    def test_and_so_does_timer_1(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = monitor.timer_period(unit, 1, divider=1, gap=1500)

        # Assert
        self.assertAlmostEqual(found, PROCESSOR_HZ / 8_000, delta=1)

    def test_timer_2_ticks_eight_times_as_often(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = monitor.timer_period(unit, 2, divider=1, gap=150)

        # Assert
        self.assertAlmostEqual(found, PROCESSOR_HZ / 64_000, delta=0.5)

    def test_so_timer_2_dividing_by_eight_keeps_pace_with_timer_0_dividing_by_one(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = monitor.timer_period(unit, 2, divider=8, gap=1500)

        # Assert
        self.assertAlmostEqual(found, PROCESSOR_HZ / 8_000, delta=1)


class GeneratorClockTest(unittest.TestCase):
    def test_a_sample_lasts_as_many_processor_cycles_as_the_two_rates_divide_into(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = monitor.sample_period(unit)

        # Assert
        self.assertAlmostEqual(found, PROCESSOR_HZ / SAMPLE_HZ, delta=1)


if __name__ == "__main__":
    unittest.main()
