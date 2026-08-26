"""Everything this package raises, and what tells the refusals apart."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import errors


class CatalogueTest(unittest.TestCase):
    def test_every_refusal_this_package_makes_is_its_own(self) -> None:
        named = [
            errors.UnknownModelError,
            errors.NoBootRom,
            errors.Unrecognised,
            errors.Corrupt,
            errors.WrongShape,
        ]

        self.assertEqual(len({one.__name__ for one in named}), len(named))

    def test_each_of_them_is_an_exception(self) -> None:
        for one in (
            errors.UnknownModelError,
            errors.NoBootRom,
            errors.Unrecognised,
            errors.Corrupt,
            errors.WrongShape,
        ):
            self.assertTrue(issubclass(one, Exception), one.__name__)

    def test_each_of_them_says_what_it_is_for(self) -> None:
        for one in (
            errors.UnknownModelError,
            errors.NoBootRom,
            errors.Unrecognised,
            errors.Corrupt,
            errors.WrongShape,
        ):
            self.assertTrue(one.__doc__, one.__name__)

    def test_a_wrong_file_and_a_broken_one_are_told_apart(self) -> None:
        self.assertNotEqual(errors.Unrecognised, errors.Corrupt)

    def test_a_refusal_carries_the_message_it_was_given(self) -> None:
        self.assertIn("why", str(errors.NoBootRom("why not")))


if __name__ == "__main__":
    unittest.main()
