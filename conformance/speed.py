"""How fast the unit runs, and a floor it must not fall through.

Not a benchmark for its own sake. The processor runs at rather over a megahertz,
so a second of a game's audio driver is more than a million cycles, and the boot
handshake alone is several thousand before a console has said anything. The way
that stops being usable is gradual: a lookup grows an allocation, a decode
becomes a comprehension, and a year later a run nobody changed takes an hour. A
floor that fails loudly is cheaper than noticing.

The floor is deliberately far below what the chip does today. It is there to
catch something several times slower, not to police the noise between one runner
and another, because a shared runner's variance is larger than any change worth
arguing about.

Every figure is a median across repeats rather than a mean, because one
scheduling hiccup moves a mean and moves a median much less, and the runtime
version is printed beside it because it is the single thing that changes these
numbers most.

Run it outside the coverage step. A tracer costs about ten times what this does,
so a floor measured under one measures the tracer.
"""

from __future__ import annotations

import statistics
import sys
import sys as _sys
import time
from pathlib import Path as _Path
from typing import TYPE_CHECKING, Any

_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import ssmp
from ssmp import board

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

FLOOR = 20_000
"""Cycles per second this must beat, well under what it does.

Deliberately far below, because this unit is two models stacked and a shared
runner's variance is larger than any change worth arguing about. It is here to
catch something several times slower rather than to police noise.
"""

CALLS = 20_000
"""Steps per repeat. Enough that the clock's resolution does not decide."""

REPEATS = 5
"""How many repeats the median is taken across."""

MODEL = "ssmp"
"""The one unit there is."""


class Timed:
    """One measured run, and what it is allowed to say about itself."""

    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        """Calls per second, or zero when the clock could not see the work.

        A run that measured zero seconds is a reading about the clock rather
        than about the code, and reporting it as unbounded speed would let a
        machine with a coarse timer pass a floor it never met.
        """
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def _a_unit(name: str) -> Any:  # pragma: no cover
    """How a unit is built when nobody says otherwise, which needs the program."""
    return ssmp.Chip(name)


def measure(
    calls: int = CALLS, repeats: int = REPEATS, build: Callable[[str], Any] = _a_unit
) -> Timed:
    """Run the unit for that many cycles, and time it.

    Cycles rather than instructions, because an instruction is between two and
    eight of them and a count of instructions would drift with whatever the boot
    program happens to be executing.
    """
    seconds = []
    for _ in range(repeats):
        unit = build(MODEL).reset()
        started = time.perf_counter()
        unit.run_for(calls)
        seconds.append(time.perf_counter() - started)
    return Timed("cycle", calls, seconds)


def unavailable() -> str | None:
    """Why this cannot be measured here, or nothing when it can."""
    return board.why_not()


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    """What the run reports, whether it passed or not."""
    runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines = [
        f"  {found.what}: {found.rate():,.0f} per second"
        f" (median of {len(found.seconds)}) on Python {runtime}",
        f"  floor: {floor:,} per second",
    ]
    if not found.beats(floor):
        lines.append(f"  below the floor: {found.rate():,.0f} is under {floor:,}")
    return lines


def main(
    calls: int = CALLS,
    repeats: int = REPEATS,
    floor: int = FLOOR,
    unavailable: Callable[[], str | None] = unavailable,
    measure: Callable[[int, int], Timed] = measure,
) -> int:
    """The tool, with both the availability answer and the measurement injectable.

    Injectable because neither is a decision this file makes. A runner has no
    boot program, so a check of what the tool does with a measurement would
    otherwise pass on a machine that has one and fail on the runner, which is
    exactly the failure this file exists to catch in the model.
    """
    reason = unavailable()
    if reason:
        print(f"  nothing was measured: {reason}")
        return 2
    found = measure(calls, repeats)
    for line in lines_for(found, floor):
        print(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    raise SystemExit(main())
