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
against the processor on real hardware. There is now a third way, and it needs
neither. Shay Green's `spc_mem_access_times.sfc` uses the timers as its phase
reference while it walks the instruction set, and checks the result against a
value he took on a console, `8f 77 58 15`. The answer moves with this ratio: at
128 and 16 processor cycles per tick the check produces `08 42 1c 30`, and at 256
and 32 it produces `92 33 b8 c9`. So the rate is measurable by finding the one
that reproduces his value.

Three of his timer checks now say the same thing from the other side.
`Timers/random timer0`, `random timer0 enable` and `random timer2` all disagree,
while `timer read vs write` and `timer0 vs other timers` agree, so the register
interface is right and the pacing is what is in question. That is a much sharper
handle than the one below, because those three drive the timers directly rather
than leaning on them to measure something else.

None of the ratios tried so far reproduces his value, and there is a reason to be
careful about reading that as an answer. The same check was run on the author's own implementation, `snes_spc
0.9.0`, and on this family's parts composed, both with no console attached and
both handed the identical program: they agree byte for byte at `5e 71 f3 c3`,
while a console gives `8f 77 58 15`. Two implementations agreeing with each other
and neither agreeing with hardware points at the console the cartridge is driven
from rather than at any ratio inside this unit.

So the coupling is real and the route stays open, but it is not a way to measure
the rate until the console around it is faithful enough to trust. What this buys
is a constraint rather than an answer, and it is recorded because a constraint
that nobody wrote down is a measurement nobody can repeat.

## What was open and is now closed

**What the five registers nothing reads back actually answer.** Zero. All five of
them: the test register, the control register, and the three timer dividers.

This project answered with the memory underneath, on the grounds that inventing a
value would be publishing a claim nobody measured. That was the right instinct and
the wrong answer, and the thing that caught it was
`initial_regs.spc`, one of the checks
[`conformance/checks.manifest.json`](conformance/checks.manifest.json) identifies. It
reads all sixteen of these addresses in order and compares a checksum of the result against a value its
author took on a console. Of every arrangement of the five, exactly one reproduces
that checksum, and it is all five answering zero. The SNESdev wiki says the same
thing in words, which is a second source and not an implementation.

The old behaviour was put back on purpose afterwards to watch the check fail:
sub-check 3 disagreed and reported `d57e2579` against the `9d4d2100` it wanted.

## Where a wire is derived rather than measured

### How fast the sound generator runs beside the processor.

**The document says.** Nothing. No Sony document for this unit is known.

**What this project follows.** One of the generator's clocks per processor
cycle, derived in [`ssmp/rates.py`](ssmp/rates.py) rather than written down. One
crystal reaches the processor through a divisor of 24 and reaches the generator
through 768 for a sample with 32 clocks inside it. Twenty four times thirty two
is seven hundred and sixty eight, so both land on 1,024,000 a second.

**Why.** It is the same shape as the timer ratios beside it: a unit built around
a different crystal with the same divisors behaves identically here, so the
ratio is the claim and the crystal is the reasoning behind it.

**What would settle or reopen it.** A Sony document, or a measurement of the
sample rate against the processor on real hardware.

### What the sound generator actually produces once it is running.

**The document says.** Nothing here. The generator is its own member and carries
its own record.

**What this project does.** Wires it to the shared memory and clocks it, and
checks that doing so does not disturb anything: blargg's three checks still
agree, including the one that reads every byte of memory and the echo buffer.

**Why.** That rules out the generator writing where it should not. It says
nothing about whether what comes out is right, and this member does not claim it
does.

**What would settle or reopen it.** blargg's `spc_dsp6.sfc`, which carries 111
checks taken on a console. It runs against this unit now that the generator is
wired, reaches the envelope group, and reports a disagreement. Which of the 111
disagrees, and whether the fault is in the generator, in this wiring, or in the
harness that drove it, is not isolated.

## What a whole cartridge of his checks said

`spc_smp.sfc` carries nineteen checks with values taken on a console. Eighteen
reached a verdict here and fourteen agree, including the two that bear directly
on what this member models:

| Check | |
| --- | --- |
| `CPU/verify IPL ROM` | agrees |
| `CPU/smp reg read-write behavior` | agrees |
| `CPU/addw and subw`, `psw is 8 independent bits`, `tset tclr` | agree |
| `CPU/wrap-around mem`, `wrap-around pc`, `wrap-around sp` | agree |
| `CPU Instructions/Edge arith`, `Full BRK`, `Full CMP`, `Full DAA DAS` | agree |
| `Timers/timer read vs write`, `timer0 vs other timers` | agree |
| `Timers/random timer0`, `random timer0 enable`, `random timer2` | **disagree** |
| `CPU Timing/mem access times` | **disagrees** |

The first of those is the boot program held to somebody else's checksum rather
than to its own digest, and the second is the register file this session's fix
changed, confirmed by a check that is not the one that found it.

Every verdict is in [`conformance/cartridge.json`](conformance/cartridge.json)
with both values beside it.

**Three timer checks disagree and two agree.** The two that agree are the
register interface, `timer read vs write` and `timer0 vs other timers`. The three
that disagree all drive the timers at rates chosen at random. So what is in
question is the pacing rather than the interface, and pacing is exactly the
figure this member derives rather than reads off a page. That is the sharpest
lead the timer rate question has.

The fourth disagreement, `CPU Timing/mem access times`, is recorded against
[sony-spc700-python](https://github.com/gufranco/sony-spc700-python), where the
author's own implementation was shown to agree with this family's.

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

  A cut-down one was built outside this repository to see what it would buy: a
  65816, memory, a cartridge decoded as LoROM, the four addresses that reach this
  unit, and enough of the video registers to read a report back as text. It
  works. Shay Green's cartridge checks upload through the real boot program and
  run their audio programs on this unit, and what they report is the same at one,
  two, three and five of this unit's cycles per console instruction, so their
  verdicts do not depend on the rate that harness has to invent.

  It is not carried here, and that is a boundary rather than an omission. This
  member is what is left once you have a processor and a sound generator, and a
  console processor is not part of that. Carrying one would hand anybody cloning
  this repository a 65816 that has nothing to do with the part being modelled.
  What those runs found is recorded where the parts they judge live:
  [sony-spc700-python](https://github.com/gufranco/sony-spc700-python) for the
  cycle shape and
  [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python) for the
  audio.
- **The boot program.** Sixty four bytes of Sony's, not carried here, not
  downloaded, and not reconstructible from anything in this repository.
- **The checks taken on hardware.** Shay Green's, not carried here either.
  [`conformance/checks.manifest.json`](conformance/checks.manifest.json) identifies
  them and carries no bytes.
