"""The console's own upload protocol, driven at the unit end to end.

This is the check that matters most in this repository, because it is the only
one where the evidence is the part itself. The sixty four bytes in the top page
are Sony's, the sequence below is the one every Super Nintendo game performs, and
nothing here was copied from an implementation of either.

A machine without a boot program skips the whole file and says so, rather than
reporting a pass.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ssmp
from conformance import console

PRESENT = ssmp.why_not() is None


@unittest.skipUnless(PRESENT, ssmp.why_not() or "")
class HandshakeTest(unittest.TestCase):
    """What the unit says before anybody has said anything to it."""

    def test_it_answers_the_two_bytes_a_console_waits_for(self) -> None:
        unit = ssmp.Chip()

        console.wait_for_ready(unit)

        self.assertEqual((unit.read(0), unit.read(1)), (console.READY_LOW, console.READY_HIGH))

    def test_it_says_nothing_on_the_other_two_ports(self) -> None:
        unit = ssmp.Chip()

        console.wait_for_ready(unit)

        self.assertEqual((unit.read(2), unit.read(3)), (0x00, 0x00))

    def test_it_reaches_the_wait_its_own_program_has(self) -> None:
        unit = ssmp.Chip()

        console.wait_for_ready(unit)

        self.assertIn(unit.processor.pc, console.WAITING)

    def test_and_stays_there_while_nothing_is_said_to_it(self) -> None:
        unit = ssmp.Chip()
        console.wait_for_ready(unit)

        unit.run_for(50_000)

        self.assertIn(unit.processor.pc, console.WAITING)


@unittest.skipUnless(PRESENT, ssmp.why_not() or "")
class UploadTest(unittest.TestCase):
    """A block of code moved in through four bytes, the way a cartridge does it."""

    def test_a_program_uploaded_through_the_ports_runs(self) -> None:
        unit = ssmp.Chip()

        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)

        self.assertEqual(unit.processor.a, 0x42)

    def test_it_leaves_what_it_wrote_where_it_wrote_it(self) -> None:
        unit = ssmp.Chip()

        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)

        self.assertEqual(unit.space.memory.read8(0x0010), 0x5A)

    def test_the_uploaded_bytes_are_the_bytes_that_arrived(self) -> None:
        unit = ssmp.Chip()

        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)

        held = bytes(
            unit.space.memory.read8(console.SOMEWHERE + at) for at in range(len(console.A_PROGRAM))
        )
        self.assertEqual(held, console.A_PROGRAM)

    def test_a_program_uploaded_somewhere_else_runs_there(self) -> None:
        unit = ssmp.Chip()

        console.upload(unit, console.A_PROGRAM, 0x0400)

        self.assertEqual(unit.processor.a, 0x42)

    def test_the_unit_acknowledges_every_byte_as_it_arrives(self) -> None:
        unit = ssmp.Chip()

        said = console.upload(unit, console.A_PROGRAM, console.SOMEWHERE)

        self.assertEqual(said, list(range(len(console.A_PROGRAM))))

    def test_a_second_block_can_follow_the_first(self) -> None:
        unit = ssmp.Chip()
        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE, jump=False)

        console.upload(unit, console.ANOTHER_PROGRAM, 0x0300, after=len(console.A_PROGRAM))

        self.assertEqual(unit.processor.a, 0x99)

    def test_and_the_first_block_is_still_where_it_was_put(self) -> None:
        unit = ssmp.Chip()
        console.upload(unit, console.A_PROGRAM, console.SOMEWHERE, jump=False)

        console.upload(unit, console.ANOTHER_PROGRAM, 0x0300, after=len(console.A_PROGRAM))

        held = bytes(
            unit.space.memory.read8(console.SOMEWHERE + at) for at in range(len(console.A_PROGRAM))
        )
        self.assertEqual(held, console.A_PROGRAM)


@unittest.skipUnless(PRESENT, ssmp.why_not() or "")
class MemoryTest(unittest.TestCase):
    """What the boot program leaves behind it."""

    def test_the_boot_program_clears_the_zero_page_before_the_handshake(self) -> None:
        unit = ssmp.Chip(fill=0xFF)

        console.wait_for_ready(unit)

        held = {unit.space.memory.read8(at) for at in range(0x01, 0xF0)}
        self.assertEqual(held, {0x00})

    def test_and_leaves_the_very_first_byte_alone(self) -> None:
        unit = ssmp.Chip(fill=0xFF)

        console.wait_for_ready(unit)

        self.assertEqual(unit.space.memory.read8(0x0000), 0xFF)

    def test_the_boot_window_covers_memory_rather_than_replacing_it(self) -> None:
        unit = ssmp.Chip()
        console.wait_for_ready(unit)
        unit.space.write8(0xFFC0, 0x5A)

        under = unit.space.memory.read8(0xFFC0)

        self.assertEqual((unit.space.read8(0xFFC0), under), (unit.space.boot[0], 0x5A))

    def test_the_stack_pointer_is_where_the_boot_program_put_it(self) -> None:
        unit = ssmp.Chip()

        console.wait_for_ready(unit)

        self.assertEqual(unit.processor.sp, 0xEF)


if __name__ == "__main__":
    unittest.main()
