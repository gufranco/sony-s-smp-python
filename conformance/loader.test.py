"""An audio unit written down, put back, and run.

Two kinds of check live here. The first builds a written-down unit by hand, so
the reading and the restoring are exercised on any machine. The second runs
blargg's, which carry checksums he took on a console, and those skip out loud
when the files are not here rather than reporting a pass nobody earned.
"""

import sys
import unittest
from pathlib import Path
from typing import override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import loader
from ssmp import Chip, board, space

CHECKS = {
    "initial_regs.spc": "the six processor registers, all sixteen ports and registers, "
    "and the sound generator's whole register file",
    "initial_in_ports.spc": "the four ports, read as the first thing the program does",
    "full_ram.spc": "every byte of memory, the stack page, the echo buffer, "
    "and the three bytes under the stack pointer",
}

QUICK = ("initial_regs.spc", "initial_in_ports.spc")

ROOM = 4_000_000

STANDING_IN = bytes(space.BOOT_BYTES)
"""A boot program of the right length and no content.

The checks below restore a written-down unit and set its program counter
themselves, so nothing they do ever runs what is in the boot window. Supplying
sixty four zeroes rather than Sony's sixty four bytes lets every one of them run
on a machine that holds no copy, and leaves the checks that genuinely need the
real thing in `boot.test.py` where they belong.
"""


def _a_unit() -> object:
    return Chip("ssmp", boot=STANDING_IN)


def _raw(program: dict[int, int], registers: bytes, pc: int) -> bytes:
    """One of these files, built rather than read, so no file is needed."""
    header = bytearray(loader.HEADER_BYTES)
    header[: len(loader.SIGNATURE)] = loader.SIGNATURE
    header[loader.PC_AT] = pc & 0xFF
    header[loader.PC_AT + 1] = (pc >> 8) & 0xFF
    header[loader.SP_AT] = 0xEF
    memory = bytearray(loader.RAM_BYTES)
    for at, value in program.items():
        memory[at] = value
    memory[loader.REGISTERS : loader.REGISTERS + 0x10] = registers
    return bytes(header) + bytes(memory) + bytes(loader.GENERATOR_BYTES)


def _registers(
    control: int = space.CONTROL_BOOT_VISIBLE, ports: bytes = b"\x00\x00\x00\x00"
) -> bytes:
    held = bytearray(0x10)
    held[0x01] = control
    held[0x04:0x08] = ports
    return bytes(held)


def _laid_out(at: int, values: bytes) -> dict[int, int]:
    return {at + index: value for index, value in enumerate(values)}


def _with_harness(agreed_at: int, disagreed_at: int, program: dict[int, int]) -> dict[int, int]:
    held = dict(program)
    held.update(_laid_out(agreed_at, loader.AGREED))
    held.update(_laid_out(disagreed_at, loader.DISAGREED))
    return held


class ReadingTest(unittest.TestCase):
    def test_a_file_that_does_not_begin_the_right_way_is_refused(self) -> None:
        with self.assertRaises(loader.NotAnSpc):
            loader.Dump(b"not one of these" + bytes(loader.SHORTEST))

    def test_and_says_what_it_expected_to_see(self) -> None:
        with self.assertRaises(loader.NotAnSpc) as caught:
            loader.Dump(b"not one of these" + bytes(loader.SHORTEST))

        self.assertIn("SNES-SPC700", str(caught.exception))

    def test_a_file_too_short_to_hold_the_generator_is_refused(self) -> None:
        with self.assertRaises(loader.NotAnSpc) as caught:
            loader.Dump(loader.SIGNATURE + bytes(loader.RAM_BYTES))

        self.assertIn("sound generator", str(caught.exception))

    def test_the_processor_registers_come_out_of_the_header(self) -> None:
        held = loader.Dump(_raw({}, _registers(), 0x1234))

        self.assertEqual((held.pc, held.sp), (0x1234, 0xEF))

    def test_the_sixteen_that_are_not_memory_come_out_of_the_image(self) -> None:
        held = loader.Dump(_raw({}, _registers(ports=b"\x11\x22\x33\x44"), 0x0200))

        self.assertEqual(held.registers[0x04:0x08], b"\x11\x22\x33\x44")

    def test_it_says_what_it_is_when_printed(self) -> None:
        held = loader.Dump(_raw({}, _registers(), 0x0200))

        self.assertIn("pc=$0200", repr(held))

    def test_one_off_disk_reads_the_same_as_one_in_memory(self) -> None:
        where = Path(self.enterContext(__import__("tempfile").TemporaryDirectory())) / "a.spc"
        where.write_bytes(_raw({}, _registers(), 0x0200))

        self.assertEqual(loader.read(where).pc, 0x0200)


class RestoringTest(unittest.TestCase):
    def test_memory_comes_back(self) -> None:
        held = loader.Dump(_raw({0x0400: 0x5A}, _registers(), 0x0400))

        unit = loader.restore(_a_unit(), held)

        self.assertEqual(unit.space.read8(0x0400), 0x5A)

    def test_the_ports_survive_a_control_value_that_clears_them(self) -> None:
        asks_for_a_clear = space.CONTROL_CLEAR_PORTS_01 | space.CONTROL_CLEAR_PORTS_23
        held = loader.Dump(
            _raw({}, _registers(control=asks_for_a_clear, ports=b"\x12\x34\x56\x78"), 0x0400)
        )

        unit = loader.restore(_a_unit(), held)

        self.assertEqual(
            bytes(unit.space.read8(space.PORT_0 + index) for index in range(4)),
            b"\x12\x34\x56\x78",
        )

    def test_the_console_side_of_the_ports_comes_back_too(self) -> None:
        held = loader.Dump(_raw({}, _registers(ports=b"\x12\x34\x56\x78"), 0x0400))

        unit = loader.restore(_a_unit(), held)

        self.assertEqual(bytes(unit.read(index) for index in range(4)), b"\x12\x34\x56\x78")

    def test_the_generator_comes_back(self) -> None:
        raw = bytearray(_raw({}, _registers(), 0x0400))
        raw[loader.GENERATOR_AT + 0x0C] = 0x7F
        held = loader.Dump(bytes(raw))

        unit = loader.restore(_a_unit(), held)

        self.assertEqual(unit.space.dsp.read(0x0C), 0x7F)

    def test_the_cycle_count_starts_again(self) -> None:
        unit = _a_unit()
        unit.run_for(100)

        loader.restore(unit, loader.Dump(_raw({}, _registers(), 0x0400)))

        self.assertEqual(unit.cycles, 0)


class ChecksumTest(unittest.TestCase):
    def test_it_reproduces_the_value_blargg_took_for_the_processor_registers(self) -> None:
        held = loader.checksum(bytes((0x1B, 0x23, 0xDC, 0xD4, 0x76)))

        self.assertEqual(held, bytes((0xE7, 0xB6, 0xCB, 0x44)))

    def test_a_different_set_of_bytes_does_not_reproduce_it(self) -> None:
        held = loader.checksum(bytes((0x1B, 0x23, 0xDC, 0xD4, 0x77)))

        self.assertNotEqual(held, bytes((0xE7, 0xB6, 0xCB, 0x44)))

    def test_it_answers_four_bytes(self) -> None:
        held = loader.checksum(b"")

        self.assertEqual(len(held), 4)


class WhereTest(unittest.TestCase):
    def test_a_named_directory_is_looked_at_first(self) -> None:
        held = loader.directories({loader.DIRECTORY_VARIABLE: "/somewhere"})

        self.assertEqual(held[0], Path("/somewhere"))

    def test_more_than_one_can_be_named_at_once(self) -> None:
        import os

        held = loader.directories({loader.DIRECTORY_VARIABLE: f"/one{os.pathsep}/two"})

        self.assertEqual(held[:2], (Path("/one"), Path("/two")))

    def test_naming_nothing_still_leaves_the_two_this_project_knows(self) -> None:
        held = loader.directories({})

        self.assertEqual(held, (loader.ALONGSIDE, loader.DEFAULT_DIRECTORY))

    def test_a_directory_named_twice_is_looked_at_once(self) -> None:
        import os

        held = loader.directories({loader.DIRECTORY_VARIABLE: f"/one{os.pathsep}/one"})

        self.assertEqual(held.count(Path("/one")), 1)

    def test_a_file_that_is_there_is_found(self) -> None:
        where = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        (where / "a.spc").write_bytes(b"")

        self.assertEqual(
            loader.find("a.spc", {loader.DIRECTORY_VARIABLE: str(where)}), where / "a.spc"
        )

    def test_a_file_that_is_not_answers_nothing(self) -> None:
        where = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))

        self.assertIsNone(loader.find("a.spc", {loader.DIRECTORY_VARIABLE: str(where)}))


class HarnessTest(unittest.TestCase):
    def test_it_is_found_by_what_it_does_rather_than_where_it_is(self) -> None:
        held = loader.Dump(_raw(_with_harness(0x0300, 0x0400, {}), _registers(), 0x0200))

        self.assertEqual(
            (loader.harness(held).agreed, loader.harness(held).disagreed), (0x0300, 0x0400)
        )

    def test_the_checksum_addresses_come_out_of_the_routine_itself(self) -> None:
        held = loader.Dump(_raw(_with_harness(0x0300, 0x0400, {}), _registers(), 0x0200))

        self.assertEqual(loader.harness(held).checksum_at, 0xDC)

    def test_a_file_carrying_no_such_routine_is_refused(self) -> None:
        held = loader.Dump(_raw({}, _registers(), 0x0200))

        with self.assertRaises(loader.NoHarness):
            loader.harness(held)

    def test_a_file_carrying_only_half_of_it_is_refused_too(self) -> None:
        held = loader.Dump(_raw(_laid_out(0x0300, loader.AGREED), _registers(), 0x0200))

        with self.assertRaises(loader.NoHarness) as caught:
            loader.harness(held)

        self.assertIn("pushes those same four bytes", str(caught.exception))

    def test_a_file_carrying_it_twice_is_refused_rather_than_guessed_at(self) -> None:
        program = _with_harness(0x0300, 0x0400, {})
        program.update(_laid_out(0x0500, loader.AGREED))
        held = loader.Dump(_raw(program, _registers(), 0x0200))

        with self.assertRaises(loader.NoHarness) as caught:
            loader.harness(held)

        self.assertIn("more than one", str(caught.exception))

    def test_it_says_what_it_found_when_printed(self) -> None:
        held = loader.Dump(_raw(_with_harness(0x0300, 0x0400, {}), _registers(), 0x0200))

        self.assertIn("$0300", repr(loader.harness(held)))


class PlayingTest(unittest.TestCase):
    def _dump(self, program: dict[int, int]) -> loader.Dump:
        return loader.Dump(_raw(_with_harness(0x0300, 0x0400, program), _registers(), 0x0200))

    def test_a_check_that_reaches_the_boot_program_has_finished(self) -> None:
        held = self._dump({0x0200: 0x5F, 0x0201: 0xC0, 0x0202: 0xFF})

        said = loader.play(_a_unit(), held, ROOM)

        self.assertTrue(said.agreed)

    def test_one_that_calls_the_agreeing_routine_first_counts_it(self) -> None:
        held = self._dump(
            {0x0200: 0x3F, 0x0201: 0x00, 0x0202: 0x03, 0x0203: 0x5F, 0x0204: 0xC0, 0x0205: 0xFF}
        )

        said = loader.play(_a_unit(), held, ROOM)

        self.assertEqual((said.agreed, said.agreements), (True, 1))

    def test_one_that_reaches_the_reporting_routine_disagrees(self) -> None:
        held = self._dump({0x0200: 0x5F, 0x0201: 0x00, 0x0202: 0x04})

        said = loader.play(_a_unit(), held, ROOM)

        self.assertFalse(said.agreed)

    def test_and_says_which_sub_check_it_was(self) -> None:
        held = self._dump({0x0200: 0x5F, 0x0201: 0x00, 0x0202: 0x04})

        said = loader.play(_a_unit(), held, ROOM)

        self.assertEqual(said.disagreed_at, 1)

    def test_and_carries_the_four_bytes_it_was_about_to_report(self) -> None:
        held = self._dump({0x0200: 0x5F, 0x0201: 0x00, 0x0202: 0x04})

        said = loader.play(_a_unit(), held, ROOM)

        self.assertEqual(len(said.reported), 4)

    def test_a_check_that_never_decides_is_not_reported_as_agreeing(self) -> None:
        held = self._dump({0x0200: 0x2F, 0x0201: 0xFE})

        with self.assertRaises(TimeoutError):
            loader.play(_a_unit(), held, 200)

    def test_an_agreeing_outcome_says_so_when_printed(self) -> None:
        held = self._dump({0x0200: 0x5F, 0x0201: 0xC0, 0x0202: 0xFF})

        said = loader.play(_a_unit(), held, ROOM)

        self.assertIn("agreed", repr(said))

    def test_a_disagreeing_one_says_which_sub_check_when_printed(self) -> None:
        held = self._dump({0x0200: 0x5F, 0x0201: 0x00, 0x0202: 0x04})

        said = loader.play(_a_unit(), held, ROOM)

        self.assertIn("disagreed on sub-check 1", repr(said))


class BlarggTest(unittest.TestCase):
    """His checks, run as they are, against expectations he took on a console.

    These build the unit with the real boot program rather than the stand-in the
    checks above use. One of them reads every byte of memory, and the boot window
    covers the top page while it is visible, so what is behind that window has to
    be the thing a console would have there.
    """

    @override
    def setUp(self) -> None:
        if board.why_not() is not None:
            self.skipTest(f"no unit can be built here: {board.why_not()}")

    def test_every_quick_check_agrees(self) -> None:
        outcomes = {}
        for name in QUICK:
            where = loader.find(name)
            if where is None:
                self.skipTest(
                    f"{name} is not on this machine. It is blargg's and is not carried"
                    f" here; put a copy in {loader.DEFAULT_DIRECTORY.name}/ or name a"
                    f" directory in {loader.DIRECTORY_VARIABLE}"
                )
            outcomes[name] = loader.play(Chip("ssmp"), loader.read(where), ROOM)

        self.assertEqual([one for one, said in outcomes.items() if not said.agreed], [])

    def test_the_one_that_reads_the_ports_first_gets_all_four(self) -> None:
        where = loader.find("initial_in_ports.spc")
        if where is None:
            self.skipTest("initial_in_ports.spc is not on this machine")

        said = loader.play(Chip("ssmp"), loader.read(where), ROOM)

        self.assertTrue(said.agreed)

    def test_a_unit_whose_write_only_registers_read_back_fails_his_checksum(self) -> None:
        where = loader.find("initial_regs.spc")
        if where is None:
            self.skipTest("initial_regs.spc is not on this machine")
        held = loader.read(where)
        as_written = list(held.registers)
        as_read = [0x00, 0x00, *as_written[2:10], 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

        self.assertNotEqual(loader.checksum(as_written), loader.checksum(as_read))


if __name__ == "__main__":
    unittest.main()
