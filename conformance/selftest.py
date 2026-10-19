from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import console
from conformance.cartridges import ALONGSIDE, DEFAULT_DIRECTORY, DIRECTORY_VARIABLE
from ssmp import Chip, board

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Mapping, Sequence

RECORD = Path(__file__).resolve().parent / "selftest.json"

SOUND_COMMAND = 0x07

SELF_TEST = 0x80

HANDSHAKE = 0x55

ENVELOPE = 0x04

SUB_TESTS = {
    "aram": 0x01,
    "echoRegion": 0x02,
    "envelope": ENVELOPE,
    "echoTiming": 0x10,
    "timer1": 0x20,
    "timer2": 0x40,
}

SLICE = 20_000

LIMIT = 40_000_000

MOST_BLOCKS = 64

SETTLE = 2_000

SUFFIXES = (".sfc", ".smc")

NOTHING_RAN = 2


class NotABlockList(ValueError): ...


class Exchange(NamedTuple):
    handshake: bool
    handshake_after: int | None
    result_after: int | None
    ports: tuple[int, int, int]


def declared(path: Path | None = None) -> dict[str, Any]:
    held: dict[str, Any] = json.loads((path or RECORD).read_text())
    return held


def directories(environment: Mapping[str, str] | None) -> tuple[Path, ...]:
    named = (os.environ if environment is None else environment).get(DIRECTORY_VARIABLE, "")
    return (
        *[Path(where) for where in named.split(os.pathsep) if where],
        ALONGSIDE,
        DEFAULT_DIRECTORY,
    )


def located(digest: str, folders: Sequence[Path]) -> Path | None:
    for folder in folders:
        held = sorted(folder.iterdir()) if folder.is_dir() else []
        for path in held:
            if (
                path.suffix.lower() in SUFFIXES
                and hashlib.sha256(path.read_bytes()).hexdigest() == digest
            ):
                return path
    return None


def word(image: bytes, at: int) -> int:
    return image[at] | (image[at + 1] << 8)


def blocks(image: bytes, at: int) -> tuple[list[tuple[int, bytes]], int]:
    found: list[tuple[int, bytes]] = []
    for _ in range(MOST_BLOCKS):
        length, where = word(image, at), word(image, at + 2)
        if length == 0:
            return found, where
        found = [*found, (where, image[at + 4 : at + 4 + length])]
        at += 4 + length
    raise NotABlockList(f"no terminator within {MOST_BLOCKS} blocks")


def upload_all(unit: Any, items: Sequence[tuple[int, bytes]], entry: int) -> None:
    after: int | None = None
    for where, data in items:
        console.upload(unit, data, where, jump=False, after=after)
        after = len(data) - 1
    unit.write(2, entry & 0xFF)
    unit.write(3, entry >> 8)
    unit.write(1, 0x00)
    kick = ((after or 0) + 2) & 0xFF
    unit.write(0, kick)
    echoed(unit, kick)
    unit.run_for(SETTLE)


def echoed(unit: Any, value: int) -> None:
    for _ in range(console.PATIENCE):
        if unit.read(0) == value:
            return
        unit.run_for(console.SLICE)
    raise console.NeverAnswered(
        f"the jump into the program was never acknowledged with {value:#04x}"
    )


def exchange(unit: Any, before: Sequence[int], slice_: int = SLICE, limit: int = LIMIT) -> Exchange:
    for index, value in enumerate(before):
        unit.write(index, value)
    unit.write(0, SOUND_COMMAND)
    unit.run_for(slice_)
    unit.write(0, SELF_TEST)
    spent, answered = 0, None
    for _ in range(limit // slice_):
        spent += unit.run_for(slice_)
        now = unit.read(1)
        if now == HANDSHAKE and answered is None:
            answered = spent
        if answered is not None and now != HANDSHAKE:
            return Exchange(True, answered, spent, ports(unit))
    return Exchange(answered is not None, answered, None, ports(unit))


def ports(unit: Any) -> tuple[int, int, int]:
    return unit.read(1), unit.read(2), unit.read(3)


def measured(run: Exchange) -> dict[str, Any]:
    result = run.ports[0]
    return {
        "handshake": run.handshake,
        "cyclesToHandshake": run.handshake_after,
        "cyclesToResult": run.result_after,
        "result": result,
        "ports": f"{run.ports[1]:02x} {run.ports[2]:02x}",
        "subTests": {name: not result & bit for name, bit in SUB_TESTS.items()},
    }


def problems(run: Mapping[str, Any]) -> list[str]:
    found = [] if run["handshake"] else [f"never answered ${HANDSHAKE:02x} on port 1"]
    if run["cyclesToResult"] is None:
        found = [*found, "never reported a result"]
    if run["result"] & ~ENVELOPE:
        found = [*found, f"result ${run['result']:02x} fails a sub-test the program enforces"]
    if run["ports"] != "00 00":
        found = [*found, f"ports 2 and 3 read {run['ports']}, not 00 00"]
    return found


def one_image(
    entry: Mapping[str, Any], options: Mapping[str, Any]
) -> tuple[bool, bool, dict[str, Any]]:
    say, where = options["say"], located(entry["sha256"], options["folders"])
    if where is None:
        say(f"  {entry['id']}: not on this machine, so nothing was run")
        return False, False, dict(entry)
    items, start = blocks(where.read_bytes(), int(entry["blockList"], 16))
    unit = options["build"]()
    upload_all(unit, items, start)
    run = measured(exchange(unit, entry["before"], options["slice_"], options["limit"]))
    found = problems(run) + ([] if run == entry["measured"] else ["differs from the recorded run"])
    say(f"  {entry['id']}: result ${run['result']:02x}, ports {run['ports']}")
    for problem in found:
        say(f"  {entry['id']}: {problem}")
    return True, bool(found), {**entry, "measured": run}


def main(
    argv: Sequence[str] = (),
    say: Callable[[str], None] = print,
    build: Callable[[], Any] = lambda: Chip("ssmp").reset(),
    why_not: Callable[[], str | None] = board.why_not,
    environment: Mapping[str, str] | None = None,
    held: dict[str, Any] | None = None,
    record_path: Path | None = None,
    slice_: int = SLICE,
    limit: int = LIMIT,
) -> int:
    stopped = why_not()
    if stopped is not None:
        say(f"nothing was run: {stopped}")
        return NOTHING_RAN
    record = declared() if held is None else held
    folders = directories(environment)
    options = {"say": say, "build": build, "folders": folders, "slice_": slice_, "limit": limit}
    results = [one_image(entry, options) for entry in record["images"]]
    ran, wrong = sum(one[0] for one in results), sum(one[1] for one in results)
    target = RECORD if "--write" in argv else record_path
    if target is not None:
        target.write_text(
            json.dumps({**record, "images": [one[2] for one in results]}, indent=2) + "\n"
        )
    if not ran and not wrong:
        say(
            f"nothing was run: no image is on this machine. Name a directory in {DIRECTORY_VARIABLE}"
        )
        return NOTHING_RAN
    say(f"{ran} run, {wrong} wrong")
    return 1 if wrong else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
