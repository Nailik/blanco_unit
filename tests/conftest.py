"""Common test fixtures for Blanco Unit tests."""

from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

# Import pytest plugins
pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    return enable_custom_integrations


@pytest.fixture
def expected_lingering_timers() -> bool:
    """Fixture used by pytest-homeassistant to decide if timers are ok."""
    return True


@pytest.fixture(autouse=True)
def mock_bluetooth(enable_bluetooth):
    """Auto-enable Bluetooth for all tests."""
    return enable_bluetooth


async def setup_integration(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


# Create fixtures for common test data
@pytest.fixture(name="mock_blanco_unit_data")
def mock_blanco_unit_data_fixture():
    """Return mock Blanco Unit data."""
    from custom_components.blanco_unit.data import (
        BlancoUnitData,
        BlancoUnitIdentity,
        BlancoUnitSettings,
        BlancoUnitStatus,
        BlancoUnitSystemInfo,
        BlancoUnitWifiInfo,
    )

    return BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
        system_info=BlancoUnitSystemInfo(
            sw_ver_comm_con="1.0.0",
            sw_ver_elec_con="1.0.0",
            sw_ver_main_con="1.0.0",
            dev_name="Test Device",
            reset_cnt=0,
        ),
        settings=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=5,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=7,
            wtr_hardness=5,
        ),
        status=BlancoUnitStatus(
            tap_state=0,
            filter_rest=100,
            co2_rest=100,
            wtr_disp_active=False,
            firm_upd_avlb=False,
            set_point_cooling=7,
            clean_mode_state=0,
            err_bits=0,
        ),
        identity=BlancoUnitIdentity(
            serial_no="123456",
            service_code="ABCDEF",
        ),
        wifi_info=BlancoUnitWifiInfo(
            cloud_connect=True,
            ssid="TestSSID",
            signal=-50,
            ip="192.168.1.100",
            ble_mac="AA:BB:CC:DD:EE:FF",
            wifi_mac="11:22:33:44:55:66",
            gateway="192.168.1.1",
            gateway_mac="AA:BB:CC:DD:EE:00",
            subnet="255.255.255.0",
        ),
    )


@pytest.fixture(name="mock_coordinator")
def mock_coordinator_fixture(mock_blanco_unit_data):
    """Return a mock coordinator."""
    from custom_components.blanco_unit.coordinator import BlancoUnitCoordinator

    coordinator = MagicMock(spec=BlancoUnitCoordinator)
    coordinator.data = mock_blanco_unit_data
    coordinator.name = "Test Blanco Unit"
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    coordinator.mac_address = "AA:BB:CC:DD:EE:FF"
    return coordinator
