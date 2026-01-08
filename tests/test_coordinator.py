"""Tests for the Blanco Unit coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from bleak_retry_connector import BleakConnectionError, BleakNotFoundError
import pytest

from custom_components.blanco_unit.client import BlancoUnitAuthenticationError
from custom_components.blanco_unit.const import CONF_MAC, CONF_PIN
from custom_components.blanco_unit.coordinator import BlancoUnitCoordinator
from custom_components.blanco_unit.data import (
    BlancoUnitData,
    BlancoUnitIdentity,
    BlancoUnitSettings,
    BlancoUnitStatus,
    BlancoUnitSystemInfo,
    BlancoUnitWifiInfo,
)
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ServiceValidationError
from homeassistant.helpers.update_coordinator import UpdateFailed


@pytest.fixture
def mock_device():
    """Create a mock BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    return device


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.title = "Test Blanco Unit"
    entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF", CONF_PIN: 12345}
    return entry


@pytest.fixture
def mock_client():
    """Create a mock Blanco Unit client."""
    client = MagicMock()
    client.device_id = "test_device_id"
    client.is_connected = True
    client.get_system_info = AsyncMock(
        return_value=BlancoUnitSystemInfo(
            sw_ver_comm_con="1.0.0",
            sw_ver_elec_con="1.0.0",
            sw_ver_main_con="1.0.0",
            dev_name="Test Device",
            reset_cnt=0,
        )
    )
    client.get_settings = AsyncMock(
        return_value=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=5,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=7,
            wtr_hardness=5,
        )
    )
    client.get_status = AsyncMock(
        return_value=BlancoUnitStatus(
            tap_state=0,
            filter_rest=100,
            co2_rest=100,
            wtr_disp_active=False,
            firm_upd_avlb=False,
            set_point_cooling=7,
            clean_mode_state=0,
            err_bits=0,
        )
    )
    client.get_device_identity = AsyncMock(
        return_value=BlancoUnitIdentity(
            serial_no="123456",
            service_code="ABCDEF",
        )
    )
    client.get_wifi_info = AsyncMock(
        return_value=BlancoUnitWifiInfo(
            cloud_connect=True,
            ssid="TestSSID",
            signal=-50,
            ip="192.168.1.100",
            ble_mac="AA:BB:CC:DD:EE:FF",
            wifi_mac="11:22:33:44:55:66",
            gateway="192.168.1.1",
            gateway_mac="AA:BB:CC:DD:EE:00",
            subnet="255.255.255.0",
        )
    )
    client.disconnect = AsyncMock()
    client.set_temperature = AsyncMock()
    client.set_water_hardness = AsyncMock()
    client.dispense_water = AsyncMock()
    client.change_pin = AsyncMock()
    client.set_calibration_still = AsyncMock()
    client.set_calibration_soda = AsyncMock()
    return client


async def test_coordinator_init(
    hass: HomeAssistant, mock_device, mock_config_entry
) -> None:
    """Test coordinator initialization."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient"
        ) as mock_client_class,
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ) as mock_track_unavailable,
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ) as mock_register_callback,
    ):
        mock_client_class.return_value = MagicMock()

        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        assert coordinator.address == "AA:BB:CC:DD:EE:FF"
        assert coordinator.mac_address == "AA:BB:CC:DD:EE:FF"
        assert coordinator.update_interval == timedelta(minutes=1)

        mock_track_unavailable.assert_called_once()
        mock_register_callback.assert_called_once()


async def test_coordinator_available_callback(
    hass: HomeAssistant, mock_device, mock_config_entry
) -> None:
    """Test available callback triggers refresh."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient"
        ) as mock_client_class,
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        mock_client_class.return_value = MagicMock()

        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        info = MagicMock(spec=BluetoothServiceInfoBleak)
        info.address = "AA:BB:CC:DD:EE:FF"

        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            coordinator._available_callback(info, None)
            await hass.async_block_till_done()

            mock_refresh.assert_called_once()


async def test_coordinator_unavailable_callback(
    hass: HomeAssistant, mock_device, mock_config_entry
) -> None:
    """Test unavailable callback sets device unavailable."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient"
        ) as mock_client_class,
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client_class.return_value = mock_client

        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        # Set initial data
        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        info = MagicMock(spec=BluetoothServiceInfoBleak)
        info.address = "AA:BB:CC:DD:EE:FF"

        with patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ) as mock_rediscover:
            coordinator._unavailable_callback(info)

            mock_rediscover.assert_called_once_with(hass, "AA:BB:CC:DD:EE:FF")
            assert coordinator.data.available is False


async def test_coordinator_unload(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test coordinator unload."""
    unsub_listener = MagicMock()
    unsub_unavailable = MagicMock()
    unsub_available = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable",
            return_value=unsub_unavailable,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback",
            return_value=unsub_available,
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        await coordinator.unload()

        unsub_unavailable.assert_called_once()
        unsub_available.assert_called_once()
        mock_client.disconnect.assert_called_once()


async def test_coordinator_refresh_data(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test refresh_data method."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            await coordinator.refresh_data()
            await hass.async_block_till_done()

            mock_refresh.assert_called_once()


async def test_coordinator_disconnect(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test disconnect method."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        await coordinator.disconnect()

        mock_client.disconnect.assert_called_once()


async def test_coordinator_set_temperature(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test set_temperature method."""
    unsub_listener = MagicMock()

    # Update mock to return the temperature we're setting
    mock_client.get_settings = AsyncMock(
        return_value=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=5,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=8,  # Match the temperature we're setting
            wtr_hardness=5,
        )
    )

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        await coordinator.set_temperature(8)

        mock_client.set_temperature.assert_called_once_with(8)
        mock_client.get_settings.assert_called_once()


async def test_coordinator_set_temperature_verification_failed(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test set_temperature when verification fails."""
    unsub_listener = MagicMock()

    # Make get_settings return different value than set
    mock_client.get_settings = AsyncMock(
        return_value=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=5,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=7,  # Different from the 8 we're trying to set
            wtr_hardness=5,
        )
    )

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        with pytest.raises(ServiceValidationError, match="not_saved_temperature"):
            await coordinator.set_temperature(8)


async def test_coordinator_set_water_hardness(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test set_water_hardness method."""
    unsub_listener = MagicMock()

    # Update mock to return the hardness we're setting
    mock_client.get_settings = AsyncMock(
        return_value=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=5,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=7,
            wtr_hardness=7,  # Match the hardness we're setting
        )
    )

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        await coordinator.set_water_hardness(7)

        mock_client.set_water_hardness.assert_called_once_with(7)
        mock_client.get_settings.assert_called_once()


async def test_coordinator_set_water_hardness_verification_failed(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test set_water_hardness when verification fails."""
    unsub_listener = MagicMock()

    # Make get_settings return different value than set
    mock_client.get_settings = AsyncMock(
        return_value=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=5,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=7,
            wtr_hardness=5,  # Different from the 7 we're trying to set
        )
    )

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        with pytest.raises(ServiceValidationError, match="not_saved_water_hardness"):
            await coordinator.set_water_hardness(7)


async def test_coordinator_dispense_water(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test dispense_water method."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        with patch.object(coordinator, "async_request_refresh") as mock_refresh:
            await coordinator.dispense_water(500, 2)
            await hass.async_block_till_done()

            mock_client.dispense_water.assert_called_once_with(500, 2)
            mock_refresh.assert_called_once()


async def test_coordinator_change_pin(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test change_pin method."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        await coordinator.change_pin("54321")

        mock_client.change_pin.assert_called_once_with("54321")
        mock_client.disconnect.assert_called_once()


async def test_coordinator_set_calibration_still(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test set_calibration_still method."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        await coordinator.set_calibration_still(7)

        mock_client.set_calibration_still.assert_called_once_with(7)
        mock_client.get_settings.assert_called_once()


async def test_coordinator_set_calibration_soda(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test set_calibration_soda method."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        await coordinator.set_calibration_soda(8)

        mock_client.set_calibration_soda.assert_called_once_with(8)
        mock_client.get_settings.assert_called_once()


async def test_coordinator_connection_changed(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test _connection_changed callback."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        coordinator._connection_changed(False)

        assert coordinator.data.connected is False


async def test_coordinator_async_update_data_success(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test successful data update."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        data = await coordinator._async_update_data()

        assert data.connected is True
        assert data.available is True
        assert data.device_id == "test_device_id"
        assert data.system_info is not None
        assert data.settings is not None
        assert data.status is not None
        assert data.identity is not None
        assert data.wifi_info is not None


async def test_coordinator_async_update_data_auth_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test data update with authentication error."""
    unsub_listener = MagicMock()

    mock_client.get_system_info = AsyncMock(
        side_effect=BlancoUnitAuthenticationError("Auth failed")
    )

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()


async def test_coordinator_async_update_data_connection_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test data update with connection error."""
    unsub_listener = MagicMock()

    mock_client.get_system_info = AsyncMock(side_effect=BleakConnectionError("Error"))

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        # Set initial data so _set_unavailable can work properly
        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_async_update_data_not_found_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test data update with device not found error."""
    unsub_listener = MagicMock()

    mock_client.get_system_info = AsyncMock(side_effect=BleakNotFoundError("Error"))

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        # Set initial data so _set_unavailable can work properly
        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_async_update_data_generic_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test data update with generic error."""
    unsub_listener = MagicMock()

    mock_client.get_system_info = AsyncMock(side_effect=ValueError("Error"))

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        # Set initial data so _set_unavailable can work properly
        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()


async def test_coordinator_call_auth_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test _call method with authentication error."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        async def failing_func():
            raise BlancoUnitAuthenticationError("Auth failed")

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._call(failing_func)


async def test_coordinator_call_connection_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test _call method with connection error."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        async def failing_func():
            raise BleakConnectionError("Error")

        with pytest.raises(ServiceValidationError):
            await coordinator._call(failing_func)


async def test_coordinator_call_not_found_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test _call method with not found error."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        async def failing_func():
            raise BleakNotFoundError("Error")

        with pytest.raises(ServiceValidationError):
            await coordinator._call(failing_func)


async def test_coordinator_call_generic_error(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test _call method with generic error."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ),
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = BlancoUnitData(
            connected=True,
            available=True,
            device_id="test_device_id",
        )

        async def failing_func():
            raise ValueError("Error")

        with pytest.raises(ServiceValidationError):
            await coordinator._call(failing_func)


async def test_coordinator_set_unavailable_with_no_data(
    hass: HomeAssistant, mock_device, mock_config_entry, mock_client
) -> None:
    """Test _set_unavailable when no data exists yet."""
    unsub_listener = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.coordinator.BlancoUnitBluetoothClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_track_unavailable"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_register_callback"
        ),
        patch(
            "custom_components.blanco_unit.coordinator.bluetooth.async_rediscover_address"
        ) as mock_rediscover,
    ):
        coordinator = BlancoUnitCoordinator(
            hass, mock_config_entry, mock_device, unsub_listener
        )

        coordinator.data = None

        coordinator._set_unavailable()

        # Should still trigger rediscovery
        mock_rediscover.assert_called_once_with(hass, "AA:BB:CC:DD:EE:FF")
