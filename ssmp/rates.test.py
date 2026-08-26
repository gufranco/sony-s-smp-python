"""The arithmetic that turns one crystal into a cost in processor cycles."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import rates


class DivisionTest(unittest.TestCase):
    def test_the_crystal_divides_into_the_sampling_rate_without_a_remainder(self) -> None:
        self.assertEqual(rates.CRYSTAL_HZ % 768, 0)

    def test_and_into_the_processor(self) -> None:
        self.assertEqual(rates.CRYSTAL_HZ % rates.PROCESSOR_DIVISOR, 0)

    def test_and_into_both_timer_rates(self) -> None:
        for one in (rates.SLOW_TIMER_DIVISOR, rates.FAST_TIMER_DIVISOR):
            self.assertEqual(rates.CRYSTAL_HZ % one, 0, one)

    def test_the_sampling_rate_is_the_one_the_generator_records(self) -> None:
        self.assertEqual(rates.CRYSTAL_HZ // 768, 32_000)

    def test_the_processor_runs_at_a_little_over_a_megahertz(self) -> None:
        self.assertEqual(rates.PROCESSOR_HZ, 1_024_000)

    def test_two_timers_tick_at_eight_kilohertz(self) -> None:
        self.assertEqual(rates.SLOW_TIMER_HZ, 8_000)

    def test_the_third_ticks_eight_times_faster(self) -> None:
        self.assertEqual(rates.FAST_TIMER_HZ, rates.SLOW_TIMER_HZ * 8)


class CostTest(unittest.TestCase):
    def test_a_slow_tick_costs_the_cycles_the_ratio_names(self) -> None:
        self.assertEqual(rates.SLOW_TIMER_CYCLES, 128)

    def test_a_fast_tick_costs_an_eighth_of_that(self) -> None:
        self.assertEqual(rates.FAST_TIMER_CYCLES, 16)

    def test_the_cost_is_derived_from_the_two_rates_rather_than_tabulated(self) -> None:
        self.assertEqual(rates.cycles_per_tick(8_000, 1_024_000), 128)

    def test_a_unit_with_the_same_ratios_behaves_the_same_way(self) -> None:
        self.assertEqual(rates.cycles_per_tick(16_000, 2_048_000), rates.SLOW_TIMER_CYCLES)


class GeneratorTest(unittest.TestCase):
    def test_the_sample_rate_is_the_one_the_neighbouring_member_records(self) -> None:
        self.assertEqual(rates.SAMPLE_HZ, 32_000)

    def test_the_generator_runs_at_the_same_rate_as_the_processor(self) -> None:
        self.assertEqual(rates.GENERATOR_HZ, rates.PROCESSOR_HZ)

    def test_so_one_processor_cycle_costs_one_of_its_clocks(self) -> None:
        self.assertEqual(rates.GENERATOR_CLOCKS, 1)

    def test_and_that_is_derived_rather_than_written_down(self) -> None:
        self.assertEqual(
            rates.clocks_per_cycle(64_000 * rates.CLOCKS_PER_SAMPLE, 1_024_000),
            2,
        )

    def test_the_two_divisors_multiply_out_to_the_sample_divisor(self) -> None:
        self.assertEqual(rates.PROCESSOR_DIVISOR * rates.CLOCKS_PER_SAMPLE, rates.SAMPLE_DIVISOR)


if __name__ == "__main__":
    unittest.main()
