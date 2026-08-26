# S-SMP

A model of the Sony S-SMP, the audio unit a Super Nintendo talks to rather than into.

[![CI](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml)

**4** bytes are the entire console interface, **64** kilobytes shared between a processor and a sound generator, **3** timers, **64** bytes of boot program that this repository does not carry, the upload protocol read off that program rather than copied, **3** checks carrying values taken on a console, **0** disagreements, **582** tests, **100%** statement and branch coverage, no dependencies

```python
from ssmp import Chip

unit = Chip("ssmp")
unit.run_for(6300)

unit.read(0), unit.read(1)

# (170, 187)
```

Those two numbers are `0xaa` and `0xbb`, and they are what every Super Nintendo
waits for before it says anything to its audio hardware.


## Install

```bash
git clone --recurse-submodules https://github.com/gufranco/sony-s-smp-python.git
cd sony-s-smp-python
```

Put a copy of the boot program you already own in `boot/`, then:

```python
from ssmp import Chip, why_not

print(why_not())

# None
```

If it prints a sentence instead, that sentence says exactly what is missing and
what to do about it. `python3 ssmp/doctor.py` says the same thing at more length.

## The interface

A console cannot reach this unit's memory, its processor, or its sound
generator. It reaches four bytes. Every audio program any cartridge ever ran
arrived through them, one byte at a time.

```python
from ssmp import Chip

unit = Chip("ssmp")
unit.run_for(6300)

unit.write(0, 0xCC)
unit.run_for(64)

print(unit.read(0))

# 204
```

`204` is `0xcc` coming back, which is the boot program saying it is ready to
take a block.

A port is two bytes at one address, one per direction. A write from the console
does not change what the console reads back. Modelling it as one byte makes both
sides appear to work until two writes cross, and then produces an answer neither
side sent.

## What composing the halves found

The processor is
[sony-spc700-python](https://github.com/gufranco/sony-spc700-python) and the
sound generator is
[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python). Neither
models the other, because two models of one wire is how two models disagree.

Putting them together found a defect in one of them, which is the argument for
this member existing at all.

The processor scrambled every flag at reset, on the grounds that the manual gives
no power-on values. That is right for all of them but one. The boot program
answers the console with `mov $f4,#$aa` and `mov $f5,#$bb`, and those reach the
ports only while the direct page is the zero page. With the flag set they write
ordinary memory at `$01f4`, the handshake never appears, and no cartridge ever
gets its audio program uploaded.

Every Super Nintendo that has ever made a sound is the measurement. The fix went
into the processor, where it belongs.

## What a check taken on hardware found

The five registers that are written and never read back answered with the memory
underneath. That was a deliberate choice, made because inventing a value would
have been publishing a claim nobody measured, and it was wrong.

`initial_regs.spc` reads all sixteen registers in order and compares a checksum of
the result against a value its author took on a console. Of every arrangement of
those five, exactly one reproduces the checksum: all five answer zero. The SNESdev
wiki says the same thing in words, which is a second source rather than a second
implementation.

The old behaviour was put back afterwards to watch the check fail. It disagreed on
sub-check 3 and reported `d57e2579` against the `9d4d2100` it wanted, and the other
two checks still agreed, because neither of them reads those registers.

## One unit, not two halves in a box

The processor and the sound generator read the same sixty four kilobytes,
because on the part they do. Voices fetch their compressed blocks out of it and
the echo unit writes back into it, so handing each half a store of its own would
be two memories where the part has one and every sample a program uploaded would
go missing.

The generator takes one clock for every processor cycle. That is derived rather
than looked up, and the derivation is in [`ssmp/rates.py`](ssmp/rates.py) beside
the timer ratios: one crystal reaches the processor through a divisor of 24 and
reaches the generator through 768 for a sample with 32 clocks inside it, and 24
times 32 is 768. Both come out at 1,024,000 a second.

It also comes up reset rather than scrambled, unlike everything else here. The
console's reset line reaches it too, and what a reset leaves is a part that
writes no echo. Without that the unit would come up scribbling wherever its
scrambled echo registers happened to point.

## What is not modelled

- **Any ratio between this unit's clock and the console's.** They run from
  separate crystals and neither divides the other, so a ratio is a property of
  one board rather than of the part. No figure is published and no elapsed time
  in console cycles is offered. The ratio above is a different thing: both
  halves of this unit hang off one crystal, so there is a whole number there.
- **The processor and the sound generator.** Both are separate members.
- **The console.** [`conformance/console.py`](conformance/console.py) plays a
  console's part in a check and is not a model of one.

## The boot program is not here

Those sixty four bytes are Sony's. This repository does not carry them, does not
download them, and nothing in it can reconstruct them.
[`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) carries four
digests and no bytes, so a copy you already own can be confirmed as the right
one. sha256 decides; the other three are cross-checked so that publishing them
means something.

Put a copy in `boot/`, or in the `boot/` of the project this one sits inside, or
name any directory in `SSMP_BOOT_DIR`.

## Models

```python
from ssmp import MODELS, describe

print(sorted(MODELS))

# ['ssmp']
```

One unit, because Sony shipped one. The catalogue exists so that a hardware
difference discovered later means adding an entry rather than restructuring the
package.

## Tests

```bash
python3 -m coverage erase
for file in $(find ssmp conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

100% statement and branch coverage, `mypy` with every strictness flag, and
`ruff` for format and lint. Every check that needs the boot program, or one of
Shay Green's files, skips out loud rather than reporting a pass.

The checks taken on hardware run outside the coverage step, because the longest
of them is twenty seconds of the unit's own time:

```bash
python3 -m conformance.against_checks
```

The throughput floor runs outside the coverage step, because a tracer costs about
ten times what the model does:

```bash
python3 -m conformance.speed
```

## Is it right

This member has no manufacturer document. Two things stand in for one, and both
are better than the usual substitute.

**The part's own code.** It carries sixty four bytes Sony wrote, so the console
interface can be read off them rather than guessed at or copied from an
implementation. [`conformance/console.py`](conformance/console.py) writes that
sequence down and [`conformance/boot.test.py`](conformance/boot.test.py) plays it
at the unit: the handshake `0xaa` and `0xbb`, the destination, the block with
every byte acknowledged by its own count, a second block after the first, and the
jump into what was uploaded.

**Checks carrying values taken on a console.** Shay Green wrote three that hold an
audio unit to what real hardware does, and a `.spc` file is a whole unit written
down, so they run here directly with no console anywhere in the chain:

| Check | What it settles | Sub-checks | Cycles |
| --- | --- | ---: | ---: |
| `initial_regs.spc` | the six processor registers, all sixteen addresses that are not memory, and the sound generator's whole register file | 4 | 744,661 |
| `initial_in_ports.spc` | the four ports, read as the first thing the program does | 1 | 654,978 |
| `full_ram.spc` | every byte of memory, the stack page, the echo buffer, and the three bytes under the stack pointer | 6 | 19,793,439 |

All three agree. One did not, at first, and what it caught is below.

Both are the second rung of [the family's authority ladder](FAMILY.md), the
artifact and a measurement of one, rather than the fourth.

The files are Shay Green's and are not carried here.
[`conformance/spc.manifest.json`](conformance/spc.manifest.json) identifies them
and carries no bytes. Put copies you own in `spc/` or name a directory in
`SSMP_SPC_DIR`.

## Working on it

[AGENTS.md](AGENTS.md) is the brief: the gates, the conventions, the layout, and
the things that will bite you. [FAMILY.md](FAMILY.md) is the standard every
member of this family carries, byte for byte.
[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) is what this project does not know, with
the measurement that would settle each one.

## References

No Sony document for the S-SMP is known to exist, so there is no page to cite
for what this member adds. What stands in its place is the part's own boot
program, which this repository does not carry and does not reproduce.

What stands beside it is Shay Green's set of checks, whose expectations were
taken on a console rather than derived from an implementation, and the
[SNESdev wiki's S-SMP page](https://snes.nesdev.org/wiki/S-SMP), which is a
later document rather than a Sony one and is cited where it is used.

The two halves carry their own references:
[sony-spc700-python](https://github.com/gufranco/sony-spc700-python) for the
processor and [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python)
for the sound generator, the second of which is held to Nintendo's own tables.

## Citing this

[CITATION.cff](CITATION.cff).

## License

MIT. See [LICENSE](LICENSE).
