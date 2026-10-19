import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import cartridges
from conformance.host import Host
from ssmp import Chip, why_not

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


def recorded(name: str) -> dict[str, Any]:
    held: list[dict[str, Any]] = cartridges.declared()["cartridges"]
    return next(one for one in held if one["id"] == name)


def agreed_throughout(entry: dict[str, Any]) -> tuple[int, int, list[str]]:
    astray = [one["check"] for one in entry["checks"] if one["console"] != one["thisModel"]]
    return entry["agreed"], len(entry["checks"]), astray


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


class TheRecordedVerdictsTest(unittest.TestCase):
    def test_every_check_spc_smp_reaches_agrees_with_a_console(self) -> None:
        # Arrange
        entry = recorded("blargg-spc-smp")

        # Act
        held = agreed_throughout(entry)

        # Assert
        self.assertEqual(held, (18, 18, []))

    def test_every_check_spc_dsp6_reaches_agrees_with_a_console(self) -> None:
        # Arrange
        entry = recorded("blargg-spc-dsp6")

        # Act
        held = agreed_throughout(entry)

        # Assert
        self.assertEqual(held, (104, 104, []))

    def test_every_check_spc_mem_access_times_reaches_agrees_with_a_console(self) -> None:
        # Arrange
        entry = recorded("blargg-spc-mem-access-times")

        # Act
        held = agreed_throughout(entry)

        # Assert
        self.assertEqual(held, (2, 2, []))

    def test_every_check_spc_timer_reaches_agrees_with_a_console(self) -> None:
        # Arrange
        entry = recorded("blargg-spc-timer")

        # Act
        held = agreed_throughout(entry)

        # Assert
        self.assertEqual(held, (1, 1, []))

    def test_three_of_his_cartridges_say_they_passed_on_their_own_screen(self) -> None:
        # Arrange
        names = ("blargg-spc-smp", "blargg-spc-mem-access-times", "blargg-spc-timer")

        # Act
        passed = ["PASSED TESTS" in recorded(name)["screen"] for name in names]

        # Assert
        self.assertEqual(passed, [True, True, True])

    def test_gilyon_spctest_reports_success_on_its_own_screen(self) -> None:
        # Arrange
        entry = recorded("gilyon-spctest")

        # Act
        screen = entry["screen"]

        # Assert
        self.assertEqual(screen, " Running tests... Success\n Test number: 0527")

    def test_peter_lemons_cartridges_stop_at_their_first_check(self) -> None:
        # Arrange
        names = [
            "peterlemon-spc700-adc",
            "peterlemon-spc700-and",
            "peterlemon-spc700-dec",
            "peterlemon-spc700-eor",
            "peterlemon-spc700-inc",
            "peterlemon-spc700-ora",
            "peterlemon-spc700-sbc",
        ]

        # Act
        endings = [recorded(name)["screen"].split()[-1] for name in names]
        passes = [recorded(name)["screen"].count("PASS") for name in names]

        # Assert
        self.assertEqual(endings, ["FAIL"] * 7)
        self.assertEqual(passes, [0] * 7)


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


class PlayTest(unittest.TestCase):
    def test_a_program_that_prints_passed_ends_the_run(self) -> None:
        # Arrange
        raw = a_rom()

        # Act
        played = cartridges.play(raw, a_unit(), limit=40_000, chunk=1_000)

        # Assert
        self.assertEqual((played.screen, played.verdicts), ("PASSED", []))
        self.assertLess(played.cycles, 2_000)

    def test_a_copier_header_is_stepped_over(self) -> None:
        # Arrange
        raw = bytes(cartridges.COPIER_HEADER) + a_rom()

        # Act
        played = cartridges.play(raw, a_unit(), limit=4_000, chunk=1_000)

        # Assert
        self.assertEqual(played.screen, "PASSED")

    def test_a_program_that_never_finishes_stops_at_the_limit(self) -> None:
        # Arrange
        raw = a_rom(SPIN)

        # Act
        played = cartridges.play(raw, a_unit(), limit=3_000, chunk=1_000)

        # Assert
        self.assertEqual(played.screen, "")
        self.assertGreaterEqual(played.cycles, 3_000)


class MainTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.said: list[str] = []
        self.folder = Path(tempfile.mkdtemp())

    def run_main(self, held: dict[str, Any] | None, **options: Any) -> int:
        settings: dict[str, Any] = {
            "say": self.said.append,
            "build": a_unit,
            "why_not": lambda: None,
            "find": lambda name: next(iter(self.folder.glob(name)), None),
            "held": held,
            "limit": 4_000,
            "chunk": 1_000,
        }
        return cartridges.main((), **{**settings, **options})

    def test_nothing_runs_without_a_boot_program_or_a_processor(self) -> None:
        # Arrange
        held = {"cartridges": [an_entry(a_rom())]}

        # Act
        status = self.run_main(held, why_not=lambda: "no boot program")

        # Assert
        self.assertEqual(status, cartridges.NOTHING_RAN)
        self.assertEqual(self.said, ["nothing was run: no boot program"])

    def test_a_cartridge_that_is_not_here_is_counted_as_not_run(self) -> None:
        # Arrange
        held = {"cartridges": [an_entry(a_rom())]}

        # Act
        status = self.run_main(held)

        # Assert
        self.assertEqual(status, cartridges.NOTHING_RAN)
        self.assertEqual(self.said[0], "  tiny.sfc: not on this machine, so nothing was run")

    def test_a_cartridge_with_another_digest_is_refused(self) -> None:
        # Arrange
        (self.folder / "tiny.sfc").write_bytes(a_rom())

        # Act
        status = self.run_main({"cartridges": [an_entry(b"other")]})

        # Assert
        self.assertEqual(status, 1)
        self.assertEqual(self.said[0], "  tiny.sfc: does not match its published sha256")

    def test_a_run_that_matches_the_record_exits_zero(self) -> None:
        # Arrange
        (self.folder / "tiny.sfc").write_bytes(a_rom())

        # Act
        status = self.run_main({"cartridges": [an_entry(a_rom())]})

        # Assert
        self.assertEqual(status, 0)
        self.assertEqual(self.said, ["  tiny.sfc: 0 verdicts, 0 disagree", "1 run, 0 wrong"])

    def test_a_run_that_differs_from_the_record_exits_one(self) -> None:
        # Arrange
        (self.folder / "tiny.sfc").write_bytes(a_rom())
        check = {"check": "x", "agreed": True, "console": "00", "thisModel": "00"}

        # Act
        status = self.run_main({"cartridges": [an_entry(a_rom(), [check])]})

        # Assert
        self.assertEqual(status, 1)
        self.assertIn("  tiny.sfc: differs from the recorded run", self.said)

    def test_a_disagreeing_check_is_named(self) -> None:
        # Arrange
        played = cartridges.Played(
            [{"check": "x", "agreed": False, "console": "01", "thisModel": "02"}], "", 0
        )

        # Act
        problems = cartridges.judged(an_entry(b""), played)

        # Assert
        self.assertEqual(
            problems, ["x: a console gave 01, this model 02", "differs from the recorded run"]
        )

    def test_a_failure_on_the_screen_is_a_problem_even_when_recorded(self) -> None:
        # Arrange
        entry = {**an_entry(b""), "screen": "ADC #const FAIL"}

        # Act
        problems = cartridges.judged(entry, cartridges.Played([], "ADC #const FAIL", 0))

        # Assert
        self.assertEqual(problems, ["the cartridge reports a failure on its own screen"])

    def test_writing_keeps_what_the_run_measured(self) -> None:
        # Arrange
        (self.folder / "tiny.sfc").write_bytes(a_rom())
        check = {"check": "x", "agreed": True, "console": "00", "thisModel": "00"}
        target = self.folder / "record.json"

        # Act
        self.run_main({"cartridges": [an_entry(a_rom(), [check])]}, record_path=target)

        # Assert
        written = json.loads(target.read_text())["cartridges"][0]
        self.assertEqual((written["checks"], written["screen"]), ([], "PASSED"))

    def test_the_committed_record_is_read_when_none_is_given(self) -> None:
        # Arrange
        nowhere = {"find": lambda name: None, "record_path": None}

        # Act
        status = self.run_main(None, **nowhere)

        # Assert
        self.assertEqual(status, cartridges.NOTHING_RAN)
        self.assertEqual(len(self.said), len(cartridges.declared()["cartridges"]) + 1)


class FindTest(unittest.TestCase):
    def test_a_named_directory_is_searched_first(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        (folder / "spc_smp.sfc").write_bytes(b"x")

        # Act
        found = cartridges.find("spc_smp.sfc", {cartridges.DIRECTORY_VARIABLE: str(folder)})

        # Assert
        self.assertEqual(found, folder / "spc_smp.sfc")

    def test_nothing_anywhere_is_none(self) -> None:
        # Arrange
        environment = {cartridges.DIRECTORY_VARIABLE: "/nowhere/at/all"}

        # Act
        found = cartridges.find("no-such-cartridge.sfc", environment)

        # Assert
        self.assertIsNone(found)

    def test_the_process_environment_is_read_when_none_is_given(self) -> None:
        # Arrange
        name = "no-such-cartridge.sfc"

        # Act
        found = cartridges.find(name)

        # Assert
        self.assertIsNone(found)


class ProcessorTest(unittest.TestCase):
    def test_the_processor_submodule_is_here(self) -> None:
        # Arrange
        where = cartridges.PROCESSOR

        # Act
        reason = cartridges.processor_absent(where)

        # Assert
        self.assertIsNone(reason)

    def test_a_missing_one_is_named_with_the_command_that_fetches_it(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())

        # Act
        reason = cartridges.processor_absent(where)

        # Assert
        self.assertIn("git submodule update --init", reason or "")

    def test_the_default_check_asks_both(self) -> None:
        # Arrange
        expected = why_not() or cartridges.processor_absent()

        # Act
        reason = cartridges.ready()

        # Assert
        self.assertEqual(reason, expected)


if __name__ == "__main__":
    unittest.main()
