"""What the doctor looks at, and what it says when something is not there."""

import sys
import unittest
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import doctor
from ssmp.errors import NoBootRom


class _Buildable:
    def reset(self) -> "_Buildable":
        return self


class _WillNotReset:
    def reset(self) -> NoReturn:
        raise NoBootRom("the unit would not restart")


class FindingTest(unittest.TestCase):
    def test_a_finding_that_passed_reads_as_passing(self) -> None:
        found = doctor.Finding("one", True, "fine")

        self.assertIn("ok", found.line)

    def test_one_that_did_not_is_marked(self) -> None:
        found = doctor.Finding("one", False, "not fine")

        self.assertIn("!", found.line)

    def test_a_failure_with_advice_prints_it(self) -> None:
        found = doctor.Finding("one", False, "not fine", "try this")

        self.assertIn("try this", found.report)

    def test_a_failure_with_none_prints_only_the_line(self) -> None:
        found = doctor.Finding("one", False, "not fine")

        self.assertEqual(found.report, found.line)

    def test_advice_on_something_that_passed_is_not_printed(self) -> None:
        found = doctor.Finding("one", True, "fine", "try this")

        self.assertEqual(found.report, found.line)

    def test_a_finding_prints_as_itself(self) -> None:
        self.assertIn("one", repr(doctor.Finding("one", True, "fine")))


class CheckTest(unittest.TestCase):
    def test_the_python_running_this_is_looked_at(self) -> None:
        self.assertTrue(doctor._python().ok)

    def test_the_package_names_its_own_version(self) -> None:
        from ssmp.version import VERSION

        self.assertIn(VERSION, doctor._package().detail)

    def test_a_unit_that_builds_and_resets_passes(self) -> None:
        found = doctor._unit("ssmp", lambda name: _Buildable())

        self.assertTrue(found.ok)

    def test_a_unit_that_builds_and_will_not_reset_does_not(self) -> None:
        found = doctor._unit("ssmp", lambda name: _WillNotReset())

        self.assertFalse(found.ok)

    def test_a_unit_that_will_not_build_says_why(self) -> None:
        def _refuse(name: str) -> object:
            raise NoBootRom("there is no boot program here")

        found = doctor._unit("ssmp", _refuse)

        self.assertIn("no boot program", found.detail)

    def test_and_advises_what_to_do_about_it(self) -> None:
        def _refuse(name: str) -> object:
            raise NoBootRom("there is no boot program here")

        found = doctor._unit("ssmp", _refuse)

        self.assertIsNotNone(found.advice)

    def test_the_boot_program_is_looked_for(self) -> None:
        found = doctor._boot(lambda: None)

        self.assertTrue(found.ok)

    def test_and_reported_when_it_is_not_there(self) -> None:
        found = doctor._boot(lambda: "no boot program was found")

        self.assertFalse(found.ok)

    def test_both_halves_are_looked_for(self) -> None:
        found = doctor._halves(lambda: (object(), object()))

        self.assertTrue(found.ok)

    def test_and_reported_when_they_are_not_checked_out(self) -> None:
        found = doctor._halves(lambda: None)

        self.assertFalse(found.ok)


class ExamineTest(unittest.TestCase):
    def test_it_looks_at_more_than_one_thing(self) -> None:
        found = doctor.examine(build=lambda name: object())

        self.assertGreater(len(found), 3)

    def test_every_finding_has_a_name(self) -> None:
        for one in doctor.examine(build=lambda name: object()):
            self.assertTrue(one.name)


class ReportTest(unittest.TestCase):
    def test_the_first_line_names_the_package_rather_than_a_part(self) -> None:
        lines = doctor.report([doctor.Finding("one", True, "fine")])

        self.assertIn("ssmp", lines[0])

    def test_a_clean_run_says_there_is_nothing_to_report(self) -> None:
        lines = doctor.report([doctor.Finding("one", True, "fine")])

        self.assertIn("nothing to report", lines[-1])

    def test_a_run_with_a_failure_counts_them(self) -> None:
        lines = doctor.report(
            [doctor.Finding("one", True, "fine"), doctor.Finding("two", False, "not")]
        )

        self.assertIn("1 of 2", lines[-1])


class MainTest(unittest.TestCase):
    def test_a_clean_run_reports_success(self) -> None:
        said: list[str] = []

        code = doctor.main(examine=lambda: [doctor.Finding("one", True, "fine")], say=said.append)

        self.assertEqual(code, 0)

    def test_a_run_with_a_failure_reports_it(self) -> None:
        said: list[str] = []

        code = doctor.main(examine=lambda: [doctor.Finding("one", False, "not")], say=said.append)

        self.assertEqual(code, 1)

    def test_it_prints_what_it_found(self) -> None:
        said: list[str] = []

        doctor.main(examine=lambda: [doctor.Finding("one", True, "fine")], say=said.append)

        self.assertTrue(any("one" in line for line in said))


if __name__ == "__main__":
    unittest.main()
