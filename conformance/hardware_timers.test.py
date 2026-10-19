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

MANIFEST_OF_CHECKS = Path(__file__).resolve().parent / "checks.manifest.json"


def declared() -> dict[str, Any]:
    found: dict[str, Any] = json.loads(RECORD.read_text())
    return found


def a_unit(fill: int = 0x00) -> Any:
    return monitor.listening(ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=fill))


def named(entry: str) -> list[int]:
    return sorted(
        int(address, 16)
        for address, what in declared()["registers"]["map"].items()
        if entry in what
    )


class TimerTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["timers"]

    def test_there_are_as_many_counters_as_the_record_gives(self) -> None:
        # Arrange
        unit = a_unit()
        for timer in range(self.held["count"]):
            monitor.poke(unit, monitor.FIRST_DIVIDER + timer, 1)
        monitor.poke(unit, monitor.CONTROL, 0x80 | (1 << self.held["count"]) - 1)

        # Act
        found = [monitor.tally(unit, one, reads=3, gap=300)[1] > 0 for one in named("counter")]

        # Assert
        self.assertEqual(found, [True] * self.held["count"])

    def test_the_counter_wraps_at_the_width_the_record_gives(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        ticks = (1 << self.held["counterBits"]) + 4
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=1), tick)

        # Act
        found = monitor.counter_at(unit, 0, started + ticks * tick + tick // 2)

        # Assert
        self.assertEqual(found, 4)

    def test_a_divider_of_zero_divides_by_what_the_record_says(self) -> None:
        # Arrange
        period = self.held["dividerWhenZero"] * self.held["fastCyclesPerTick"]
        unit = a_unit()
        started = monitor.start(unit, 2, divider=0)

        # Act
        found = monitor.counter_at(unit, 2, started + 10 * period - 64)

        # Assert
        self.assertEqual(found, 9)

    def test_the_two_tick_costs_are_the_ones_measured(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = (
            monitor.timer_period(unit, 0, divider=1, gap=1500),
            monitor.timer_period(unit, 2, divider=1, gap=150),
        )

        # Assert
        self.assertEqual(
            [round(one) for one in found],
            [self.held["slowCyclesPerTick"], self.held["fastCyclesPerTick"]],
        )


def printed() -> dict[str, Any]:
    timers: dict[str, Any] = declared()["timers"]["printed"]
    return timers


def on_the_prescaler(cycle: int, period: int) -> int:
    first = monitor.first_tick(ssmp.Chip("ssmp", boot=monitor.MONITOR), 0, period)
    return cycle - (cycle - first) % period


class PrintedTimerTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["timers"]

    def test_the_printed_rates_are_the_tick_costs_the_unit_spends(self) -> None:
        # Arrange
        rates = printed()["prescalerRates"]
        timing = printed()["instructionTime"]
        cycle = timing["shortestNanoseconds"] / timing["shortestCycles"]
        unit = a_unit()

        # Act
        found = (
            monitor.timer_period(unit, 0, divider=1, gap=1500),
            monitor.timer_period(unit, 2, divider=1, gap=150),
        )

        # Assert
        self.assertEqual(
            [round(one) for one in found],
            [round(1e9 / rates["slowHz"] / cycle), round(1e9 / rates["fastHz"] / cycle)],
        )

    def test_switching_a_timer_on_leaves_the_one_prescaler_running(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        drawn = printed()["onePrescaler"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=1), tick)

        # Act
        found = monitor.counter_at(unit, 0, started + tick + tick // 5)

        # Assert
        self.assertEqual((found, drawn["document"]), (1, "developmentManual"))

    def test_a_divider_lowered_below_the_stage_waits_for_the_stage_to_wrap(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        said = printed()["dividerMatch"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=8), tick)
        monitor.aim(unit, monitor.FIRST_DIVIDER)
        unit.run_for(started + 5 * tick + tick // 2 - unit.cycles - monitor.READ_LAG)
        monitor.store(unit, 3)

        # Act
        found = monitor.counter_at(unit, 0, started + 6 * tick + tick // 2)

        # Assert
        self.assertEqual((found, said["page"]), (0, "3-5-2"))

    def test_switching_a_timer_off_and_on_clears_both_of_its_counters(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        said = printed()["enableClears"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=4), tick)
        unit.run_for(started + 6 * tick - unit.cycles)
        monitor.switch(unit, 0, on=False)
        restarted = on_the_prescaler(monitor.switch(unit, 0, on=True), tick)

        # Act
        found = monitor.counter_at(unit, 0, restarted + 3 * tick + tick // 2)

        # Assert
        self.assertEqual((found, said["page"]), (0, "3-5-2"))

    def test_reading_a_counter_empties_it(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        said = printed()["readClears"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=1), tick)
        first = monitor.counter_at(unit, 0, started + 3 * tick + tick // 2)

        # Act
        second = monitor.fetch(unit)

        # Assert
        self.assertEqual((first, second, said["page"]), (3, 0, "3-5-2"))

    def test_a_reset_stops_every_timer(self) -> None:
        # Arrange
        said = printed()["resetStops"]
        drawn = declared()["control"]["printed"]["whenReset"]
        unit = a_unit()
        for timer in range(3):
            monitor.poke(unit, monitor.FIRST_DIVIDER + timer, 1)
        monitor.poke(unit, monitor.CONTROL, monitor.BOOT_VISIBLE | 0x07)
        unit.reset()
        for timer in range(3):
            monitor.peek(unit, monitor.FIRST_COUNTER + timer)

        # Act
        found = [
            monitor.tally(unit, monitor.FIRST_COUNTER + timer, reads=3, gap=300)[1]
            for timer in range(3)
        ]

        # Assert
        self.assertEqual((found, said["page"], drawn["page"]), ([0, 0, 0], "3-5-2", "3-4-2"))


if __name__ == "__main__":
    unittest.main()
