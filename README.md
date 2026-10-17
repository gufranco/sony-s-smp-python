# Sony S-SMP

The Sony S-SMP audio unit of the Super Nintendo in Python: an SPC700 processor and an S-DSP sound generator sharing 64 KB, four ports, three timers and a 64-byte boot program, held to that boot program and to checks whose values were taken on a console.

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/sony-s-smp-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/sony-s-smp-python)](https://github.com/gufranco/sony-s-smp-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**4** ports are the whole console interface, **3** checks carrying values taken on a console, **0** disagreements, **14** of **18** verdicts from a cartridge of checks agree, **725** tests, **100%** statement and branch coverage, no dependencies

```python
import ssmp

unit = ssmp.Chip("ssmp").reset()
unit.run_for(6300)
print(hex(unit.read(0)), hex(unit.read(1)))

unit.write(0, 0xCC)
unit.run_for(64)
print(hex(unit.read(0)))
```

```
0xaa 0xbb
0xcc
```

The unit runs its boot program for 6,300 cycles and then answers `0xaa` on port 0 and `0xbb` on port 1. Every Super Nintendo waits for those two bytes before it sends its audio hardware anything. The console then writes `0xcc` to port 0, and 64 cycles later the boot program echoes it back, which means it is ready to take a block.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any, to fetch the two submodules |
| The boot program | A 64-byte copy you already own |

```bash
git clone --recurse-submodules https://github.com/gufranco/sony-s-smp-python.git
cd sony-s-smp-python
python3 ssmp/doctor.py
```

The package imports nothing outside the standard library. The processor is [sony-spc700-python](https://github.com/gufranco/sony-spc700-python) and the sound generator is [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python), both checked out as submodules. Without them nothing builds, and `git submodule update --init --recursive` fetches them.

The boot program is Sony's and is not in this repository. Put a copy in `boot/`, in the `boot/` of the directory this checkout sits in, or in any directory named by `SSMP_BOOT_DIR`. Every example that builds a unit from it refuses on a machine without one, with a sentence saying what is missing.

The doctor checks the machine and the checkout, builds the unit, and ends with one line. It exits 0 when every finding about the package passes and 1 otherwise. Paste its whole output into any bug report. With both submodules and a boot program present it ends with:

```
  5 checks, nothing to report
```

Installing the package also installs the same report as `ssmp-doctor`.

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/sony-s-smp-python/releases).

## The interface

`ssmp.Chip(model, boot=None, identity=None, images=None, fill=None)` builds one unit, powered on and running its boot program. `model` is required.

| Argument | Meaning |
|:--|:--|
| `model` | The model name. Case and the separators `-`, `_`, `.` and space are ignored, so `"S-SMP"` and `"s_smp"` both build `ssmp` |
| `boot` | The 64 bytes of a boot program. Left out, the unit searches the boot directories and identifies what it finds by SHA-256 |
| `identity` | The record for a supplied `boot`. Left out, it is recorded as `supplied` |
| `images` | A catalogue to search in place of the boot directories, keyed by model name |
| `fill` | The byte the processor's memory is filled with at power on. Left out, it is scrambled |

### Calls

| Call | Effect |
|:--|:--|
| `reset()` | Builds a fresh processor, memory, sound generator and register space from the same boot program. Returns the unit |
| `step()` | One processor instruction. Returns the cycles it took |
| `run_for(cycles)` | Instructions until at least `cycles` cycles have passed. Returns the cycles spent |
| `read(index)` | What the console reads at port `index`, 0 to 3: the byte the unit last wrote there |
| `write(index, value)` | What the console writes to port `index`: the byte the unit reads there |

### State

| Attribute | Meaning |
|:--|:--|
| `model` | The canonical model name |
| `part` | The same name, as the boot catalogue keys it |
| `identity` | The boot program's record: `part`, `processor`, `revision`, `bytes_long` |
| `cycles` | Processor cycles since the unit was built. A reset does not clear it |
| `processor` | The SPC700 from the processor submodule |
| `dsp` | The S-DSP from the sound generator submodule |
| `space` | The 64 KB the processor sees, with the 16 registers at `$00F0` and the boot window at `$FFC0` |

`processor`, `dsp` and `space` reach past what a console can. A check that drives them is checking the model, not the part.

### Module contents

| Name | Content |
|:--|:--|
| `ssmp.MODELS` | The one `Model` record, keyed by name |
| `ssmp.Model` | A record with `name`, `summary`, `processor`, `memory` and `boot` |
| `ssmp.why_not()` | `None` when a unit can be built here, or the sentence saying what is missing |
| `ssmp.available()` | The boot programs found here, keyed by model name |
| `ssmp.VERSION`, `ssmp.__version__` | The installed version |

| Error | Raised when |
|:--|:--|
| `ssmp.UnknownModelError` | No model is named, or the name is not one this package covers. The message lists the names there are |
| `ssmp.NoBootRom` | A submodule is not checked out, or no boot program is found for the model |
| `ssmp.WrongShape` | A boot program is not exactly 64 bytes |
| `ssmp.Unrecognised` | A file's SHA-256 matches nothing in [`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) |
| `ssmp.Corrupt` | A file matches on SHA-256 and disagrees on another published digest, or matches a recorded bad dump |

```python
import ssmp
from ssmp import firmware

for name in (None, "s-dsp"):
    try:
        ssmp.Chip(name)
    except ssmp.UnknownModelError as error:
        print(error)

try:
    ssmp.Chip("ssmp", boot=bytes(10))
except ssmp.WrongShape as error:
    print(error)

try:
    firmware.identify(bytes(100))
except ssmp.Unrecognised as error:
    print(error)
```

```
no model was named, and this package will not choose one for you. Name one of: ssmp
s-dsp is not a unit this package covers; there is ssmp
a boot program is exactly 64 bytes and this one is 10
nothing in the manifest has sha256 cd00e292c5970d3c5e2f0ffa5171e555bc46bfc4faddfb4a418b6840b86e79a3. It is 100 bytes and a boot program is 64, so this is not one of them at all.
```

When the file is the right program in the wrong form, the message names the repair instead: read it as a hexadecimal listing, or take the first or last 64 bytes of a larger file.

### A port is two bytes

```python
import ssmp

unit = ssmp.Chip("ssmp").reset()
unit.run_for(6300)
unit.write(2, 0x55)
print(unit.read(2), unit.space.read8(0xF6))
```

```
0 85
```

Each port holds one byte from the console to the unit and one from the unit to the console. The console wrote `0x55` to port 2 and reads back 0, the byte the unit last wrote there, while the unit reads 85 at `$F6`. A model that keeps one byte per port passes until two writes cross, and then hands both sides a value neither side sent.

### Timers

```python
import ssmp

unit = ssmp.Chip("ssmp", boot=bytes(64))
space = unit.space
space.write8(0xFA, 0)
space.write8(0xFC, 2)
space.write8(0xF1, 0x85)

space.spend(128 * 256 * 3)
print(space.read8(0xFD), space.read8(0xFD))

space.write8(0xF1, 0x80)
space.write8(0xF1, 0x84)
space.spend(16 * 2 * 20)
print(space.read8(0xFF))
print([space.read8(address) for address in (0xF0, 0xF1, 0xFA, 0xFB, 0xFC)])
```

```
3 0
4
[0, 0, 0, 0, 0]
```

The example builds a unit from 64 zero bytes, so it runs on a machine with no boot program, and drives the register space directly. Timers 0 and 1 tick every 128 processor cycles and timer 2 every 16. Each divides its ticks by the value written to its divider at `$FA` to `$FC`, and a divider of 0 divides by 256. Writing `0x85` to the control register at `$F1` enables timers 0 and 2 and keeps the boot window visible.

Timer 0 counts 3 in 98,304 cycles, and the read clears its counter, so a second read gets 0. Timer 2 counts 20 and reads 4, because the counter is four bits. The test register, the control register and the three dividers are written and never read back: all five answer 0.

| Address | Register |
|:--|:--|
| `$F0` | Test. Reads 0 |
| `$F1` | Control: timer enables in bits 0 to 2, clear ports 0 and 1 in bit 4, clear ports 2 and 3 in bit 5, boot window in bit 7. Reads 0 |
| `$F2`, `$F3` | The sound generator's address and data |
| `$F4` to `$F7` | Ports 0 to 3 |
| `$F8`, `$F9` | Ordinary memory |
| `$FA` to `$FC` | Timer dividers. Read 0 |
| `$FD` to `$FF` | Timer counters, cleared by the read |

### Command-line tools

| Command | What it does | Exit codes |
|:--|:--|:--|
| `python3 ssmp/doctor.py` | Reports the machine and the checkout, then builds and resets the unit | 0 nothing to report, 1 a finding did not pass |
| `python3 -m conformance.against_checks` | Runs Shay Green's three checks against the unit | 0 all agree, 1 one disagrees or does not match its digests, 2 nothing was checked |
| `python3 -m conformance.speed` | Measures processor cycles per second against a floor of 20,000 | 0 at or above the floor, 1 below it, 2 nothing was measured |
| `python3 -m conformance.links` | Probes every address in this README and prints a JSON report | 0 none gone, 1 one answers 404 or 410 |
| `python3 -m conformance.package <wheel>` | Checks a built wheel ships every module and no test | 0 clean, 1 a fault or no such file, 2 no wheel named |

## What composing the halves found

Neither half models the other, because two models of one wire is how two models disagree. Putting them together found a defect in the processor.

The processor scrambled every flag at reset, on the grounds that its manual gives no power-on values. The boot program answers the console with `mov $f4,#$aa` and `mov $f5,#$bb`, and those reach the ports only while the direct page is the zero page. With the direct page flag set they write ordinary memory at `$01f4`, the handshake never appears, and no cartridge gets its audio program uploaded. The fix went into [sony-spc700-python](https://github.com/gufranco/sony-spc700-python): that flag is clear after reset.

## What a check taken on hardware found

The five registers that are written and never read back answered with the memory underneath.

`initial_regs.spc` reads all sixteen registers in order and compares a checksum of the result against a value its author took on a console. Of every arrangement of those five, exactly one reproduces the checksum: all five answer 0. The [SNESdev wiki](https://snes.nesdev.org/wiki/S-SMP) says the same in words.

The old behaviour was put back afterwards to watch the check fail. It disagreed on sub-check 3 and reported `d57e2579` against the `9d4d2100` it wanted. The other two checks still agreed, because neither reads those registers.

## One unit, not two halves in a box

The processor and the sound generator read the same 64 KB, because on the part they do. Voices fetch their compressed blocks out of it and the echo unit writes back into it. A store per half would lose every sample a program uploaded.

The generator takes one clock for every processor cycle. [`ssmp/rates.py`](ssmp/rates.py) derives that rather than stating it: one crystal reaches the processor through a divisor of 24, and reaches the generator through 768 for a sample with 32 clocks inside it. 24 times 32 is 768, and both come out at 1,024,000 a second.

```python
from ssmp import rates

print(rates.PROCESSOR_HZ, rates.GENERATOR_HZ, rates.GENERATOR_CLOCKS)
print(rates.SLOW_TIMER_CYCLES, rates.FAST_TIMER_CYCLES)
```

```
1024000 1024000 1
128 16
```

The generator comes up reset rather than scrambled, the one exception in this unit. The console's reset line reaches it, and a reset generator writes no echo. Scrambled echo registers would point it at memory it then overwrites.

## What is not modelled

- **Any ratio between this unit's clock and the console's.** They run from separate crystals and neither divides the other, so a ratio is a property of one board. No figure is published, and no elapsed time is offered in console cycles. The ratio above is between two halves on one crystal.
- **The processor and the sound generator.** Each is its own member, consumed here as a submodule.
- **The console.** [`conformance/console.py`](conformance/console.py) plays a console's half of the protocol in a check and models nothing else.

## The boot program is not here

Those 64 bytes are Sony's. This repository does not carry them, does not download them, and nothing in it can reconstruct them. [`ssmp/artifacts.manifest.json`](ssmp/artifacts.manifest.json) carries four digests of them and no bytes. SHA-256 decides; CRC32, MD5 and SHA-1 are cross-checked, and a file that matches on SHA-256 and disagrees on one of them is refused as `Corrupt`.

The search order is `SSMP_BOOT_DIR`, which may name several directories, then `boot/` beside this checkout, then `boot/` inside it. The first copy found for a model wins.

## Models

```python
import ssmp

for name, model in ssmp.MODELS.items():
    print(name, model.processor, model.memory, model.boot)

print(ssmp.Chip("S-SMP", boot=bytes(64)).model)
```

```
ssmp spc700 65536 64
ssmp
```

There is one model, because Sony shipped one unit. The catalogue exists so that a hardware difference found later is a new entry, not a new interface. The model is still named at construction. A caller who learns to leave it out here writes the same call against mos65xx-python, which covers sixteen parts, and gets a part nobody picked, so naming none raises and lists every model there is.

## Is it right

No Sony document for the S-SMP is known to exist. Three things stand in for one, all on the second rung of [the family's authority ladder](FAMILY.md): the part's own code, checks carrying values taken on a console, and a cartridge of checks.

**The part's own code.** The boot program is 64 bytes Sony wrote, so the console interface is read off them. [`conformance/console.py`](conformance/console.py) writes that sequence down and [`conformance/boot.test.py`](conformance/boot.test.py) plays it at the unit: the handshake `0xaa` and `0xbb`, the destination, a block with every byte acknowledged by its own count, a second block after the first, and the jump into what was uploaded.

**Checks carrying values taken on a console.** Shay Green, known as blargg, wrote three that hold an audio unit to real hardware. A `.spc` file is a whole unit written down, so they run here directly, with no console in the chain:

| Check | What it settles | Sub-checks | Cycles |
| --- | --- | ---: | ---: |
| `initial_regs.spc` | The six processor registers, all sixteen addresses that are not memory, and the sound generator's whole register file | 4 | 744,661 |
| `initial_in_ports.spc` | The four ports, read as the first thing the program does | 1 | 654,978 |
| `full_ram.spc` | Every byte of memory, the stack page, the echo buffer, and the three bytes under the stack pointer | 6 | 19,793,439 |

All three agree. [`conformance/hardware.json`](conformance/hardware.json) records each run.

**A cartridge of checks, driven by a cut-down console.** Shay Green's `spc_smp` cartridge reaches 18 verdicts and 14 agree, recorded one by one in [`conformance/cartridge.json`](conformance/cartridge.json). Among the agreeing ones are `CPU/verify IPL ROM` and `CPU/smp reg read-write behavior`. Three of the four disagreements are timer pacing, the question [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) already turns on. The fourth, `CPU Timing/mem access times`, is recorded against the processor.

The `.spc` files are Shay Green's and are not carried here. [`conformance/checks.manifest.json`](conformance/checks.manifest.json) identifies them by size and four digests. Put copies you own in `spc/` or name a directory in `SSMP_SPC_DIR`; without them, `python3 -m conformance.against_checks` exits 2 and says nothing was checked.

Where the sources contradict the model, or each other, the entry is in [`conformance/divergences.json`](conformance/divergences.json).

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent, and what will bite you | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| What is not known, and the measurement that would settle each | [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/sony-s-smp-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
python3 -m coverage erase
for file in $(find ssmp conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Each module has a test file beside it, named after it, and each runs on its own. Coverage is a hard gate at 100% statement and branch. Every check that needs the boot program or one of Shay Green's files skips and says so, rather than reporting a pass.

`python3 -m conformance.against_checks` and `python3 -m conformance.speed` run outside the coverage step. The longest check is 19,793,439 cycles, about 19 seconds of the unit's own time, and the floor measures the model without a tracer.

## References

- The S-SMP boot program, 64 bytes, SHA-256 `c95f88b299030d5afa55b1031e2b5ef2dff650c4b4e6bb6f8b1359436521278f`. Sony's, not redistributable, and not in this repository.
- Shay Green, `initial_regs.spc`, `initial_in_ports.spc`, `full_ram.spc` and the `spc_smp` cartridge, for values taken on a console. Not carried here.
- [SNESdev wiki, S-SMP](https://snes.nesdev.org/wiki/S-SMP), a later document rather than a Sony one, cited where it is used.
- [sony-spc700-python](https://github.com/gufranco/sony-spc700-python) for the processor and [sony-s-dsp-python](https://github.com/gufranco/sony-s-dsp-python) for the sound generator, each with its own references. The sound generator is held to Nintendo's own tables.

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
