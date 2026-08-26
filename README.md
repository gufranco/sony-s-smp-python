<div align="center">

<h1>S-SMP</h1>

<strong>A model of the Sony S-SMP, the audio unit a Super Nintendo talks to rather than into.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#install">Install</a> &nbsp;|&nbsp;
  <a href="#the-interface">The interface</a> &nbsp;|&nbsp;
  <a href="#is-it-right">Is it right</a> &nbsp;|&nbsp;
  <a href="#what-composing-the-halves-found">What composing found</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/sony-s-smp-python/issues">Issues</a>
</p>

**4** bytes are the entire console interface · **64** kilobytes shared between a processor and a sound generator · **3** timers · **64** bytes of boot program that this repository does not carry · the upload protocol read off that program rather than copied, with **0** disagreements against it · **487** tests · **100%** statement and branch coverage · no dependencies

```python
from ssmp import Chip

unit = Chip("ssmp")
unit.run_for(6300)

unit.read(0), unit.read(1)

# (170, 187)
```

Those two numbers are `0xaa` and `0xbb`, and they are what every Super Nintendo
waits for before it says anything to its audio hardware.

---

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

## What is not modelled

- **Any ratio between this unit's clock and the console's.** They run from
  separate crystals and neither divides the other, so a ratio is a property of
  one board rather than of the part. No figure is published and no elapsed time
  in console cycles is offered.
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
`ruff` for format and lint. Every check that needs the boot program skips out
loud rather than reporting a pass.

The throughput floor runs outside the coverage step, because a tracer costs about
ten times what the model does:

```bash
python3 -m conformance.speed
```

## Is it right

This member has no manufacturer document. What it has instead is better than the
usual substitute: the part carries sixty four bytes of Sony's own code, and the
console interface can be read off them rather than guessed at or copied from an
implementation.

[`conformance/console.py`](conformance/console.py) writes that sequence down and
[`conformance/boot.test.py`](conformance/boot.test.py) plays it at the unit:

- the handshake, `0xaa` and `0xbb`
- the destination, the block, and every byte acknowledged by its own count
- a second block after the first
- the jump, and the uploaded program running

That is the second rung of [the family's authority ladder](FAMILY.md), the
artifact, rather than the fourth.

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

The two halves carry their own references:
[sony-spc700-python](https://github.com/gufranco/sony-spc700-python) for the
processor and [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python)
for the sound generator, the second of which is held to Nintendo's own tables.

## Citing this

[CITATION.cff](CITATION.cff).

## License

MIT. See [LICENSE](LICENSE).
