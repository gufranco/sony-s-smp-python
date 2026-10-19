import hashlib
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import cartridges
from conformance.host import Host
from ssmp import Chip

CODE = bytes.fromhex("9c15219c16219c1721") + b"".join(
    bytes((0xA9, letter, 0x8D, 0x18, 0x21)) for letter in b"PASSED"
)

SPIN = bytes.fromhex("80fe")


def a_rom(code: bytes = CODE + SPIN) -> bytes:
    body = bytearray(0x8000)
    body[: len(code)] = code
    body[0x7FFC:0x7FFE] = bytes((0x00, 0x80))
    return bytes(body)


def a_unit() -> Any:
    return Chip("ssmp", boot=bytes(64), seed=3, fill=0).reset()


def a_compare_at(unit: Any, at: int, expected: bytes, held: bytes) -> None:
    memory = unit.space.memory
    for index, (want, place) in enumerate(zip(expected, cartridges.CHECKSUM, strict=True)):
        block = bytes((cartridges.COMPARE, want, place, cartridges.BRANCH, 0x10))
        for offset, value in enumerate(block):
            memory.write8(at + index * cartridges.STRIDE + offset, value)
    for place, value in zip(cartridges.CHECKSUM, held, strict=True):
        memory.write8(place, value)


def an_entry(raw: bytes, checks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": "tiny",
        "name": "tiny.sfc",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "screen": "PASSED",
        "verdicts": 0,
        "agreed": 0,
        "disagreed": 0,
        "checks": [] if checks is None else checks,
    }


class WatchTest(unittest.TestCase):
    def test_a_comparison_that_agrees_is_recorded_and_its_branches_emptied(self) -> None:
        # Arrange
        unit = a_unit()
        a_compare_at(unit, 0x0400, b"\x8f\x77\x58\x15", b"\x8f\x77\x58\x15")
        watch = cartridges.Watch(unit.space, Host(a_rom(), unit))

        # Act
        watch.read8(0x0400)

        # Assert
        self.assertEqual(
            watch.verdicts,
            [{"check": "", "agreed": True, "console": "8f 77 58 15", "thisModel": "8f 77 58 15"}],
        )
        self.assertEqual(unit.space.memory.read8(0x0403), 0)

    def test_a_comparison_that_disagrees_is_named_from_the_unit_memory(self) -> None:
        # Arrange
        unit = a_unit()
        a_compare_at(unit, 0x0600, b"\x01\x02\x03\x04", b"\x01\x02\x03\x05")
        for offset, letter in enumerate(b"Test 3, CPU/tset tclr\x00"):
            unit.space.memory.write8(0x0320 + offset, letter)
        watch = cartridges.Watch(unit.space, Host(a_rom(), unit))

        # Act
        watch.read8(0x0600)

        # Assert
        self.assertEqual(
            watch.verdicts[0],
            {
                "check": "CPU/tset tclr",
                "agreed": False,
                "console": "01 02 03 04",
                "thisModel": "01 02 03 05",
            },
        )

    def test_any_other_read_passes_through_and_records_nothing(self) -> None:
        # Arrange
        unit = a_unit()
        unit.space.memory.write8(0x0500, cartridges.COMPARE)
        watch = cartridges.Watch(unit.space, Host(a_rom(), unit))

        # Act
        read = watch.read8(0x0500)

        # Assert
        self.assertEqual((read, watch.verdicts), (cartridges.COMPARE, []))

    def test_a_write_lands_in_the_unit(self) -> None:
        # Arrange
        unit = a_unit()
        watch = cartridges.Watch(unit.space, Host(a_rom(), unit))

        # Act
        watch.write8(0x0234, 0x99)

        # Assert
        self.assertEqual(unit.space.memory.read8(0x0234), 0x99)


def a_status_check_at(unit: Any, wanted: int, held: int) -> Any:
    for offset, value in enumerate((cartridges.COMPARE_X, wanted, cartridges.BRANCH, 0x05)):
        unit.space.memory.write8(0x0400 + offset, value)
    unit.processor.pc, unit.processor.x = 0x0400, held
    return cartridges.Watch(unit.space, Host(a_rom(), unit), unit.processor, 0x04)


class StatusWordTest(unittest.TestCase):
    def test_a_status_word_apart_only_in_the_excused_flag_is_let_through(self) -> None:
        # Arrange
        unit = a_unit()
        watch = a_status_check_at(unit, 0x0B, 0x0F)

        # Act
        watch.read8(0x0400)

        # Assert
        self.assertEqual(
            (watch.excused, unit.space.memory.read8(0x0401)),
            ([{"at": "0400", "expected": "0b", "thisModel": "0f", "excused": True}], 0x0F),
        )

    def test_one_apart_in_any_other_flag_is_left_to_fail(self) -> None:
        # Arrange
        unit = a_unit()
        watch = a_status_check_at(unit, 0x0B, 0x8F)

        # Act
        watch.read8(0x0400)

        # Assert
        self.assertEqual(
            (watch.excused[0]["excused"], unit.space.memory.read8(0x0401)), (False, 0x0B)
        )

    def test_a_status_word_held_in_y_is_weighed_the_same_way(self) -> None:
        # Arrange
        unit = a_unit()
        watch = a_status_check_at(unit, 0x80, 0x00)
        unit.space.memory.write8(0x0400, cartridges.COMPARE_Y)
        unit.processor.y = 0x84

        # Act
        watch.read8(0x0400)

        # Assert
        self.assertEqual(
            watch.excused[0], {"at": "0400", "expected": "80", "thisModel": "84", "excused": True}
        )

    def test_a_matching_word_or_a_read_that_is_not_the_fetch_is_left_alone(self) -> None:
        # Arrange
        matching = a_status_check_at(a_unit(), 0x0B, 0x0B)
        other = a_unit()
        elsewhere = a_status_check_at(other, 0x0B, 0x0F)
        other.processor.pc = 0x0300

        # Act
        matching.read8(0x0400)
        elsewhere.read8(0x0400)

        # Assert
        self.assertEqual((matching.excused, elsewhere.excused), ([], []))

    def test_a_status_word_that_fails_is_named(self) -> None:
        # Arrange
        failing = {"at": "0400", "expected": "0b", "thisModel": "8f", "excused": False}
        played = cartridges.Played([], "", 0, [failing])

        # Act
        problems = cartridges.judged(an_entry(b"") | {"excused": [failing], "screen": ""}, played)

        # Assert
        self.assertEqual(problems, ["the status word at 0400 is 8f, not 0b"])


if __name__ == "__main__":
    unittest.main()
