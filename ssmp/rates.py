from __future__ import annotations

CRYSTAL_HZ = 24_576_000

PROCESSOR_DIVISOR = 24

SLOW_TIMER_DIVISOR = 3072

FAST_TIMER_DIVISOR = 384

PROCESSOR_HZ = CRYSTAL_HZ // PROCESSOR_DIVISOR

SLOW_TIMER_HZ = CRYSTAL_HZ // SLOW_TIMER_DIVISOR

FAST_TIMER_HZ = CRYSTAL_HZ // FAST_TIMER_DIVISOR


def cycles_per_tick(timer_hz: int, processor_hz: int = PROCESSOR_HZ) -> int:
    return processor_hz // timer_hz


SLOW_TIMER_CYCLES = cycles_per_tick(SLOW_TIMER_HZ)

FAST_TIMER_CYCLES = cycles_per_tick(FAST_TIMER_HZ)


SAMPLE_DIVISOR = 768

SAMPLE_HZ = CRYSTAL_HZ // SAMPLE_DIVISOR

CLOCKS_PER_SAMPLE = 32

GENERATOR_HZ = SAMPLE_HZ * CLOCKS_PER_SAMPLE


def clocks_per_cycle(generator_hz: int = GENERATOR_HZ, processor_hz: int = PROCESSOR_HZ) -> int:
    return generator_hz // processor_hz


GENERATOR_CLOCKS = clocks_per_cycle()
