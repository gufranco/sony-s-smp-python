"""What the package says its version is."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import version


class VersionTest(unittest.TestCase):
    def test_the_version_is_three_numbers(self) -> None:
        self.assertEqual(len(version.VERSION.split(".")), 3)

    def test_every_one_of_them_is_a_number(self) -> None:
        for part in version.VERSION.split("."):
            self.assertTrue(part.isdigit(), part)


if __name__ == "__main__":
    unittest.main()
