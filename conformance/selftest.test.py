import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import cartridges, console, selftest

SUB_TESTS = ["aram", "echoRegion", "envelope", "echoTiming", "timer1", "timer2"]


def recorded(name: str) -> dict[str, Any]:
    held: list[dict[str, Any]] = selftest.declared()["images"]
    return next(one for one in held if one["id"] == name)


def passed_apart_from_the_envelope(name: str) -> tuple[bool, int, str, list[str]]:
    run = recorded(name)["measured"]
    failing = [one for one in SUB_TESTS if not run["subTests"][one]]
    return run["handshake"], run["result"] & ~selftest.ENVELOPE, run["ports"], failing


def a_block_list(blocks: list[tuple[int, bytes]], entry: int, at: int = 4) -> bytes:
    body = b"".join(
        bytes((len(data) & 0xFF, len(data) >> 8, where & 0xFF, where >> 8)) + data
        for where, data in blocks
    )
    return bytes(at) + body + bytes((0, 0, entry & 0xFF, entry >> 8))


class Echoing:
    def __init__(self) -> None:
        self.held = {0: console.READY_LOW, 1: console.READY_HIGH, 2: 0x00, 3: 0x00}

    def read(self, index: int) -> int:
        return self.held[index]

    def write(self, index: int, value: int) -> None:
        self.held[index] = value

    def run_for(self, cycles: int) -> int:
        return cycles


class SelfTesting(Echoing):
    def __init__(self, result: int, late: int = 0, ports: tuple[int, int] = (0, 0)) -> None:
        super().__init__()
        self.result, self.late, self.ports = result, late, ports
        self.after_command: int | None = None

    @override
    def write(self, index: int, value: int) -> None:
        super().write(index, value)
        if index == 0 and value == selftest.SELF_TEST:
            self.after_command = 0

    @override
    def run_for(self, cycles: int) -> int:
        if self.after_command is None:
            return super().run_for(cycles)
        self.after_command += cycles
        self.held[1] = selftest.HANDSHAKE if self.after_command <= self.late else self.result
        self.held[2], self.held[3] = self.ports if self.after_command > self.late else (0, 0)
        return super().run_for(cycles)


class TheRecordedSelfTestsTest(unittest.TestCase):
    def test_the_burn_in_self_test_passes_every_sub_test_but_the_envelope(self) -> None:
        # Arrange
        name = "burn-in-rev-d-apu"

        # Act
        held = passed_apart_from_the_envelope(name)

        # Assert
        self.assertEqual(held, (True, 0, "00 00", []))

    def test_the_snsp_aging_self_test_passes_every_sub_test(self) -> None:
        # Arrange
        name = "snsp-aging-1-02-apu"

        # Act
        held = passed_apart_from_the_envelope(name)

        # Assert
        self.assertEqual(held, (True, 0, "00 00", []))

    def test_the_control_deck_tester_self_test_passes_every_sub_test(self) -> None:
        # Arrange
        name = "control-deck-tester-rev-1-apu"

        # Act
        held = passed_apart_from_the_envelope(name)

        # Assert
        self.assertEqual(held, (True, 0, "00 00", []))

    def test_the_aging_1_00_self_test_passes_all_six_of_its_sub_tests(self) -> None:
        # Arrange
        name = "aging-1-00-apu"

        # Act
        held = passed_apart_from_the_envelope(name)

        # Assert
        self.assertEqual(held, (True, 0, "00 00", []))

    def test_this_model_clears_the_envelope_bit_the_programs_mask(self) -> None:
        # Arrange
        names = [
            "burn-in-rev-d-apu",
            "snsp-aging-1-02-apu",
            "control-deck-tester-rev-1-apu",
            "aging-1-00-apu",
        ]

        # Act
        bits = [recorded(name)["measured"]["result"] & selftest.ENVELOPE for name in names]

        # Assert
        self.assertEqual(bits, [0, 0, 0, 0])


class BlocksTest(unittest.TestCase):
    def test_the_list_is_read_up_to_its_terminator_and_entry(self) -> None:
        # Arrange
        image = a_block_list([(0x0800, b"\x01\x02"), (0x3C00, b"\x03")], 0x0800)

        # Act
        found = selftest.blocks(image, 4)

        # Assert
        self.assertEqual(found, ([(0x0800, b"\x01\x02"), (0x3C00, b"\x03")], 0x0800))

    def test_a_list_that_never_ends_is_refused(self) -> None:
        # Arrange
        image = b"\x01\x00\x00\x08\xff" * 80

        # Act
        attempt = lambda: selftest.blocks(image, 0)  # noqa: E731

        # Assert
        self.assertRaises(selftest.NotABlockList, attempt)


class Unacknowledged(Echoing):
    @override
    def write(self, index: int, value: int) -> None:
        super().write(index, 0x00 if (index, value) == (0, 0x02) else value)


class UploadTest(unittest.TestCase):
    def test_a_jump_nobody_acknowledges_is_reported(self) -> None:
        # Arrange
        unit = Unacknowledged()

        # Act
        attempt = lambda: selftest.upload_all(unit, [(0x0800, b"\x2f")], 0x0800)  # noqa: E731

        # Assert
        self.assertRaisesRegex(console.NeverAnswered, "never acknowledged", attempt)


class ExchangeTest(unittest.TestCase):
    def test_a_unit_that_answers_and_then_reports_is_measured(self) -> None:
        # Arrange
        unit = SelfTesting(0x04, late=60_000)

        # Act
        run = selftest.exchange(unit, [0x00, 0xFF, 0xFF, 0xFF], slice_=20_000, limit=200_000)

        # Assert
        self.assertEqual(
            (run.handshake, run.handshake_after, run.result_after, run.ports),
            (True, 20_000, 80_000, (0x04, 0, 0)),
        )

    def test_a_unit_that_never_answers_is_measured_as_such(self) -> None:
        # Arrange
        unit = Echoing()

        # Act
        run = selftest.exchange(unit, [], slice_=20_000, limit=100_000)

        # Assert
        self.assertEqual((run.handshake, run.result_after), (False, None))

    def test_a_unit_still_answering_at_the_limit_has_no_result(self) -> None:
        # Arrange
        unit = SelfTesting(0x00, late=10_000_000)

        # Act
        run = selftest.exchange(unit, [], slice_=20_000, limit=100_000)

        # Assert
        self.assertEqual((run.handshake, run.result_after), (True, None))


class MeasuredTest(unittest.TestCase):
    def test_each_bit_of_the_result_is_one_sub_test(self) -> None:
        # Arrange
        run = selftest.Exchange(True, 100, 200, (0x24, 0x00, 0x03))

        # Act
        measured = selftest.measured(run)

        # Assert
        self.assertEqual(
            measured["subTests"],
            {
                "aram": True,
                "echoRegion": True,
                "envelope": False,
                "echoTiming": True,
                "timer1": False,
                "timer2": True,
            },
        )
        self.assertEqual((measured["result"], measured["ports"]), (0x24, "00 03"))

    def test_a_pass_needs_the_handshake_a_clear_result_and_quiet_ports(self) -> None:
        # Arrange
        good = selftest.measured(selftest.Exchange(True, 1, 2, (0x04, 0, 0)))
        bad = selftest.measured(selftest.Exchange(False, None, None, (0x01, 0, 7)))

        # Act
        problems = (selftest.problems(good), selftest.problems(bad))

        # Assert
        self.assertEqual(
            problems,
            (
                [],
                [
                    "never answered $55 on port 1",
                    "never reported a result",
                    "result $01 fails a sub-test the program enforces",
                    "ports 2 and 3 read 00 07, not 00 00",
                ],
            ),
        )


class MainTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.said: list[str] = []
        self.folder = Path(tempfile.mkdtemp())
        self.image = a_block_list([(0x0800, b"\x2f\xfe")], 0x0800, at=8)

    def an_entry(self, **fields: Any) -> dict[str, Any]:
        return {
            "id": "tiny",
            "sha256": hashlib.sha256(self.image).hexdigest(),
            "blockList": "0x00008",
            "before": [],
            "measured": {},
            **fields,
        }

    def run_main(self, held: dict[str, Any] | None, **options: Any) -> int:
        settings: dict[str, Any] = {
            "say": self.said.append,
            "build": lambda: SelfTesting(0x00, late=20_000),
            "why_not": lambda: None,
            "environment": {cartridges.DIRECTORY_VARIABLE: str(self.folder)},
            "held": held,
            "slice_": 20_000,
            "limit": 200_000,
        }
        return selftest.main((), **{**settings, **options})

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

    def test_files_that_are_not_the_image_are_passed_over(self) -> None:
        # Arrange
        (self.folder / "notes.txt").write_bytes(self.image)
        (self.folder / "another.sfc").write_bytes(b"another")

        # Act
        found = selftest.located(hashlib.sha256(self.image).hexdigest(), [self.folder])

        # Assert
        self.assertIsNone(found)

    def test_an_image_held_under_any_name_is_found_by_its_digest(self) -> None:
        # Arrange
        (self.folder / "whatever it is called.sfc").write_bytes(self.image)
        measured = selftest.measured(selftest.Exchange(True, 20_000, 40_000, (0, 0, 0)))

        # Act
        status = self.run_main({"images": [self.an_entry(measured=measured)]})

        # Assert
        self.assertEqual(status, 0)
        self.assertEqual(self.said, ["  tiny: result $00, ports 00 00", "1 run, 0 wrong"])

    def test_a_run_that_differs_from_the_record_is_wrong(self) -> None:
        # Arrange
        (self.folder / "tiny.sfc").write_bytes(self.image)

        # Act
        status = self.run_main({"images": [self.an_entry()]})

        # Assert
        self.assertEqual(status, 1)
        self.assertIn("  tiny: differs from the recorded run", self.said)

    def test_a_failing_self_test_is_wrong(self) -> None:
        # Arrange
        (self.folder / "tiny.sfc").write_bytes(self.image)

        # Act
        status = self.run_main(
            {"images": [self.an_entry()]}, build=lambda: SelfTesting(0x01, late=20_000)
        )

        # Assert
        self.assertEqual(status, 1)
        self.assertIn("  tiny: result $01 fails a sub-test the program enforces", self.said)

    def test_writing_keeps_what_the_run_measured(self) -> None:
        # Arrange
        (self.folder / "tiny.sfc").write_bytes(self.image)
        target = self.folder / "record.json"

        # Act
        self.run_main({"images": [self.an_entry()]}, record_path=target)

        # Assert
        written = json.loads(target.read_text())["images"][0]["measured"]
        self.assertEqual((written["result"], written["handshake"]), (0, True))

    def test_the_committed_record_is_read_when_none_is_given(self) -> None:
        # Arrange
        nowhere = {cartridges.DIRECTORY_VARIABLE: str(self.folder)}

        # Act
        status = self.run_main(None, environment=nowhere)

        # Assert
        self.assertEqual(status, 2)

    def test_the_process_environment_is_read_when_none_is_given(self) -> None:
        # Arrange
        folder = selftest.directories(None)

        # Act
        found = selftest.located("0" * 64, folder)

        # Assert
        self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
