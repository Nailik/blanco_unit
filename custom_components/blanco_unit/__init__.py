"""Integration for a Blanco Unit via BLE."""

from __future__ import annotations

import logging

from packaging import version

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    IntegrationError,
)

from .const import BLE_CALLBACK, CONF_MAC, DOMAIN, MIN_HA_VERSION
from .coordinator import BlancoUnitCoordinator
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]

type BlancoUnitConfigEntry = ConfigEntry[BlancoUnitCoordinator]


async def async_setup(hass: HomeAssistant, entry: BlancoUnitConfigEntry) -> bool:
    """Set up Blanco Unit integration services."""
    _LOGGER.debug("async_setup called with config_entry: %s", entry)
    if version.parse(ha_version) < version.parse(MIN_HA_VERSION):
        raise IntegrationError(
            translation_key="invalid_ha_version",
            translation_placeholders={"version": MIN_HA_VERSION},
        )
    async_setup_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> bool:
    """Set up Blanco Unit Integration from a config entry."""
    _LOGGER.debug("async_setup_entry called with config_entry: %s", config_entry)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})

    # Initialise the coordinator that manages data updates from your api.
    device = bluetooth.async_ble_device_from_address(
        hass=hass,
        address=config_entry.data[CONF_MAC],
        connectable=True,
    )

    if device is None:
        _LOGGER.debug("async_setup_entry device not found")

        if hass.data[DOMAIN][config_entry.entry_id].get(BLE_CALLBACK) is None:
            # Register a callback to retry setup when the device appears
            def _available_callback(
                info: BluetoothServiceInfoBleak, change: BluetoothChange
            ) -> None:
                _LOGGER.debug("%s is discovered again", info)
                if info.address == config_entry.data[CONF_MAC]:
                    _LOGGER.debug("%s is discovered again", info.address)
                    # Schedule a reload of the config entry immediately
                    hass.async_create_task(
                        hass.config_entries.async_reload(config_entry.entry_id)
                    )

            _LOGGER.debug("async_setup_entry async_register_callback")
            unregister_ble_callback = bluetooth.async_register_callback(
                hass,
                _available_callback,
                {"address": config_entry.data[CONF_MAC], "connectable": True},
                BluetoothScanningMode.ACTIVE,
            )
            hass.data[DOMAIN][config_entry.entry_id][BLE_CALLBACK] = (
                unregister_ble_callback
            )
        raise ConfigEntryNotReady(
            translation_key="error_device_not_found",
        )

    # Registers update listener to update config entry when options are updated.
    unsub_update_listener = config_entry.add_update_listener(async_reload_entry)

    coordinator = BlancoUnitCoordinator(
        hass=hass,
        config_entry=config_entry,
        device=device,
        unsub_options_update_listener=unsub_update_listener,
    )
    config_entry.runtime_data = coordinator

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed as err:
        # do not reload if setup failed
        _LOGGER.debug("async_setup_entry ConfigEntryAuthFailed %s", str(err))
        unsub_update_listener()
        raise err from err
    except HomeAssistantError as err:
        _LOGGER.debug("async_setup_entry HomeAssistantError %s", str(err))
        # do not reload if setup failed
        unsub_update_listener()
        raise ConfigEntryNotReady(
            translation_key=err.translation_key,
            translation_placeholders=err.translation_placeholders,
        ) from err
    except Exception as err:
        _LOGGER.debug("async_setup_entry Exception %s", str(err))
        # do not reload if setup failed
        unsub_update_listener()
        raise ConfigEntryNotReady(
            translation_key="error_unknown",
            translation_placeholders={"error": repr(err)},
        ) from err

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_reload_entry(
    hass: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> None:
    """Reload config entry."""
    _LOGGER.debug(
        "async_reload_entry async_reload with pin %s", config_entry.data["conf_pin"]
    )
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)


async def async_unload_entry(
    hass: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("async_unload_entry")

    entry_data = hass.data[DOMAIN].get(config_entry.entry_id)
    if entry_data:
        unregister_ble_callback = entry_data.get(BLE_CALLBACK)
        if unregister_ble_callback:
            _LOGGER.debug("unregister_ble_callback")
            unregister_ble_callback()

    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        coordinator: BlancoUnitCoordinator = config_entry.runtime_data
        await coordinator.unload()
        bluetooth.async_rediscover_address(hass, config_entry.data[CONF_MAC])

    return unload_ok
