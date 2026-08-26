# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this family
carries, byte for byte, and it decides most questions before they are asked. What
follows is only what is true of this member.

## What this project is, in one paragraph

A model of the S-SMP, the audio unit a Super Nintendo talks to rather than into.
The console cannot reach its memory, its processor or its sound generator: it
reaches four bytes, and every audio program any cartridge ever ran arrived
through them one byte at a time. The processor is
[sony-spc700-python](https://github.com/gufranco/sony-spc700-python) and the
sound generator is
[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python), both consumed
as submodules. What this repository adds is everything between them: the sixty
four kilobytes they share, the four ports, three timers, a control register that
changes what the address space is, and sixty four bytes of boot program in the
top page.

## The interface a caller drives

```python
from ssmp import Chip

unit = Chip("ssmp")
unit.run_for(6300)
unit.read(0), unit.read(1)  # 0xaa, 0xbb: the unit is listening
unit.write(0, 0xCC)  # what a console says to start a transfer
```

`read` and `write` are the console's four addresses and nothing else. Reaching
into `unit.space` or `unit.processor` is reaching past what a console can do, and
a check that does it is checking the model rather than the part.

## The authority ladder

Rung one is empty: Sony published no document for this unit. Rung two is not, and
it is where almost everything here sits. The boot program is the part's own code,
and the upload protocol is read off it rather than copied from an implementation
of either half.

## What is settled and what is not

**Not settled: 4 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
the measurement that would close it. The sharpest is that nothing here is a
timing claim against a console, because the two crystals are independent.

Settled, and settled by the part rather than by agreement with anybody: the
handshake, the transfer, the acknowledgement, a second block after the first, and
the jump.

## It needs a boot program and carries none

Those sixty four bytes are Sony's. A copy you already own goes in `boot/`, or in
the `boot/` of the project this one sits inside, or anywhere named by
`SSMP_BOOT_DIR`. Nothing is downloaded. Without one the unit refuses to be built
and says why, and every check that needs one skips out loud.

`ssmp/artifacts.manifest.json` carries the four digests and no bytes. sha256
decides; the other three are cross-checked so that publishing them means
something.

## The boot program is the evidence

`conformance/boot.test.py` plays the console's own sequence at the unit. If a
change makes the unit stop answering `0xaa 0xbb`, or stop taking a block, the
part being modelled has been broken rather than the test. That file is the one to
believe.

Composing the two halves has already found a defect in one of them: the processor
scrambled the direct-page flag at reset, and the boot program proves it must be
clear. The fix belongs in `sony-spc700-python`, not here.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
python3 -m coverage erase
for file in $(find ssmp conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Then the throughput floor, which runs outside the coverage step because a tracer
costs about ten times what the model does:

```bash
python3 -m conformance.speed
```

And the runs that report what they could not check rather than passing quietly:

```bash
python3 ssmp/doctor.py
python3 -m conformance.links
```

Everything under `conformance/` runs as a module. Run as a script, its own
directory goes on the import path and a file there shadows any standard library
module of the same name. `doctor.py` is the exception and runs as a file on
purpose, so that it still runs when the package itself will not import, which is
the case it exists for.

## Conventions that are not negotiable

- Python only, standard library only, no dependencies.
- No comments in source. Reasoning goes in docstrings, and a step that would need
  a comment needs a better name instead.
- Tests are `<module>.test.py` beside what they test. Arrange, blank line, one
  act, blank line, assert. No section labels.
- 100% statement and branch coverage, and `mypy` with every strictness flag.
- Nothing is cleared at construction. Power on scrambles; reset defines.

## Layout

```
ssmp/board.py       the unit: processor, space, generator, and the cycles between
ssmp/space.py       the sixty four kilobytes, registers included
ssmp/ports.py       four bytes each way, which is the whole console interface
ssmp/timers.py      three timers, a divider written and a counter read
ssmp/rates.py       one crystal, four divisions, and the two ratios that matter
ssmp/firmware.py    recognising a boot program and saying why one is not
ssmp/models.py      which units this package covers
ssmp/doctor.py      what is here, what is not, what to do about it
conformance/console.py    the console's half of the protocol
conformance/boot.test.py  that half, played at the real unit
```

## Things that will bite you

- A port is two bytes at one address, not one. Modelling it as one makes both
  sides appear to work until two writes cross.
- The boot window covers memory rather than replacing it. A program writes under
  it and finds its bytes there once the window is switched off, and that is how
  every uploader gets its own code into the top page.
- The boot program clears `$01` through `$ef` and never touches `$00`, because
  its loop stops when the index reaches zero.
- A timer divider of zero means 256, not nothing.
- The counter is four bits and clears on read, so two readers of one timer take
  each other's ticks.

## Before calling anything finished

Every gate above, then `conformance/boot.test.py` with a real boot program
present. A change that keeps the unit tests green and stops the handshake
appearing has broken the part.

## What a change is expected to leave behind

The gates green, the record in `conformance/` matching what the code does, and
`OPEN-QUESTIONS.md` still true. A new claim about the hardware arrives with what
would settle it, or it does not arrive.
