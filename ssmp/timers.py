from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    import random

COUNTER_MASK = 0x0F

STAGE_MASK = 0xFF


class Timer:
    __slots__ = ("counter", "divider", "enabled", "stage", "ticks_every", "waited")

    def __init__(
        self, ticks_every: int, scrambled: random.Random, waited: int, enabled: bool
    ) -> None:
        self.ticks_every = ticks_every
        self.divider = scrambled.randrange(STAGE_MASK + 1)
        self.stage = scrambled.randrange(STAGE_MASK + 1)
        self.counter = scrambled.randrange(COUNTER_MASK + 1)
        self.enabled = enabled
        self.waited = waited % ticks_every

    def enable(self, wanted: bool) -> None:
        if wanted and not self.enabled:
            self.stage = 0
            self.counter = 0
        self.enabled = wanted

    def spend(self, cycles: int) -> None:
        self.waited += cycles
        while self.waited >= self.ticks_every:
            self.waited -= self.ticks_every
            self._tick()

    def _tick(self) -> None:
        if not self.enabled:
            return
        self.stage = (self.stage + 1) & STAGE_MASK
        if self.stage == self.divider:
            self.stage = 0
            self.counter = (self.counter + 1) & COUNTER_MASK

    def read(self) -> int:
        held = self.counter
        self.counter = 0
        return held
