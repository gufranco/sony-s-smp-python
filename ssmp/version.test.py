import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp


class VersionTest(unittest.TestCase):
    def test_the_version_is_three_numbers(self) -> None:
        # Arrange
        version = ssmp.VERSION

        # Act
        parts = version.split(".")

        # Assert
        self.assertEqual([part.isdigit() for part in parts], [True, True, True])

    def test_the_dunder_name_carries_the_same_version(self) -> None:
        # Arrange
        version = ssmp.VERSION

        # Act
        dunder = ssmp.__version__

        # Assert
        self.assertEqual(dunder, version)


if __name__ == "__main__":
    unittest.main()
