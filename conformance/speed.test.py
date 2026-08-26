from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import speed  # noqa: E402


class TimedTest(unittest.TestCase):
    """That a run is reported by its median rather than its mean.

    One scheduling hiccup on a shared runner moves a mean and moves a median
    much less, and the difference between the two is larger than any change to
    this code worth arguing about.
    """

    def test_the_median_is_the_middle_reading(self) -> None:
        found = speed.Timed("cycle", 100, [0.4, 0.1, 0.2])

        self.assertEqual(found.median(), 0.2)

    def test_the_rate_is_calls_over_that_median(self) -> None:
        found = speed.Timed("cycle", 100, [0.5, 0.5, 0.5])

        self.assertEqual(found.rate(), 200.0)

    def test_a_run_above_the_floor_beats_it(self) -> None:
        found = speed.Timed("cycle", 1000, [0.001])

        self.assertTrue(found.beats(1000))

    def test_and_one_below_it_does_not(self) -> None:
        found = speed.Timed("cycle", 1, [1.0])

        self.assertFalse(found.beats(1000))

    def test_a_run_that_took_no_time_is_not_read_as_infinitely_fast(self) -> None:
        """A clock too coarse to see the work is a reading, not a result."""
        found = speed.Timed("cycle", 100, [0.0])

        self.assertEqual(found.rate(), 0.0)
        self.assertFalse(found.beats(1))


class ReportTest(unittest.TestCase):
    def test_the_report_names_the_rate_the_floor_and_the_runtime(self) -> None:
        lines = speed.lines_for(speed.Timed("cycle", 1000, [0.001]), floor=1000)
        held = "\n".join(lines)

        self.assertIn("cycle", held)
        self.assertIn("floor", held)
        self.assertIn(f"{sys.version_info.major}.{sys.version_info.minor}", held)

    def test_a_run_under_the_floor_says_so(self) -> None:
        lines = speed.lines_for(speed.Timed("cycle", 1, [1.0]), floor=1_000_000)

        self.assertTrue(any("below" in one for one in lines), lines)


class AvailabilityTest(unittest.TestCase):
    def test_it_asks_the_package_rather_than_deciding_for_itself(self) -> None:
        import ssmp

        self.assertEqual(speed.unavailable(), ssmp.why_not())


class MainTest(unittest.TestCase):
    def run_main(self, **changes: object) -> tuple[int, str]:
        """One run of the tool, with the unit always reported as available.

        Every case below is about what the tool does once it has something to
        measure, and a runner has no boot program, so leaving this to the machine
        would make these cases pass here and fail there. The case that is about
        having nothing to measure passes its own answer instead.
        """
        changes.setdefault("unavailable", lambda: None)
        changes.setdefault("measure", lambda calls, repeats: speed.Timed("cycle", calls, [0.0001]))
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = speed.main(**changes)  # type: ignore[arg-type]
        return code, captured.getvalue()

    def test_a_machine_that_cannot_measure_says_so_rather_than_passing(self) -> None:
        code, output = self.run_main(unavailable=lambda: "no boot program is here")

        self.assertEqual((code, "nothing was measured" in output), (2, True))

    def test_a_run_that_beats_the_floor_reports_success(self) -> None:
        code, output = self.run_main(repeats=1, calls=200, floor=1)

        self.assertEqual(code, 0)
        self.assertIn("cycle", output)

    def test_a_measurement_runs_the_unit_for_the_cycles_it_was_given(self) -> None:
        asked = []

        class Counting:
            def run_for(self, cycles: int) -> int:
                asked.append(cycles)
                return cycles

        speed.measure(calls=200, repeats=2, build=lambda name: Counting())

        self.assertEqual(asked, [200, 200])

    def test_and_reports_one_reading_per_repeat(self) -> None:
        class Counting:
            def run_for(self, cycles: int) -> int:
                return cycles

        found = speed.measure(calls=200, repeats=3, build=lambda name: Counting())

        self.assertEqual(len(found.seconds), 3)

    def test_a_floor_nothing_could_beat_fails_the_run(self) -> None:
        code, output = self.run_main(repeats=1, calls=200, floor=10**12)

        self.assertEqual(code, 1)
        self.assertIn("below", output)

    def test_a_run_at_exactly_the_shipped_floor_is_not_below_it(self) -> None:
        """The shipped number, held to something that does not involve timing.

        Whether the floor is beaten on a given machine is not asked in this file,
        and deliberately. This file runs under the coverage tracer, which costs
        about ten times what the measured call does, so a floor assertion taken
        here measures the tracer: it passed on a fast desktop and failed on a
        hosted runner, which is one reading arriving at two answers. That
        question is settled by running the module uninstrumented, in its own job,
        outside the coverage step.

        What is left for the shipped number here is that it is usable: positive,
        printable, and on the passing side of a comparison that is inclusive at
        the boundary rather than one step off it.
        """
        exactly = speed.Timed("at the floor", speed.FLOOR, [1.0])

        self.assertGreater(speed.FLOOR, 0)
        self.assertTrue(exactly.beats(speed.FLOOR))
        self.assertIn(f"{speed.FLOOR:,}", "\n".join(speed.lines_for(exactly, speed.FLOOR)))


if __name__ == "__main__":
    unittest.main()
