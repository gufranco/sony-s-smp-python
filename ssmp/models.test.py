"""Which units this package covers, and how a name resolves to one."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp
from ssmp import models
from ssmp.errors import UnknownModelError


class CatalogueTest(unittest.TestCase):
    def test_the_package_covers_the_one_unit_sony_shipped(self) -> None:
        self.assertEqual(sorted(models.MODELS), ["ssmp"])

    def test_the_default_is_that_unit(self) -> None:
        self.assertIn(models.DEFAULT_MODEL, models.MODELS)

    def test_every_entry_says_what_it_is(self) -> None:
        for name, model in models.MODELS.items():
            self.assertTrue(model.summary, name)

    def test_every_entry_names_its_processor(self) -> None:
        for name, model in models.MODELS.items():
            self.assertEqual(model.processor, "spc700", name)

    def test_every_entry_carries_the_memory_the_unit_has(self) -> None:
        for name, model in models.MODELS.items():
            self.assertEqual(model.memory, 0x10000, name)

    def test_every_entry_carries_the_boot_program_length(self) -> None:
        for name, model in models.MODELS.items():
            self.assertEqual(model.boot, 0x40, name)


class DescribeTest(unittest.TestCase):
    def test_a_name_resolves_to_its_model(self) -> None:
        self.assertEqual(models.lookup("ssmp").name, "ssmp")

    def test_a_name_resolves_whatever_its_case(self) -> None:
        self.assertEqual(models.lookup("SSMP").name, "ssmp")

    def test_a_name_resolves_through_the_separators_people_write(self) -> None:
        for written in ("s-smp", "s_smp", "S-SMP"):
            self.assertEqual(models.lookup(written).name, "ssmp", written)

    def test_a_name_nothing_goes_by_is_refused(self) -> None:
        with self.assertRaises(UnknownModelError):
            models.lookup("s-cpu")

    def test_the_refusal_names_what_would_have_worked(self) -> None:
        with self.assertRaises(UnknownModelError) as caught:
            models.lookup("s-cpu")

        self.assertIn("ssmp", str(caught.exception))


class ChipTest(unittest.TestCase):
    """The wrapper every member of the family carries, checked without a program."""

    def test_a_unit_is_built_through_the_name_the_caller_gave(self) -> None:
        import ssmp
        from ssmp import firmware

        made_up = bytes(range(0x40))
        identity = firmware.Identity("ssmp", "spc700", "made up", 0x40)

        unit = ssmp.Chip("s-smp", boot=made_up, identity=identity)

        self.assertEqual(unit.part, "ssmp")

    def test_a_name_nothing_goes_by_is_refused_before_anything_is_built(self) -> None:
        import ssmp

        with self.assertRaises(UnknownModelError):
            ssmp.Chip("s-cpu")


class PrintingTest(unittest.TestCase):
    def test_a_model_prints_as_the_unit_it_is(self) -> None:
        self.assertIn("ssmp", repr(models.lookup("ssmp")))


class NamingNoneTest(unittest.TestCase):
    """That leaving the model out is refused, and refused usefully.

    One unit is the tempting place to allow a default and the worst one: the
    habit learned here is the habit carried to a member covering sixteen parts.
    """

    def test_building_without_naming_a_model_is_refused(self) -> None:
        with self.assertRaises(UnknownModelError):
            ssmp.Chip()

    def test_and_the_refusal_names_every_model_there_is(self) -> None:
        with self.assertRaises(UnknownModelError) as caught:
            ssmp.Chip()

        missing = [name for name in ssmp.MODELS if name not in str(caught.exception)]

        self.assertEqual(missing, [])

    def test_nothing_named_describe_is_published(self) -> None:
        self.assertFalse(hasattr(ssmp, "describe"))

    def test_and_no_default_model_is_published_either(self) -> None:
        self.assertFalse(hasattr(ssmp, "DEFAULT_MODEL"))


if __name__ == "__main__":
    unittest.main()
