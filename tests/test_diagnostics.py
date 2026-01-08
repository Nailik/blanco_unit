"""Tests for the Blanco Unit diagnostics."""

from unittest.mock import MagicMock

from custom_components.blanco_unit.const import CONF_MAC, CONF_PIN
from custom_components.blanco_unit.data import (
    BlancoUnitData,
    BlancoUnitIdentity,
    BlancoUnitSettings,
    BlancoUnitStatus,
    BlancoUnitSystemInfo,
    BlancoUnitWifiInfo,
)
from custom_components.blanco_unit.diagnostics import async_get_config_entry_diagnostics
from homeassistant.core import HomeAssistant


async def test_async_get_config_entry_diagnostics(hass: HomeAssistant) -> None:
    """Test async_get_config_entry_diagnostics returns proper data."""
    # Create mock coordinator with data
    mock_coordinator = MagicMock()
    mock_coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
        system_info=BlancoUnitSystemInfo(
            sw_ver_comm_con="1.0.0",
            sw_ver_elec_con="1.0.0",
            sw_ver_main_con="1.0.0",
            dev_name="Test Device",
            reset_cnt=5,
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

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_PIN: 12345,
        "conf_name": "Test Device",
    }
    mock_entry.runtime_data = mock_coordinator

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_entry)

    # Verify structure
    assert "config_entry_data" in diagnostics
    assert "blanco:unit_data" in diagnostics

    # Verify coordinator data is included
    assert diagnostics["blanco:unit_data"] == mock_coordinator.data

    # Verify config entry data is present
    assert diagnostics["config_entry_data"] is not None


async def test_diagnostics_redacts_sensitive_data(hass: HomeAssistant) -> None:
    """Test that diagnostics redacts sensitive data like MAC and PIN."""
    # Create mock coordinator with data
    mock_coordinator = MagicMock()
    mock_coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
    )

    # Create mock config entry with sensitive data
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_PIN: 12345,
        "conf_name": "Test Device",
    }
    mock_entry.runtime_data = mock_coordinator

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_entry)

    # Verify sensitive data is redacted
    assert diagnostics["config_entry_data"][CONF_MAC] == "**REDACTED**"
    assert diagnostics["config_entry_data"][CONF_PIN] == "**REDACTED**"

    # Verify non-sensitive data is not redacted
    assert diagnostics["config_entry_data"]["conf_name"] == "Test Device"


async def test_diagnostics_with_partial_data(hass: HomeAssistant) -> None:
    """Test diagnostics when coordinator has partial data."""
    # Create mock coordinator with minimal data
    mock_coordinator = MagicMock()
    mock_coordinator.data = BlancoUnitData(
        connected=False,
        available=False,
        device_id="test_device_id",
        system_info=None,
        settings=None,
        status=None,
        identity=None,
        wifi_info=None,
    )

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_PIN: 12345,
    }
    mock_entry.runtime_data = mock_coordinator

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_entry)

    # Verify structure exists
    assert "config_entry_data" in diagnostics
    assert "blanco:unit_data" in diagnostics

    # Verify partial data is included
    assert diagnostics["blanco:unit_data"].connected is False
    assert diagnostics["blanco:unit_data"].available is False
    assert diagnostics["blanco:unit_data"].system_info is None


async def test_diagnostics_includes_all_data_fields(hass: HomeAssistant) -> None:
    """Test that diagnostics includes all data fields."""
    # Create mock coordinator with complete data
    mock_coordinator = MagicMock()
    mock_coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
        system_info=BlancoUnitSystemInfo(
            sw_ver_comm_con="1.0.0",
            sw_ver_elec_con="1.1.0",
            sw_ver_main_con="1.2.0",
            dev_name="Test Device",
            reset_cnt=10,
        ),
        settings=BlancoUnitSettings(
            calib_still_wtr=6,
            calib_soda_wtr=7,
            filter_life_tm=400,
            post_flush_quantity=150,
            set_point_cooling=8,
            wtr_hardness=6,
        ),
        status=BlancoUnitStatus(
            tap_state=1,
            filter_rest=85,
            co2_rest=90,
            wtr_disp_active=True,
            firm_upd_avlb=True,
            set_point_cooling=8,
            clean_mode_state=1,
            err_bits=2,
        ),
        identity=BlancoUnitIdentity(
            serial_no="789012",
            service_code="GHIJKL",
        ),
        wifi_info=BlancoUnitWifiInfo(
            cloud_connect=False,
            ssid="MyNetwork",
            signal=-60,
            ip="10.0.0.50",
            ble_mac="BB:CC:DD:EE:FF:00",
            wifi_mac="CC:DD:EE:FF:00:11",
            gateway="10.0.0.1",
            gateway_mac="DD:EE:FF:00:11:22",
            subnet="255.255.255.0",
        ),
    )

    # Create mock config entry
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_MAC: "BB:CC:DD:EE:FF:00",
        CONF_PIN: 54321,
    }
    mock_entry.runtime_data = mock_coordinator

    # Get diagnostics
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_entry)

    # Verify all data fields are present
    data = diagnostics["blanco:unit_data"]
    assert data.connected is True
    assert data.available is True
    assert data.device_id == "test_device_id"

    # System info
    assert data.system_info.sw_ver_comm_con == "1.0.0"
    assert data.system_info.sw_ver_elec_con == "1.1.0"
    assert data.system_info.sw_ver_main_con == "1.2.0"
    assert data.system_info.dev_name == "Test Device"
    assert data.system_info.reset_cnt == 10

    # Settings
    assert data.settings.calib_still_wtr == 6
    assert data.settings.calib_soda_wtr == 7
    assert data.settings.filter_life_tm == 400
    assert data.settings.post_flush_quantity == 150
    assert data.settings.set_point_cooling == 8
    assert data.settings.wtr_hardness == 6

    # Status
    assert data.status.tap_state == 1
    assert data.status.filter_rest == 85
    assert data.status.co2_rest == 90
    assert data.status.wtr_disp_active is True
    assert data.status.firm_upd_avlb is True
    assert data.status.set_point_cooling == 8
    assert data.status.clean_mode_state == 1
    assert data.status.err_bits == 2

    # Identity
    assert data.identity.serial_no == "789012"
    assert data.identity.service_code == "GHIJKL"

    # WiFi info
    assert data.wifi_info.cloud_connect is False
    assert data.wifi_info.ssid == "MyNetwork"
    assert data.wifi_info.signal == -60
    assert data.wifi_info.ip == "10.0.0.50"
    assert data.wifi_info.ble_mac == "BB:CC:DD:EE:FF:00"
    assert data.wifi_info.wifi_mac == "CC:DD:EE:FF:00:11"
    assert data.wifi_info.gateway == "10.0.0.1"
    assert data.wifi_info.gateway_mac == "DD:EE:FF:00:11:22"
    assert data.wifi_info.subnet == "255.255.255.0"
