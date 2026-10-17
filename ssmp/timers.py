from __future__ import annotations

COUNTER_MASK = 0x0F

DIVIDER_WHEN_ZERO = 256


class Timer:
    __slots__ = ("counter", "divider", "enabled", "stage", "ticks_every", "waited")

    def __init__(self, ticks_every: int, fill: int = 0) -> None:
        self.ticks_every = ticks_every
        self.divider = fill & 0xFF
        self.stage = 0
        self.counter = 0
        self.enabled = False
        self.waited = 0

    def divides_by(self) -> int:
        return self.divider if self.divider else DIVIDER_WHEN_ZERO

    def enable(self, wanted: bool) -> None:
        if wanted and not self.enabled:
            self.stage = 0
            self.counter = 0
            self.waited = 0
        self.enabled = wanted

    def spend(self, cycles: int) -> None:
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
        held = self.counter
        self.counter = 0
        return held
