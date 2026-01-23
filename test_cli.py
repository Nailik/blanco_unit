#!/usr/bin/env python3
"""CLI tool for testing Blanco Unit Bluetooth client functionality."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import bleak
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends import get_default_backend


# Import client with workaround for relative imports
import importlib.util
import os

# Create a proper package structure in sys.modules to support relative imports
sys.path.insert(0, "custom_components")

# Load const module
const_path = os.path.join("custom_components", "blanco_unit", "const.py")
const_spec = importlib.util.spec_from_file_location("blanco_unit.const", const_path)
const_module = importlib.util.module_from_spec(const_spec)
sys.modules["blanco_unit.const"] = const_module
const_spec.loader.exec_module(const_module)

# Load data module
data_path = os.path.join("custom_components", "blanco_unit", "data.py")
data_spec = importlib.util.spec_from_file_location("blanco_unit.data", data_path)
data_module = importlib.util.module_from_spec(data_spec)
sys.modules["blanco_unit.data"] = data_module
data_spec.loader.exec_module(data_module)

# Create a fake package module for blanco_unit
import types
blanco_unit_package = types.ModuleType("blanco_unit")
blanco_unit_package.__path__ = [os.path.join("custom_components", "blanco_unit")]
blanco_unit_package.__package__ = "blanco_unit"
sys.modules["blanco_unit"] = blanco_unit_package

# Load client module with package context
client_path = os.path.join("custom_components", "blanco_unit", "client.py")
client_spec = importlib.util.spec_from_file_location("blanco_unit.client", client_path,
                                                       submodule_search_locations=[os.path.join("custom_components", "blanco_unit")])
client_module = importlib.util.module_from_spec(client_spec)
client_module.__package__ = "blanco_unit"
sys.modules["blanco_unit.client"] = client_module
client_spec.loader.exec_module(client_module)

BlancoUnitBluetoothClient = client_module.BlancoUnitBluetoothClient


class BlancoUnitCLI:
    """Interactive CLI for testing Blanco Unit Bluetooth client."""

    def __init__(self) -> None:
        """Initialize the CLI."""
        self.client: BlancoUnitBluetoothClient | None = None
        self.device: BLEDevice | None = None
        self.pin: str = ""
        self.is_connected: bool = False

    def print_header(self) -> None:
        """Print CLI header with version info."""
        print("=" * 70)
        print("Blanco Unit Bluetooth Client Test CLI")
        print("=" * 70)

        # Get bleak version
        try:
            bleak_version = bleak.__version__
        except AttributeError:
            try:
                import importlib.metadata
                bleak_version = importlib.metadata.version("bleak")
            except Exception:  # noqa: BLE001
                bleak_version = "Unknown"

        print(f"Bleak Version: {bleak_version}")
        print(f"Python Version: {sys.version.split()[0]}")
        print(f"Platform: {sys.platform}")

        # Detect actual BLE backend from bleak
        try:
            backend = get_default_backend()
            backend_str = str(backend)

            # Determine friendly name and details based on backend enum
            if "BLUEZDBUS" in backend_str or "BlueZ" in backend_str:
                friendly_name = "BlueZ (Linux D-Bus)"
                backend_module = "bleak.backends.bluezdbus"
            elif "CORE_BLUETOOTH" in backend_str or "CoreBluetooth" in backend_str:
                friendly_name = "CoreBluetooth (macOS/iOS)"
                backend_module = "bleak.backends.corebluetooth"
            elif "DOTNET" in backend_str or "WinRT" in backend_str:
                friendly_name = "Windows Runtime BLE"
                backend_module = "bleak.backends.winrt"
            else:
                friendly_name = backend_str
                backend_module = "Unknown"

            print(f"BLE: {backend_str}")
            print(f"BLE Backend: {friendly_name}")
            print(f"Backend Enum: {backend}")
            print(f"Backend Module: {backend_module}")
        except Exception as e:  # noqa: BLE001
            print(f"BLE Backend: Could not detect ({e})")

        print()

    async def discover_devices(self) -> list[BLEDevice]:
        """Discover BLE devices."""
        print("Scanning for BLE devices...")
        print("(This may take a few seconds)")
        print()

        # Use discovered_devices_and_advertisement_data to get RSSI
        scanner = BleakScanner()
        await scanner.start()
        await asyncio.sleep(10.0)
        await scanner.stop()

        # Get devices with advertisement data
        # discovered_devices_and_advertisement_data is dict[str, tuple[BLEDevice, AdvertisementData]]
        self.devices_with_advdata = scanner.discovered_devices_and_advertisement_data
        devices = [device for device, _ in self.devices_with_advdata.values()]
        return devices

    def display_devices(self, devices: list[BLEDevice]) -> None:
        """Display discovered devices."""
        print(f"Found {len(devices)} devices:")
        print()
        for idx, device in enumerate(devices, 1):
            name = device.name or "Unknown"
            print(f"{idx}. {name}")
            print(f"   Address: {device.address}")

            # Get RSSI from advertisement data if available
            if hasattr(self, 'devices_with_advdata') and device.address in self.devices_with_advdata:
                _, adv_data = self.devices_with_advdata[device.address]
                rssi = adv_data.rssi
                print(f"   RSSI: {rssi} dBm")

            print()

    def select_device(self, devices: list[BLEDevice]) -> BLEDevice | None:
        """Let user select a device."""
        while True:
            try:
                choice = input("Select device number (or 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    return None

                idx = int(choice) - 1
                if 0 <= idx < len(devices):
                    return devices[idx]

                print(f"Invalid selection. Please choose 1-{len(devices)}")
            except ValueError:
                print("Please enter a valid number or 'q' to quit")

    def get_pin(self) -> str:
        """Get PIN from user."""
        while True:
            pin = input("Enter 5-digit PIN: ").strip()
            if len(pin) == 5 and pin.isdigit():
                return pin
            print("PIN must be exactly 5 digits. Please try again.")

    def connection_callback(self, connected: bool) -> None:
        """Handle connection state changes."""
        self.is_connected = connected
        if connected:
            print("✓ Connected to device")
        else:
            print("✗ Disconnected from device")

    async def connect_to_device(self) -> bool:
        """Connect to the selected device."""
        if not self.device or not self.pin:
            print("Error: Device or PIN not set")
            return False

        print(f"\nConnecting to {self.device.name or 'Unknown'} ({self.device.address})...")

        try:
            self.client = BlancoUnitBluetoothClient(
                pin=self.pin,
                device=self.device,
                connection_callback=self.connection_callback,
            )

            # Test connection by getting system info
            print("Authenticating and retrieving system info...")
            info = await self.client.get_system_info()

            print("\n" + "=" * 70)
            print("CONNECTION SUCCESSFUL!")
            print("=" * 70)
            print(f"Device Name: {info.dev_name}")
            print(f"Device ID: {self.client.device_id}")
            print(f"Main Controller FW: {info.sw_ver_main_con}")
            print(f"Electronic Controller FW: {info.sw_ver_elec_con}")
            print(f"Communication Controller FW: {info.sw_ver_comm_con}")
            print(f"Reset Count: {info.reset_cnt}")
            print("=" * 70)
            print()

            return True

        except Exception as e:
            print(f"\n✗ Connection failed: {e}")
            return False

    async def show_menu(self) -> None:
        """Show main menu and handle user input."""
        while True:
            print("\n" + "=" * 70)
            print("MAIN MENU")
            print("=" * 70)
            print("Read Operations:")
            print("  1. Get System Info")
            print("  2. Get Settings")
            print("  3. Get Status")
            print("  4. Get Device Identity")
            print("  5. Get WiFi Info")
            print()
            print("Write Operations:")
            print("  6. Set Temperature")
            print("  7. Set Water Hardness")
            print("  8. Dispense Water")
            print("  9. Set Still Water Calibration")
            print(" 10. Set Soda Water Calibration")
            print(" 11. Change PIN")
            print()
            print("Other:")
            print("  0. Disconnect and Exit")
            print("=" * 70)

            choice = input("\nSelect option: ").strip()

            try:
                if choice == "0":
                    break
                elif choice == "1":
                    await self.test_get_system_info()
                elif choice == "2":
                    await self.test_get_settings()
                elif choice == "3":
                    await self.test_get_status()
                elif choice == "4":
                    await self.test_get_device_identity()
                elif choice == "5":
                    await self.test_get_wifi_info()
                elif choice == "6":
                    await self.test_set_temperature()
                elif choice == "7":
                    await self.test_set_water_hardness()
                elif choice == "8":
                    await self.test_dispense_water()
                elif choice == "9":
                    await self.test_set_calibration_still()
                elif choice == "10":
                    await self.test_set_calibration_soda()
                elif choice == "11":
                    await self.test_change_pin()
                else:
                    print("Invalid option. Please try again.")
            except Exception as e:
                print(f"\n✗ Error: {e}")
                import traceback
                traceback.print_exc()

    # Test methods for each function

    async def test_get_system_info(self) -> None:
        """Test get_system_info()."""
        print("\n--- Get System Info ---")
        info = await self.client.get_system_info()
        print(f"Device Name: {info.dev_name}")
        print(f"Main Controller FW: {info.sw_ver_main_con}")
        print(f"Electronic Controller FW: {info.sw_ver_elec_con}")
        print(f"Communication Controller FW: {info.sw_ver_comm_con}")
        print(f"Reset Count: {info.reset_cnt}")

    async def test_get_settings(self) -> None:
        """Test get_settings()."""
        print("\n--- Get Settings ---")
        settings = await self.client.get_settings()
        print(f"Still Water Calibration: {settings.calib_still_wtr}")
        print(f"Soda Water Calibration: {settings.calib_soda_wtr}")
        print(f"Filter Life Time: {settings.filter_life_tm}")
        print(f"Post Flush Quantity: {settings.post_flush_quantity}")
        print(f"Cooling Setpoint: {settings.set_point_cooling}°C")
        print(f"Water Hardness: {settings.wtr_hardness}")

    async def test_get_status(self) -> None:
        """Test get_status()."""
        print("\n--- Get Status ---")
        status = await self.client.get_status()
        print(f"Tap State: {status.tap_state}")
        print(f"Filter Rest: {status.filter_rest}%")
        print(f"CO2 Rest: {status.co2_rest}%")
        print(f"Water Dispense Active: {status.wtr_disp_active}")
        print(f"Firmware Update Available: {status.firm_upd_avlb}")
        print(f"Cooling Setpoint: {status.set_point_cooling}°C")
        print(f"Clean Mode State: {status.clean_mode_state}")
        print(f"Error Bits: {status.err_bits}")

    async def test_get_device_identity(self) -> None:
        """Test get_device_identity()."""
        print("\n--- Get Device Identity ---")
        identity = await self.client.get_device_identity()
        print(f"Serial Number: {identity.serial_no}")
        print(f"Service Code: {identity.service_code}")

    async def test_get_wifi_info(self) -> None:
        """Test get_wifi_info()."""
        print("\n--- Get WiFi Info ---")
        wifi = await self.client.get_wifi_info()
        print(f"Cloud Connected: {wifi.cloud_connect}")
        print(f"SSID: {wifi.ssid}")
        print(f"Signal Strength: {wifi.signal}")
        print(f"IP Address: {wifi.ip}")
        print(f"BLE MAC: {wifi.ble_mac}")
        print(f"WiFi MAC: {wifi.wifi_mac}")
        print(f"Gateway: {wifi.gateway}")
        print(f"Gateway MAC: {wifi.gateway_mac}")
        print(f"Subnet: {wifi.subnet}")

    async def test_set_temperature(self) -> None:
        """Test set_temperature()."""
        print("\n--- Set Temperature ---")
        print("Valid range: 4-10°C")

        while True:
            try:
                temp = input("Enter temperature (°C): ").strip()
                temp_int = int(temp)

                if 4 <= temp_int <= 10:
                    result = await self.client.set_temperature(temp_int)
                    if result:
                        print(f"✓ Temperature set to {temp_int}°C successfully")
                    else:
                        print("✗ Failed to set temperature")
                    break
                else:
                    print("Temperature must be between 4 and 10°C")
            except ValueError:
                print("Please enter a valid number")

    async def test_set_water_hardness(self) -> None:
        """Test set_water_hardness()."""
        print("\n--- Set Water Hardness ---")
        print("Valid range: 1-9")

        while True:
            try:
                level = input("Enter hardness level: ").strip()
                level_int = int(level)

                if 1 <= level_int <= 9:
                    result = await self.client.set_water_hardness(level_int)
                    if result:
                        print(f"✓ Water hardness set to level {level_int} successfully")
                    else:
                        print("✗ Failed to set water hardness")
                    break
                else:
                    print("Hardness level must be between 1 and 9")
            except ValueError:
                print("Please enter a valid number")

    async def test_dispense_water(self) -> None:
        """Test dispense_water()."""
        print("\n--- Dispense Water ---")
        print("Amount: 100-1500ml (multiples of 100)")
        print("CO2 Intensity: 1=still, 2=medium, 3=high")

        while True:
            try:
                amount = input("Enter amount (ml): ").strip()
                amount_int = int(amount)

                if not (100 <= amount_int <= 1500 and amount_int % 100 == 0):
                    print("Amount must be 100-1500ml in multiples of 100")
                    continue

                co2 = input("Enter CO2 intensity (1-3): ").strip()
                co2_int = int(co2)

                if co2_int not in (1, 2, 3):
                    print("CO2 intensity must be 1, 2, or 3")
                    continue

                confirm = input(f"Dispense {amount_int}ml with CO2 level {co2_int}? (y/n): ").strip().lower()
                if confirm == 'y':
                    result = await self.client.dispense_water(amount_int, co2_int)
                    if result:
                        print(f"✓ Dispensing started successfully")
                    else:
                        print("✗ Failed to start dispensing")
                break

            except ValueError:
                print("Please enter valid numbers")

    async def test_set_calibration_still(self) -> None:
        """Test set_calibration_still()."""
        print("\n--- Set Still Water Calibration ---")

        try:
            amount = input("Enter calibration amount: ").strip()
            amount_int = int(amount)

            result = await self.client.set_calibration_still(amount_int)
            if result:
                print(f"✓ Still water calibration set to {amount_int} successfully")
            else:
                print("✗ Failed to set calibration")
        except ValueError:
            print("Please enter a valid number")

    async def test_set_calibration_soda(self) -> None:
        """Test set_calibration_soda()."""
        print("\n--- Set Soda Water Calibration ---")

        try:
            amount = input("Enter calibration amount: ").strip()
            amount_int = int(amount)

            result = await self.client.set_calibration_soda(amount_int)
            if result:
                print(f"✓ Soda water calibration set to {amount_int} successfully")
            else:
                print("✗ Failed to set calibration")
        except ValueError:
            print("Please enter a valid number")

    async def test_change_pin(self) -> None:
        """Test change_pin()."""
        print("\n--- Change PIN ---")
        print("⚠️  WARNING: This will change the device PIN!")
        print("⚠️  Make sure you remember the new PIN!")

        confirm = input("Are you sure you want to change the PIN? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("PIN change cancelled")
            return

        while True:
            new_pin = input("Enter new 5-digit PIN: ").strip()
            if len(new_pin) == 5 and new_pin.isdigit():
                confirm_pin = input("Confirm new PIN: ").strip()
                if new_pin == confirm_pin:
                    result = await self.client.change_pin(new_pin)
                    if result:
                        print(f"✓ PIN changed successfully to {new_pin}")
                        self.pin = new_pin
                        print("⚠️  The CLI has updated its stored PIN")
                    else:
                        print("✗ Failed to change PIN")
                    break
                else:
                    print("PINs don't match. Please try again.")
            else:
                print("PIN must be exactly 5 digits. Please try again.")

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            print("\nDisconnecting...")
            await self.client.disconnect()
            print("Disconnected.")

    async def run(self) -> None:
        """Run the CLI application."""
        self.print_header()

        try:
            # Discover devices
            devices = await self.discover_devices()

            if not devices:
                print("No BLE devices found. Exiting.")
                return

            # Display and select device
            self.display_devices(devices)
            self.device = self.select_device(devices)

            if not self.device:
                print("No device selected. Exiting.")
                return

            print(f"\nSelected: {self.device.name or 'Unknown'} ({self.device.address})")

            # Get PIN
            self.pin = self.get_pin()

            # Connect to device
            if await self.connect_to_device():
                # Show menu and handle operations
                await self.show_menu()

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()


async def main() -> None:
    """Main entry point."""
    cli = BlancoUnitCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())