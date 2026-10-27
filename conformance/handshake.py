from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.cartridges import DIRECTORY_VARIABLE
from conformance.selftest import KEPT, directories, located
from ssmp import Chip, board

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Mapping, Sequence

RECORD = Path(__file__).resolve().parent / "handshake.json"

MARKER = 0x5A

LANDING = bytes((0x8F, MARKER, 0xF7, 0x2F, 0xFE))

PATIENCE = 400

SLICE = 64

SETTLE = 2_000

NOTHING_RAN = 2


class Constants(NamedTuple):
    ready: int
    destination: int
    start: int
    length: int


def declared(path: Path | None = None) -> dict[str, Any]:
    held: dict[str, Any] = json.loads((path or RECORD).read_text())
    return held


def word(image: bytes, at: int) -> int:
    return image[at] | (image[at + 1] << 8)


def constants(image: bytes, offsets: Mapping[str, str]) -> Constants:
    return Constants(
        word(image, int(offsets["ready"], 16)),
        word(image, int(offsets["destination"], 16)),
        image[int(offsets["start"], 16)],
        word(image, int(offsets["count"], 16)),
    )


def payload(count: int) -> bytes:
    return (LANDING + bytes(count))[:count]


def answered(unit: Any, port: int, value: int) -> bool:
    for _ in range(PATIENCE):
        if unit.read(port) == value:
            return True
        unit.run_for(SLICE)
    return False


def ready(unit: Any, wanted: int) -> bool:
    for _ in range(PATIENCE):
        if unit.read(0) | (unit.read(1) << 8) == wanted:
            return True
        unit.run_for(SLICE)
    return False


def begin(unit: Any, held: Constants) -> bool:
    if not ready(unit, held.ready):
        return False
    unit.write(1, held.ready & 0xFF)
    unit.write(2, held.ready >> 8)
    unit.write(2, held.destination & 0xFF)
    unit.write(3, held.destination >> 8)
    unit.write(0, held.start)
    return answered(unit, 0, held.start)


def send(unit: Any, data: bytes) -> int:
    echoed = 0
    for index, value in enumerate(data):
        unit.write(0, index & 0xFF)
        unit.write(1, value)
        if not answered(unit, 0, index & 0xFF):
            return echoed
        echoed += 1
    return echoed


def jump(unit: Any, held: Constants) -> bool:
    unit.write(1, 0x00)
    unit.write(2, held.destination & 0xFF)
    unit.write(3, held.destination >> 8)
    unit.write(0, (held.length - 1 + 2) & 0xFF)
    unit.run_for(SETTLE)
    return bool(unit.read(3) == MARKER)


def replay(unit: Any, held: Constants) -> dict[str, Any]:
    if not begin(unit, held):
        return {"echoes": 0, "of": held.length + 1, "landed": False}
    echoed = 1 + send(unit, payload(held.length))
    landed = echoed == held.length + 1 and jump(unit, held)
    return {"echoes": echoed, "of": held.length + 1, "landed": landed}


def problems(run: Mapping[str, Any]) -> list[str]:
    short = [] if run["echoes"] == run["of"] else [f"{run['echoes']} of {run['of']} bytes echoed"]
    return short + ([] if run["landed"] else ["the payload never ran at its destination"])


def one_image(
    entry: Mapping[str, Any], options: Mapping[str, Any]
) -> tuple[bool, bool, dict[str, Any]]:
    say, where = options["say"], located(entry["sha256"], options["folders"])
    if where is None:
        say(f"  {entry['id']}: not on this machine, so nothing was run")
        return False, False, dict(entry)
    run = replay(options["build"](), constants(where.read_bytes(), entry["offsets"]))
    found = problems(run) + ([] if run == entry["measured"] else ["differs from the recorded run"])
    said = "landed" if run["landed"] else "did not land"
    say(f"  {entry['id']}: {run['echoes']} of {run['of']} echoed, {said}")
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
    kept: tuple[Path, ...] = KEPT,
) -> int:
    stopped = why_not()
    if stopped is not None:
        say(f"nothing was run: {stopped}")
        return NOTHING_RAN
    record = declared() if held is None else held
    options = {"say": say, "build": build, "folders": directories(environment, kept)}
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
