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

DEFAULT_DIRECTORY = ROOT / "external" / "boot"

ALONGSIDE = ROOT.parent / "external" / "boot"

BOOT_BYTES = 0x40

READABLE_SUFFIXES = (".bin", ".rom", ".ipl", ".txt", ".hex")

DIGESTS = ("crc32", "md5", "sha1", "sha256")

DECIDES = "sha256"

HEX_BYTE = re.compile(rb"(?:0x)?([0-9a-fA-F]{2})")


def digests_of(image: bytes) -> dict[str, str]:
    return {
        "crc32": f"{zlib.crc32(image) & 0xFFFFFFFF:08x}",
        "md5": hashlib.md5(image, usedforsecurity=False).hexdigest(),
        "sha1": hashlib.sha1(image, usedforsecurity=False).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


class Identity:
    __slots__ = ("bytes_long", "part", "processor", "revision")

    def __init__(self, part: str, processor: str, revision: str, bytes_long: int) -> None:
        self.part = part
        self.processor = processor
        self.revision = revision
        self.bytes_long = bytes_long

    @override
    def __repr__(self) -> str:
        return f"<Identity {self.part} {self.revision} for {self.processor}>"


def manifest() -> dict[str, Any]:
    held: dict[str, Any] = json.loads(MANIFEST.read_text())
    return held


def directories(environment: Mapping[str, str] | None = None) -> tuple[Path, ...]:
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
    held = bytes(image)
    if len(held) != BOOT_BYTES:
        raise WrongShape(
            f"a boot program is exactly {BOOT_BYTES} bytes and this one is {len(held)}"
        )


def as_bytes(held: bytes) -> bytes:
    if len(held) == BOOT_BYTES and not _looks_like_text(held):
        return held
    found = HEX_BYTE.findall(held)
    if len(found) == BOOT_BYTES:
        return bytes(int(one, 16) for one in found)
    return held


def _looks_like_text(held: bytes) -> bool:
    return all(one in b"0123456789abcdefABCDEFx ,\n\r\t$" for one in held)


def identify(image: bytes, catalogue: dict[str, Any] | None = None) -> Identity:
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


def found(where: Path, catalogue: dict[str, Any] | None = None) -> Iterator[tuple[Identity, Path]]:
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
    seen: set[str] = set()
    for where in directories(environment):
        for identity, path in found(where, catalogue):
            if identity.part in seen:
                continue
            seen.add(identity.part)
            yield identity, path
