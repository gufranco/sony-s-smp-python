import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from conformance import monitor

SLOW = 128

FAST = 16


class Running:
    def __init__(self, timer: int, divider: int) -> None:
        self.timer = timer
        self.unit: Any = ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=0x00).reset()
        self.started = monitor.start(self.unit, timer, divider)

    def switch(self, on: bool) -> int:
        return monitor.switch(self.unit, self.timer, on)

    def divide_by(self, divider: int, at: int) -> None:
        monitor.aim(self.unit, monitor.FIRST_DIVIDER + self.timer)
        self.unit.run_for(max(1, self.started + at - self.unit.cycles - monitor.READ_LAG))
        monitor.store(self.unit, divider)

    def wait_until(self, at: int) -> None:
        self.unit.run_for(max(1, self.started + at - self.unit.cycles))

    def counter_at(self, at: int) -> int:
        return monitor.counter_at(self.unit, self.timer, self.started + at)


class DividerTest(unittest.TestCase):
    def test_a_divider_holds_the_counter_back_by_that_many_ticks(self) -> None:
        # Arrange
        timer = Running(0, divider=4)

        # Act
        found = timer.counter_at(int(3.5 * 4 * SLOW))

        # Assert
        self.assertEqual(found, 3)

    def test_and_lets_it_through_on_the_last_one(self) -> None:
        # Arrange
        timer = Running(0, divider=4)

        # Act
        found = timer.counter_at(int(4.5 * 4 * SLOW))

        # Assert
        self.assertEqual(found, 4)

    def test_a_divider_of_zero_divides_by_256(self) -> None:
        # Arrange
        timer = Running(2, divider=0)

        # Act
        found = timer.counter_at(10 * 256 * FAST - 64)

        # Assert
        self.assertEqual(found, 9)

    def test_and_not_by_255(self) -> None:
        # Arrange
        timer = Running(2, divider=0)

        # Act
        found = timer.counter_at(10 * 255 * FAST + 64)

        # Assert
        self.assertEqual(found, 9)


class EnableTest(unittest.TestCase):
    def test_a_timer_nobody_turned_on_counts_nothing(self) -> None:
        # Arrange
        unit = ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=0x00).reset()
        monitor.poke(unit, monitor.FIRST_DIVIDER, 1)
        unit.run_for(20 * SLOW)

        # Act
        found = monitor.peek(unit, monitor.FIRST_COUNTER)

        # Assert
        self.assertEqual(found, 0)

    def test_fewer_cycles_than_its_period_moves_nothing(self) -> None:
        # Arrange
        timer = Running(0, divider=4)

        # Act
        found = timer.counter_at(int(0.75 * 4 * SLOW))

        # Assert
        self.assertEqual(found, 0)

    def test_turning_one_off_and_on_again_empties_the_counter(self) -> None:
        # Arrange
        timer = Running(0, divider=1)
        timer.wait_until(int(2.5 * SLOW))
        timer.switch(on=False)
        timer.started = timer.switch(on=True)

        # Act
        found = timer.counter_at(int(0.5 * SLOW))

        # Assert
        self.assertEqual(found, 0)

    def test_and_starts_its_divider_over(self) -> None:
        # Arrange
        timer = Running(0, divider=4)
        timer.wait_until(int(2.5 * SLOW))
        timer.switch(on=False)
        timer.started = timer.switch(on=True)

        # Act
        found = timer.counter_at(int(3.5 * SLOW))

        # Assert
        self.assertEqual(found, 0)

    def test_turning_on_a_timer_that_is_already_on_leaves_it_counting(self) -> None:
        # Arrange
        timer = Running(0, divider=1)
        timer.wait_until(int(2.5 * SLOW))
        timer.switch(on=True)

        # Act
        found = timer.counter_at(int(4.5 * SLOW))

        # Assert
        self.assertEqual(found, 4)

    def test_and_leaves_its_divider_where_it_was(self) -> None:
        # Arrange
        timer = Running(0, divider=4)
        timer.wait_until(int(2.5 * SLOW))
        timer.switch(on=True)

        # Act
        found = timer.counter_at(int(4.5 * SLOW))

        # Assert
        self.assertEqual(found, 1)


class CountTest(unittest.TestCase):
    def test_the_counter_is_four_bits_and_wraps(self) -> None:
        # Arrange
        timer = Running(0, divider=1)

        # Act
        found = timer.counter_at(int(20.5 * SLOW))

        # Assert
        self.assertEqual(found, 4)

    def test_reading_gives_what_the_counter_held_and_empties_it(self) -> None:
        # Arrange
        timer = Running(0, divider=1)
        first = timer.counter_at(int(3.5 * SLOW))

        # Act
        second = monitor.fetch(timer.unit)

        # Assert
        self.assertEqual((first, second), (3, 0))

    def test_it_goes_on_counting_after_a_read(self) -> None:
        # Arrange
        timer = Running(0, divider=1)
        timer.counter_at(int(3.5 * SLOW))

        # Act
        found = timer.counter_at(int(5.5 * SLOW))

        # Assert
        self.assertEqual(found, 2)


class MidCountTest(unittest.TestCase):
    def test_lowering_a_divider_below_the_stage_counts_on_the_very_next_tick(self) -> None:
        # Arrange
        timer = Running(0, divider=8)
        timer.divide_by(3, at=int(5.5 * SLOW))

        # Act
        found = timer.counter_at(int(6.6 * SLOW))

        # Assert
        self.assertEqual(found, 1)

    def test_raising_it_carries_the_stage_on_rather_than_starting_over(self) -> None:
        # Arrange
        timer = Running(0, divider=4)
        timer.divide_by(200, at=int(3.5 * SLOW))

        # Act
        found = timer.counter_at(int(201.5 * SLOW))

        # Assert
        self.assertEqual(found, 1)


if __name__ == "__main__":
    unittest.main()
