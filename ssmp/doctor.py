"""What is here, what is not, and what to do about it.

Run this before opening an issue and paste what it prints. It is deliberately
readable by somebody who has never seen this package: every line says what was
looked at, what was there, and what to do when there is something to do.

The interesting case for this member is a machine that has almost everything.
The unit is built out of two other repositories and sixty four bytes nobody may
distribute, so there are three separate ways to be nearly ready, and telling them
apart is most of what this file is for.

    python3 -m ssmp.doctor
"""

from __future__ import annotations

import platform
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, override

if str(Path(__file__).resolve().parent.parent) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import board, firmware, models
from ssmp.version import VERSION

ROOT = Path(__file__).resolve().parent.parent

from ssmp import environment  # noqa: E402

OLDEST_PYTHON = (3, 12)


class Finding:
    """One thing that was looked at, and what was there."""

    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> Finding:
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> Finding:
    """The distribution, named for itself rather than for the unit it models.

    They share the letters, which is why this says version and not much else: a
    line reading `ssmp: ssmp` would tell a reader nothing.
    """
    return Finding("package", True, f"ssmp {VERSION}")


def _halves(members: Callable[[], tuple[Any, Any] | None]) -> Finding:
    """Whether the two repositories this unit is assembled from are checked out."""
    found = members()
    return Finding(
        "halves",
        found is not None,
        "the processor and the sound generator are both here"
        if found is not None
        else "one of them is missing",
        "run git submodule update --init --recursive",
    )


def _boot(why_not: Callable[[], str | None]) -> Finding:
    """Whether a boot program is on this machine, and what to do if not."""
    said = why_not()
    return Finding(
        "boot program",
        said is None,
        "found" if said is None else said,
        f"put a copy you own in {firmware.DEFAULT_DIRECTORY.name}/ or name a directory"
        f" in {firmware.DIRECTORY_VARIABLE}",
    )


def _default_build(name: str) -> Any:  # pragma: no cover
    """How the unit is built when nobody says otherwise.

    Not measured, because every caller of it takes the builder as an argument so
    that the decision behind it can be exercised on a machine holding no boot
    program. This line is the one that needs one.
    """
    return board.Chip(name)


def _unit(name: str, build: Callable[[str], Any]) -> Finding:
    """Whether the unit builds and resets, saying what stopped it if not.

    The reset is driven rather than described. It rebuilds both halves on one
    store, masks the boot program back in at the top page and takes the sound
    generator to the state that writes no echo, so it is the path a console puts
    the unit through and the one a report should have exercised.
    """
    try:
        unit = build(name)
        unit.reset()
    except Exception as reason:
        return Finding(
            name,
            False,
            str(reason),
            "the two lines above say which of the three pieces is missing",
        )
    return Finding(name, True, "builds, starts and resets")


def examine(
    build: Callable[[str], Any] = _default_build,
    members: Callable[[], tuple[Any, Any] | None] = board._members,
    why_not: Callable[[], str | None] = board.why_not,
) -> list[Finding]:
    """Everything worth looking at, in the order a reader wants it.

    The order is the order a reader can act in: the language, then the package,
    then the two halves, then the program, then the unit itself. Anything that
    fails makes everything after it fail too, so the first failure is the one to
    read.
    """
    found = [_python(), _package(), _halves(members), _boot(why_not)]
    found.extend(_unit(name, build) for name in sorted(models.MODELS))
    return found


def report(found: list[Finding]) -> list[str]:
    """The lines a person pastes into an issue."""
    unwell = [one for one in found if not one.ok]
    lines = [f"ssmp {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
