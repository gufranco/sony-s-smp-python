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

unit = Chip("ssmp").reset()
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

**Not settled: 7 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
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

They are Shay Green's. `conformance/checks.manifest.json` identifies three of them
and carries no bytes. Copies you own go in `spc/`, or anywhere named by
`SSMP_SPC_DIR`. Without them `conformance/against_checks.py` exits two and says
nothing was checked, which is not the same as agreement.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm run format:check
uvx yamllint==1.38.0 --strict .
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for file in $(find ssmp conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$file"
done
"${cov[@]}" report
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
- No comments in source, and a docstring counts as one. A step that would need
  a comment needs a better name instead.
- Tests are `<module>.test.py` beside what they test. Arrange, act and
  assert, each block opened by its bare marker.
- 100% statement and branch coverage, and `mypy` with every strictness flag.
- Nothing is cleared at construction. Power on scrambles; reset defines.

The linter's ignores in [`pyproject.toml`](pyproject.toml) carry no comments, so
their reasons live here, beside those of the other exclusions:

- `N818`: the control flow signals are named the way CPython names its own,
  like `StopIteration`. The exceptions that report a failure do end in `Error`.
- `BLE001` and `T201` in `environment.py`: it reports what a machine is, so a
  check that throws becomes a line in the report rather than ending the run.
- `N999` in tests: a test file is named after the module it covers, with a dot,
  so a module and its tests are read together.
- `T201` in `conformance/`: these are command line tools and printing is their
  output. A logger would put a level and a timestamp in front of a report meant
  for a person.
- `BLE001` and `T201` in the doctor: it must survive whatever a check throws and
  report it, because a narrower catch would let a traceback take the rest of the
  report with it.
- Every optional `mypy` error class is on because the errors that matter in a
  model of hardware are a width, a mask or a `None` crossing a boundary.
- The `spc700.*` and `sdsp.*` override in `mypy`: the submodules are checked in
  their own repositories, against their own gate.
- The `__main__` guard is excluded from coverage: it hands argv to a tested
  function, and importing the module to cover it would run the tool.
- The doctor's `sys.path` guard is excluded: a suite that imports the doctor has
  already put the repository on the path, so no test can take that branch.
- `if TYPE_CHECKING:` is excluded: it never runs, and Python 3.14 drops it before
  coverage sees it while earlier versions do not.
- A lone ellipsis and a signature ending in one are excluded: a protocol method
  has no body to run, and the same version split applies.
- `@unittest\.skipUnless\(CLOCKED,` in the coverage exclusions: this member is
  not a clocked part, so the family tests that drive a clock are skipped here
  and their bodies never run.
- `@unittest\.skipUnless\(A_PART,`,
  `@unittest\.skipUnless\(A_PART and BUILDABLE,` and
  `^def accounts_for_a_reset\(` in the coverage exclusions: this member is not a
  part, so the family tests that build a `Chip` and account for its reset are
  skipped here and their bodies never run.
- `@unittest\.skipUnless\(QUOTED,` in the coverage exclusions: this record
  quotes no document, so the family tests that hold a quote checker to the
  pipeline are skipped here.
- `@unittest\.skipUnless\(VARIANTS,` and `^def built\(` in the coverage
  exclusions: this package names no variants, so the family test that finds each
  one built in the readme is skipped here.
- `@unittest\.skipUnless\(SOLD_AS_A_COMPONENT,`, `^def machine_mentions\(` and
  `^def listing\(` in the coverage exclusions: this part only existed inside one
  machine, so the family sweep for machine names is skipped here.

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
conformance/monitor.py    a program that reads and writes the unit for a check, through the four ports
conformance/loader.py     an audio unit written down, and the order to restore it in
conformance/against_checks.py  Shay Green's checks, run against the model
```

## Things that will bite you

- The search order in `firmware.py` is one rule with a copy in
  `snes-dsp-python` and `snes-st-python` too, because no package is a
  dependency of all three. The three copies of `directories` are byte-identical
  below the constants and are meant to stay that way. The diff that holds
  them together runs from `def directories` to `return tuple(seen)`:

  ```sh
  cut='/^def directories/,/^    return tuple(seen)/p'
  diff <(sed -n "$cut" mine/firmware.py) <(sed -n "$cut" theirs/firmware.py)
  ```
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
- Building a unit resets nothing: the generator and the processor both come up
  scrambled. `reset()` is the console's reset line, which reaches both halves,
  so it resets the generator to what `resetLine` in its record lists and then
  the processor. A check, a runner or an example that wants the boot program
  running calls `reset()` itself.
- `reset()` never rebuilds anything. It shows the boot window, which the boot
  program needs to leave reset at all, and resets the two halves. Memory, the
  timers, the ports and the other registers hold what they held.
- A generator nobody reset is clocked like any other, and when its scrambled
  flag register leaves echo writes on it writes wherever its scrambled echo
  registers point. That is what power on does here, and it is modelled rather
  than prevented. `OPEN-QUESTIONS.md` says what would settle it.

## Before calling anything finished

Every gate above, then `conformance/boot.test.py` with a real boot program
present and `python3 -m conformance.against_checks` with Shay Green's files
present. A change that keeps the unit tests green and stops the handshake
appearing, or makes one of those checks disagree, has broken the part.

## What a change is expected to leave behind

The gates green, the record in `conformance/` matching what the code does, and
`OPEN-QUESTIONS.md` still true. A new claim about the hardware arrives with what
would settle it, or it does not arrive.
