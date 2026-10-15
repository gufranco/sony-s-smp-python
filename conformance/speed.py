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

CALLS = 20_000

REPEATS = 5

MODEL = "ssmp"


class Timed:
    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def _a_unit(name: str) -> Any:  # pragma: no cover
    return ssmp.Chip(name)


def measure(
    calls: int = CALLS, repeats: int = REPEATS, build: Callable[[str], Any] = _a_unit
) -> Timed:
    seconds = []
    for _ in range(repeats):
        unit = build(MODEL).reset()
        started = time.perf_counter()
        unit.run_for(calls)
        seconds.append(time.perf_counter() - started)
    return Timed("cycle", calls, seconds)


def unavailable() -> str | None:
    return board.why_not()


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
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
