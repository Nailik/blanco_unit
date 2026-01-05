"""Coordinator for Vogels Motion Mount BLE integration in order to communicate with client."""

from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta
import logging

from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakConnectionError, BleakNotFoundError

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BlancoUnitBluetoothClient
from .const import CONF_MAC, CONF_PIN, DOMAIN
from .data import (
    BlancoUnitData,
)

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


class BlancoUnitCoordinator(DataUpdateCoordinator[BlancoUnitData]):
    """Vogels Motion Mount BLE coordinator."""

    # -------------------------------
    # region Setup
    # -------------------------------

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        device: BLEDevice,
        unsub_options_update_listener: Callable[[], None],
    ) -> None:
        """Initialize coordinator and setup client."""
        _LOGGER.debug("Startup coordinator with %s", config_entry.data)

        # Store setup data
        self.address = device.address

        # Create client
        self._client = BlancoUnitBluetoothClient(
            pin=config_entry.data.get(CONF_PIN),
            device=device,
            connection_callback=self._connection_changed,
        )

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=config_entry.title,
            config_entry=config_entry,
            update_interval=timedelta(minutes=5),
        )

        # Setup listeners
        self._unsub_options_update_listener = unsub_options_update_listener
        self._unsub_unavailable_update_listener = bluetooth.async_track_unavailable(
            hass, self._unavailable_callback, self.address, connectable=True
        )
        self._unsub_available_update_listener = bluetooth.async_register_callback(
            hass,
            self._available_callback,
            {"address": self.address, "connectable": True},
            BluetoothScanningMode.ACTIVE,
        )

        _LOGGER.debug("Coordinator startup finished")

    def _available_callback(
        self, info: BluetoothServiceInfoBleak, change: BluetoothChange
    ) -> None:
        _LOGGER.debug("%s is discovered again", info.address)
        self.hass.async_create_task(self.async_request_refresh())  # load the data

    def _unavailable_callback(self, info: BluetoothServiceInfoBleak) -> None:
        _LOGGER.debug("%s is no longer seen", info.address)
        self._set_unavailable()

    async def unload(self):
        """Disconnect and unload."""
        _LOGGER.debug("unload coordinator")
        self._unsub_unavailable_update_listener()
        self._unsub_available_update_listener()
        await self._client.disconnect()

    async def refresh_data(self):
        """Load data form client."""
        self.hass.async_create_task(self.async_request_refresh())

    async def read_data(self):
        """Load data form client."""
        await self._client.read_data()

    # -------------------------------
    # region Control
    # -------------------------------

    async def disconnect(self):
        """Disconnect form client."""
        await self._call(self._client.disconnect)

    # -------------------------------
    # region Notifications
    # -------------------------------

    def _connection_changed(self, connected: bool):
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, connected=connected))

    # -------------------------------
    # region internal
    # -------------------------------

    async def _async_update_data(self) -> BlancoUnitData:
        """Fetch data from device."""
        try:
            # await self._client.read_data()
            return BlancoUnitData(
                connected=True,
                device_id="",
            )
        except BleakConnectionError as err:
            # treat BleakConnectionError as device not found
            raise UpdateFailed(translation_key="error_device_not_found") from err
        except BleakNotFoundError as err:
            _LOGGER.debug("_async_update_data BleakNotFoundError %s", str(err))
            self._set_unavailable()
            # treat BleakNotFoundError as device not found
            raise UpdateFailed(translation_key="error_device_not_found") from err
        except Exception as err:
            _LOGGER.debug("_async_update_data Exception %s", repr(err))
            self._set_unavailable()
            # Device unreachable → tell HA gracefully
            raise UpdateFailed(
                translation_key="error_unknown",
                translation_placeholders={"error": repr(err)},
            ) from err

    async def _call(self, func, *args, **kwargs):
        """Execute a BLE client call safely."""
        try:
            return await func(*args, **kwargs)
        except BleakConnectionError as err:
            _LOGGER.debug("BleakConnectionError Exception %s", repr(err))
            self._set_unavailable()
            # treat BleakConnectionError as device not found
            raise ServiceValidationError(
                translation_key="error_device_not_found"
            ) from err
        except BleakNotFoundError as err:
            _LOGGER.debug("_async_update_data BleakNotFoundError %s", str(err))
            self._set_unavailable()
            # treat BleakNotFoundError as device not found
            raise ServiceValidationError(
                translation_key="error_device_not_found"
            ) from err
        except Exception as err:
            _LOGGER.debug("_async_update_data Exception %s", repr(err))
            self._set_unavailable()
            # Device unreachable → tell HA gracefully
            raise ServiceValidationError(
                translation_key="error_unknown",
                translation_placeholders={"error": repr(err)},
            ) from err

    def _set_unavailable(self):
        _LOGGER.debug("_set_unavailable width data %s", str(self.data))
        # trigger rediscovery for the device
        bluetooth.async_rediscover_address(self.hass, self.config_entry.data[CONF_MAC])
        if self.data is None:  # may be called before data is available
            return
        # tell HA to refresh all entities
        self.async_set_updated_data(replace(self.data, available=False))
