# Open questions

What this project does not know for certain, and what it would take to find out.

This is a short list, and the reason is the subject. Almost everything this
member models is settled by the part's own boot program, which is Sony's code
rather than anybody's reading of it, or by checks Shay Green wrote that carry
values he took on a console. What is left is what neither of those reaches.

Every entry is also in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## What would settle almost all of them

A Sony document for the S-SMP, which is not known to exist, or a logic capture of
a real audio unit.

## Where the two clocks meet, and nothing here says how

### How many console cycles one of this unit's cycles is worth.

**The document says.** Nothing. No Sony document for this unit is known.

**What this project does.** Publishes no figure at all, and offers no elapsed
time in console cycles.

**Why.** The console and the audio unit are clocked from separate crystals and
neither divides the other. A ratio would look like the one thing a caller wants
from a model of this part, and it would be wrong everywhere by an amount that
drifts. Refusing to answer is the honest answer, and it is the answer this
package gives.

**What would settle or reopen it.** A measurement of both oscillators on one
board, which would give a ratio for that board rather than for the part. There is
no ratio to publish, only a distribution.

## Where the boot program stops and nothing takes over

### What the unit does when a transfer is started with no program to jump to.

**The document says.** Nothing.

**What this project does.** Whatever the boot program does, which is to jump
where it was told and run whatever is there.

**Why.** There is nothing to model. The boot program hands control over and stops
being involved, so a console that hands over a destination holding nothing gets a
processor executing nothing in particular. That is the part's behaviour rather
than a decision here.

**What would settle or reopen it.** Nothing needs settling. It is written down so
a reader does not mistake the absence of a check for an absence of thought.

## Where a figure comes from a ratio rather than a printed row

### The rate the timers tick at.

**The document says.** Nothing about this unit. What is printed is the sound
generator's sampling rate, and that is in the neighbouring member.

**What this project follows.** The ratio between the timers and the processor,
which is 128 processor cycles for the two slow timers and 16 for the fast one.
The crystal and its four divisions are in
[`ssmp/rates.py`](ssmp/rates.py) as the reasoning behind the ratio rather than as
a claim of their own.

**Why.** A unit built around a different crystal with the same ratios behaves
identically here, so the ratio is the weaker claim and it is the one worth
making. Every one of the four divisions is a whole number, which is the only
evidence offered that the division is the right one.

**What would settle or reopen it.** A Sony document, or a measurement of a timer
against the processor on real hardware.

## What was open and is now closed

**What the five registers nothing reads back actually answer.** Zero. All five of
them: the test register, the control register, and the three timer dividers.

This project answered with the memory underneath, on the grounds that inventing a
value would be publishing a claim nobody measured. That was the right instinct and
the wrong answer, and the thing that caught it was
`initial_regs.spc`, one of the checks
[`conformance/spc.manifest.json`](conformance/spc.manifest.json) identifies. It
reads all sixteen of these addresses in order and compares a checksum of the result against a value its
author took on a console. Of every arrangement of the five, exactly one reproduces
that checksum, and it is all five answering zero. The SNESdev wiki says the same
thing in words, which is a second source and not an implementation.

The old behaviour was put back on purpose afterwards to watch the check fail:
sub-check 3 disagreed and reported `d57e2579` against the `9d4d2100` it wanted.

## What is not in question

So the boundary is visible rather than implied:

- **All sixteen addresses that are not memory.** Read in order and checksummed
  against a value taken on a console, so the whole register file is settled at
  once rather than register by register.
- **That memory comes back whole.** `full_ram.spc` checks every byte, the stack
  page, the echo buffer and the three bytes under the stack pointer, across
  nineteen point eight million cycles.
- **The handshake.** The unit answers `0xaa` and `0xbb`, and it is checked
  against the boot program rather than against an implementation.
- **The transfer.** A block arrives one byte at a time, each acknowledged by the
  running count coming back, and a second block can follow the first.
- **The jump.** Zero in the port that would have carried a byte means jump rather
  than transfer, and the uploaded program runs.
- **What the boot program clears.** `$01` through `$ef`, and never `$00`, because
  the loop stops when its index reaches zero.
- **That the boot window covers memory rather than replacing it.** A write under
  it reaches the memory beneath, which is how an uploader gets code into the top
  page.

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **The processor.** It is
  [sony-spc700-python](https://github.com/gufranco/sony-spc700-python), consumed
  as a submodule. Two models of one instruction set is how two models disagree.
- **The sound generator.** It is
  [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python), for the
  same reason.
- **The console.** Nothing here models the other side of the four ports.
  `conformance/console.py` plays a console's part in a check and is not a model
  of one.
- **The boot program.** Sixty four bytes of Sony's, not carried here, not
  downloaded, and not reconstructible from anything in this repository.
- **The checks taken on hardware.** Shay Green's, not carried here either.
  [`conformance/spc.manifest.json`](conformance/spc.manifest.json) identifies
  them and carries no bytes.
