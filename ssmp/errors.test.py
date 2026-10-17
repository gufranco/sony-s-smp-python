import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp

REFUSALS = (
    ssmp.UnknownModelError,
    ssmp.NoBootRom,
    ssmp.Unrecognised,
    ssmp.Corrupt,
    ssmp.WrongShape,
)


class CatalogueTest(unittest.TestCase):
    def test_every_refusal_this_package_makes_is_its_own(self) -> None:
        # Arrange
        named = REFUSALS

        # Act
        distinct = {one.__name__ for one in named}

        # Assert
        self.assertEqual(len(distinct), 5)

    def test_each_of_them_is_an_exception(self) -> None:
        # Arrange
        named = REFUSALS

        # Act
        found = [issubclass(one, Exception) for one in named]

        # Assert
        self.assertEqual(found, [True] * 5)

    def test_a_wrong_file_and_a_broken_one_are_told_apart(self) -> None:
        # Arrange
        wrong = ssmp.Unrecognised

        # Act
        same = issubclass(wrong, ssmp.Corrupt) or issubclass(ssmp.Corrupt, wrong)

        # Assert
        self.assertIs(same, False)

    def test_a_wrong_model_is_refused_with_a_sentence_saying_what_there_is(self) -> None:
        # Arrange
        name = "s-cpu"

        # Act
        with self.assertRaises(ssmp.UnknownModelError) as caught:
            ssmp.Chip(name)

        # Assert
        self.assertEqual(
            str(caught.exception), "s-cpu is not a unit this package covers; there is ssmp"
        )


if __name__ == "__main__":
    unittest.main()
