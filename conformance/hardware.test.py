"""The record held to the model, so neither can drift away from the other.

A record nothing checks is a record that goes stale quietly. Every figure in
`hardware.json` is compared here against what the package actually does, so a
change to one that is not a change to the other fails.
"""

import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from conformance import console
from ssmp import rates, space, timers

RECORD = Path(__file__).resolve().parent / "hardware.json"

MANIFEST_OF_CHECKS = Path(__file__).resolve().parent / "spc.manifest.json"

_CANNOT_BE_READ = (space.TEST, space.CONTROL, *range(space.TIMER_0_DIVIDER, space.COUNTER_0))
"""The five that are written and never read, which all answer zero."""


def declared() -> dict[str, Any]:
    found: dict[str, Any] = json.loads(RECORD.read_text())
    return found


class ShapeTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()

    def test_the_record_says_which_source_outranks_which(self) -> None:
        self.assertGreater(len(self.held["authority"]["order"]), 1)

    def test_it_says_why_that_order_and_not_another(self) -> None:
        self.assertTrue(self.held["authority"]["why"])

    def test_it_carries_a_documents_key_even_though_there_are_none(self) -> None:
        self.assertEqual(self.held["documents"], {})

    def test_and_says_why_it_is_empty_rather_than_leaving_a_reader_to_infer_it(self) -> None:
        self.assertTrue(self.held["documentsNote"])

    def test_what_is_not_stated_is_written_down_rather_than_filled_in(self) -> None:
        self.assertGreater(len(self.held["notStated"]), 0)

    def test_every_claim_says_whether_it_is_verified(self) -> None:
        for name in (
            "bootProgram",
            "registers",
            "control",
            "timers",
            "ports",
            "checksFromHardware",
        ):
            self.assertIn("verified", self.held[name], name)

    def test_and_what_would_settle_it(self) -> None:
        for name in (
            "bootProgram",
            "registers",
            "control",
            "timers",
            "ports",
            "checksFromHardware",
        ):
            self.assertTrue(self.held[name]["howToSettleIt"], name)

    def test_and_what_stands_behind_it_today(self) -> None:
        for name in (
            "bootProgram",
            "registers",
            "control",
            "timers",
            "ports",
            "checksFromHardware",
        ):
            self.assertTrue(self.held[name]["evidence"], name)


class GeneratorTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["generator"]

    def test_the_clock_the_record_gives_is_the_one_derived(self) -> None:
        self.assertEqual(self.held["clocksPerProcessorCycle"], rates.GENERATOR_CLOCKS)

    def test_the_record_says_the_two_halves_share_one_memory(self) -> None:
        self.assertTrue(self.held["sharesMemoryWithTheProcessor"])

    def test_and_that_the_generator_is_reset_rather_than_left_scrambled(self) -> None:
        self.assertTrue(self.held["resetAtConstruction"])

    def test_it_does_not_claim_what_the_generator_produces_is_checked(self) -> None:
        self.assertFalse(self.held["verified"])

    def test_and_names_the_thing_that_would_settle_that(self) -> None:
        self.assertIn("spc_dsp6", self.held["howToSettleIt"])

    def test_a_unit_here_shares_its_memory_the_way_the_record_says(self) -> None:
        """Built on sixty four zeroes rather than Sony's sixty four bytes.

        Nothing here runs what is in the boot window, so a stand-in of the right
        length lets this run on a machine holding no copy of the real one.
        """
        from ssmp import Chip

        unit = Chip("ssmp", boot=bytes(space.BOOT_BYTES))

        self.assertIs(unit.dsp.memory, unit.space.memory)


class FromHardwareTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["checksFromHardware"]

    def test_the_record_names_the_run_that_plays_these_checks(self) -> None:
        self.assertTrue((Path(__file__).resolve().parent.parent / self.held["runner"]).is_file())

    def test_and_the_manifest_that_identifies_them(self) -> None:
        self.assertTrue((Path(__file__).resolve().parent.parent / self.held["manifest"]).is_file())

    def test_it_says_outright_that_the_files_are_not_carried(self) -> None:
        self.assertFalse(self.held["carried"])

    def test_every_check_it_lists_is_one_the_manifest_identifies(self) -> None:
        named = {one["name"] for one in json.loads(MANIFEST_OF_CHECKS.read_text())["checks"]}

        self.assertEqual([one["name"] for one in self.held["ran"] if one["name"] not in named], [])

    def test_and_every_one_of_them_agreed(self) -> None:
        self.assertEqual([one["name"] for one in self.held["ran"] if not one["agreed"]], [])

    def test_the_disagreement_it_found_was_also_reproduced_on_purpose(self) -> None:
        self.assertTrue(self.held["shownToFail"])

    def test_the_register_file_is_no_longer_an_open_question(self) -> None:
        self.assertTrue(declared()["registers"]["verified"])

    def test_and_what_a_write_only_register_answers_is_no_longer_unstated(self) -> None:
        unstated = " ".join(declared()["notStated"])

        self.assertNotIn("dividers answer when read", unstated)

    def test_every_write_only_register_the_map_names_says_a_read_answers_zero(self) -> None:
        held = declared()["registers"]["map"]
        cannot = ("0xF0", "0xF1", "0xFA", "0xFB", "0xFC")

        self.assertEqual([one for one in cannot if "answers zero" not in held[one]], [])

    def test_and_the_model_answers_zero_at_every_one_of_them(self) -> None:
        held = space.Space(memory=_AnyMemory())
        for at in _CANNOT_BE_READ:
            held.memory.write8(at, 0xA5)

        self.assertEqual([held.read8(at) for at in _CANNOT_BE_READ], [0x00] * 5)

    def test_without_looking_at_the_memory_underneath_to_get_there(self) -> None:
        """Answering zero and answering a zero that happened to be there differ.

        The model read memory at these addresses before the checksum caught it,
        and a stub full of zeroes would let that behaviour pass this check. What
        rules it out is that the read never reaches memory at all.

        The spare register is read alongside them so the recorder is seen to
        record. Without it this would pass just as well against a stub that had
        stopped noticing reads, which is a check that cannot fail.
        """
        store = _AnyMemory()
        held = space.Space(memory=store)
        for at in _CANNOT_BE_READ:
            held.memory.write8(at, 0xA5)

        for at in (*_CANNOT_BE_READ, space.SPARE_0):
            held.read8(at)

        self.assertEqual(store.read_at, [space.SPARE_0])


class _AnyMemory:
    """Sixty four kilobytes that remembers being read, so a read can be ruled out."""

    def __init__(self) -> None:
        self.held = bytearray(space.SPACE)
        self.read_at: list[int] = []

    def read8(self, address: int) -> int:
        self.read_at.append(address)
        return self.held[address]

    def write8(self, address: int, value: int) -> None:
        self.held[address] = value & 0xFF


class BootTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["bootProgram"]

    def test_the_length_the_record_gives_is_the_one_the_package_enforces(self) -> None:
        self.assertEqual(self.held["bytes"], space.BOOT_BYTES)

    def test_the_address_it_gives_is_where_the_window_sits(self) -> None:
        self.assertEqual(int(self.held["at"], 16), space.BOOT_AT)

    def test_the_two_ready_bytes_are_the_ones_a_console_waits_for(self) -> None:
        self.assertEqual(
            (int(self.held["readyLow"], 16), int(self.held["readyHigh"], 16)),
            (console.READY_LOW, console.READY_HIGH),
        )

    def test_the_start_byte_is_the_one_the_protocol_uses(self) -> None:
        self.assertEqual(int(self.held["start"], 16), console.START)


class RegisterTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["registers"]

    def test_the_register_file_begins_where_the_record_says(self) -> None:
        self.assertEqual(int(self.held["at"], 16), space.REGISTERS_AT)

    def test_there_are_as_many_as_the_record_gives(self) -> None:
        self.assertEqual(self.held["count"], space.REGISTER_COUNT)

    def test_the_map_covers_every_one_of_them(self) -> None:
        self.assertEqual(len(self.held["map"]), space.REGISTER_COUNT)

    def test_it_names_no_address_outside_the_file(self) -> None:
        outside = [
            one
            for one in self.held["map"]
            if not space.REGISTERS_AT <= int(one, 16) < space.REGISTERS_AT + space.REGISTER_COUNT
        ]

        self.assertEqual(outside, [])

    def test_the_addresses_it_names_for_the_ports_are_the_ones_used(self) -> None:
        named = sorted(one for one, what in self.held["map"].items() if what.startswith("port"))

        self.assertEqual(
            [int(one, 16) for one in named],
            list(range(space.PORT_0, space.PORT_0 + 4)),
        )

    def test_the_address_it_names_for_the_control_register_is_the_one_used(self) -> None:
        named = next(one for one, what in self.held["map"].items() if what.startswith("control"))

        self.assertEqual(int(named, 16), space.CONTROL)


class ControlTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["control"]

    def test_every_bit_the_record_names_is_the_bit_the_package_uses(self) -> None:
        self.assertEqual(
            [int(self.held[name], 16) for name in ("timer0", "timer1", "timer2")],
            [space.CONTROL_TIMER_0, space.CONTROL_TIMER_1, space.CONTROL_TIMER_2],
        )

    def test_the_two_port_clears_match(self) -> None:
        self.assertEqual(
            [int(self.held[name], 16) for name in ("clearPorts01", "clearPorts23")],
            [space.CONTROL_CLEAR_PORTS_01, space.CONTROL_CLEAR_PORTS_23],
        )

    def test_the_boot_window_bit_matches(self) -> None:
        self.assertEqual(int(self.held["bootVisible"], 16), space.CONTROL_BOOT_VISIBLE)

    def test_no_two_bits_it_names_are_the_same_bit(self) -> None:
        named = [
            int(self.held[name], 16)
            for name in (
                "timer0",
                "timer1",
                "timer2",
                "clearPorts01",
                "clearPorts23",
                "bootVisible",
            )
        ]

        self.assertEqual(len(set(named)), len(named))


class TimerTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["timers"]

    def test_there_are_as_many_as_the_record_gives(self) -> None:
        self.assertEqual(self.held["count"], space.TIMER_COUNT)

    def test_the_counter_is_as_wide_as_the_record_says(self) -> None:
        self.assertEqual((1 << self.held["counterBits"]) - 1, timers.COUNTER_MASK)

    def test_a_divider_of_zero_means_what_the_record_says(self) -> None:
        self.assertEqual(self.held["dividerWhenZero"], timers.DIVIDER_WHEN_ZERO)

    def test_the_two_tick_costs_are_the_ones_derived(self) -> None:
        self.assertEqual(
            (self.held["slowCyclesPerTick"], self.held["fastCyclesPerTick"]),
            (rates.SLOW_TIMER_CYCLES, rates.FAST_TIMER_CYCLES),
        )


class PortTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["ports"]

    def test_there_are_as_many_as_the_record_gives(self) -> None:
        from ssmp import ports

        self.assertEqual(self.held["count"], ports.COUNT)

    def test_each_one_holds_a_byte_per_direction(self) -> None:
        from ssmp import ports

        held = ports.Ports()
        held.console_writes(0, 0x11)
        held.unit_writes(0, 0x22)

        self.assertEqual(
            len({held.unit_reads(0), held.console_reads(0)}), self.held["bytesPerPort"]
        )


if __name__ == "__main__":
    unittest.main()
