"""How often a timer ticks, said as a number of processor cycles.

Nothing here is a figure anybody printed. What is printed is elsewhere: the
sound generator beside this unit samples at 32 kHz, and that member records the
rate as falling out of a table's top row rather than being stated. Everything
below is the arithmetic that connects that to the processor, kept here so a
reader can disagree with the derivation rather than with a constant.

One crystal drives the whole unit. Divide it four ways and every quotient is a
whole number, which is the only evidence offered that the division is the right
one:

    24_576_000 / 768  = 32_000    the rate the sound generator samples at
    24_576_000 / 24   = 1_024_000 the rate the processor runs at
    24_576_000 / 3072 = 8_000     the rate two of the three timers tick at
    24_576_000 / 384  = 64_000    the rate the third ticks at

What this model actually depends on is narrower than those four figures, and
deliberately so. It uses only the ratio between a timer and the processor:

    1_024_000 / 8_000  = 128 processor cycles per tick of the slow timers
    1_024_000 / 64_000 = 16  processor cycles per tick of the fast one

A unit built around a different crystal with the same ratios behaves identically
here, so the ratio is the claim and the crystal is the reasoning behind it. That
is the weaker of the two claims and it is the one worth making.
"""

from __future__ import annotations

CRYSTAL_HZ = 24_576_000
"""The oscillator the whole unit is divided down from. Not a printed figure."""

PROCESSOR_DIVISOR = 24
"""What the crystal is divided by to reach the processor."""

SLOW_TIMER_DIVISOR = 3072
"""What it is divided by to reach the two slow timers."""

FAST_TIMER_DIVISOR = 384
"""What it is divided by to reach the fast one."""

PROCESSOR_HZ = CRYSTAL_HZ // PROCESSOR_DIVISOR

SLOW_TIMER_HZ = CRYSTAL_HZ // SLOW_TIMER_DIVISOR

FAST_TIMER_HZ = CRYSTAL_HZ // FAST_TIMER_DIVISOR


def cycles_per_tick(timer_hz: int, processor_hz: int = PROCESSOR_HZ) -> int:
    """How many processor cycles one tick of that timer costs.

    Derived rather than tabulated, so a reader changing one rate does not have
    to remember to change a constant somewhere else that quietly disagrees.
    """
    return processor_hz // timer_hz


SLOW_TIMER_CYCLES = cycles_per_tick(SLOW_TIMER_HZ)

FAST_TIMER_CYCLES = cycles_per_tick(FAST_TIMER_HZ)


SAMPLE_DIVISOR = 768
"""What the crystal is divided by to reach one sample of sound."""

SAMPLE_HZ = CRYSTAL_HZ // SAMPLE_DIVISOR

CLOCKS_PER_SAMPLE = 32
"""How many of the generator's clocks make one sample.

The neighbouring member's own figure: its schedule is thirty two clocks long and
the voices are pipelined across it rather than run one after another.
"""

GENERATOR_HZ = SAMPLE_HZ * CLOCKS_PER_SAMPLE


def clocks_per_cycle(generator_hz: int = GENERATOR_HZ, processor_hz: int = PROCESSOR_HZ) -> int:
    """How many of the generator's clocks one processor cycle costs.

    One, and the fact that it is one is the whole point of deriving it rather
    than writing it down. Both halves hang off the same crystal, the processor
    through a divisor of 24 and the generator through 768 for a sample and 32
    clocks inside it, and 24 times 32 is 768. A reader who doubts the wire can
    disagree with that arithmetic instead of with a constant.
    """
    return generator_hz // processor_hz


GENERATOR_CLOCKS = clocks_per_cycle()
