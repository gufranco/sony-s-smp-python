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
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def check_python() -> Finding:
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def check_package() -> Finding:
    return Finding("package", True, f"ssmp {VERSION}")


def check_halves(members: Callable[[], tuple[Any, Any] | None]) -> Finding:
    found = members()
    return Finding(
        "halves",
        found is not None,
        "the processor and the sound generator are both here"
        if found is not None
        else "one of them is missing",
        "run git submodule update --init --recursive",
    )


def check_boot(why_not: Callable[[], str | None]) -> Finding:
    said = why_not()
    return Finding(
        "boot program",
        said is None,
        "found" if said is None else said,
        f"put a copy you own in {firmware.DEFAULT_DIRECTORY.name}/ or name a directory"
        f" in {firmware.DIRECTORY_VARIABLE}",
    )


def _default_build(name: str) -> Any:  # pragma: no cover
    return board.Chip(name)


def check_unit(name: str, build: Callable[[str], Any]) -> Finding:
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
    found = [check_python(), check_package(), check_halves(members), check_boot(why_not)]
    found.extend(check_unit(name, build) for name in sorted(models.MODELS))
    return found


def report(found: list[Finding]) -> list[str]:
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
