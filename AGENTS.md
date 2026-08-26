# Working in this repository

Read [FAMILY.md](FAMILY.md) first. It is the standard every member of this
family carries, byte for byte, and it decides most questions before they are
asked. What follows is only what is true of this member. [README.md](README.md)
is the document written for a person.

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

Rung one is empty: Sony published no document for this unit. Rung two holds two
things, and between them they carry almost everything here. The boot program is
the part's own code, and the upload protocol is read off it rather than copied
from an implementation of either half. Beside it are three checks Shay Green
wrote, each carrying a checksum he took on a console, which settle what those
sixty four bytes never touch.

## What is settled and what is not

**Not settled: 5 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
the measurement that would close it. The sharpest is that nothing here is a
timing claim against a console, because the two crystals are independent.

Settled by the part rather than by agreement with anybody: the handshake, the
transfer, the acknowledgement, a second block after the first, and the jump.

Settled by a measurement somebody took on a console: all sixteen addresses that
are not memory, read in order and checksummed together, and that memory comes
back whole across nineteen point eight million cycles.

## It needs a boot program and carries none

Those sixty four bytes are Sony's. A copy you already own goes in `boot/`, or in
the `boot/` of the project this one sits inside, or anywhere named by
`SSMP_BOOT_DIR`. Nothing is downloaded. Without one the unit refuses to be built
and says why, and every check that needs one skips out loud.

`ssmp/artifacts.manifest.json` carries the four digests and no bytes. sha256
decides; the other three are cross-checked so that publishing them means
something.

## The two things that are the evidence

`conformance/boot.test.py` plays the console's own sequence at the unit. If a
change makes the unit stop answering `0xaa 0xbb`, or stop taking a block, the
part being modelled has been broken rather than the test.

`conformance/against_checks.py` runs Shay Green's checks, which compare against
values he took on hardware. A `.spc` file is a whole audio unit written down, so
they run here with no console anywhere in the chain. Those two files are the ones
to believe.

Both have already found a defect. Composing the halves caught the processor
scrambling the direct-page flag at reset, which the boot program proves must be
clear; that fix belongs in `sony-spc700-python`. And `initial_regs.spc` caught
this member answering the memory underneath at the five registers that cannot be
read, where the part answers zero.

## The checks are not here either

They are Shay Green's. `conformance/spc.manifest.json` identifies three of them
and carries no bytes. Copies you own go in `spc/`, or anywhere named by
`SSMP_SPC_DIR`. Without them `conformance/against_checks.py` exits two and says
nothing was checked, which is not the same as agreement.

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

And the checks taken on hardware, which run outside coverage because the longest
of them is twenty seconds of the unit's own time:

```bash
python3 -m conformance.against_checks
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
ssmp/rates.py       one crystal, five divisions, and the ratios that fall out
ssmp/space.py       the sixty four kilobytes, registers included
ssmp/ports.py       four bytes each way, which is the whole console interface
ssmp/timers.py      three timers, a divider written and a counter read
ssmp/firmware.py    recognising a boot program and saying why one is not
ssmp/models.py      which units this package covers
ssmp/doctor.py      what is here, what is not, what to do about it
conformance/console.py    the console's half of the protocol
conformance/boot.test.py  that half, played at the real unit
conformance/loader.py     an audio unit written down, and the order to restore it in
conformance/against_checks.py  Shay Green's checks, run against the model
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
- Five registers cannot be read and answer zero: the test register, the control
  register and the three dividers. Answering the value last written, or the
  memory underneath, is wrong and looks right until a program reads one.
- Restoring a written-down unit puts the control register back before the ports,
  never after. Writing control clears whichever pairs of ports its bits ask for,
  so the other order silently loses two of them.
- The generator shares the processor's memory rather than holding one of its
  own, and it is clocked once per processor cycle. Both are easy to leave out
  and nothing fails loudly when you do: the unit runs, the handshake works, and
  no sound is ever produced.
- The generator is reset at construction. That is the one exception to power on
  scrambles, reset defines, and it is there because a scrambled echo register
  points somewhere and the generator writes there.

## Before calling anything finished

Every gate above, then `conformance/boot.test.py` with a real boot program
present and `python3 -m conformance.against_checks` with Shay Green's files
present. A change that keeps the unit tests green and stops the handshake
appearing, or makes one of those checks disagree, has broken the part.

## What a change is expected to leave behind

The gates green, the record in `conformance/` matching what the code does, and
`OPEN-QUESTIONS.md` still true. A new claim about the hardware arrives with what
would settle it, or it does not arrive.
