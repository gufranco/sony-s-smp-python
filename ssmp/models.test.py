import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from conformance import monitor


def built(name: str) -> str:
    unit = ssmp.Chip(name, boot=monitor.MONITOR)
    model: str = unit.model
    return model


class CatalogueTest(unittest.TestCase):
    def test_the_package_covers_the_one_unit_sony_shipped(self) -> None:
        # Arrange
        catalogue = ssmp.MODELS

        # Act
        names = sorted(catalogue)

        # Assert
        self.assertEqual(names, ["ssmp"])

    def test_every_entry_says_what_it_is(self) -> None:
        # Arrange
        catalogue = ssmp.MODELS

        # Act
        empty = [name for name, model in catalogue.items() if not model.summary]

        # Assert
        self.assertEqual(empty, [])

    def test_the_entry_names_its_processor_memory_and_boot_program_length(self) -> None:
        # Arrange
        model = ssmp.MODELS["ssmp"]

        # Act
        found = (model.name, model.processor, model.memory, model.boot)

        # Assert
        self.assertEqual(found, ("ssmp", "spc700", 0x10000, 0x40))

    def test_a_model_prints_as_the_unit_it_is(self) -> None:
        # Arrange
        model = ssmp.MODELS["ssmp"]

        # Act
        printed = repr(model)

        # Assert
        self.assertEqual(printed, "<Model ssmp, spc700 and 64K>")


class NamingTest(unittest.TestCase):
    def test_a_name_builds_its_model(self) -> None:
        # Arrange
        name = "ssmp"

        # Act
        model = built(name)

        # Assert
        self.assertEqual(model, "ssmp")

    def test_a_name_builds_whatever_its_case(self) -> None:
        # Arrange
        name = "SSMP"

        # Act
        model = built(name)

        # Assert
        self.assertEqual(model, "ssmp")

    def test_a_name_builds_through_the_separators_people_write(self) -> None:
        # Arrange
        names = ("s-smp", "s_smp", "S-SMP", "s.smp", "s smp", " ssmp ")

        # Act
        models = [built(name) for name in names]

        # Assert
        self.assertEqual(models, ["ssmp"] * 6)

    def test_the_unit_is_keyed_by_the_same_name(self) -> None:
        # Arrange
        name = "S-SMP"

        # Act
        unit = ssmp.Chip(name, boot=monitor.MONITOR)

        # Assert
        self.assertEqual(unit.part, "ssmp")

    def test_a_name_nothing_goes_by_is_refused_and_told_what_would_have_worked(self) -> None:
        # Arrange
        name = "s-cpu"

        # Act
        with self.assertRaises(ssmp.UnknownModelError) as caught:
            ssmp.Chip(name, boot=monitor.MONITOR)

        # Assert
        self.assertIn("there is ssmp", str(caught.exception))


class NamingNoneTest(unittest.TestCase):
    def test_building_without_naming_a_model_is_refused(self) -> None:
        # Arrange
        program = monitor.MONITOR

        # Act
        with self.assertRaises(ssmp.UnknownModelError) as caught:
            ssmp.Chip(boot=program)

        # Assert
        self.assertIn("no model was named", str(caught.exception))

    def test_and_the_refusal_names_every_model_there_is(self) -> None:
        # Arrange
        named = list(ssmp.MODELS)

        # Act
        with self.assertRaises(ssmp.UnknownModelError) as caught:
            ssmp.Chip()

        # Assert
        self.assertEqual([name for name in named if name not in str(caught.exception)], [])

    def test_nothing_named_describe_is_published(self) -> None:
        # Arrange
        published = set(ssmp.__all__)

        # Act
        found = "describe" in published or hasattr(ssmp, "describe")

        # Assert
        self.assertIs(found, False)

    def test_and_no_default_model_is_published_either(self) -> None:
        # Arrange
        published = set(ssmp.__all__)

        # Act
        found = "DEFAULT_MODEL" in published or hasattr(ssmp, "DEFAULT_MODEL")

        # Assert
        self.assertIs(found, False)


if __name__ == "__main__":
    unittest.main()
