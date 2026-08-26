"""The run that reports what it could not check, checked itself.

Every decision it makes is taken as an argument, so a machine that holds all of
blargg's files and a machine that holds none of them both exercise every path.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import against_checks, loader
from ssmp import firmware


def _smallest() -> bytes:
    """The least that still reads as one of these, so no real file is needed."""
    header = bytearray(loader.HEADER_BYTES)
    header[: len(loader.SIGNATURE)] = loader.SIGNATURE
    return bytes(header) + bytes(loader.RAM_BYTES) + bytes(loader.GENERATOR_BYTES)


RAW = _smallest()


def _entry(name: str = "a.spc", raw: bytes = RAW) -> dict[str, Any]:
    return {
        "name": name,
        "covers": "something",
        "bytes": len(raw),
        "digests": firmware.digests_of(raw),
    }


def _record(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"what": "", "why": "", "author": "", "decides": "sha256", "checks": list(entries)}


class Agreed:
    agreed, agreements, cycles, disagreed_at = True, 3, 100, None


class Disagreed:
    agreed, agreements, cycles, disagreed_at = False, 1, 100, 2


class DeclaredTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = against_checks.declared()

    def test_the_record_names_every_check_this_project_knows(self) -> None:
        self.assertEqual(
            sorted(one["name"] for one in self.held["checks"]),
            ["full_ram.spc", "initial_in_ports.spc", "initial_regs.spc"],
        )

    def test_each_one_says_what_it_covers(self) -> None:
        self.assertEqual([one for one in self.held["checks"] if not one["covers"]], [])

    def test_each_one_carries_all_four_digests(self) -> None:
        self.assertEqual(
            [
                one["name"]
                for one in self.held["checks"]
                if set(one["digests"]) != set(firmware.DIGESTS)
            ],
            [],
        )

    def test_the_deciding_digest_is_the_one_the_family_decides_on(self) -> None:
        self.assertEqual(self.held["decides"], firmware.DECIDES)

    def test_it_says_the_files_are_not_carried_here(self) -> None:
        self.assertIn("is carried here", self.held["why"])

    def test_it_credits_whoever_wrote_them(self) -> None:
        self.assertTrue(self.held["author"])

    def test_a_record_can_be_read_from_somewhere_else(self) -> None:
        where = Path(self.enterContext(tempfile.TemporaryDirectory())) / "r.json"
        where.write_text(json.dumps(_record()))

        self.assertEqual(against_checks.declared(where)["checks"], [])


class ConfirmTest(unittest.TestCase):
    def test_a_file_matching_every_published_value_reports_nothing(self) -> None:
        held = against_checks.confirm(RAW, firmware.digests_of(RAW))

        self.assertEqual(held, [])

    def test_a_file_matching_none_of_them_reports_all_four(self) -> None:
        held = against_checks.confirm(b"different", firmware.digests_of(RAW))

        self.assertEqual(sorted(held), sorted(firmware.DIGESTS))

    def test_a_value_published_for_a_digest_nobody_computed_is_reported(self) -> None:
        held = against_checks.confirm(RAW, {"whirlpool": "00"})

        self.assertEqual(held, ["whirlpool"])


class RunTest(unittest.TestCase):
    def _where(self, raw: bytes = RAW) -> Path:
        where = Path(self.enterContext(tempfile.TemporaryDirectory())) / "a.spc"
        where.write_bytes(raw)
        return where

    def test_a_machine_that_cannot_build_a_unit_checks_nothing(self) -> None:
        said: list[str] = []

        code = against_checks.main(say=said.append, why_not=lambda: "no boot program")

        self.assertEqual(code, against_checks.NOTHING_CHECKED)

    def test_and_says_why_rather_than_reporting_agreement(self) -> None:
        said: list[str] = []

        against_checks.main(say=said.append, why_not=lambda: "no boot program")

        self.assertIn("no boot program", said[0])

    def test_a_machine_holding_none_of_the_files_checks_nothing(self) -> None:
        said: list[str] = []

        code = against_checks.main(
            say=said.append, why_not=lambda: None, find=lambda _: None, held=_record(_entry())
        )

        self.assertEqual(code, against_checks.NOTHING_CHECKED)

    def test_and_names_the_variable_that_would_point_at_them(self) -> None:
        said: list[str] = []

        against_checks.main(
            say=said.append, why_not=lambda: None, find=lambda _: None, held=_record(_entry())
        )

        self.assertIn(loader.DIRECTORY_VARIABLE, said[-1])

    def test_a_file_that_is_not_the_one_it_claims_to_be_is_refused(self) -> None:
        where = self._where(b"something else entirely")
        said: list[str] = []

        code = against_checks.main(
            say=said.append, why_not=lambda: None, find=lambda _: where, held=_record(_entry())
        )

        self.assertEqual(code, 1)

    def test_and_the_check_is_never_run_against_it(self) -> None:
        where = self._where(b"something else entirely")
        said: list[str] = []

        against_checks.main(
            say=said.append,
            why_not=lambda: None,
            find=lambda _: where,
            build=lambda: self.fail("a file that failed its digest was run anyway"),
            held=_record(_entry()),
        )

        self.assertIn("does not match its published", said[0])

    def test_a_check_that_agrees_reports_agreement(self) -> None:
        where = self._where()
        said: list[str] = []
        self.enterContext(StandingIn(Agreed()))

        code = against_checks.main(
            say=said.append,
            why_not=lambda: None,
            find=lambda _: where,
            build=lambda: None,
            held=_record(_entry()),
        )

        self.assertEqual((code, "agreed" in said[0]), (0, True))

    def test_a_check_that_disagrees_fails_the_run(self) -> None:
        where = self._where()
        said: list[str] = []
        self.enterContext(StandingIn(Disagreed()))

        code = against_checks.main(
            say=said.append,
            why_not=lambda: None,
            find=lambda _: where,
            build=lambda: None,
            held=_record(_entry()),
        )

        self.assertEqual((code, "disagreed on sub-check 2" in said[0]), (1, True))

    def test_a_file_that_is_absent_is_reported_and_the_rest_still_run(self) -> None:
        where = self._where()
        said: list[str] = []
        self.enterContext(StandingIn(Agreed()))

        code = against_checks.main(
            say=said.append,
            why_not=lambda: None,
            find=lambda name: None if name == "a.spc" else where,
            build=lambda: None,
            held=_record(_entry(), _entry("b.spc")),
        )

        self.assertEqual((code, "1 of 2 run" in said[-1]), (0, True))


class StandingIn:
    """Stand in for the run itself, so the reporting is checked without a unit."""

    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.before = loader.play

    def __enter__(self) -> None:
        loader.play = lambda *_args, **_kwargs: self.outcome

    def __exit__(self, *_: object) -> None:
        loader.play = self.before


if __name__ == "__main__":
    unittest.main()
