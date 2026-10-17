import sys
import unittest
from pathlib import Path
from typing import NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from ssmp import doctor


class _Buildable:
    def reset(self) -> "_Buildable":
        return self


class _WillNotReset:
    def reset(self) -> NoReturn:
        raise ssmp.NoBootRom("the unit would not restart")


def _refuse(name: str) -> object:
    raise ssmp.NoBootRom("there is no boot program here")


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
        # Arrange
        running = sys.version_info[:2] >= (3, 12)

        # Act
        found = doctor.check_python()

        # Assert
        self.assertIs(found.ok, running)

    def test_the_package_names_its_own_version(self) -> None:
        # Arrange
        version = ssmp.VERSION

        # Act
        found = doctor.check_package()

        # Assert
        self.assertEqual(found.detail, f"ssmp {version}")

    def test_a_unit_that_builds_and_resets_passes(self) -> None:
        # Arrange
        build = lambda name: _Buildable()  # noqa: E731

        # Act
        found = doctor.check_unit("ssmp", build)

        # Assert
        self.assertEqual((found.ok, found.detail), (True, "builds, starts and resets"))

    def test_a_unit_that_builds_and_will_not_reset_does_not(self) -> None:
        # Arrange
        build = lambda name: _WillNotReset()  # noqa: E731

        # Act
        found = doctor.check_unit("ssmp", build)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "the unit would not restart"))

    def test_a_unit_that_will_not_build_says_why_and_what_to_do(self) -> None:
        # Arrange
        build = _refuse

        # Act
        found = doctor.check_unit("ssmp", build)

        # Assert
        self.assertEqual(
            (found.detail, found.advice),
            (
                "there is no boot program here",
                "the two lines above say which of the three pieces is missing",
            ),
        )

    def test_a_real_unit_built_from_a_supplied_program_passes(self) -> None:
        # Arrange
        build = lambda name: ssmp.Chip(name, boot=bytes(64))  # noqa: E731

        # Act
        found = doctor.check_unit("ssmp", build)

        # Assert
        self.assertIs(found.ok, True)

    def test_the_boot_program_is_looked_for(self) -> None:
        # Arrange
        why_not = lambda: None  # noqa: E731

        # Act
        found = doctor.check_boot(why_not)

        # Assert
        self.assertEqual((found.ok, found.detail), (True, "found"))

    def test_and_reported_when_it_is_not_there(self) -> None:
        # Arrange
        why_not = lambda: "no boot program was found"  # noqa: E731

        # Act
        found = doctor.check_boot(why_not)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "no boot program was found"))

    def test_and_the_advice_names_the_variable_to_set(self) -> None:
        # Arrange
        why_not = lambda: "no boot program was found"  # noqa: E731

        # Act
        found = doctor.check_boot(why_not)

        # Assert
        self.assertIn("SSMP_BOOT_DIR", str(found.advice))

    def test_both_halves_are_looked_for(self) -> None:
        # Arrange
        members = lambda: (object(), object())  # noqa: E731

        # Act
        found = doctor.check_halves(members)

        # Assert
        self.assertIs(found.ok, True)

    def test_and_reported_when_they_are_not_checked_out(self) -> None:
        # Arrange
        members = lambda: None  # noqa: E731

        # Act
        found = doctor.check_halves(members)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "one of them is missing"))


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
