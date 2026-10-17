import hashlib
import json
import os
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ssmp

ROOT = Path(__file__).resolve().parent.parent

A_PROGRAM = bytes(range(64))

ANOTHER = bytes(range(1, 65))

MANIFEST = ROOT / "ssmp" / "artifacts.manifest.json"


def digests(image: bytes) -> dict[str, str]:
    return {
        "crc32": f"{zlib.crc32(image):08x}",
        "md5": hashlib.md5(image, usedforsecurity=False).hexdigest(),
        "sha1": hashlib.sha1(image, usedforsecurity=False).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }


def a_catalogue(image: bytes = A_PROGRAM, bad: bytes | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "part": "ssmp",
        "processor": "spc700",
        "bytes": 64,
        "accepted": [{"revision": "one", **digests(image)}],
    }
    if bad is not None:
        entry["knownBad"] = [{"why": "half of it is zeroes", **digests(bad)}]
    return {"artifacts": [entry]}


def refusal(image: bytes, catalogue: dict[str, Any] | None = None) -> str:
    try:
        ssmp.identify(image, a_catalogue() if catalogue is None else catalogue)
    except (ssmp.Unrecognised, ssmp.Corrupt) as error:
        return f"{type(error).__name__}: {error}"
    return "accepted"


def a_folder(test: unittest.TestCase, files: dict[str, bytes]) -> str:
    where = Path(test.enterContext(tempfile.TemporaryDirectory()))
    for name, content in files.items():
        (where / name).write_bytes(content)
    return str(where)


def found_with(named: str, catalogue: dict[str, Any] | None = None) -> dict[str, Any]:
    with mock.patch.dict(os.environ, {"SSMP_BOOT_DIR": named}):
        return ssmp.available(catalogue=a_catalogue() if catalogue is None else catalogue)


def found_in(named: str) -> list[str]:
    return [str(path.parent) for _, path in found_with(named).values()]


class IdentifyTest(unittest.TestCase):
    def test_a_known_image_is_named_with_its_processor_and_revision(self) -> None:
        # Arrange
        catalogue = a_catalogue()

        # Act
        found = ssmp.identify(A_PROGRAM, catalogue)

        # Assert
        self.assertEqual(
            (found.part, found.processor, found.revision, found.bytes_long),
            ("ssmp", "spc700", "one", 64),
        )

    def test_an_identity_prints_the_part_the_revision_and_the_processor(self) -> None:
        # Arrange
        catalogue = a_catalogue()

        # Act
        found = repr(ssmp.identify(A_PROGRAM, catalogue))

        # Assert
        self.assertEqual(found, "<Identity ssmp one for spc700>")

    def test_an_unknown_image_is_refused_with_the_digest_that_was_computed(self) -> None:
        # Arrange
        image = ANOTHER

        # Act
        said = refusal(image)

        # Assert
        self.assertIn(
            f"Unrecognised: nothing in the manifest has sha256 {digests(image)['sha256']}", said
        )

    def test_sha256_alone_decides(self) -> None:
        # Arrange
        catalogue = a_catalogue()
        catalogue["artifacts"][0]["accepted"][0]["sha256"] = digests(ANOTHER)["sha256"]

        # Act
        said = refusal(A_PROGRAM, catalogue)

        # Assert
        self.assertTrue(said.startswith("Unrecognised:"), said)

    def test_a_dump_the_manifest_records_as_bad_is_refused_as_corrupt_with_why(self) -> None:
        # Arrange
        catalogue = a_catalogue(bad=ANOTHER)

        # Act
        said = refusal(ANOTHER, catalogue)

        # Assert
        self.assertIn("Corrupt:", said)
        self.assertIn("half of it is zeroes", said)

    def test_an_image_matching_neither_the_good_nor_the_bad_is_unrecognised(self) -> None:
        # Arrange
        catalogue = a_catalogue(bad=bytes(64))

        # Act
        said = refusal(ANOTHER, catalogue)

        # Assert
        self.assertTrue(said.startswith("Unrecognised:"), said)

    def test_the_manifest_this_package_carries_is_the_one_used_by_default(self) -> None:
        # Arrange
        image = A_PROGRAM

        # Act
        with self.assertRaises(ssmp.Unrecognised) as caught:
            ssmp.identify(image)

        # Assert
        self.assertIn("different content", str(caught.exception))


class CrossCheckTest(unittest.TestCase):
    def test_a_match_whose_other_digests_disagree_is_refused_naming_the_one(self) -> None:
        # Arrange
        catalogue = a_catalogue()
        catalogue["artifacts"][0]["accepted"][0]["crc32"] = "deadbeef"

        # Act
        said = refusal(A_PROGRAM, catalogue)

        # Assert
        self.assertIn(
            "Corrupt: the ssmp boot program matches on sha256 and disagrees on crc32", said
        )

    def test_each_of_the_other_three_is_checked(self) -> None:
        # Arrange
        wrong = {"crc32": "0" * 8, "md5": "0" * 32, "sha1": "0" * 40}

        # Act
        found = []
        for name, value in wrong.items():
            catalogue = a_catalogue()
            catalogue["artifacts"][0]["accepted"][0][name] = value
            found.append(refusal(A_PROGRAM, catalogue).startswith("Corrupt"))

        # Assert
        self.assertEqual(found, [True, True, True])

    def test_a_manifest_naming_fewer_digests_is_still_accepted(self) -> None:
        # Arrange
        catalogue = a_catalogue()
        del catalogue["artifacts"][0]["accepted"][0]["crc32"]

        # Act
        said = refusal(A_PROGRAM, catalogue)

        # Assert
        self.assertEqual(said, "accepted")


class DiagnosisTest(unittest.TestCase):
    def test_a_file_of_the_wrong_length_is_told_so(self) -> None:
        # Arrange
        image = bytes(100)

        # Act
        said = refusal(image)

        # Assert
        self.assertIn("It is 100 bytes and a boot program is 64", said)

    def test_a_file_of_the_right_length_is_told_it_is_the_content(self) -> None:
        # Arrange
        image = ANOTHER

        # Act
        said = refusal(image)

        # Assert
        self.assertIn("It is the right length with different content", said)

    def test_a_program_at_the_front_of_a_longer_file_is_offered_as_a_repair(self) -> None:
        # Arrange
        image = A_PROGRAM + b"\xff" * 32

        # Act
        said = refusal(image)

        # Assert
        self.assertIn("Try this: take the first 64 bytes", said)

    def test_a_program_at_the_end_of_one_is_offered_too(self) -> None:
        # Arrange
        image = b"\xff" * 32 + A_PROGRAM

        # Act
        said = refusal(image)

        # Assert
        self.assertIn("Try this: take the last 64 bytes", said)

    def test_a_listing_is_offered_as_a_repair(self) -> None:
        # Arrange
        image = " ".join(f"{one:02x}" for one in A_PROGRAM).encode()

        # Act
        said = refusal(image)

        # Assert
        self.assertIn("Try this: read it as a hexadecimal listing", said)

    def test_a_file_nothing_can_be_done_with_is_offered_nothing(self) -> None:
        # Arrange
        image = b"\x11" * 200

        # Act
        said = refusal(image)

        # Assert
        self.assertNotIn("Try this", said)


class SearchTest(unittest.TestCase):
    def test_a_program_in_the_named_directory_is_found(self) -> None:
        # Arrange
        named = a_folder(self, {"ipl.bin": A_PROGRAM})

        # Act
        found = found_with(named)

        # Assert
        self.assertEqual((sorted(found), found["ssmp"][0].revision), (["ssmp"], "one"))

    def test_a_hexadecimal_listing_is_read_as_the_bytes_it_names(self) -> None:
        # Arrange
        named = a_folder(self, {"ipl.txt": " ".join(f"{one:02x}" for one in A_PROGRAM).encode()})

        # Act
        found = found_in(named)

        # Assert
        self.assertEqual(found, [named])

    def test_a_listing_written_with_a_prefix_is_read_too(self) -> None:
        # Arrange
        named = a_folder(self, {"ipl.hex": ", ".join(f"0x{one:02x}" for one in A_PROGRAM).encode()})

        # Act
        found = found_in(named)

        # Assert
        self.assertEqual(found, [named])

    def test_a_listing_naming_the_wrong_number_of_bytes_is_passed_over(self) -> None:
        # Arrange
        named = a_folder(self, {"ipl.txt": b"aa bb cc"})

        # Act
        found = found_in(named)

        # Assert
        self.assertEqual(found, [])

    def test_a_file_of_a_suffix_this_package_does_not_read_is_passed_over(self) -> None:
        # Arrange
        named = a_folder(self, {"notes.md": A_PROGRAM})

        # Act
        found = found_in(named)

        # Assert
        self.assertEqual(found, [])

    def test_a_file_nothing_recognises_is_passed_over(self) -> None:
        # Arrange
        named = a_folder(self, {"other.bin": b"\x11" * 64})

        # Act
        found = found_in(named)

        # Assert
        self.assertEqual(found, [])

    def test_a_dump_recorded_as_bad_is_passed_over(self) -> None:
        # Arrange
        named = a_folder(self, {"bad.bin": ANOTHER})

        # Act
        found = found_with(named, a_catalogue(bad=ANOTHER))

        # Assert
        self.assertEqual(found, {})

    def test_a_directory_that_is_not_there_yields_nothing(self) -> None:
        # Arrange
        named = str(Path(a_folder(self, {})) / "nowhere")

        # Act
        found = found_in(named)

        # Assert
        self.assertEqual(found, [])

    def test_more_than_one_directory_can_be_named_and_the_first_wins(self) -> None:
        # Arrange
        first = a_folder(self, {"ipl.bin": A_PROGRAM})
        second = a_folder(self, {"ipl.bin": A_PROGRAM})

        # Act
        found = found_in(os.pathsep.join((first, second)))

        # Assert
        self.assertEqual(found, [first])

    def test_the_same_directory_named_twice_is_looked_at_once(self) -> None:
        # Arrange
        once = a_folder(self, {"ipl.bin": A_PROGRAM})

        # Act
        found = found_in(os.pathsep.join((once, once)))

        # Assert
        self.assertEqual(found, [once])

    def test_the_boot_directory_inside_this_checkout_is_looked_at(self) -> None:
        # Arrange
        inside = ROOT / "boot"
        inside.mkdir(exist_ok=True)
        held = self.enterContext(tempfile.NamedTemporaryFile(dir=inside, suffix=".bin"))
        Path(held.name).write_bytes(A_PROGRAM)

        # Act
        found = found_in(a_folder(self, {}))

        # Assert
        self.assertEqual(found, [str(inside)])

    def test_a_variable_this_member_does_not_read_names_nothing(self) -> None:
        # Arrange
        elsewhere = a_folder(self, {"ipl.bin": A_PROGRAM})

        # Act
        with mock.patch.dict(os.environ, {"UPD7725_FIRMWARE_DIR": elsewhere, "SSMP_BOOT_DIR": ""}):
            found = ssmp.available(catalogue=a_catalogue())

        # Assert
        self.assertNotIn(elsewhere, [str(path.parent) for _, path in found.values()])


class ManifestTest(unittest.TestCase):
    def test_it_names_the_unit_and_its_processor(self) -> None:
        # Arrange
        held = json.loads(MANIFEST.read_text())

        # Act
        entry = held["artifacts"][0]

        # Assert
        self.assertEqual(
            (entry["part"], entry["processor"], entry["bytes"]), ("ssmp", "spc700", 64)
        )

    def test_every_accepted_image_carries_all_four_digests(self) -> None:
        # Arrange
        held = json.loads(MANIFEST.read_text())

        # Act
        missing = [
            name
            for entry in held["artifacts"]
            for accepted in entry["accepted"]
            for name in ("crc32", "md5", "sha1", "sha256")
            if name not in accepted
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_it_says_where_its_digests_came_from(self) -> None:
        # Arrange
        held = json.loads(MANIFEST.read_text())

        # Act
        entry = held["artifacts"][0]

        # Assert
        self.assertIn("provenance", entry)

    def test_it_names_the_digest_that_decides_and_says_the_others_do_not(self) -> None:
        # Arrange
        held = json.loads(MANIFEST.read_text())

        # Act
        said = str(held["decides"])

        # Assert
        self.assertEqual(
            ("sha256 decides" in said, "decides anything on its own" in said), (True, True)
        )


if __name__ == "__main__":
    unittest.main()
