"""Tests for the Blanco Unit sensor entities."""

from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.blanco_unit.const import CONF_MAC, CONF_NAME, CONF_PIN, DOMAIN
from custom_components.blanco_unit.data import (
    BlancoUnitData,
    BlancoUnitIdentity,
    BlancoUnitSettings,
    BlancoUnitStatus,
    BlancoUnitSystemInfo,
    BlancoUnitWifiInfo,
)
from custom_components.blanco_unit.sensor import (
    BLEMacSensor,
    CleanModeStateSensor,
    CO2RemainingSensor,
    DeviceNameSensor,
    DeviceTypeSensor,
    ErrorBitsSensor,
    FilterLifetimeSensor,
    FilterRemainingSensor,
    FirmwareCommSensor,
    FirmwareElecSensor,
    FirmwareMainSensor,
    GatewayMacSensor,
    GatewaySensor,
    IPAddressSensor,
    PostFlushQuantitySensor,
    ResetCountSensor,
    SerialNumberSensor,
    ServiceCodeSensor,
    SubnetSensor,
    TapStateSensor,
    WiFiMacSensor,
    WiFiSignalSensor,
    WiFiSSIDSensor,
    async_setup_entry,
)
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration  # noqa: TID251


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
        device_type=1,
        status=BlancoUnitStatus(
            tap_state=1,
            filter_rest=85,
            co2_rest=90,
            wtr_disp_active=True,
            firm_upd_avlb=False,
            set_point_cooling=7,
            clean_mode_state=0,
            err_bits=0,
        ),
        settings=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=5,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=7,
            wtr_hardness=5,
        ),
        system_info=BlancoUnitSystemInfo(
            sw_ver_comm_con="1.0.0",
            sw_ver_elec_con="1.1.0",
            sw_ver_main_con="1.2.0",
            dev_name="Test Device",
            reset_cnt=10,
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
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    return entry


async def test_all_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_blanco_unit_data,
    mock_bluetooth_device,
) -> None:
    """Test all entities."""
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "Test Blanco Unit",
            CONF_PIN: 12345,
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )

    with (
        patch("custom_components.blanco_unit.PLATFORMS", [Platform.SENSOR]),
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=mock_bluetooth_device,
        ),
    ):
        await setup_integration(hass, mock_config_entry)

        await snapshot_platform(
            hass, entity_registry, snapshot, mock_config_entry.entry_id
        )


@pytest.mark.parametrize(
    ("device_type", "expected_count"),
    [
        (1, 24),
        (2, 33),
    ],
)
async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_coordinator,
    device_type,
    expected_count,
) -> None:
    """Test async_setup_entry creates correct sensors."""
    mock_coordinator.data.device_type = device_type
    mock_config_entry.runtime_data = mock_coordinator
    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Verify all 24 sensors were added
    assert len(entities_added) == expected_count

    # Verify sensor types
    sensor_types = [type(entity).__name__ for entity in entities_added]
    assert "FilterRemainingSensor" in sensor_types
    assert "CO2RemainingSensor" in sensor_types
    assert "TapStateSensor" in sensor_types
    assert "CleanModeStateSensor" in sensor_types
    assert "ErrorBitsSensor" in sensor_types
    assert "FilterLifetimeSensor" in sensor_types
    assert "PostFlushQuantitySensor" in sensor_types
    assert "FirmwareMainSensor" in sensor_types
    assert "FirmwareCommSensor" in sensor_types
    assert "FirmwareElecSensor" in sensor_types
    assert "DeviceNameSensor" in sensor_types
    assert "ResetCountSensor" in sensor_types
    assert "DeviceTypeSensor" in sensor_types
    assert "SerialNumberSensor" in sensor_types
    assert "ServiceCodeSensor" in sensor_types
    assert "WiFiSSIDSensor" in sensor_types
    assert "WiFiSignalSensor" in sensor_types
    assert "IPAddressSensor" in sensor_types
    assert "BLEMacSensor" in sensor_types
    assert "WiFiMacSensor" in sensor_types
    assert "GatewaySensor" in sensor_types
    assert "GatewayMacSensor" in sensor_types
    assert "SubnetSensor" in sensor_types
    if device_type == 2:
        assert "BoilerTemp1Sensor" in sensor_types
        assert "BoilerTemp2Sensor" in sensor_types
        assert "CoolingTempSensor" in sensor_types
        assert "MainControllerStatusSensor" in sensor_types
        assert "ConnControllerStatusSensor" in sensor_types
        assert "MediumCarbonationRatioSensor" in sensor_types
        assert "ClassicCarbonationRatioSensor" in sensor_types
        assert "HeatingSetpointSensor" in sensor_types
        assert "HotWaterCalibrationSensor" in sensor_types


async def test_filter_remaining_sensor(mock_coordinator) -> None:
    """Test FilterRemainingSensor."""
    sensor = FilterRemainingSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 85
    assert sensor.unique_id == "filter_remaining"


async def test_filter_remaining_sensor_unavailable(mock_coordinator) -> None:
    """Test FilterRemainingSensor when status is None."""
    mock_coordinator.data.status = None
    sensor = FilterRemainingSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_co2_remaining_sensor(mock_coordinator) -> None:
    """Test CO2RemainingSensor."""
    sensor = CO2RemainingSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 90
    assert sensor.unique_id == "co2_remaining"


async def test_co2_remaining_sensor_unavailable(mock_coordinator) -> None:
    """Test CO2RemainingSensor when status is None."""
    mock_coordinator.data.status = None
    sensor = CO2RemainingSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_tap_state_sensor(mock_coordinator) -> None:
    """Test TapStateSensor."""
    sensor = TapStateSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 1
    assert sensor.unique_id == "tap_state"


async def test_tap_state_sensor_unavailable(mock_coordinator) -> None:
    """Test TapStateSensor when status is None."""
    mock_coordinator.data.status = None
    sensor = TapStateSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_clean_mode_state_sensor(mock_coordinator) -> None:
    """Test CleanModeStateSensor."""
    sensor = CleanModeStateSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 0
    assert sensor.unique_id == "clean_mode_state"


async def test_clean_mode_state_sensor_unavailable(mock_coordinator) -> None:
    """Test CleanModeStateSensor when status is None."""
    mock_coordinator.data.status = None
    sensor = CleanModeStateSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_error_bits_sensor(mock_coordinator) -> None:
    """Test ErrorBitsSensor."""
    sensor = ErrorBitsSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 0
    assert sensor.unique_id == "error_bits"


async def test_error_bits_sensor_unavailable(mock_coordinator) -> None:
    """Test ErrorBitsSensor when status is None."""
    mock_coordinator.data.status = None
    sensor = ErrorBitsSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_filter_lifetime_sensor(mock_coordinator) -> None:
    """Test FilterLifetimeSensor."""
    sensor = FilterLifetimeSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 365
    assert sensor.unique_id == "filter_lifetime"


async def test_filter_lifetime_sensor_unavailable(mock_coordinator) -> None:
    """Test FilterLifetimeSensor when settings is None."""
    mock_coordinator.data.settings = None
    sensor = FilterLifetimeSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_post_flush_quantity_sensor(mock_coordinator) -> None:
    """Test PostFlushQuantitySensor."""
    sensor = PostFlushQuantitySensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 100
    assert sensor.unique_id == "post_flush_quantity"


async def test_post_flush_quantity_sensor_unavailable(mock_coordinator) -> None:
    """Test PostFlushQuantitySensor when settings is None."""
    mock_coordinator.data.settings = None
    sensor = PostFlushQuantitySensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_firmware_main_sensor(mock_coordinator) -> None:
    """Test FirmwareMainSensor."""
    sensor = FirmwareMainSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "1.2.0"
    assert sensor.unique_id == "firmware_main"


async def test_firmware_main_sensor_unavailable(mock_coordinator) -> None:
    """Test FirmwareMainSensor when system_info is None."""
    mock_coordinator.data.system_info = None
    sensor = FirmwareMainSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_firmware_comm_sensor(mock_coordinator) -> None:
    """Test FirmwareCommSensor."""
    sensor = FirmwareCommSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "1.0.0"
    assert sensor.unique_id == "firmware_comm"


async def test_firmware_comm_sensor_unavailable(mock_coordinator) -> None:
    """Test FirmwareCommSensor when system_info is None."""
    mock_coordinator.data.system_info = None
    sensor = FirmwareCommSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_firmware_elec_sensor(mock_coordinator) -> None:
    """Test FirmwareElecSensor."""
    sensor = FirmwareElecSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "1.1.0"
    assert sensor.unique_id == "firmware_elec"


async def test_firmware_elec_sensor_unavailable(mock_coordinator) -> None:
    """Test FirmwareElecSensor when system_info is None."""
    mock_coordinator.data.system_info = None
    sensor = FirmwareElecSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_device_name_sensor(mock_coordinator) -> None:
    """Test DeviceNameSensor."""
    sensor = DeviceNameSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "Test Device"
    assert sensor.unique_id == "device_name"


async def test_device_name_sensor_unavailable(mock_coordinator) -> None:
    """Test DeviceNameSensor when system_info is None."""
    mock_coordinator.data.system_info = None
    sensor = DeviceNameSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_reset_count_sensor(mock_coordinator) -> None:
    """Test ResetCountSensor."""
    sensor = ResetCountSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == 10
    assert sensor.unique_id == "reset_count"


async def test_reset_count_sensor_unavailable(mock_coordinator) -> None:
    """Test ResetCountSensor when system_info is None."""
    mock_coordinator.data.system_info = None
    sensor = ResetCountSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_device_type_sensor(mock_coordinator) -> None:
    """Test DeviceTypeSensor."""
    sensor = DeviceTypeSensor(mock_coordinator)

    assert sensor.native_value == 1
    assert sensor.unique_id == "device_type"


async def test_device_type_sensor_none(mock_coordinator) -> None:
    """Test DeviceTypeSensor when device_type is None."""
    mock_coordinator.data.device_type = None
    sensor = DeviceTypeSensor(mock_coordinator)

    assert sensor.native_value is None


async def test_serial_number_sensor(mock_coordinator) -> None:
    """Test SerialNumberSensor."""
    sensor = SerialNumberSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "123456"
    assert sensor.unique_id == "serial_number"


async def test_serial_number_sensor_unavailable(mock_coordinator) -> None:
    """Test SerialNumberSensor when identity is None."""
    mock_coordinator.data.identity = None
    sensor = SerialNumberSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_service_code_sensor(mock_coordinator) -> None:
    """Test ServiceCodeSensor."""
    sensor = ServiceCodeSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "ABCDEF"
    assert sensor.unique_id == "service_code"


async def test_service_code_sensor_unavailable(mock_coordinator) -> None:
    """Test ServiceCodeSensor when identity is None."""
    mock_coordinator.data.identity = None
    sensor = ServiceCodeSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_wifi_ssid_sensor(mock_coordinator) -> None:
    """Test WiFiSSIDSensor."""
    sensor = WiFiSSIDSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "TestSSID"
    assert sensor.unique_id == "wifi_ssid"


async def test_wifi_ssid_sensor_unavailable(mock_coordinator) -> None:
    """Test WiFiSSIDSensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = WiFiSSIDSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_wifi_signal_sensor(mock_coordinator) -> None:
    """Test WiFiSignalSensor."""
    sensor = WiFiSignalSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == -50
    assert sensor.unique_id == "wifi_signal"


async def test_wifi_signal_sensor_unavailable(mock_coordinator) -> None:
    """Test WiFiSignalSensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = WiFiSignalSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_ip_address_sensor(mock_coordinator) -> None:
    """Test IPAddressSensor."""
    sensor = IPAddressSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "192.168.1.100"
    assert sensor.unique_id == "ip_address"


async def test_ip_address_sensor_unavailable(mock_coordinator) -> None:
    """Test IPAddressSensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = IPAddressSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_ble_mac_sensor(mock_coordinator) -> None:
    """Test BLEMacSensor."""
    sensor = BLEMacSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "AA:BB:CC:DD:EE:FF"
    assert sensor.unique_id == "ble_mac"


async def test_ble_mac_sensor_unavailable(mock_coordinator) -> None:
    """Test BLEMacSensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = BLEMacSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_wifi_mac_sensor(mock_coordinator) -> None:
    """Test WiFiMacSensor."""
    sensor = WiFiMacSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "11:22:33:44:55:66"
    assert sensor.unique_id == "wifi_mac"


async def test_wifi_mac_sensor_unavailable(mock_coordinator) -> None:
    """Test WiFiMacSensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = WiFiMacSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_gateway_sensor(mock_coordinator) -> None:
    """Test GatewaySensor."""
    sensor = GatewaySensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "192.168.1.1"
    assert sensor.unique_id == "gateway"


async def test_gateway_sensor_unavailable(mock_coordinator) -> None:
    """Test GatewaySensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = GatewaySensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_gateway_mac_sensor(mock_coordinator) -> None:
    """Test GatewayMacSensor."""
    sensor = GatewayMacSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "AA:BB:CC:DD:EE:00"
    assert sensor.unique_id == "gateway_mac"


async def test_gateway_mac_sensor_unavailable(mock_coordinator) -> None:
    """Test GatewayMacSensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = GatewayMacSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_subnet_sensor(mock_coordinator) -> None:
    """Test SubnetSensor."""
    sensor = SubnetSensor(mock_coordinator)

    assert sensor.available is True
    assert sensor.native_value == "255.255.255.0"
    assert sensor.unique_id == "subnet"


async def test_subnet_sensor_unavailable(mock_coordinator) -> None:
    """Test SubnetSensor when wifi_info is None."""
    mock_coordinator.data.wifi_info = None
    sensor = SubnetSensor(mock_coordinator)

    assert sensor.available is False
    assert sensor.native_value is None


async def test_sensor_when_data_is_unavailable(mock_coordinator) -> None:
    """Test sensor when data is unavailable."""
    mock_coordinator.data.available = False
    sensor = FilterRemainingSensor(mock_coordinator)

    assert sensor.available is False
