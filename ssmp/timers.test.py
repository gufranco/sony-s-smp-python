"""What a timer counts, what a read of one costs, and what zero means."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import timers


def _running(ticks_every: int = 16, divider: int = 1) -> timers.Timer:
    held = timers.Timer(ticks_every)
    held.divider = divider
    held.enable(True)
    return held


class DividerTest(unittest.TestCase):
    def test_a_divider_names_itself(self) -> None:
        held = timers.Timer(16)
        held.divider = 5

        self.assertEqual(held.divides_by(), 5)

    def test_a_divider_of_zero_names_the_whole_range(self) -> None:
        held = timers.Timer(16)
        held.divider = 0

        self.assertEqual(held.divides_by(), timers.DIVIDER_WHEN_ZERO)

    def test_the_whole_range_is_two_hundred_and_fifty_six(self) -> None:
        self.assertEqual(timers.DIVIDER_WHEN_ZERO, 256)


class EnableTest(unittest.TestCase):
    def test_a_fresh_timer_is_off(self) -> None:
        self.assertFalse(timers.Timer(16).enabled)

    def test_a_timer_that_is_off_counts_nothing(self) -> None:
        held = timers.Timer(16)
        held.divider = 1

        held.spend(1000)

        self.assertEqual(held.counter, 0)

    def test_turning_one_on_starts_it_counting_from_now(self) -> None:
        held = timers.Timer(16)
        held.divider = 1
        held.enable(True)
        held.spend(40)
        held.enable(False)

        held.enable(True)

        self.assertEqual((held.stage, held.counter, held.waited), (0, 0, 0))

    def test_turning_on_a_timer_that_is_already_on_leaves_it_counting(self) -> None:
        held = _running()
        held.spend(16)

        held.enable(True)

        self.assertEqual(held.counter, 1)

    def test_a_timer_prints_whether_it_is_running(self) -> None:
        self.assertIn("off", repr(timers.Timer(16)))
        self.assertIn("on", repr(_running()))


class CountTest(unittest.TestCase):
    def test_one_tick_of_a_timer_dividing_by_one_moves_the_counter(self) -> None:
        held = _running(ticks_every=16, divider=1)

        held.spend(16)

        self.assertEqual(held.counter, 1)

    def test_fewer_cycles_than_a_tick_moves_nothing(self) -> None:
        held = _running(ticks_every=16, divider=1)

        held.spend(15)

        self.assertEqual(held.counter, 0)

    def test_the_remainder_carries_so_two_short_runs_equal_one_long_one(self) -> None:
        held = _running(ticks_every=16, divider=1)

        held.spend(9)
        held.spend(7)

        self.assertEqual(held.counter, 1)

    def test_a_divider_holds_the_counter_back_by_that_many_ticks(self) -> None:
        held = _running(ticks_every=16, divider=4)

        held.spend(16 * 3)

        self.assertEqual(held.counter, 0)

    def test_and_lets_it_through_on_the_last_one(self) -> None:
        held = _running(ticks_every=16, divider=4)

        held.spend(16 * 4)

        self.assertEqual(held.counter, 1)

    def test_the_counter_is_four_bits_and_wraps(self) -> None:
        held = _running(ticks_every=16, divider=1)

        held.spend(16 * 16)

        self.assertEqual(held.counter, 0)

    def test_a_timer_dividing_by_zero_takes_the_full_range_to_move(self) -> None:
        held = _running(ticks_every=16, divider=0)

        held.spend(16 * 255)

        self.assertEqual(held.counter, 0)


class ReadTest(unittest.TestCase):
    def test_reading_gives_what_the_counter_held(self) -> None:
        held = _running(ticks_every=16, divider=1)
        held.spend(16 * 3)

        self.assertEqual(held.read(), 3)

    def test_reading_empties_it(self) -> None:
        held = _running(ticks_every=16, divider=1)
        held.spend(16 * 3)
        held.read()

        self.assertEqual(held.read(), 0)

    def test_it_goes_on_counting_after_a_read(self) -> None:
        held = _running(ticks_every=16, divider=1)
        held.spend(16 * 3)
        held.read()

        held.spend(16 * 2)

        self.assertEqual(held.read(), 2)


if __name__ == "__main__":
    unittest.main()
