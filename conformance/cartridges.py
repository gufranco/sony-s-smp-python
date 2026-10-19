from __future__ import annotations

import datetime
import hashlib
import itertools
import json
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.host import Host
from ssmp import Chip, board

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parent.parent

PROCESSOR = ROOT / "mos65xx-python"

RECORD = Path(__file__).resolve().parent / "cartridge.json"

DIRECTORY_VARIABLE = "SSMP_CARTRIDGE_DIR"

DEFAULT_DIRECTORY = ROOT / "cartridges"

ALONGSIDE = ROOT.parent / "cartridges"

CHECKSUM = (0xDC, 0xDD, 0xDE, 0xDF)

COMPARE = 0x78

COMPARE_X = 0xC8

COMPARE_Y = 0xAD

STATUS_COMPARES = {COMPARE_X: "x", COMPARE_Y: "y"}

BRANCH = 0xD0

EMPTIED = 0x00

STRIDE = 5

NAMES = range(0x300, 0x500)

MASTER_PER_HOST_CYCLE = 8

MASTER_PER_UNIT_CYCLE = 21

CHUNK = 2_000_000

LIMIT = 400_000_000

ENDINGS = ("PASSED", "Failed", "Done", "FAIL", "Success")

FAILURES = ("FAIL", "Failed")

COPIER_HEADER = 512

ROM_BANK_BYTES = 0x8000

NOTHING_RAN = 2

WHY_NOT_PROCESSOR = (
    "the console's processor is not here: the cartridges run on a 65816 from"
    " mos65xx-python, which is a member of this family consumed as a submodule, and"
    " the submodule is not checked out. Run git submodule update --init --recursive"
)


def processor_absent(where: Path = PROCESSOR) -> str | None:
    return None if (where / "mos65xx" / "__init__.py").is_file() else WHY_NOT_PROCESSOR


def ready() -> str | None:
    return board.why_not() or processor_absent()


def processor() -> Any:
    if str(PROCESSOR) not in sys.path:
        sys.path.append(str(PROCESSOR))
    import mos65xx

    return mos65xx


def find(name: str, environment: Mapping[str, str] | None = None) -> Path | None:
    named = (os.environ if environment is None else environment).get(DIRECTORY_VARIABLE, "")
    wanted = [Path(where) for where in named.split(os.pathsep) if where]
    for where in [*wanted, ALONGSIDE, DEFAULT_DIRECTORY]:
        if (where / name).is_file():
            return where / name
    return None


def declared(path: Path | None = None) -> dict[str, Any]:
    held: dict[str, Any] = json.loads((path or RECORD).read_text())
    return held


def hexed(values: Sequence[int]) -> str:
    return " ".join(f"{value:02x}" for value in values)


class Watch:
    def __init__(self, space: Any, host: Host, processor: Any = None, excuse: int = 0) -> None:
        self.space = space
        self.host = host
        self.processor = processor
        self.excuse = excuse
        self.verdicts: list[dict[str, Any]] = []
        self.excused: list[dict[str, Any]] = []

    def read8(self, address: int) -> int:
        if self.space.memory.read8(address) == COMPARE and self.compares(address):
            self.record(address)
        if self.excuse and self.checks_a_status_word(address):
            self.weigh(address)
        return int(self.space.read8(address))

    def checks_a_status_word(self, address: int) -> bool:
        memory = self.space.memory
        return bool(
            memory.read8(address) in STATUS_COMPARES
            and memory.read8(address + 2) == BRANCH
            and self.processor.pc == address
        )

    def weigh(self, address: int) -> None:
        memory = self.space.memory
        register = STATUS_COMPARES[memory.read8(address)]
        wanted, held = memory.read8(address + 1), getattr(self.processor, register)
        if wanted == held:
            return
        excused = not (wanted ^ held) & ~self.excuse
        found = {"at": f"{address:04x}", "expected": hexed([wanted]), "thisModel": hexed([held])}
        self.excused = [*self.excused, {**found, "excused": excused}]
        if excused:
            memory.write8(address + 1, held)

    def write8(self, address: int, value: int) -> None:
        self.space.write8(address, value)

    def compares(self, address: int) -> bool:
        memory = self.space.memory
        return all(
            memory.read8(address + index * STRIDE) == COMPARE
            and memory.read8(address + index * STRIDE + 2) == place
            and memory.read8(address + index * STRIDE + 3) == BRANCH
            for index, place in enumerate(CHECKSUM)
        )

    def record(self, address: int) -> None:
        memory = self.space.memory
        console = [memory.read8(address + index * STRIDE + 1) for index in range(len(CHECKSUM))]
        model = [memory.read8(place) for place in CHECKSUM]
        verdict = {"check": self.name(), "agreed": console == model}
        self.verdicts.append({**verdict, "console": hexed(console), "thisModel": hexed(model)})
        for index in range(len(CHECKSUM)):
            memory.write8(address + index * STRIDE + 3, EMPTIED)
            memory.write8(address + index * STRIDE + 4, EMPTIED)

    def name(self) -> str:
        blob = bytes(self.space.memory.read8(address) for address in NAMES)
        runs = [run.decode() for run in re.findall(rb"[ -~]{4,}", blob) if b"/" in run]
        return runs[0].split(", ", 1)[-1] if runs else self.host.current_line()


class Played(NamedTuple):
    verdicts: list[dict[str, Any]]
    screen: str
    cycles: int
    excused: list[dict[str, Any]]


def rom_of(raw: bytes) -> bytes:
    return raw[COPIER_HEADER:] if len(raw) % ROM_BANK_BYTES == COPIER_HEADER else raw


def advance(cpu: Any, unit: Any, owed: int, cycles: int) -> int:
    target = cpu.cycles + cycles
    for _ in itertools.takewhile(lambda _: cpu.cycles < target, range(cycles)):
        before = cpu.cycles
        cpu.step()
        owed += (cpu.cycles - before) * MASTER_PER_HOST_CYCLE
        due = owed // MASTER_PER_UNIT_CYCLE
        if due:
            owed -= unit.run_for(due) * MASTER_PER_UNIT_CYCLE
    return owed


def play(
    raw: bytes,
    unit: Any,
    limit: int = LIMIT,
    chunk: int = CHUNK,
    excuse: int = 0,
    passes: int | None = None,
) -> Played:
    host = Host(rom_of(raw), unit)
    watch = Watch(unit.space, host, unit.processor, excuse)
    unit.processor.memory = watch
    cpu = processor().Cpu("65816", host)
    cpu.reset()
    owed = 0
    for _ in range(max(1, limit // chunk)):
        owed = advance(cpu, unit, owed, chunk)
        if any(word in host.screen() for word in ENDINGS):
            break
        if passes is not None and host.passes >= passes:
            break
    return Played(watch.verdicts, host.screen(), cpu.cycles, watch.excused)


def judged(entry: Mapping[str, Any], played: Played) -> list[str]:
    problems = [
        f"{one['check']}: a console gave {one['console']}, this model {one['thisModel']}"
        for one in played.verdicts
        if not one["agreed"]
    ]
    problems += [
        f"the status word at {one['at']} is {one['thisModel']}, not {one['expected']}"
        for one in played.excused
        if not one["excused"]
    ]
    if any(word in played.screen for word in FAILURES):
        problems.append("the cartridge reports a failure on its own screen")
    recorded = (entry["checks"], entry["screen"], entry.get("excused", []))
    if (played.verdicts, played.screen, played.excused) != recorded:
        problems.append("differs from the recorded run")
    return problems


def measured(entry: Mapping[str, Any], played: Played) -> dict[str, Any]:
    agreed = sum(1 for one in played.verdicts if one["agreed"])
    return {
        **entry,
        "runOn": datetime.datetime.now(datetime.UTC).date().isoformat(),
        "screen": played.screen,
        "verdicts": len(played.verdicts),
        "agreed": agreed,
        "disagreed": len(played.verdicts) - agreed,
        "checks": played.verdicts,
        "excused": played.excused,
    }


def one_cartridge(
    entry: Mapping[str, Any], options: Mapping[str, Any]
) -> tuple[bool, bool, dict[str, Any]]:
    say, where = options["say"], options["find"](entry["name"])
    if where is None:
        say(f"  {entry['name']}: not on this machine, so nothing was run")
        return False, False, dict(entry)
    raw = Path(where).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        say(f"  {entry['name']}: does not match its published sha256")
        return False, True, dict(entry)
    excuse = int(entry.get("excuse", "00"), 16)
    passes = entry.get("passes")
    played = play(raw, options["build"](), options["limit"], options["chunk"], excuse, passes)
    problems = judged(entry, played)
    disagree = sum(1 for one in played.verdicts if not one["agreed"])
    say(f"  {entry['name']}: {len(played.verdicts)} verdicts, {disagree} disagree")
    for problem in problems:
        say(f"  {entry['name']}: {problem}")
    return True, bool(problems), measured(entry, played)


def main(
    argv: Sequence[str] = (),
    say: Callable[[str], None] = print,
    build: Callable[[], Any] = lambda: Chip("ssmp").reset(),
    why_not: Callable[[], str | None] = ready,
    find: Callable[[str], Path | None] = find,
    held: dict[str, Any] | None = None,
    record_path: Path | None = None,
    limit: int = LIMIT,
    chunk: int = CHUNK,
) -> int:
    stopped = why_not()
    if stopped is not None:
        say(f"nothing was run: {stopped}")
        return NOTHING_RAN
    record = declared() if held is None else held
    options = {"say": say, "build": build, "find": find, "limit": limit, "chunk": chunk}
    results = [one_cartridge(entry, options) for entry in record["cartridges"]]
    ran, wrong = sum(one[0] for one in results), sum(one[1] for one in results)
    target = RECORD if "--write" in argv else record_path
    if target is not None:
        kept = {**record, "cartridges": [one[2] for one in results]}
        target.write_text(json.dumps(kept, indent=2) + "\n")
    if not ran and not wrong:
        say(
            f"nothing was run: no cartridge is on this machine. Name a directory in {DIRECTORY_VARIABLE}"
        )
        return NOTHING_RAN
    say(f"{ran} run, {wrong} wrong")
    return 1 if wrong else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
