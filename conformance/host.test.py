import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance.host import Host
from ssmp import Chip

ROM = bytes(range(256)) * 512


def a_host(rom: bytes = ROM) -> Host:
    return Host(rom, Chip("ssmp", boot=bytes(64), seed=7).reset())


class MemoryMapTest(unittest.TestCase):
    def test_work_ram_holds_what_was_written_in_its_own_banks(self) -> None:
        # Arrange
        host = a_host()

        # Act
        host.write8(0x7F1234, 0x5A)

        # Assert
        self.assertEqual(host.read8(0x7F1234), 0x5A)

    def test_the_low_page_of_a_system_bank_is_the_start_of_work_ram(self) -> None:
        # Arrange
        host = a_host()

        # Act
        host.write8(0x800123, 0xA5)

        # Assert
        self.assertEqual(host.read8(0x7E0123), 0xA5)

    def test_the_upper_half_of_a_bank_is_the_rom_decoded_as_lorom(self) -> None:
        # Arrange
        host = a_host()

        # Act
        read = host.read8(0x818001)

        # Assert
        self.assertEqual(read, ROM[0x8001])

    def test_a_write_to_rom_changes_nothing(self) -> None:
        # Arrange
        host = a_host()

        # Act
        host.write8(0x008000, 0xEE)

        # Assert
        self.assertEqual(host.read8(0x008000), ROM[0])

    def test_a_bank_with_no_system_area_reads_zero_and_ignores_writes(self) -> None:
        # Arrange
        host = a_host()

        # Act
        host.write8(0x400010, 0x77)

        # Assert
        self.assertEqual((host.read8(0x400010), host.read8(0x000010)), (0, 0))

    def test_an_unmodelled_register_reads_zero(self) -> None:
        # Arrange
        host = a_host()

        # Act
        read = host.read8(0x002100)

        # Assert
        self.assertEqual(read, 0)


class AudioPortTest(unittest.TestCase):
    def test_a_read_of_a_port_is_what_the_unit_shows_the_host(self) -> None:
        # Arrange
        host = a_host()

        # Act
        read = [host.read8(0x002140 + index) for index in range(4)]

        # Assert
        self.assertEqual(read, [host.unit.read(index) for index in range(4)])

    def test_the_ports_repeat_every_four_bytes_up_to_2180(self) -> None:
        # Arrange
        host = a_host()

        # Act
        read = host.read8(0x00217D)

        # Assert
        self.assertEqual(read, host.unit.read(1))

    def test_a_write_to_a_port_reaches_the_unit(self) -> None:
        # Arrange
        host = a_host()

        # Act
        host.write8(0x002142, 0x3C)

        # Assert
        self.assertEqual(host.unit.space.ports.unit_reads(2), 0x3C)


class StatusTest(unittest.TestCase):
    def test_the_blanking_flag_alternates_on_every_read(self) -> None:
        # Arrange
        host = a_host()

        # Act
        read = [host.read8(0x004212) for _ in range(3)]

        # Assert
        self.assertEqual(read, [0x80, 0x00, 0x80])

    def test_the_vblank_flag_is_raised_and_cleared_by_the_read_beside_the_version(self) -> None:
        # Arrange
        host = a_host()

        # Act
        read = [host.read8(0x004210) for _ in range(3)]

        # Assert
        self.assertEqual(read, [0x82, 0x02, 0x82])


class ArithmeticTest(unittest.TestCase):
    def test_a_multiply_leaves_its_product_in_4216(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x004202, 200)

        # Act
        host.write8(0x004203, 100)

        # Assert
        self.assertEqual(host.read8(0x004216) | host.read8(0x004217) << 8, 20000)

    def test_a_divide_leaves_quotient_and_remainder(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x004204, 0x39)
        host.write8(0x004205, 0x30)

        # Act
        host.write8(0x004206, 10)

        # Assert
        quotient = host.read8(0x004214) | host.read8(0x004215) << 8
        remainder = host.read8(0x004216) | host.read8(0x004217) << 8
        self.assertEqual((quotient, remainder), (1234, 5))

    def test_a_divide_by_zero_gives_all_ones_and_keeps_the_dividend(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x004204, 0x34)
        host.write8(0x004205, 0x12)

        # Act
        host.write8(0x004206, 0)

        # Assert
        quotient = host.read8(0x004214) | host.read8(0x004215) << 8
        remainder = host.read8(0x004216) | host.read8(0x004217) << 8
        self.assertEqual((quotient, remainder), (0xFFFF, 0x1234))


class VideoMemoryTest(unittest.TestCase):
    def test_low_byte_writes_step_the_address_when_the_increment_is_low(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x002115, 0x00)
        host.write8(0x002116, 0x10)
        host.write8(0x002117, 0x00)

        # Act
        host.write8(0x002118, 0x41)
        host.write8(0x002118, 0x42)

        # Assert
        host.write8(0x002116, 0x10)
        self.assertEqual(host.read8(0x002139), 0x41)

    def test_high_byte_writes_step_by_thirty_two_when_asked(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x002115, 0x81)
        host.write8(0x002116, 0x00)
        host.write8(0x002117, 0x00)

        # Act
        host.write8(0x002118, 0x48)
        host.write8(0x002119, 0x00)
        host.write8(0x002118, 0x49)
        host.write8(0x002119, 0x00)

        # Assert
        self.assertEqual(host.screen(), "H\nI")

    def test_the_screen_is_read_from_the_tilemap_base_as_ascii(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x002107, 0x04)
        host.write8(0x002115, 0x00)
        host.write8(0x002116, 0x00)
        host.write8(0x002117, 0x04)

        # Act
        for letter in b"OK\x01!":
            host.write8(0x002118, letter)

        # Assert
        self.assertEqual(host.screen(), "OK !")

    def test_the_line_last_written_is_the_one_named(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x002115, 0x00)
        host.write8(0x002116, 0x40)
        host.write8(0x002117, 0x00)

        # Act
        for letter in b" CPU/tset ":
            host.write8(0x002118, letter)

        # Assert
        self.assertEqual(host.current_line(), "CPU/tset")


class DmaTest(unittest.TestCase):
    def test_a_transfer_from_work_ram_fills_video_memory(self) -> None:
        # Arrange
        host = a_host()
        for offset, letter in enumerate(b"GO"):
            host.write8(0x7E0100 + offset, letter)
        host.write8(0x002115, 0x00)
        host.write8(0x002116, 0x00)
        host.write8(0x002117, 0x00)
        for register, value in enumerate((0x00, 0x18, 0x00, 0x01, 0x7E, 0x02, 0x00)):
            host.write8(0x004300 + register, value)

        # Act
        host.write8(0x00420B, 0x01)

        # Assert
        self.assertEqual((host.screen(), host.read8(0x004305)), ("GO", 0))

    def test_a_fixed_source_repeats_one_byte(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x7E0200, 0x5A)
        host.write8(0x002115, 0x00)
        for register, value in enumerate((0x08, 0x18, 0x00, 0x02, 0x7E, 0x03, 0x00)):
            host.write8(0x004310 + register, value)

        # Act
        host.write8(0x00420B, 0x02)

        # Assert
        self.assertEqual(host.screen(), "ZZZ")

    def test_a_transfer_to_work_ram_reads_the_register(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x002115, 0x80)
        host.write8(0x002118, 0x5A)
        for register, value in enumerate((0x80, 0x39, 0x00, 0x03, 0x7E, 0x02, 0x00)):
            host.write8(0x004320 + register, value)

        # Act
        host.write8(0x00420B, 0x04)

        # Assert
        self.assertEqual((host.read8(0x7E0300), host.read8(0x7E0301)), (0x5A, 0x5A))

    def test_a_decrementing_two_register_transfer_alternates_its_targets(self) -> None:
        # Arrange
        host = a_host()
        host.write8(0x7E0401, 0x41)
        host.write8(0x7E0400, 0x00)
        host.write8(0x002115, 0x80)
        for register, value in enumerate((0x11, 0x18, 0x01, 0x04, 0x7E, 0x02, 0x00)):
            host.write8(0x004330 + register, value)

        # Act
        host.write8(0x00420B, 0x08)

        # Assert
        self.assertEqual(host.screen(), "A")

    def test_an_unknown_pattern_writes_one_register_and_a_zero_count_is_65536(self) -> None:
        # Arrange
        host = a_host()
        for register, value in enumerate((0x07, 0x80, 0x00, 0x00, 0x7E, 0x00, 0x00)):
            host.write8(0x004340 + register, value)

        # Act
        host.write8(0x00420B, 0x10)

        # Assert
        self.assertEqual(host.read8(0x004340 + 5) | host.read8(0x004346) << 8, 0)

    def test_the_channel_registers_read_back(self) -> None:
        # Arrange
        host = a_host()

        # Act
        host.write8(0x004372, 0x9C)

        # Assert
        self.assertEqual(host.read8(0x004372), 0x9C)


if __name__ == "__main__":
    unittest.main()
