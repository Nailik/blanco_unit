"""Tests for the Blanco Unit binary sensor entities."""

from unittest.mock import MagicMock

import pytest

from custom_components.blanco_unit.binary_sensor import (
    CloudConnectBinarySensor,
    ConnectionBinarySensor,
    FirmwareUpdateBinarySensor,
    WaterDispensingBinarySensor,
    async_setup_entry,
)
from custom_components.blanco_unit.data import (
    BlancoUnitData,
    BlancoUnitStatus,
    BlancoUnitWifiInfo,
)
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
        status=BlancoUnitStatus(
            tap_state=1,
            filter_rest=85,
            co2_rest=90,
            wtr_disp_active=True,
            firm_upd_avlb=True,
            set_point_cooling=7,
            clean_mode_state=0,
            err_bits=0,
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
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    return entry


async def test_async_setup_entry(
    hass: HomeAssistant, mock_config_entry, mock_coordinator
) -> None:
    """Test async_setup_entry creates all binary sensors."""
    mock_config_entry.runtime_data = mock_coordinator
    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Verify all 4 binary sensors were added
    assert len(entities_added) == 4

    # Verify sensor types
    sensor_types = [type(entity).__name__ for entity in entities_added]
    assert "ConnectionBinarySensor" in sensor_types
    assert "WaterDispensingBinarySensor" in sensor_types
    assert "FirmwareUpdateBinarySensor" in sensor_types
    assert "CloudConnectBinarySensor" in sensor_types


async def test_connection_binary_sensor(mock_coordinator) -> None:
    """Test ConnectionBinarySensor."""
    sensor = ConnectionBinarySensor(mock_coordinator)

    assert sensor.is_on is True
    assert sensor.unique_id == "connection"
    assert sensor.icon == "mdi:bluetooth-connect"


async def test_connection_binary_sensor_disconnected(mock_coordinator) -> None:
    """Test ConnectionBinarySensor when disconnected."""
    mock_coordinator.data.connected = False
    sensor = ConnectionBinarySensor(mock_coordinator)

    assert sensor.is_on is False
    assert sensor.icon == "mdi:bluetooth-off"


async def test_water_dispensing_binary_sensor(mock_coordinator) -> None:
    """Test WaterDispensingBinarySensor."""
    sensor = WaterDispensingBinarySensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.is_on is True
    assert sensor.unique_id == "water_dispensing"


async def test_water_dispensing_binary_sensor_not_active(mock_coordinator) -> None:
    """Test WaterDispensingBinarySensor when not active."""
    mock_coordinator.data.status.wtr_disp_active = False
    sensor = WaterDispensingBinarySensor(mock_coordinator)

    assert sensor.is_on is False


async def test_water_dispensing_binary_sensor_unavailable(mock_coordinator) -> None:
    """Test WaterDispensingBinarySensor when status is None."""
    mock_coordinator.data.status = None
    sensor = WaterDispensingBinarySensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.is_on is None


async def test_firmware_update_binary_sensor(mock_coordinator) -> None:
    """Test FirmwareUpdateBinarySensor."""
    sensor = FirmwareUpdateBinarySensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.is_on is True
    assert sensor.unique_id == "firmware_update"


async def test_firmware_update_binary_sensor_not_available(mock_coordinator) -> None:
    """Test FirmwareUpdateBinarySensor when update not available."""
    mock_coordinator.data.status.firm_upd_avlb = False
    sensor = FirmwareUpdateBinarySensor(mock_coordinator)

    assert sensor.is_on is False


async def test_firmware_update_binary_sensor_unavailable(mock_coordinator) -> None:
    """Test FirmwareUpdateBinarySensor when status is None."""
    mock_coordinator.data.status = None
    sensor = FirmwareUpdateBinarySensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.is_on is None


async def test_cloud_connect_binary_sensor(mock_coordinator) -> None:
    """Test CloudConnectBinarySensor."""
    sensor = CloudConnectBinarySensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.is_on is True
    assert sensor.unique_id == "cloud_connection"


async def test_cloud_connect_binary_sensor_disconnected(mock_coordinator) -> None:
    """Test CloudConnectBinarySensor when not connected to cloud."""
    mock_coordinator.data.wifi_info.cloud_connect = False
    sensor = CloudConnectBinarySensor(mock_coordinator)

    assert sensor.is_on is False


async def test_cloud_connect_binary_sensor_unavailable(mock_coordinator) -> None:
    """Test CloudConnectBinarySensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = CloudConnectBinarySensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.is_on is None


async def test_binary_sensor_when_data_unavailable(mock_coordinator) -> None:
    """Test binary sensor when data is unavailable."""
    mock_coordinator.data.available = False
    sensor = ConnectionBinarySensor(mock_coordinator)

    assert sensor.available is False


async def test_connection_binary_sensor_icon_property(mock_coordinator) -> None:
    """Test ConnectionBinarySensor icon property changes."""
    sensor = ConnectionBinarySensor(mock_coordinator)

    # Connected
    mock_coordinator.data.connected = True
    assert sensor.icon == "mdi:bluetooth-connect"

    # Disconnected
    mock_coordinator.data.connected = False
    assert sensor.icon == "mdi:bluetooth-off"
