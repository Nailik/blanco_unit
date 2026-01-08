"""Tests for the Blanco Unit __init__ module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.blanco_unit import (
    async_reload_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.blanco_unit.const import BLE_CALLBACK, CONF_MAC, DOMAIN
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
