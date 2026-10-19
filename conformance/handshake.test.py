import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import cartridges, console, handshake

OFFSETS = {"ready": "0x00001", "destination": "0x00004", "start": "0x00007", "count": "0x0000a"}


def an_image(count: int = 6) -> bytes:
    held = bytearray(16)
    held[1:3] = bytes((console.READY_LOW, console.READY_HIGH))
    held[4:6] = b"\x00\x04"
    held[7] = console.START
    held[10:12] = bytes((count & 0xFF, count >> 8))
    return bytes(held)


class Echoing:
    def __init__(self) -> None:
        self.held = {0: console.READY_LOW, 1: console.READY_HIGH, 2: 0x00, 3: 0x00}
        self.written: list[tuple[int, int]] = []

    def read(self, index: int) -> int:
        return self.held[index]

    def write(self, index: int, value: int) -> None:
        self.held[index] = value
        self.written = [*self.written, (index, value)]

    def run_for(self, cycles: int) -> int:
        return cycles


class Landing(Echoing):
    @override
    def run_for(self, cycles: int) -> int:
        self.held[3] = handshake.MARKER
        return cycles


class Stalling(Echoing):
    @override
    def write(self, index: int, value: int) -> None:
        super().write(index, 0xEE if (index, value) == (0, 3) else value)


class Deaf(Echoing):
    @override
    def read(self, index: int) -> int:
        return 0x00


def recorded(name: str) -> dict[str, Any]:
    held: list[dict[str, Any]] = handshake.declared()["images"]
    return next(one for one in held if one["id"] == name)


class TheRecordedHandshakesTest(unittest.TestCase):
    def test_the_ntsc_240p_suite_upload_is_echoed_byte_for_byte_and_runs(self) -> None:
        # Arrange
        entry = recorded("240p-test-suite-1-061-ntsc")

        # Act
        run = entry["measured"]

        # Assert
        self.assertEqual(run, {"echoes": 5562, "of": 5562, "landed": True})

    def test_the_pal_240p_suite_upload_is_echoed_byte_for_byte_and_runs(self) -> None:
        # Arrange
        entry = recorded("240p-test-suite-1-061-pal")

        # Act
        run = entry["measured"]

        # Assert
        self.assertEqual(run, {"echoes": 5562, "of": 5562, "landed": True})


class ConstantsTest(unittest.TestCase):
    def test_the_four_constants_are_read_where_the_record_says(self) -> None:
        # Arrange
        image = an_image()

        # Act
        held = handshake.constants(image, OFFSETS)

        # Assert
        self.assertEqual(held, handshake.Constants(0xBBAA, 0x0400, 0xCC, 6))

    def test_the_payload_marks_a_port_and_waits_at_the_destination(self) -> None:
        # Arrange
        count = 9

        # Act
        payload = handshake.payload(count)

        # Assert
        self.assertEqual(payload, bytes((0x8F, handshake.MARKER, 0xF7, 0x2F, 0xFE)) + bytes(4))


class ReplayTest(unittest.TestCase):
    def test_a_unit_that_echoes_and_runs_what_it_was_given_lands(self) -> None:
        # Arrange
        unit = Landing()

        # Act
        run = handshake.replay(unit, handshake.constants(an_image(), OFFSETS))

        # Assert
        self.assertEqual(run, {"echoes": 7, "of": 7, "landed": True})

    def test_the_writes_follow_the_programs_own_order(self) -> None:
        # Arrange
        unit = Landing()

        # Act
        handshake.replay(unit, handshake.constants(an_image(1), OFFSETS))

        # Assert
        self.assertEqual(
            unit.written,
            [
                *((1, 0xAA), (2, 0xBB), (2, 0x00), (3, 0x04), (0, 0xCC)),
                *((0, 0x00), (1, 0x8F)),
                *((1, 0x00), (2, 0x00), (3, 0x04), (0, 0x02)),
            ],
        )

    def test_a_unit_that_stops_echoing_partway_is_counted_to_where_it_stopped(self) -> None:
        # Arrange
        unit = Stalling()

        # Act
        run = handshake.replay(unit, handshake.constants(an_image(), OFFSETS))

        # Assert
        self.assertEqual(run, {"echoes": 4, "of": 7, "landed": False})

    def test_a_unit_that_never_answers_lands_nowhere(self) -> None:
        # Arrange
        unit = Deaf()

        # Act
        run = handshake.replay(unit, handshake.constants(an_image(), OFFSETS))

        # Assert
        self.assertEqual(run, {"echoes": 0, "of": 7, "landed": False})


class MainTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.said: list[str] = []
        self.folder = Path(tempfile.mkdtemp())
        self.image = an_image()

    def an_entry(self, measured: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "id": "tiny",
            "sha256": hashlib.sha256(self.image).hexdigest(),
            "offsets": OFFSETS,
            "measured": measured or {},
        }

    def run_main(self, held: dict[str, Any] | None, **options: Any) -> int:
        settings: dict[str, Any] = {
            "say": self.said.append,
            "build": Landing,
            "why_not": lambda: None,
            "environment": {cartridges.DIRECTORY_VARIABLE: str(self.folder)},
            "held": held,
        }
        return handshake.main((), **{**settings, **options})

    def test_nothing_runs_without_a_boot_program(self) -> None:
        # Arrange
        held = {"images": [self.an_entry()]}

        # Act
        status = self.run_main(held, why_not=lambda: "no boot program")

        # Assert
        self.assertEqual((status, self.said), (2, ["nothing was run: no boot program"]))

    def test_an_image_that_is_not_here_runs_nothing(self) -> None:
        # Arrange
        held = {"images": [self.an_entry()]}

        # Act
        status = self.run_main(held)

        # Assert
        self.assertEqual(status, 2)
        self.assertEqual(self.said[0], "  tiny: not on this machine, so nothing was run")

    def test_a_run_that_matches_the_record_passes(self) -> None:
        # Arrange
        (self.folder / "any name.sfc").write_bytes(self.image)
        held = {"images": [self.an_entry({"echoes": 7, "of": 7, "landed": True})]}

        # Act
        status = self.run_main(held)

        # Assert
        self.assertEqual(
            (status, self.said), (0, ["  tiny: 7 of 7 echoed, landed", "1 run, 0 wrong"])
        )

    def test_a_unit_that_does_not_land_is_wrong(self) -> None:
        # Arrange
        (self.folder / "any name.sfc").write_bytes(self.image)
        held = {"images": [self.an_entry({"echoes": 7, "of": 7, "landed": False})]}

        # Act
        status = self.run_main(held, build=Echoing)

        # Assert
        self.assertEqual(status, 1)
        self.assertIn("  tiny: the payload never ran at its destination", self.said)

    def test_a_short_echo_and_a_changed_run_are_both_wrong(self) -> None:
        # Arrange
        (self.folder / "any name.sfc").write_bytes(self.image)

        # Act
        status = self.run_main({"images": [self.an_entry()]}, build=Deaf)

        # Assert
        self.assertEqual(status, 1)
        self.assertEqual(
            self.said[1:3],
            ["  tiny: 0 of 7 bytes echoed", "  tiny: the payload never ran at its destination"],
        )

    def test_writing_keeps_what_the_run_measured(self) -> None:
        # Arrange
        (self.folder / "any name.sfc").write_bytes(self.image)
        target = self.folder / "record.json"

        # Act
        self.run_main({"images": [self.an_entry()]}, record_path=target)

        # Assert
        written = json.loads(target.read_text())["images"][0]["measured"]
        self.assertEqual(written, {"echoes": 7, "of": 7, "landed": True})

    def test_the_committed_record_is_read_when_none_is_given(self) -> None:
        # Arrange
        nowhere = {cartridges.DIRECTORY_VARIABLE: str(self.folder)}

        # Act
        status = self.run_main(None, environment=nowhere)

        # Assert
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
