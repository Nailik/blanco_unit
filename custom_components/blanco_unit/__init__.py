"""Integration for a Blanco Unit via BLE."""

from __future__ import annotations

import logging

from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
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

from .client import validate_pin
from .const import (
    BLE_CALLBACK,
    CHARACTERISTIC_UUID,
    CONF_DEV_ID,
    CONF_MAC,
    CONF_PIN,
    DOMAIN,
    MIN_HA_VERSION,
    RANDOM_MAC_PLACEHOLDER,
)
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


def _is_random_mac(config_entry: BlancoUnitConfigEntry) -> bool:
    """Check if config entry has a randomized MAC address."""
    return config_entry.data.get(CONF_MAC) == RANDOM_MAC_PLACEHOLDER


async def _find_device_by_scanning(
    hass: HomeAssistant, pin: str, expected_dev_id: str
) -> BLEDevice:
    """Find a BLE device by active scanning for CHARACTERISTIC_UUID and matching PIN + dev_id.

    Uses the shared HA BLE scanner to actively scan for devices that advertise
    the Blanco Unit service UUID, sorts them by RSSI (closest first),
    and tries to connect and validate each one.

    Raises:
        ConfigEntryNotReady: No devices with the correct UUID were found.
        ConfigEntryAuthFailed: Devices were found but none matched PIN + dev_id.
    """
    scanner = bluetooth.async_get_scanner(hass)
    discovered = scanner.discovered_devices_and_advertisement_data

    # Filter by CHARACTERISTIC_UUID and sort by RSSI (closest first)
    candidates: list[tuple[BLEDevice, int]] = []
    for device, adv_data in discovered.values():
        if CHARACTERISTIC_UUID in adv_data.service_uuids:
            candidates.append((device, adv_data.rssi))
    candidates.sort(key=lambda item: item[1], reverse=True)

    _LOGGER.debug(
        "Random MAC scan: found %d candidates with UUID %s",
        len(candidates),
        CHARACTERISTIC_UUID,
    )

    if not candidates:
        raise ConfigEntryNotReady(
            translation_key="error_device_not_found",
        )

    had_auth_failure = False

    for device, rssi in candidates:
        _LOGGER.debug(
            "Random MAC scan: trying %s (RSSI: %s)", device.address, rssi
        )
        client = None
        try:
            client = await establish_connection(
                client_class=BleakClientWithServiceCache,
                device=device,
                name=device.name or "Unknown Device",
            )

            result = await validate_pin(client, pin)

            if not result.is_valid:
                _LOGGER.debug(
                    "Random MAC scan: PIN rejected by %s", device.address
                )
                had_auth_failure = True
                continue

            if result.dev_id == expected_dev_id:
                _LOGGER.debug(
                    "Random MAC scan: matched device %s (dev_id: %s)",
                    device.address,
                    result.dev_id,
                )
                return device

            _LOGGER.debug(
                "Random MAC scan: dev_id mismatch on %s (got %s, expected %s)",
                device.address,
                result.dev_id,
                expected_dev_id,
            )
        except (OSError, TimeoutError):
            _LOGGER.debug(
                "Random MAC scan: connection failed for %s",
                device.address,
                exc_info=True,
            )
        finally:
            if client is not None and client.is_connected:
                await client.disconnect()

    # Tried all candidates, none matched
    if had_auth_failure:
        raise ConfigEntryAuthFailed(
            translation_key="error_invalid_authentication",
        )

    raise ConfigEntryNotReady(
        translation_key="error_device_not_found",
    )


def _register_retry_callback(
    hass: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> None:
    """Register a BLE callback to retry setup when device appears."""
    if hass.data[DOMAIN][config_entry.entry_id].get(BLE_CALLBACK) is not None:
        return

    random_mac = _is_random_mac(config_entry)

    def _available_callback(
        info: BluetoothServiceInfoBleak, _change: BluetoothChange
    ) -> None:
        if random_mac:
            _LOGGER.debug(
                "Random MAC: device with UUID discovered at %s", info.address
            )
        else:
            _LOGGER.debug("%s is discovered again", info.address)
        hass.async_create_task(
            hass.config_entries.async_reload(config_entry.entry_id)
        )

    _LOGGER.debug("async_setup_entry async_register_callback (random_mac=%s)", random_mac)

    if random_mac:
        # For random MAC, listen for any device advertising our service UUID
        unregister_ble_callback = bluetooth.async_register_callback(
            hass,
            _available_callback,
            {"service_uuid": CHARACTERISTIC_UUID, "connectable": True},
            BluetoothScanningMode.ACTIVE,
        )
    else:
        # For static MAC, listen for the specific address
        unregister_ble_callback = bluetooth.async_register_callback(
            hass,
            _available_callback,
            {"address": config_entry.data[CONF_MAC], "connectable": True},
            BluetoothScanningMode.ACTIVE,
        )

    hass.data[DOMAIN][config_entry.entry_id][BLE_CALLBACK] = unregister_ble_callback


async def _resolve_device(
    hass: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> BLEDevice:
    """Resolve the BLE device, handling both static and random MAC cases.

    Raises:
        ConfigEntryNotReady: Device not found.
        ConfigEntryAuthFailed: Device found but PIN/dev_id mismatch (random MAC only).
    """
    if _is_random_mac(config_entry):
        _LOGGER.debug("async_setup_entry: random MAC, scanning for device")
        return await _find_device_by_scanning(
            hass,
            pin=str(config_entry.data[CONF_PIN]),
            expected_dev_id=config_entry.data[CONF_DEV_ID],
        )

    device = bluetooth.async_ble_device_from_address(
        hass=hass,
        address=config_entry.data[CONF_MAC],
        connectable=True,
    )

    if device is None:
        _LOGGER.debug("async_setup_entry device not found")
        _register_retry_callback(hass, config_entry)
        raise ConfigEntryNotReady(
            translation_key="error_device_not_found",
        )

    return device


async def async_setup_entry(
    hass: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> bool:
    """Set up Blanco Unit Integration from a config entry."""
    _LOGGER.debug("async_setup_entry called with config_entry: %s", config_entry)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(config_entry.entry_id, {})

    try:
        device = await _resolve_device(hass, config_entry)
    except ConfigEntryNotReady:
        _register_retry_callback(hass, config_entry)
        raise
    except ConfigEntryAuthFailed:
        raise

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
        if not _is_random_mac(config_entry):
            bluetooth.async_rediscover_address(hass, config_entry.data[CONF_MAC])

    return unload_ok
