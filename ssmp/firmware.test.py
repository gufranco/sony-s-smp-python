"""Recognising a boot program, refusing the wrong one, and saying why.

Every case here builds its own bytes, so the file runs on a machine holding no
boot program at all. What needs the real one is `conformance/boot.test.py`.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ssmp import firmware
from ssmp.errors import Corrupt, Unrecognised, WrongShape

A_PROGRAM = bytes(range(firmware.BOOT_BYTES))

ANOTHER = bytes(range(1, firmware.BOOT_BYTES + 1))


def _artifacts(image: bytes = A_PROGRAM, bad: bytes | None = None) -> list[dict[str, Any]]:
    """The entries alone, for the helpers that take them rather than a manifest."""
    found = _a_manifest(image, bad)["artifacts"]
    assert isinstance(found, list)
    return found


def _a_manifest(image: bytes = A_PROGRAM, bad: bytes | None = None) -> dict[str, Any]:
    entry: dict[str, object] = {
        "part": "ssmp",
        "processor": "spc700",
        "name": "a boot program",
        "bytes": firmware.BOOT_BYTES,
        "accepted": [{"revision": "one", **firmware.digests_of(image)}],
    }
    if bad is not None:
        entry["knownBad"] = [{"why": "half of it is zeroes", **firmware.digests_of(bad)}]
    return {"artifacts": [entry]}


class DigestTest(unittest.TestCase):
    def test_an_image_is_measured_four_ways(self) -> None:
        self.assertEqual(sorted(firmware.digests_of(A_PROGRAM)), sorted(firmware.DIGESTS))

    def test_the_one_that_decides_is_the_strongest(self) -> None:
        self.assertEqual(firmware.DECIDES, "sha256")

    def test_two_images_differing_by_one_byte_measure_differently(self) -> None:
        self.assertNotEqual(firmware.digests_of(A_PROGRAM), firmware.digests_of(ANOTHER))

    def test_every_digest_is_as_wide_as_it_should_be(self) -> None:
        found = firmware.digests_of(A_PROGRAM)

        for name, width in firmware.DIGEST_WIDTHS.items():
            self.assertEqual(len(found[name]), width, name)


class ShapeTest(unittest.TestCase):
    def test_an_image_of_the_right_length_passes(self) -> None:
        firmware.check_shape(A_PROGRAM)

        self.assertEqual(len(A_PROGRAM), firmware.BOOT_BYTES)

    def test_a_short_one_is_refused(self) -> None:
        with self.assertRaises(WrongShape):
            firmware.check_shape(A_PROGRAM[:-1])

    def test_a_long_one_is_refused_too(self) -> None:
        with self.assertRaises(WrongShape):
            firmware.check_shape(A_PROGRAM + b"\x00")

    def test_the_refusal_says_how_long_the_file_actually_is(self) -> None:
        with self.assertRaises(WrongShape) as caught:
            firmware.check_shape(b"\x00" * 10)

        self.assertIn("10", str(caught.exception))


class ListingTest(unittest.TestCase):
    def test_an_image_is_taken_as_it_is(self) -> None:
        self.assertEqual(firmware.as_bytes(A_PROGRAM), A_PROGRAM)

    def test_a_hexadecimal_listing_is_read_as_the_bytes_it_names(self) -> None:
        listing = " ".join(f"{one:02x}" for one in A_PROGRAM).encode()

        self.assertEqual(firmware.as_bytes(listing), A_PROGRAM)

    def test_a_listing_written_with_a_prefix_is_read_too(self) -> None:
        listing = ", ".join(f"0x{one:02x}" for one in A_PROGRAM).encode()

        self.assertEqual(firmware.as_bytes(listing), A_PROGRAM)

    def test_something_that_is_neither_comes_back_unchanged(self) -> None:
        held = b"nothing like a boot program at all"

        self.assertEqual(firmware.as_bytes(held), held)

    def test_a_listing_naming_the_wrong_number_of_bytes_is_left_alone(self) -> None:
        listing = b"aa bb cc"

        self.assertEqual(firmware.as_bytes(listing), listing)


class IdentifyTest(unittest.TestCase):
    def test_a_known_image_is_named(self) -> None:
        found = firmware.identify(A_PROGRAM, _a_manifest())

        self.assertEqual((found.part, found.processor), ("ssmp", "spc700"))

    def test_it_carries_the_revision_the_manifest_gave_it(self) -> None:
        found = firmware.identify(A_PROGRAM, _a_manifest())

        self.assertEqual(found.revision, "one")

    def test_an_unknown_image_is_refused(self) -> None:
        with self.assertRaises(Unrecognised):
            firmware.identify(ANOTHER, _a_manifest())

    def test_the_refusal_prints_the_digest_that_was_computed(self) -> None:
        with self.assertRaises(Unrecognised) as caught:
            firmware.identify(ANOTHER, _a_manifest())

        self.assertIn(firmware.digests_of(ANOTHER)["sha256"], str(caught.exception))

    def test_a_dump_the_manifest_records_as_bad_is_told_apart(self) -> None:
        with self.assertRaises(Corrupt):
            firmware.identify(ANOTHER, _a_manifest(bad=ANOTHER))

    def test_the_corrupt_refusal_says_what_is_wrong_with_it(self) -> None:
        with self.assertRaises(Corrupt) as caught:
            firmware.identify(ANOTHER, _a_manifest(bad=ANOTHER))

        self.assertIn("zeroes", str(caught.exception))


class DiagnosisTest(unittest.TestCase):
    def test_a_file_of_the_wrong_length_is_told_so(self) -> None:
        with self.assertRaises(Unrecognised) as caught:
            firmware.identify(b"\x00" * 100, _a_manifest())

        self.assertIn("100 bytes", str(caught.exception))

    def test_a_file_of_the_right_length_is_told_it_is_content(self) -> None:
        with self.assertRaises(Unrecognised) as caught:
            firmware.identify(ANOTHER, _a_manifest())

        self.assertIn("right length", str(caught.exception))

    def test_a_program_at_the_front_of_a_longer_file_is_offered_as_a_repair(self) -> None:
        found = firmware.repairs(A_PROGRAM + b"\xff" * 32, _artifacts())

        self.assertIn("take the first 64 bytes", [how for how, _why in found])

    def test_a_program_at_the_end_of_one_is_offered_too(self) -> None:
        found = firmware.repairs(b"\xff" * 32 + A_PROGRAM, _artifacts())

        self.assertIn("take the last 64 bytes", [how for how, _why in found])

    def test_a_listing_is_offered_as_a_repair(self) -> None:
        listing = " ".join(f"{one:02x}" for one in A_PROGRAM).encode()

        found = firmware.repairs(listing, _artifacts())

        self.assertIn("read it as a hexadecimal listing", [how for how, _why in found])

    def test_a_file_nothing_can_be_done_with_is_offered_nothing(self) -> None:
        found = firmware.repairs(b"\x11" * 200, _artifacts())

        self.assertEqual(found, [])


class ManifestTest(unittest.TestCase):
    def test_the_manifest_this_package_carries_reads(self) -> None:
        self.assertIn("artifacts", firmware.manifest())

    def test_it_names_the_unit_and_its_processor(self) -> None:
        entry = firmware.manifest()["artifacts"][0]

        self.assertEqual((entry["part"], entry["processor"]), ("ssmp", "spc700"))

    def test_every_accepted_image_carries_all_four_digests(self) -> None:
        for entry in firmware.manifest()["artifacts"]:
            for accepted in entry["accepted"]:
                for name in firmware.DIGESTS:
                    self.assertIn(name, accepted)

    def test_it_says_where_its_digests_came_from(self) -> None:
        entry = firmware.manifest()["artifacts"][0]

        self.assertIn("provenance", entry)

    def test_a_manifest_elsewhere_is_read_from_there(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "one.json"
            path.write_text(json.dumps(_a_manifest()))

            self.assertEqual(firmware.manifest(path)["artifacts"][0]["part"], "ssmp")


class DirectoryTest(unittest.TestCase):
    def test_the_project_and_the_one_it_sits_inside_are_both_looked_at(self) -> None:
        self.assertIn(firmware.DEFAULT_DIRECTORY, firmware.directories({}))

    def test_a_named_directory_is_looked_at_first(self) -> None:
        found = firmware.directories({firmware.DIRECTORY_VARIABLE: "/somewhere"})

        self.assertEqual(found[0], Path("/somewhere"))

    def test_more_than_one_can_be_named_at_once(self) -> None:
        import os

        named = os.pathsep.join(("/one", "/two"))

        found = firmware.directories({firmware.DIRECTORY_VARIABLE: named})

        self.assertEqual(found[:2], (Path("/one"), Path("/two")))

    def test_the_same_directory_named_twice_is_looked_at_once(self) -> None:
        import os

        named = os.pathsep.join(("/one", "/one"))

        found = firmware.directories({firmware.DIRECTORY_VARIABLE: named})

        self.assertEqual(len([one for one in found if one == Path("/one")]), 1)

    def test_the_only_variable_this_member_reads_is_its_own(self) -> None:
        self.assertEqual(firmware.DIRECTORY_VARIABLES, (firmware.DIRECTORY_VARIABLE,))

    def test_a_variable_this_member_does_not_read_names_nothing(self) -> None:
        found = firmware.directories({"UPD7725_FIRMWARE_DIR": "/x"})

        self.assertNotIn(Path("/x"), found)


class FoundTest(unittest.TestCase):
    def test_a_directory_that_is_not_one_yields_nothing(self) -> None:
        self.assertEqual(list(firmware.found(Path("/nowhere-at-all"))), [])

    def test_a_file_of_a_suffix_this_package_reads_is_identified(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "ipl.bin").write_bytes(A_PROGRAM)
            (Path(where) / "notes.md").write_bytes(A_PROGRAM)

            found = list(firmware.found(Path(where), _a_manifest()))

            self.assertEqual([path.name for _identity, path in found], ["ipl.bin"])

    def test_a_file_nothing_recognises_is_passed_over(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            (Path(where) / "other.bin").write_bytes(b"\x11" * 64)

            self.assertEqual(list(firmware.found(Path(where), _a_manifest())), [])


class IdentityTest(unittest.TestCase):
    def test_an_identity_prints_the_part_and_the_revision(self) -> None:
        found = firmware.Identity("ssmp", "spc700", "one", 64)

        self.assertIn("one", repr(found))

    def test_it_carries_how_long_the_image_should_be(self) -> None:
        found = firmware.Identity("ssmp", "spc700", "one", 64)

        self.assertEqual(found.bytes_long, 64)


class CrossCheckTest(unittest.TestCase):
    def test_a_manifest_whose_other_digests_disagree_is_refused(self) -> None:
        catalogue = _a_manifest()
        catalogue["artifacts"][0]["accepted"][0]["crc32"] = "deadbeef"

        with self.assertRaises(Corrupt):
            firmware.identify(A_PROGRAM, catalogue)

    def test_the_refusal_names_the_digest_that_disagreed(self) -> None:
        catalogue = _a_manifest()
        catalogue["artifacts"][0]["accepted"][0]["crc32"] = "deadbeef"

        with self.assertRaises(Corrupt) as caught:
            firmware.identify(A_PROGRAM, catalogue)

        self.assertIn("crc32", str(caught.exception))

    def test_a_manifest_naming_fewer_digests_is_still_accepted(self) -> None:
        catalogue = _a_manifest()
        del catalogue["artifacts"][0]["accepted"][0]["crc32"]

        self.assertEqual(firmware.identify(A_PROGRAM, catalogue).part, "ssmp")


class SearchTest(unittest.TestCase):
    def test_a_machine_with_nowhere_to_look_finds_nothing(self) -> None:
        found = list(firmware.search({firmware.DIRECTORY_VARIABLE: "/nowhere-at-all"}))

        self.assertEqual([one for one in found if one[1].parent == Path("/nowhere-at-all")], [])

    def test_a_part_found_twice_is_yielded_once(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            for where in (first, second):
                (Path(where) / "ipl.bin").write_bytes(A_PROGRAM)
            named = os.pathsep.join((first, second))

            found = list(firmware.search({firmware.DIRECTORY_VARIABLE: named}, _a_manifest()))

            self.assertEqual([str(path.parent) for _identity, path in found], [first])


class RepairInRefusalTest(unittest.TestCase):
    def test_a_refusal_offers_the_repair_the_file_needs(self) -> None:
        with self.assertRaises(Unrecognised) as caught:
            firmware.identify(A_PROGRAM + b"\xff" * 32, _a_manifest())

        self.assertIn("take the first 64 bytes", str(caught.exception))


class KnownBadTest(unittest.TestCase):
    def test_an_image_matching_neither_the_good_nor_the_bad_is_unrecognised(self) -> None:
        catalogue = _a_manifest(bad=b"\x00" * firmware.BOOT_BYTES)

        with self.assertRaises(Unrecognised):
            firmware.identify(ANOTHER, catalogue)


class LoadTest(unittest.TestCase):
    def test_an_image_is_put_where_the_unit_reads_it(self) -> None:
        class Space:
            boot = None

        held = Space()

        firmware.load(held, A_PROGRAM)

        self.assertEqual(held.boot, A_PROGRAM)

    def test_an_image_of_the_wrong_length_is_refused_before_it_is_loaded(self) -> None:
        class Space:
            boot = None

        held = Space()

        with self.assertRaises(WrongShape):
            firmware.load(held, A_PROGRAM[:-1])

        self.assertIsNone(held.boot)


if __name__ == "__main__":
    unittest.main()
