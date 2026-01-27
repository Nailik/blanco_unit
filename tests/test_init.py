"""Tests for the Blanco Unit __init__ module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.blanco_unit import (
    _find_device_by_scanning,
    _is_random_mac,
    _register_retry_callback,
    async_reload_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.blanco_unit.client import PinValidationResult
from custom_components.blanco_unit.const import (
    BLE_CALLBACK,
    CHARACTERISTIC_UUID,
    CONF_DEV_ID,
    CONF_MAC,
    CONF_PIN,
    DOMAIN,
    RANDOM_MAC_PLACEHOLDER,
)
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    IntegrationError,
)


async def test_async_setup_min_ha_version_check(hass: HomeAssistant) -> None:
    """Test async_setup checks minimum HA version."""
    mock_entry = MagicMock(spec=ConfigEntry)

    with patch("custom_components.blanco_unit.ha_version", "2024.1.0"):
        with pytest.raises(IntegrationError) as exc_info:
            await async_setup(hass, mock_entry)

        assert exc_info.value.translation_key == "invalid_ha_version"


async def test_async_setup_success(hass: HomeAssistant) -> None:
    """Test successful async_setup."""
    mock_entry = MagicMock(spec=ConfigEntry)

    with (
        patch("homeassistant.const.__version__", "2025.6.0"),
        patch(
            "custom_components.blanco_unit.async_setup_services"
        ) as mock_setup_services,
    ):
        result = await async_setup(hass, mock_entry)

        assert result is True
        mock_setup_services.assert_called_once_with(hass)


async def test_async_setup_entry_success(hass: HomeAssistant) -> None:
    """Test successful config entry setup."""
    mock_device = MagicMock()
    mock_device.address = "AA:BB:CC:DD:EE:FF"

    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}
    mock_entry.add_update_listener = MagicMock(return_value=MagicMock())

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=mock_device,
        ),
        patch(
            "custom_components.blanco_unit.BlancoUnitCoordinator",
            return_value=mock_coordinator,
        ),
        patch.object(hass.config_entries, "async_forward_entry_setups") as mock_forward,
    ):
        result = await async_setup_entry(hass, mock_entry)

        assert result is True
        assert mock_entry.runtime_data == mock_coordinator
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()
        mock_forward.assert_called_once()

        # Verify platforms are registered
        call_args = mock_forward.call_args[0]
        assert call_args[0] == mock_entry
        assert Platform.BINARY_SENSOR in call_args[1]
        assert Platform.BUTTON in call_args[1]
        assert Platform.NUMBER in call_args[1]
        assert Platform.SELECT in call_args[1]
        assert Platform.SENSOR in call_args[1]


async def test_async_setup_entry_device_not_found_first_time(
    hass: HomeAssistant,
) -> None:
    """Test config entry setup when device not found initially."""
    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][mock_entry.entry_id] = {}

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=None,
        ),
        patch(
            "custom_components.blanco_unit.bluetooth.async_register_callback"
        ) as mock_register_callback,
    ):
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, mock_entry)

        assert exc_info.value.translation_key == "error_device_not_found"
        # Verify callback was registered
        mock_register_callback.assert_called_once()
        assert BLE_CALLBACK in hass.data[DOMAIN][mock_entry.entry_id]


async def test_async_setup_entry_device_not_found_callback_exists(
    hass: HomeAssistant,
) -> None:
    """Test config entry setup when device not found and callback already exists."""
    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][mock_entry.entry_id] = {BLE_CALLBACK: MagicMock()}

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=None,
        ),
        patch(
            "custom_components.blanco_unit.bluetooth.async_register_callback"
        ) as mock_register_callback,
    ):
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, mock_entry)

        assert exc_info.value.translation_key == "error_device_not_found"
        # Verify callback was NOT registered again
        mock_register_callback.assert_not_called()


async def test_async_setup_entry_ble_callback_triggers_reload(
    hass: HomeAssistant,
) -> None:
    """Test BLE callback triggers config entry reload."""
    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][mock_entry.entry_id] = {}

    callback_func = None

    def capture_callback(hass, callback, *args, **kwargs):
        nonlocal callback_func
        callback_func = callback
        return MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=None,
        ),
        patch(
            "custom_components.blanco_unit.bluetooth.async_register_callback",
            side_effect=capture_callback,
        ),
        patch.object(hass.config_entries, "async_reload") as mock_reload,
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_entry)

        # Simulate device discovery
        info = MagicMock(spec=BluetoothServiceInfoBleak)
        info.address = "AA:BB:CC:DD:EE:FF"
        change = BluetoothChange.ADVERTISEMENT

        callback_func(info, change)

        # Wait for task to be scheduled
        await hass.async_block_till_done()

        mock_reload.assert_called_once_with("test_entry_id")


async def test_async_setup_entry_auth_failed(hass: HomeAssistant) -> None:
    """Test config entry setup with authentication failure."""
    mock_device = MagicMock()
    mock_device.address = "AA:BB:CC:DD:EE:FF"

    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=ConfigEntryAuthFailed("Auth failed")
    )

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}

    unsub_listener = MagicMock()
    mock_entry.add_update_listener = MagicMock(return_value=unsub_listener)

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=mock_device,
        ),
        patch(
            "custom_components.blanco_unit.BlancoUnitCoordinator",
            return_value=mock_coordinator,
        ),
    ):
        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, mock_entry)

        # Verify unsub listener was called
        unsub_listener.assert_called_once()


async def test_async_setup_entry_home_assistant_error(hass: HomeAssistant) -> None:
    """Test config entry setup with HomeAssistantError."""
    mock_device = MagicMock()
    mock_device.address = "AA:BB:CC:DD:EE:FF"

    mock_coordinator = MagicMock()
    error = HomeAssistantError()
    error.translation_key = "test_error"
    error.translation_placeholders = {"key": "value"}
    mock_coordinator.async_config_entry_first_refresh = AsyncMock(side_effect=error)

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}

    unsub_listener = MagicMock()
    mock_entry.add_update_listener = MagicMock(return_value=unsub_listener)

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=mock_device,
        ),
        patch(
            "custom_components.blanco_unit.BlancoUnitCoordinator",
            return_value=mock_coordinator,
        ),
    ):
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, mock_entry)

        assert exc_info.value.translation_key == "test_error"
        # Verify unsub listener was called
        unsub_listener.assert_called_once()


async def test_async_setup_entry_generic_exception(hass: HomeAssistant) -> None:
    """Test config entry setup with generic exception."""
    mock_device = MagicMock()
    mock_device.address = "AA:BB:CC:DD:EE:FF"

    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=ValueError("Test error")
    )

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}

    unsub_listener = MagicMock()
    mock_entry.add_update_listener = MagicMock(return_value=unsub_listener)

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=mock_device,
        ),
        patch(
            "custom_components.blanco_unit.BlancoUnitCoordinator",
            return_value=mock_coordinator,
        ),
    ):
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, mock_entry)

        assert exc_info.value.translation_key == "error_unknown"
        # Verify unsub listener was called
        unsub_listener.assert_called_once()


async def test_async_reload_entry(hass: HomeAssistant) -> None:
    """Test config entry reload."""
    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.data = {"conf_pin": 12345}

    with (
        patch(
            "custom_components.blanco_unit.async_unload_entry", return_value=True
        ) as mock_unload,
        patch(
            "custom_components.blanco_unit.async_setup_entry", return_value=True
        ) as mock_setup,
    ):
        await async_reload_entry(hass, mock_entry)

        mock_unload.assert_called_once_with(hass, mock_entry)
        mock_setup.assert_called_once_with(hass, mock_entry)


async def test_async_unload_entry_success(hass: HomeAssistant) -> None:
    """Test successful config entry unload."""
    mock_coordinator = MagicMock()
    mock_coordinator.unload = AsyncMock()

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}
    mock_entry.runtime_data = mock_coordinator

    unregister_callback = MagicMock()
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["test_entry_id"] = {BLE_CALLBACK: unregister_callback}

    with (
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            return_value=True,
        ) as mock_unload_platforms,
        patch(
            "custom_components.blanco_unit.bluetooth.async_rediscover_address"
        ) as mock_rediscover,
    ):
        result = await async_unload_entry(hass, mock_entry)

        assert result is True
        unregister_callback.assert_called_once()
        mock_coordinator.unload.assert_called_once()
        mock_rediscover.assert_called_once_with(hass, "AA:BB:CC:DD:EE:FF")
        mock_unload_platforms.assert_called_once()


async def test_async_unload_entry_no_callback(hass: HomeAssistant) -> None:
    """Test config entry unload when no BLE callback exists."""
    mock_coordinator = MagicMock()
    mock_coordinator.unload = AsyncMock()

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}
    mock_entry.runtime_data = mock_coordinator

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["test_entry_id"] = {}

    with (
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            return_value=True,
        ),
        patch(
            "custom_components.blanco_unit.bluetooth.async_rediscover_address"
        ) as mock_rediscover,
    ):
        result = await async_unload_entry(hass, mock_entry)

        assert result is True
        mock_coordinator.unload.assert_called_once()
        mock_rediscover.assert_called_once_with(hass, "AA:BB:CC:DD:EE:FF")


async def test_async_unload_entry_failed(hass: HomeAssistant) -> None:
    """Test config entry unload failure."""
    mock_coordinator = MagicMock()
    mock_coordinator.unload = AsyncMock()

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}
    mock_entry.runtime_data = mock_coordinator

    hass.data[DOMAIN] = {}

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        return_value=False,
    ):
        result = await async_unload_entry(hass, mock_entry)

        assert result is False
        # Coordinator.unload should NOT be called if unload_platforms fails
        mock_coordinator.unload.assert_not_called()


async def test_async_unload_entry_no_entry_data(hass: HomeAssistant) -> None:
    """Test config entry unload when entry data does not exist."""
    mock_coordinator = MagicMock()
    mock_coordinator.unload = AsyncMock()

    mock_entry = MagicMock(spec=ConfigEntry)
    mock_entry.entry_id = "test_entry_id"
    mock_entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}
    mock_entry.runtime_data = mock_coordinator

    hass.data[DOMAIN] = {}

    with (
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            return_value=True,
        ),
        patch(
            "custom_components.blanco_unit.bluetooth.async_rediscover_address"
        ) as mock_rediscover,
    ):
        result = await async_unload_entry(hass, mock_entry)

        assert result is True
        mock_coordinator.unload.assert_called_once()
        mock_rediscover.assert_called_once()


# -------------------------------
# Random MAC Tests
# -------------------------------


def _make_discovered_device(
    address: str, rssi: int = -50
) -> tuple[MagicMock, MagicMock]:
    """Create a mock (BLEDevice, AdvertisementData) tuple for scanner results."""
    device = MagicMock()
    device.address = address
    device.name = f"Device_{address}"

    adv_data = MagicMock()
    adv_data.service_uuids = [CHARACTERISTIC_UUID]
    adv_data.rssi = rssi

    return device, adv_data


def _make_scanner(
    discovered: dict[str, tuple[MagicMock, MagicMock]],
) -> MagicMock:
    """Create a mock BLE scanner with discovered devices."""
    scanner = MagicMock()
    scanner.discovered_devices_and_advertisement_data = discovered
    return scanner


def _make_random_mac_entry() -> MagicMock:
    """Create a mock config entry with random MAC."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_MAC: RANDOM_MAC_PLACEHOLDER,
        CONF_PIN: "12345",
        CONF_DEV_ID: "expected_dev_id",
    }
    return entry


def test_is_random_mac_true() -> None:
    """Test _is_random_mac returns True for randomized MAC."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {CONF_MAC: RANDOM_MAC_PLACEHOLDER}
    assert _is_random_mac(entry) is True


def test_is_random_mac_false() -> None:
    """Test _is_random_mac returns False for static MAC."""
    entry = MagicMock(spec=ConfigEntry)
    entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}
    assert _is_random_mac(entry) is False


async def test_find_device_by_scanning_match_found(hass: HomeAssistant) -> None:
    """Test _find_device_by_scanning finds matching device."""
    dev_close, adv_close = _make_discovered_device("11:22:33:44:55:66", rssi=-30)
    dev_far, adv_far = _make_discovered_device("AA:BB:CC:DD:EE:FF", rssi=-80)

    scanner = _make_scanner(
        {
            "AA:BB:CC:DD:EE:FF": (dev_far, adv_far),
            "11:22:33:44:55:66": (dev_close, adv_close),
        }
    )

    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_get_scanner",
            return_value=scanner,
        ),
        patch(
            "custom_components.blanco_unit.establish_connection",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.validate_pin",
            return_value=PinValidationResult(
                is_valid=True, dev_id="expected_dev_id", dev_type=1
            ),
        ),
    ):
        device = await _find_device_by_scanning(hass, "12345", "expected_dev_id")

    # Should return the closest device (higher RSSI first)
    assert device == dev_close


async def test_find_device_by_scanning_no_candidates(hass: HomeAssistant) -> None:
    """Test _find_device_by_scanning raises ConfigEntryNotReady when no devices found."""
    scanner = _make_scanner({})

    with patch(
        "custom_components.blanco_unit.bluetooth.async_get_scanner",
        return_value=scanner,
    ):
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await _find_device_by_scanning(hass, "12345", "expected_dev_id")

        assert exc_info.value.translation_key == "error_device_not_found"


async def test_find_device_by_scanning_filters_by_uuid(hass: HomeAssistant) -> None:
    """Test _find_device_by_scanning ignores devices without matching UUID."""
    dev_match, adv_match = _make_discovered_device("11:22:33:44:55:66")

    dev_other = MagicMock()
    dev_other.address = "AA:BB:CC:DD:EE:FF"
    adv_other = MagicMock()
    adv_other.service_uuids = ["00001800-0000-1000-8000-00805f9b34fb"]
    adv_other.rssi = -20

    scanner = _make_scanner(
        {
            "11:22:33:44:55:66": (dev_match, adv_match),
            "AA:BB:CC:DD:EE:FF": (dev_other, adv_other),
        }
    )

    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_get_scanner",
            return_value=scanner,
        ),
        patch(
            "custom_components.blanco_unit.establish_connection",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.validate_pin",
            return_value=PinValidationResult(
                is_valid=True, dev_id="expected_dev_id", dev_type=1
            ),
        ),
    ):
        device = await _find_device_by_scanning(hass, "12345", "expected_dev_id")

    assert device == dev_match


async def test_find_device_by_scanning_auth_failure(hass: HomeAssistant) -> None:
    """Test _find_device_by_scanning raises ConfigEntryAuthFailed when PIN rejected."""
    dev, adv = _make_discovered_device("11:22:33:44:55:66")
    scanner = _make_scanner({"11:22:33:44:55:66": (dev, adv)})

    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_get_scanner",
            return_value=scanner,
        ),
        patch(
            "custom_components.blanco_unit.establish_connection",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.validate_pin",
            return_value=PinValidationResult(
                is_valid=False, dev_id=None, dev_type=None
            ),
        ),
    ):
        with pytest.raises(ConfigEntryAuthFailed) as exc_info:
            await _find_device_by_scanning(hass, "12345", "expected_dev_id")

        assert exc_info.value.translation_key == "error_invalid_authentication"


async def test_find_device_by_scanning_dev_id_mismatch(hass: HomeAssistant) -> None:
    """Test _find_device_by_scanning raises ConfigEntryNotReady when dev_id doesn't match."""
    dev, adv = _make_discovered_device("11:22:33:44:55:66")
    scanner = _make_scanner({"11:22:33:44:55:66": (dev, adv)})

    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_get_scanner",
            return_value=scanner,
        ),
        patch(
            "custom_components.blanco_unit.establish_connection",
            return_value=mock_client,
        ),
        patch(
            "custom_components.blanco_unit.validate_pin",
            return_value=PinValidationResult(
                is_valid=True, dev_id="wrong_dev_id", dev_type=1
            ),
        ),
    ):
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await _find_device_by_scanning(hass, "12345", "expected_dev_id")

        assert exc_info.value.translation_key == "error_device_not_found"


async def test_find_device_by_scanning_connection_failure_skipped(
    hass: HomeAssistant,
) -> None:
    """Test _find_device_by_scanning skips devices with connection failures."""
    dev_fail, adv_fail = _make_discovered_device("11:22:33:44:55:66", rssi=-20)
    dev_ok, adv_ok = _make_discovered_device("AA:BB:CC:DD:EE:FF", rssi=-50)

    scanner = _make_scanner(
        {
            "11:22:33:44:55:66": (dev_fail, adv_fail),
            "AA:BB:CC:DD:EE:FF": (dev_ok, adv_ok),
        }
    )

    mock_client_ok = AsyncMock()
    mock_client_ok.is_connected = True
    mock_client_ok.disconnect = AsyncMock()

    call_count = 0

    async def mock_establish(client_class, device, name):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OSError("Connection failed")
        return mock_client_ok

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_get_scanner",
            return_value=scanner,
        ),
        patch(
            "custom_components.blanco_unit.establish_connection",
            side_effect=mock_establish,
        ),
        patch(
            "custom_components.blanco_unit.validate_pin",
            return_value=PinValidationResult(
                is_valid=True, dev_id="expected_dev_id", dev_type=1
            ),
        ),
    ):
        device = await _find_device_by_scanning(hass, "12345", "expected_dev_id")

    # Should skip the failed device and return the second one
    assert device == dev_ok


async def test_find_device_by_scanning_sorts_by_rssi(hass: HomeAssistant) -> None:
    """Test _find_device_by_scanning tries closest device first."""
    dev_far, adv_far = _make_discovered_device("AA:BB:CC:DD:EE:FF", rssi=-80)
    dev_close, adv_close = _make_discovered_device("11:22:33:44:55:66", rssi=-20)
    dev_medium, adv_medium = _make_discovered_device("22:33:44:55:66:77", rssi=-50)

    scanner = _make_scanner(
        {
            "AA:BB:CC:DD:EE:FF": (dev_far, adv_far),
            "11:22:33:44:55:66": (dev_close, adv_close),
            "22:33:44:55:66:77": (dev_medium, adv_medium),
        }
    )

    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.disconnect = AsyncMock()

    tried_addresses = []

    async def mock_establish(client_class, device, name):
        tried_addresses.append(device.address)
        return mock_client

    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_get_scanner",
            return_value=scanner,
        ),
        patch(
            "custom_components.blanco_unit.establish_connection",
            side_effect=mock_establish,
        ),
        patch(
            "custom_components.blanco_unit.validate_pin",
            return_value=PinValidationResult(
                is_valid=True, dev_id="expected_dev_id", dev_type=1
            ),
        ),
    ):
        await _find_device_by_scanning(hass, "12345", "expected_dev_id")

    # Closest device (highest RSSI) should be tried first
    assert tried_addresses[0] == "11:22:33:44:55:66"


async def test_register_retry_callback_random_mac(hass: HomeAssistant) -> None:
    """Test _register_retry_callback uses service_uuid filter for random MAC."""
    entry = _make_random_mac_entry()

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {}

    with patch(
        "custom_components.blanco_unit.bluetooth.async_register_callback"
    ) as mock_register:
        mock_register.return_value = MagicMock()
        _register_retry_callback(hass, entry)

        mock_register.assert_called_once()
        call_args = mock_register.call_args
        # Second argument is the filter dict
        filter_dict = call_args[0][2]
        assert "service_uuid" in filter_dict
        assert filter_dict["service_uuid"] == CHARACTERISTIC_UUID


async def test_register_retry_callback_static_mac(hass: HomeAssistant) -> None:
    """Test _register_retry_callback uses address filter for static MAC."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {CONF_MAC: "AA:BB:CC:DD:EE:FF"}

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {}

    with patch(
        "custom_components.blanco_unit.bluetooth.async_register_callback"
    ) as mock_register:
        mock_register.return_value = MagicMock()
        _register_retry_callback(hass, entry)

        mock_register.assert_called_once()
        call_args = mock_register.call_args
        filter_dict = call_args[0][2]
        assert "address" in filter_dict
        assert filter_dict["address"] == "AA:BB:CC:DD:EE:FF"


async def test_register_retry_callback_skips_if_already_registered(
    hass: HomeAssistant,
) -> None:
    """Test _register_retry_callback does not register twice."""
    entry = _make_random_mac_entry()

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {BLE_CALLBACK: MagicMock()}

    with patch(
        "custom_components.blanco_unit.bluetooth.async_register_callback"
    ) as mock_register:
        _register_retry_callback(hass, entry)
        mock_register.assert_not_called()


async def test_async_setup_entry_random_mac_success(hass: HomeAssistant) -> None:
    """Test config entry setup with random MAC finds device via scanning."""
    mock_device = MagicMock()
    mock_device.address = "11:22:33:44:55:66"

    mock_coordinator = MagicMock()
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()

    mock_entry = _make_random_mac_entry()
    mock_entry.title = "Test Blanco"
    mock_entry.add_update_listener = MagicMock(return_value=MagicMock())

    with (
        patch(
            "custom_components.blanco_unit._find_device_by_scanning",
            return_value=mock_device,
        ),
        patch(
            "custom_components.blanco_unit.BlancoUnitCoordinator",
            return_value=mock_coordinator,
        ),
        patch.object(hass.config_entries, "async_forward_entry_setups") as mock_forward,
    ):
        result = await async_setup_entry(hass, mock_entry)

        assert result is True
        assert mock_entry.runtime_data == mock_coordinator
        mock_forward.assert_called_once()


async def test_async_setup_entry_random_mac_not_found(hass: HomeAssistant) -> None:
    """Test config entry setup with random MAC when no device found."""
    mock_entry = _make_random_mac_entry()

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][mock_entry.entry_id] = {}

    with (
        patch(
            "custom_components.blanco_unit._find_device_by_scanning",
            side_effect=ConfigEntryNotReady(translation_key="error_device_not_found"),
        ),
        patch(
            "custom_components.blanco_unit.bluetooth.async_register_callback",
            return_value=MagicMock(),
        ) as mock_register,
    ):
        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, mock_entry)

        assert exc_info.value.translation_key == "error_device_not_found"
        # Should register retry callback with service_uuid
        mock_register.assert_called_once()


async def test_async_setup_entry_random_mac_auth_failed(hass: HomeAssistant) -> None:
    """Test config entry setup with random MAC when PIN fails."""
    mock_entry = _make_random_mac_entry()

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][mock_entry.entry_id] = {}

    with patch(
        "custom_components.blanco_unit._find_device_by_scanning",
        side_effect=ConfigEntryAuthFailed(
            translation_key="error_invalid_authentication"
        ),
    ):
        with pytest.raises(ConfigEntryAuthFailed) as exc_info:
            await async_setup_entry(hass, mock_entry)

        assert exc_info.value.translation_key == "error_invalid_authentication"


async def test_async_unload_entry_random_mac_skips_rediscover(
    hass: HomeAssistant,
) -> None:
    """Test config entry unload with random MAC skips async_rediscover_address."""
    mock_coordinator = MagicMock()
    mock_coordinator.unload = AsyncMock()

    mock_entry = _make_random_mac_entry()
    mock_entry.runtime_data = mock_coordinator

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][mock_entry.entry_id] = {}

    with (
        patch.object(
            hass.config_entries,
            "async_unload_platforms",
            return_value=True,
        ),
        patch(
            "custom_components.blanco_unit.bluetooth.async_rediscover_address"
        ) as mock_rediscover,
    ):
        result = await async_unload_entry(hass, mock_entry)

        assert result is True
        mock_coordinator.unload.assert_called_once()
        # Should NOT call rediscover for random MAC
        mock_rediscover.assert_not_called()
