# Open questions

What this project does not know for certain, and what it would take to find out.

This is a short list, and the reason is the subject. Almost everything this
member models is settled by Nintendo's development manual, which prints the
timers, by the part's own boot program, which is Sony's code rather than
anybody's reading of it, or by checks Shay Green wrote that carry values he took
on a console. What is left is what none of those reaches.

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

## What was open and is now closed

**The rate the timers tick at, and how they count.** Book I of Nintendo's
development manual prints it: Figure 3-5-1 draws one prescaler on a 2.048 MHz
clock, and page 3-5-1 says it feeds timers 0 and 1 at 8 kHz and timer 2 at
64 kHz. Page 3-1-1 gives the shortest instruction as 1.953 microseconds, and
Appendix C gives the shortest instructions two cycles, so a cycle is 976.5
nanoseconds and the ticks are 128 and 16 cycles apart. Page 3-5-2 says switching
a timer on clears its two counters, the stage is matched to the divider by
equality, and a reset stops the timers. Every one of those is quoted in
[`conformance/hardware.json`](conformance/hardware.json) with its page and held
by a test.

This model had the rates and had the rest wrong: it restarted a prescaler for
each timer whenever one was switched on, and wrapped a divider lowered below the
stage at once. Shay Green's `spc_smp.sfc` found it. Its three random timer checks
and its memory access check disagreed with values he took on a console, and with
the prescaler shared and free running and the divider matched by equality, all
four reproduce them (as of 2026-10-19). The cartridge is SHA-256
`2ed302c5b989675d4ab6b40001fd5166ac4c6e0188a6b1b6df878e4608999c03`, from
`https://gitlab.com/higan/snes-test-roms` at commit
`26e8aa91e0d3b90b901e7e693bc4a8244b391d7b`, and is not carried here.

**How fast the sound generator runs beside the processor.** One generator clock
per processor cycle. The 41 checks in the timing group of Shay Green's
`spc_dsp6.sfc` read and write the generator's registers at named steps of its
thirty two step schedule, timed by this processor's own instructions, and all 41
reproduce the values he took on a console. A generator running at any other rate
beside the processor would move every one of those steps.

**What the sound generator produces once it is running, as far as the cartridge
reaches.** All 104 verdicts `spc_dsp6.sfc` reaches here agree with a console.
The seven that used to disagree had three causes, two in the generator and one
here: every write to the sixteen registers also lands in the memory beneath them,
which the generator reads directly, and `$F8` and `$F9` read back what was last
written to them rather than that memory. The check `Misc/$F0-$FF are not ram`
reproduces its console value only with both. The sample values themselves are
the generator's question and stay in its own record.

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

## Before the console's reset reaches the unit

### What the sound generator writes between power on and the reset.

**The document says.** Nothing. No Sony document for this unit is known, and
the generator's own record marks what it holds at power on, and what a reset
sets beyond the flag register, as unverified.

**What this project does.** Builds the unit with the generator scrambled from
its seed and the processor scrambled too, and resets neither. A caller who runs
a unit before calling `reset()` clocks that scrambled generator, and when its
scrambled flag register leaves echo writes on, it writes its echo buffer
wherever its scrambled registers point, into the memory the processor runs on.
Nothing here stops that. `reset()` is the console's reset line: it resets the
generator to what `resetLine` in
[sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python)'s record
lists, with the flag register at `$e0`, which turns echo writes off, and then
resets the processor, which starts the boot program.

**Why.** The console's reset line reaches both halves, so the unit's reset
resets both, and a unit nobody reset holds what power on left in both. Whether a
real generator runs, and writes, before that line reaches it is not settled by
any source here. With the seed this package builds the generator from, the
question does not bite: the scrambled flag register comes up as `$25`, whose
bit 5 turns echo writes off, and a unit run for 64,000 cycles without a reset
had its generator write nothing to memory (as of 2026-10-17). A scramble with
that bit clear would write, and this model would let it.

**What would settle or reopen it.** A logic capture of a real unit's memory bus
from the rail coming up until the reset line is released, repeated across power
cycles, which shows whether the generator drives any write before the reset
reaches it.

### What the reset line sets in the unit's own registers, and whether memory survives it.

**The document says.** Book I of Nintendo's development manual, page 3-5-2,
says that at the time of reset `ST0` of the control register is 0 and the
timer's counter and divider are indeterminate, and Figure 3-4-3 gives the control
register's reset value as `--00-000`. It says nothing about memory, the ports or
the other registers.

**What this project does.** `reset()` shows the boot window, stops all three
timers, resets the generator and resets the processor, and nothing else. Memory
keeps every byte. The timers keep their dividers, stages and counters, the ports
keep both directions, and the test register and the generator's address register
keep what was last written.

**Why.** The boot window has a source in the boot program: it never writes
`$f1`, and the processor leaves reset through the vector at `$fffe`, which only
the boot program supplies, so the window has to be visible then. The timer starts
have a source in the manual. Nothing settles the rest, and a reset leaves what it
does not define holding what it held.

**What would settle or reopen it.** A capture of a real unit's registers and
memory either side of a console reset, with the timers running and the ports
written before it.

## What a whole cartridge of his checks said

`spc_smp.sfc` carries nineteen checks with values taken on a console. Eighteen
reach a verdict here and all eighteen agree (as of 2026-10-19):

| Check                                                                 |       |
| --------------------------------------------------------------------- | ----- |
| `CPU/verify IPL ROM`                                                  | agree |
| `CPU/smp reg read-write behavior`                                     | agree |
| `CPU/addw and subw`, `psw is 8 independent bits`, `tset tclr`         | agree |
| `CPU/wrap-around mem`, `wrap-around pc`, `wrap-around sp`             | agree |
| `CPU Instructions/Edge arith`, `Full BRK`, `Full CMP`, `Full DAA DAS` | agree |
| `CPU Timing/mem access times`                                         | agree |
| `Timers/timer read vs write`, `timer0 vs other timers`                | agree |
| `Timers/random timer0`, `random timer0 enable`, `random timer2`       | agree |

The nineteenth, `CPU Timing/time all opcodes`, prints its name and reaches no
comparison here. Every verdict is in
[`conformance/cartridge.json`](conformance/cartridge.json) with both values
beside it.

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
