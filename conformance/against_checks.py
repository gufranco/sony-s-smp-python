"""Every one of blargg's checks, run against the model, including the slow one.

Kept out of the coverage step because the longest of them is twenty seconds of
the unit's own time, which is about ten seconds here and a great deal more under
a tracer. The two quick ones also run in `loader.test.py`; this is where the
whole set runs, and where the file digests are confirmed rather than assumed.

Exit two means nothing was checked, which is the honest answer on a machine that
holds neither the boot program nor the files. It is not the same as agreement and
the run page says so.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import loader
from ssmp import Chip, board, firmware

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

MANIFEST = Path(__file__).resolve().parent / "checks.manifest.json"

ROOM = 60_000_000

NOTHING_CHECKED = 2


def declared(path: Path | str | None = None) -> dict[str, Any]:
    """What this project says blargg's checks are."""
    held: dict[str, Any] = json.loads(Path(path or MANIFEST).read_text())
    return held


def confirm(raw: bytes, expected: dict[str, str]) -> list[str]:
    """Every published digest that the file on disk does not match.

    All four are confirmed rather than only the deciding one, because publishing
    a value nothing ever looks at is publishing decoration.
    """
    found = firmware.digests_of(raw)
    return [name for name, value in expected.items() if found.get(name) != value]


def main(
    say: Callable[[str], None] = print,
    build: Callable[[], Any] = lambda: Chip("ssmp"),
    why_not: Callable[[], str | None] = board.why_not,
    find: Callable[[str], Path | None] = loader.find,
    held: dict[str, Any] | None = None,
) -> int:
    stopped = why_not()
    if stopped is not None:
        say(f"nothing was checked: {stopped}")
        return NOTHING_CHECKED

    record = declared() if held is None else held
    ran, wrong = 0, []
    for one in record["checks"]:
        where = find(one["name"])
        if where is None:
            say(f"  {one['name']}: not on this machine, so nothing was run against it")
            continue
        raw = Path(where).read_bytes()
        mismatched = confirm(raw, one["digests"])
        if mismatched:
            say(f"  {one['name']}: does not match its published {', '.join(mismatched)}")
            wrong.append(one["name"])
            continue
        said = loader.play(build(), loader.Dump(raw), ROOM)
        ran += 1
        if said.agreed:
            say(f"  {one['name']}: agreed, {said.agreements} sub-checks, {said.cycles} cycles")
        else:
            say(f"  {one['name']}: disagreed on sub-check {said.disagreed_at}")
            wrong.append(one["name"])

    if not ran and not wrong:
        say(
            "nothing was checked: none of blargg's files is on this machine. They are"
            f" his and are not carried here; name a directory in {loader.DIRECTORY_VARIABLE}"
        )
        return NOTHING_CHECKED
    say(f"{ran} of {len(record['checks'])} run, {len(wrong)} disagreed")
    return 1 if wrong else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
