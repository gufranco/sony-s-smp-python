import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ssmp
from conformance import console, monitor

RECORD = Path(__file__).resolve().parent / "hardware.json"

MANIFEST_OF_CHECKS = Path(__file__).resolve().parent / "checks.manifest.json"


def declared() -> dict[str, Any]:
    found: dict[str, Any] = json.loads(RECORD.read_text())
    return found


def a_unit(fill: int = 0x00) -> Any:
    return ssmp.Chip("ssmp", boot=monitor.MONITOR, fill=fill).reset()


def named(entry: str) -> list[int]:
    return sorted(
        int(address, 16)
        for address, what in declared()["registers"]["map"].items()
        if entry in what
    )


def cannot_be_read() -> list[int]:
    return named("answers zero")


def ports() -> list[int]:
    return [address for address in named("port") if address not in named("control")]


def writing_to(addresses: list[int]) -> bytes:
    stores = [(0x8F, value, address) for value, address in enumerate(addresses, start=0x11)]
    return monitor.boot(bytes(byte for store in stores for byte in store) + bytes((0x2F, 0xFE)))


class ShapeTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()

    def test_the_record_says_which_source_outranks_which(self) -> None:
        self.assertGreater(len(self.held["authority"]["order"]), 1)

    def test_it_says_why_that_order_and_not_another(self) -> None:
        self.assertTrue(self.held["authority"]["why"])

    def test_the_one_document_it_cites_is_pinned_by_digest(self) -> None:
        # Arrange
        documents = self.held["documents"]

        # Act
        digests = [len(one["sha256"]) for one in documents.values()]

        # Assert
        self.assertEqual(digests, [64])

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

    def test_and_the_unit_answers_zero_at_every_one_of_them(self) -> None:
        # Arrange
        unit = a_unit()
        for address in cannot_be_read():
            monitor.poke(unit, address, 0x80 if address == monitor.CONTROL else 0xA5)

        # Act
        found = [monitor.peek(unit, address) for address in cannot_be_read()]

        # Assert
        self.assertEqual(found, [0x00] * 5)

    def test_without_answering_with_the_memory_underneath(self) -> None:
        # Arrange
        unit = a_unit(fill=0xA5)

        # Act
        found = [monitor.peek(unit, address) for address in cannot_be_read()]

        # Assert
        self.assertEqual(found, [0x00] * 5)


class BootTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["bootProgram"]

    def test_a_program_of_the_length_the_record_gives_is_accepted(self) -> None:
        # Arrange
        program = monitor.MONITOR[: self.held["bytes"]]

        # Act
        unit = ssmp.Chip("ssmp", boot=program)

        # Assert
        self.assertEqual(unit.identity.bytes_long, self.held["bytes"])

    def test_and_one_byte_fewer_is_refused(self) -> None:
        # Arrange
        program = monitor.MONITOR[: self.held["bytes"] - 1]

        # Act
        with self.assertRaises(ssmp.WrongShape) as caught:
            ssmp.Chip("ssmp", boot=program)

        # Assert
        self.assertIn(f"this one is {self.held['bytes'] - 1}", str(caught.exception))

    def test_the_window_begins_at_the_address_the_record_gives(self) -> None:
        # Arrange
        at = int(self.held["at"], 16)
        unit = a_unit(fill=0x5A)

        # Act
        found = (monitor.peek(unit, at - 1), monitor.peek(unit, at))

        # Assert
        self.assertEqual(found, (0x5A, monitor.MONITOR[0]))

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

    def test_the_byte_below_the_file_is_memory_and_the_first_in_it_is_not(self) -> None:
        # Arrange
        at = int(self.held["at"], 16)
        unit = a_unit(fill=0xA5)

        # Act
        found = (monitor.peek(unit, at - 1), monitor.peek(unit, at))

        # Assert
        self.assertEqual(found, (0xA5, 0x00))

    def test_the_byte_past_the_last_of_them_is_memory_again(self) -> None:
        # Arrange
        past = int(self.held["at"], 16) + self.held["count"]
        unit = a_unit()
        monitor.poke(unit, past, 0x3C)

        # Act
        found = monitor.peek(unit, past)

        # Assert
        self.assertEqual(found, 0x3C)

    def test_the_map_names_every_one_of_them_and_nothing_else(self) -> None:
        # Arrange
        at = int(self.held["at"], 16)

        # Act
        found = sorted(int(address, 16) for address in self.held["map"])

        # Assert
        self.assertEqual(found, list(range(at, at + self.held["count"])))

    def test_the_addresses_it_names_for_the_ports_reach_the_console_in_order(self) -> None:
        # Arrange
        program = writing_to(ports())
        unit = ssmp.Chip("ssmp", boot=program, fill=0x00).reset()
        unit.run_for(100)

        # Act
        found = [unit.read(index) for index in range(4)]

        # Assert
        self.assertEqual(found, [0x11, 0x12, 0x13, 0x14])

    def test_the_addresses_it_names_as_spare_keep_what_is_written(self) -> None:
        # Arrange
        unit = a_unit()
        spare = named("spare")
        for address in spare:
            monitor.poke(unit, address, 0x66)

        # Act
        found = [monitor.peek(unit, address) for address in spare]

        # Assert
        self.assertEqual(found, [0x66, 0x66])


class ControlTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["control"]

    def test_every_timer_bit_the_record_names_starts_its_own_timer(self) -> None:
        # Arrange
        boot = int(self.held["bootVisible"], 16)
        units = [a_unit() for _ in range(3)]
        for timer, name in enumerate(("timer0", "timer1", "timer2")):
            monitor.poke(units[timer], monitor.FIRST_DIVIDER + timer, 1)
            monitor.poke(units[timer], monitor.CONTROL, boot | int(self.held[name], 16))

        # Act
        found = [
            monitor.tally(unit, monitor.FIRST_COUNTER + timer, reads=3, gap=300)[1] > 0
            for timer, unit in enumerate(units)
        ]

        # Assert
        self.assertEqual(found, [True, True, True])

    def test_the_port_clear_the_record_names_for_ports_2_and_3_clears_them(self) -> None:
        # Arrange
        boot = int(self.held["bootVisible"], 16)
        unit = a_unit()
        unit.write(2, 0xFF)
        unit.write(3, 0xFF)

        # Act
        monitor.poke(unit, monitor.CONTROL, boot | int(self.held["clearPorts23"], 16))

        # Assert
        self.assertEqual((monitor.peek(unit, 0xF6), monitor.peek(unit, 0xF7)), (0, 0))

    def test_the_boot_window_bit_is_the_one_that_keeps_the_top_page_showing(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        monitor.poke(unit, monitor.CONTROL, int(self.held["bootVisible"], 16))

        # Assert
        self.assertEqual(monitor.peek(unit, 0xFFFE), 0xC0)

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

    def test_there_are_as_many_counters_as_the_record_gives(self) -> None:
        # Arrange
        unit = a_unit()
        for timer in range(self.held["count"]):
            monitor.poke(unit, monitor.FIRST_DIVIDER + timer, 1)
        monitor.poke(unit, monitor.CONTROL, 0x80 | (1 << self.held["count"]) - 1)

        # Act
        found = [monitor.tally(unit, one, reads=3, gap=300)[1] > 0 for one in named("counter")]

        # Assert
        self.assertEqual(found, [True] * self.held["count"])

    def test_the_counter_wraps_at_the_width_the_record_gives(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        ticks = (1 << self.held["counterBits"]) + 4
        unit = a_unit()
        written = monitor.start(unit, 0, divider=1)
        started = written - written % tick

        # Act
        found = monitor.counter_at(unit, 0, started + ticks * tick + tick // 2)

        # Assert
        self.assertEqual(found, 4)

    def test_a_divider_of_zero_divides_by_what_the_record_says(self) -> None:
        # Arrange
        period = self.held["dividerWhenZero"] * self.held["fastCyclesPerTick"]
        unit = a_unit()
        started = monitor.start(unit, 2, divider=0)

        # Act
        found = monitor.counter_at(unit, 2, started + 10 * period - 64)

        # Assert
        self.assertEqual(found, 9)

    def test_the_two_tick_costs_are_the_ones_measured(self) -> None:
        # Arrange
        unit = a_unit()

        # Act
        found = (
            monitor.timer_period(unit, 0, divider=1, gap=1500),
            monitor.timer_period(unit, 2, divider=1, gap=150),
        )

        # Assert
        self.assertEqual(
            [round(one) for one in found],
            [self.held["slowCyclesPerTick"], self.held["fastCyclesPerTick"]],
        )


def printed() -> dict[str, Any]:
    timers: dict[str, Any] = declared()["timers"]["printed"]
    return timers


def on_the_prescaler(cycle: int, period: int) -> int:
    return cycle - cycle % period


class PrintedTimerTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["timers"]

    def test_the_printed_rates_are_the_tick_costs_the_unit_spends(self) -> None:
        # Arrange
        rates = printed()["prescalerRates"]
        timing = printed()["instructionTime"]
        cycle = timing["shortestNanoseconds"] / timing["shortestCycles"]
        unit = a_unit()

        # Act
        found = (
            monitor.timer_period(unit, 0, divider=1, gap=1500),
            monitor.timer_period(unit, 2, divider=1, gap=150),
        )

        # Assert
        self.assertEqual(
            [round(one) for one in found],
            [round(1e9 / rates["slowHz"] / cycle), round(1e9 / rates["fastHz"] / cycle)],
        )

    def test_switching_a_timer_on_leaves_the_one_prescaler_running(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        drawn = printed()["onePrescaler"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=1), tick)

        # Act
        found = monitor.counter_at(unit, 0, started + tick + tick // 5)

        # Assert
        self.assertEqual((found, drawn["document"]), (1, "developmentManual"))

    def test_a_divider_lowered_below_the_stage_waits_for_the_stage_to_wrap(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        said = printed()["dividerMatch"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=8), tick)
        monitor.aim(unit, monitor.FIRST_DIVIDER)
        unit.run_for(started + 5 * tick + tick // 2 - unit.cycles - monitor.READ_LAG)
        monitor.store(unit, 3)

        # Act
        found = monitor.counter_at(unit, 0, started + 6 * tick + tick // 2)

        # Assert
        self.assertEqual((found, said["page"]), (0, "3-5-2"))

    def test_switching_a_timer_off_and_on_clears_both_of_its_counters(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        said = printed()["enableClears"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=4), tick)
        unit.run_for(started + 6 * tick - unit.cycles)
        monitor.switch(unit, 0, on=False)
        restarted = on_the_prescaler(monitor.switch(unit, 0, on=True), tick)

        # Act
        found = monitor.counter_at(unit, 0, restarted + 3 * tick + tick // 2)

        # Assert
        self.assertEqual((found, said["page"]), (0, "3-5-2"))

    def test_reading_a_counter_empties_it(self) -> None:
        # Arrange
        tick = self.held["slowCyclesPerTick"]
        said = printed()["readClears"]
        unit = a_unit()
        started = on_the_prescaler(monitor.start(unit, 0, divider=1), tick)
        first = monitor.counter_at(unit, 0, started + 3 * tick + tick // 2)

        # Act
        second = monitor.fetch(unit)

        # Assert
        self.assertEqual((first, second, said["page"]), (3, 0, "3-5-2"))

    def test_a_reset_stops_every_timer(self) -> None:
        # Arrange
        said = printed()["resetStops"]
        drawn = declared()["control"]["printed"]["whenReset"]
        unit = a_unit()
        for timer in range(3):
            monitor.poke(unit, monitor.FIRST_DIVIDER + timer, 1)
        monitor.poke(unit, monitor.CONTROL, monitor.BOOT_VISIBLE | 0x07)
        unit.reset()
        for timer in range(3):
            monitor.peek(unit, monitor.FIRST_COUNTER + timer)

        # Act
        found = [
            monitor.tally(unit, monitor.FIRST_COUNTER + timer, reads=3, gap=300)[1]
            for timer in range(3)
        ]

        # Assert
        self.assertEqual((found, said["page"], drawn["page"]), ([0, 0, 0], "3-5-2", "3-4-2"))


class PortTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.held = declared()["ports"]

    def test_a_console_index_wraps_after_as_many_ports_as_the_record_gives(self) -> None:
        # Arrange
        unit = a_unit()
        monitor.poke(unit, 0xF7, 0x3C)

        # Act
        found = unit.read(3 + self.held["count"])

        # Assert
        self.assertEqual(found, 0x3C)

    def test_each_one_holds_a_byte_per_direction(self) -> None:
        # Arrange
        unit = a_unit()
        unit.write(3, 0x11)

        # Act
        monitor.poke(unit, 0xF7, 0x22)

        # Assert
        self.assertEqual(len({monitor.fetch(unit), unit.read(3)}), self.held["bytesPerPort"])


if __name__ == "__main__":
    unittest.main()
