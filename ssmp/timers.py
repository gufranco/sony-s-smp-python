"""The three timers the unit gives its processor, and what one tick costs.

Each timer is two numbers a program can see and one it cannot. The divider is
written and never read back. The counter is read and never written, is four bits
wide, and is cleared by the act of reading it, so two readers of one timer take
each other's ticks. The stage between them, which counts up to the divider and
wraps, is not reachable at all.

A divider of zero means two hundred and fifty six rather than nothing, because
the register is eight bits and the count it names runs from one to that. A timer
told to divide by zero and taken literally never ticks, which is the shape of a
program that appears to hang for no reason.

How often a timer ticks is not a figure this file chooses. Two of them run at one
rate and the third at a rate eight times higher, and what turns those into a
number of processor cycles is the ratio between the unit's own clock and the
processor's, which is in `rates.py` next to the derivation.
"""

from __future__ import annotations

from typing import override

COUNTER_MASK = 0x0F
"""The counter is four bits. The upper nibble of the register reads as zero."""

DIVIDER_WHEN_ZERO = 256
"""What a divider of zero names, because the count runs from one to 256."""


class Timer:
    """One timer: a divider written, a counter read, and a stage between them."""

    __slots__ = ("counter", "divider", "enabled", "stage", "ticks_every", "waited")

    def __init__(self, ticks_every: int, fill: int = 0) -> None:
        self.ticks_every = ticks_every
        self.divider = fill & 0xFF
        self.stage = 0
        self.counter = 0
        self.enabled = False
        self.waited = 0

    def divides_by(self) -> int:
        """The count this timer divides by, with zero read as the full range."""
        return self.divider if self.divider else DIVIDER_WHEN_ZERO

    def enable(self, wanted: bool) -> None:
        """Turn the timer on or off.

        Turning one on clears the stage and the counter, because a program that
        enables a timer is asking to count from now rather than from whatever
        was left over from the last time it was on.
        """
        if wanted and not self.enabled:
            self.stage = 0
            self.counter = 0
            self.waited = 0
        self.enabled = wanted

    def spend(self, cycles: int) -> None:
        """Advance by that many processor cycles.

        The timer runs on the unit's own clock rather than on the processor's,
        so a number of processor cycles buys a number of timer ticks and usually
        a remainder. Carrying the remainder is what stops a long run drifting
        away from a short one.
        """
        if not self.enabled:
            return
        self.waited += cycles
        while self.waited >= self.ticks_every:
            self.waited -= self.ticks_every
            self._tick()

    def _tick(self) -> None:
        self.stage += 1
        if self.stage >= self.divides_by():
            self.stage = 0
            self.counter = (self.counter + 1) & COUNTER_MASK

    def read(self) -> int:
        """What a program sees, and the read that empties it.

        Clearing on read is the whole interface: a program learns how many times
        the timer wrapped since it last asked, and there is no way to ask without
        also forgetting.
        """
        held = self.counter
        self.counter = 0
        return held

    @override
    def __repr__(self) -> str:
        state = "on" if self.enabled else "off"
        return f"<Timer {state}, dividing by {self.divides_by()}, counter {self.counter}>"
