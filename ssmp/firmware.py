"""The boot program its owner supplies, identified before it is run.

The unit is complete without it in every way except the one that matters: it
comes up reading the top of memory, and until something is there it has nothing
to run. Those sixty four bytes are Sony's, so they are never carried here and
never will be.

What is carried is the manifest: what the image is, how long it is, and the
digest that decides whether the copy on your disk is the one it claims to be. A
digest identifies a file and reconstructs nothing, which is the difference
between saying what something is and handing it over.

A file that does not match is diagnosed rather than merely refused. Being told
that a digest failed leaves you no wiser; being told the file is the right length
with different content, or twice the length because something concatenated it, or
a text listing of the bytes rather than the bytes, tells you what to do next.

That last one is worth naming because it is the common case. The program is
easier to find written out as hexadecimal in an article than as a file, and a
reader who saves the article has a file of the right content in the wrong form.
`repairs` says so and says what to do about it, rather than reporting a digest
nobody can act on.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import zlib
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

from ssmp.errors import Corrupt, Unrecognised, WrongShape

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Iterator, Mapping

ROOT = Path(__file__).resolve().parent.parent

MANIFEST = Path(__file__).resolve().parent / "artifacts.manifest.json"

DIRECTORY_VARIABLE = "SSMP_BOOT_DIR"

DIRECTORY_VARIABLES = (DIRECTORY_VARIABLE,)
"""Every variable naming a directory, most specific first.

One entry, because no other member reads a boot program for this unit. The
tuple exists anyway so the search order below is the same function here as in
the members that do share a name with a sibling.
"""

DEFAULT_DIRECTORY = ROOT / "boot"

ALONGSIDE = ROOT.parent / "boot"

BOOT_BYTES = 0x40

READABLE_SUFFIXES = (".bin", ".rom", ".ipl", ".txt", ".hex")

DIGESTS = ("crc32", "md5", "sha1", "sha256")

DECIDES = "sha256"

DIGEST_WIDTHS = {"crc32": 8, "md5": 32, "sha1": 40, "sha256": 64}

HEX_BYTE = re.compile(rb"(?:0x)?([0-9a-fA-F]{2})")


def digests_of(image: bytes) -> dict[str, str]:
    """Every value published for an image, not only the deciding one.

    Publishing a crc32 beside a sha256 and never looking at the crc32 is
    publishing decoration, so all four are computed and all four are confirmed.
    """
    return {
        "crc32": f"{zlib.crc32(image) & 0xFFFFFFFF:08x}",
        "md5": hashlib.md5(image, usedforsecurity=False).hexdigest(),
        "sha1": hashlib.sha1(image, usedforsecurity=False).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


class Identity:
    """What an image turned out to be."""

    __slots__ = ("bytes_long", "part", "processor", "revision")

    def __init__(self, part: str, processor: str, revision: str, bytes_long: int) -> None:
        self.part = part
        self.processor = processor
        self.revision = revision
        self.bytes_long = bytes_long

    @override
    def __repr__(self) -> str:
        return f"<Identity {self.part} {self.revision} for {self.processor}>"


def manifest(path: Path | str | None = None) -> dict[str, Any]:
    """What this package says the boot programs are."""
    held: dict[str, Any] = json.loads(Path(path or MANIFEST).read_text())
    return held


def directories(environment: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    """Every place an image is looked for, in the order they are looked at.

    Whatever was named comes first, then the project this package sits inside if
    it is a submodule of one, then this package itself. More than one can be
    named at once, separated the way the operating system separates a path.

    `DIRECTORY_VARIABLES` is read in order, so a member that shares a variable
    with a sibling reads its own name first and the shared one after it. A
    caller who has set only the shared name keeps working; a caller who sets
    both points the two members at different directories, which is the whole
    reason the member's own name exists.

    This function is one rule with a copy in every member that reads an image it
    does not carry, because no package is a dependency of all of them. The
    copies are byte-identical below the constants and are meant to stay that
    way, so a diff against a sibling is the check:

        cut='/^def directories/,/^    return tuple(seen)/p'
        diff <(sed -n "$cut" mine/firmware.py) <(sed -n "$cut" theirs/firmware.py)
    """
    held = environment if environment is not None else os.environ
    wanted = [
        Path(where)
        for variable in DIRECTORY_VARIABLES
        for where in held.get(variable, "").split(os.pathsep)
        if where
    ]
    wanted += [ALONGSIDE, DEFAULT_DIRECTORY]
    seen: list[Path] = []
    for where in wanted:
        if where not in seen:
            seen.append(where)
    return tuple(seen)


def check_shape(image: Iterable[int]) -> None:
    """Refuse an image that is not the length the unit reads.

    Before anything is loaded rather than at the first read, because a boot
    window filled from a short image would run and would run wrongly, and a
    program that runs wrongly is harder to diagnose than one that refuses.
    """
    held = bytes(image)
    if len(held) != BOOT_BYTES:
        raise WrongShape(
            f"a boot program is exactly {BOOT_BYTES} bytes and this one is {len(held)}"
        )


def as_bytes(held: bytes) -> bytes:
    """The image itself, whether it arrived as bytes or as text naming them.

    The program circulates more often as hexadecimal in an article than as a
    file, so a reader who saved the article has the right content in the wrong
    form. Reading it costs nothing and saves them a conversion they would
    otherwise have to work out.
    """
    if len(held) == BOOT_BYTES and not _looks_like_text(held):
        return held
    found = HEX_BYTE.findall(held)
    if len(found) == BOOT_BYTES:
        return bytes(int(one, 16) for one in found)
    return held


def _looks_like_text(held: bytes) -> bool:
    """Whether these bytes are more likely a listing than an image.

    A sixty four byte program and a sixty four character listing are the same
    length, so length cannot decide. What decides is that a listing is printable
    and a program is not: the real one carries bytes no text encoding produces.
    """
    return all(one in b"0123456789abcdefABCDEFx ,\n\r\t$" for one in held)


def identify(image: bytes, catalogue: dict[str, Any] | None = None) -> Identity:
    """What this image is, or a refusal that says what it is not.

    Every published digest is confirmed rather than only the deciding one,
    because a manifest whose other three values are never checked is a manifest
    with three unchecked claims in it.
    """
    held = catalogue if catalogue is not None else manifest()
    found = digests_of(image)
    for entry in held["artifacts"]:
        for accepted in entry["accepted"]:
            if accepted[DECIDES] != found[DECIDES]:
                continue
            _confirm(entry, accepted, found)
            return Identity(entry["part"], entry["processor"], accepted["revision"], entry["bytes"])
        for bad in entry.get("knownBad", []):
            if bad[DECIDES] == found[DECIDES]:
                raise Corrupt(
                    f"this is a copy of the {entry['part']} boot program the manifest"
                    f" records as a bad dump: {bad.get('why', 'no reason recorded')}"
                )
    raise Unrecognised(
        f"nothing in the manifest has sha256 {found['sha256']}."
        f" {_diagnosis(image, found[DECIDES], held['artifacts'])}"
    )


def _confirm(entry: dict[str, Any], accepted: dict[str, Any], found: dict[str, str]) -> None:
    """Every other value the manifest publishes, held to what was computed."""
    for name in DIGESTS:
        if name not in accepted:
            continue
        if accepted[name].lower() != found[name]:
            raise Corrupt(
                f"the {entry['part']} boot program matches on {DECIDES} and disagrees"
                f" on {name}: the manifest says {accepted[name]} and this file is"
                f" {found[name]}, so one of the two is wrong and neither can be trusted"
            )


def repairs(image: bytes, entries: Iterable[dict[str, Any]]) -> list[tuple[str, str]]:
    """What a reader could do to the file they have, and what it would give them.

    Only transformations of their own copy: strip a wrapper, read a listing as
    bytes, take the first sixty four. Never a download and never a patch that
    supplies content the file does not already hold.
    """
    found: list[tuple[str, str]] = []
    wanted = {one[DECIDES] for entry in entries for one in entry["accepted"]}
    read = as_bytes(image)
    if read is not image and digests_of(read)[DECIDES] in wanted:
        found.append(("read it as a hexadecimal listing", "the bytes it names are the program"))
    if len(image) > BOOT_BYTES:
        head = digests_of(image[:BOOT_BYTES])[DECIDES]
        if head in wanted:
            found.append(("take the first 64 bytes", "the program is at the front of this file"))
        tail = digests_of(image[-BOOT_BYTES:])[DECIDES]
        if tail in wanted:
            found.append(("take the last 64 bytes", "the program is at the end of this file"))
    return found


def _diagnosis(image: bytes, digest: str, entries: list[dict[str, Any]]) -> str:
    """The nearest miss, said in terms the reader can act on."""
    mending = repairs(image, entries)
    if mending:
        return " ".join(f"Try this: {how}, because {why}." for how, why in mending)
    if len(image) != BOOT_BYTES:
        return (
            f"It is {len(image)} bytes and a boot program is {BOOT_BYTES},"
            " so this is not one of them at all."
        )
    return (
        "It is the right length with different content, which is either a"
        " revision nobody has catalogued or a damaged copy."
    )


def load(space: Any, image: bytes) -> None:
    """Put the image where the unit reads its first instruction from."""
    check_shape(image)
    space.boot = bytes(image)


def found(where: Path, catalogue: dict[str, Any] | None = None) -> Iterator[tuple[Identity, Path]]:
    """Every file in that directory this package recognises.

    The catalogue is an argument so a test can hand over one it built, rather
    than needing a copy of a program nobody can be assumed to hold.
    """
    if not where.is_dir():
        return
    for one in sorted(where.iterdir()):
        if not one.is_file() or one.suffix.lower() not in READABLE_SUFFIXES:
            continue
        try:
            image = as_bytes(one.read_bytes())
            yield identify(image, catalogue), one
        except (Corrupt, Unrecognised, OSError):
            continue


def search(
    environment: Mapping[str, str] | None = None,
    catalogue: dict[str, Any] | None = None,
) -> Iterator[tuple[Identity, Path]]:
    """Every image this machine holds, wherever it was told to look.

    A part found in more than one of those directories is yielded once, from the
    first one that held it, so naming a directory puts it ahead of the rest
    rather than beside them.
    """
    seen: set[str] = set()
    for where in directories(environment):
        for identity, path in found(where, catalogue):
            if identity.part in seen:
                continue
            seen.add(identity.part)
            yield identity, path
