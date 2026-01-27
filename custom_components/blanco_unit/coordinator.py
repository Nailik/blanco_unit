"""Coordinator for Blanco Unit BLE integration in order to communicate with client."""

from collections.abc import Callable
from dataclasses import replace
from datetime import timedelta
import logging
from typing import Any

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

from .client import BlancoUnitAuthenticationError, BlancoUnitBluetoothClient
from .const import CONF_MAC, CONF_PIN, DOMAIN
from .data import BlancoUnitData

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


class BlancoUnitCoordinator(DataUpdateCoordinator[BlancoUnitData]):
    """Blanco Unit BLE coordinator."""

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
        self.mac_address = config_entry.data[CONF_MAC]

        # Create client
        self._client = BlancoUnitBluetoothClient(
            pin=str(config_entry.data[CONF_PIN]),
            device=device,
            connection_callback=self._connection_changed,
        )

        # Initialise DataUpdateCoordinator
        # Water dispenser - update more frequently than motion mount (1 minute vs 5 minutes)
        super().__init__(
            hass,
            _LOGGER,
            name=config_entry.title,
            config_entry=config_entry,
            update_interval=timedelta(minutes=1),
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

    async def unload(self) -> None:
        """Disconnect and unload."""
        _LOGGER.debug("unload coordinator")
        self._unsub_unavailable_update_listener()
        self._unsub_available_update_listener()
        await self._client.disconnect()

    async def refresh_data(self) -> None:
        """Load data from client."""
        self.hass.async_create_task(self.async_request_refresh())

    # -------------------------------
    # region Control
    # -------------------------------

    async def disconnect(self) -> None:
        """Disconnect from client."""
        await self._call(self._client.disconnect)

    async def set_temperature(self, cooling_celsius: int) -> None:
        """Set target cooling temperature (4-10°C)."""
        await self._call(self._client.set_temperature, cooling_celsius)
        # Refresh settings to verify the change
        settings = await self._call(self._client.get_settings)
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, settings=settings))
        if settings.set_point_cooling != cooling_celsius:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_saved_temperature",
                translation_placeholders={
                    "expected": str(cooling_celsius),
                    "actual": str(settings.set_point_cooling),
                },
            )

    async def set_water_hardness(self, level: int) -> None:
        """Set water hardness level (1-9)."""
        await self._call(self._client.set_water_hardness, level)
        # Refresh settings to verify the change
        settings = await self._call(self._client.get_settings)
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, settings=settings))
        if settings.wtr_hardness != level:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="not_saved_water_hardness",
                translation_placeholders={
                    "expected": str(level),
                    "actual": str(settings.wtr_hardness),
                },
            )

    async def dispense_water(self, amount_ml: int, co2_intensity: int) -> None:
        """Dispense water with specified amount and CO2 intensity."""
        await self._call(self._client.dispense_water, amount_ml, co2_intensity)
        # Trigger refresh after dispensing
        self.hass.async_create_task(self.async_request_refresh())

    async def change_pin(self, new_pin: str) -> None:
        """Change the device PIN."""
        await self._call(self._client.change_pin, new_pin)
        # Disconnect after PIN change as reconnection with new PIN is needed
        await self.disconnect()

    async def set_calibration_still(self, amount: int) -> None:
        """Set calibration for still water."""
        await self._call(self._client.set_calibration_still, amount)
        # Refresh settings to get updated calibration value
        settings = await self._call(self._client.get_settings)
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, settings=settings))

    async def set_calibration_soda(self, amount: int) -> None:
        """Set calibration for soda water."""
        await self._call(self._client.set_calibration_soda, amount)
        # Refresh settings to get updated calibration value
        settings = await self._call(self._client.get_settings)
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, settings=settings))

    # -------------------------------
    # region Notifications
    # -------------------------------

    def _connection_changed(self, connected: bool) -> None:
        if self.data is not None:
            self.async_set_updated_data(replace(self.data, connected=connected))

    # -------------------------------
    # region Testing
    # -------------------------------

    async def test_protocol_parameters(
        self, evt_type: int, ctrl: int | None = None, pars: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Test protocol parameters by sending a custom event."""
        return await self._call(
            self._client.test_protocol_parameters, evt_type, ctrl, pars
        )

    # -------------------------------
    # region internal
    # -------------------------------

    async def _async_update_data(self) -> BlancoUnitData:
        """Fetch data from device."""
        try:
            return BlancoUnitData(
                system_info=await self._client.get_system_info(),
                settings=await self._client.get_settings(),
                status=await self._client.get_status(),
                identity=await self._client.get_device_identity(),
                wifi_info=await self._client.get_wifi_info(),
                connected=self._client.is_connected,
                available=True,
                device_id=self._client.device_id or "",
            )
        except BlancoUnitAuthenticationError as err:
            self._set_unavailable()
            # reraise auth issues
            _LOGGER.debug("_async_update_data ConfigEntryAuthFailed %s", str(err))
            raise ConfigEntryAuthFailed from err
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

    async def _call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a BLE client call safely."""
        try:
            return await func(*args, **kwargs)
        except BlancoUnitAuthenticationError as err:
            # reraise auth issues
            _LOGGER.debug("_call ConfigEntryAuthFailed %s", str(err))
            raise ConfigEntryAuthFailed from err
        except BleakConnectionError as err:
            _LOGGER.debug("BleakConnectionError Exception %s", repr(err))
            self._set_unavailable()
            # treat BleakConnectionError as device not found
            raise ServiceValidationError(
                translation_key="error_device_not_found"
            ) from err
        except BleakNotFoundError as err:
            _LOGGER.debug("_call BleakNotFoundError %s", str(err))
            self._set_unavailable()
            # treat BleakNotFoundError as device not found
            raise ServiceValidationError(
                translation_key="error_device_not_found"
            ) from err
        except Exception as err:
            _LOGGER.debug("_call Exception %s", repr(err))
            self._set_unavailable()
            # Device unreachable → tell HA gracefully
            raise ServiceValidationError(
                translation_key="error_unknown",
                translation_placeholders={"error": repr(err)},
            ) from err

    def _set_unavailable(self) -> None:
        _LOGGER.debug("_set_unavailable width data %s", str(self.data))
        # trigger rediscovery for the device
        bluetooth.async_rediscover_address(self.hass, self.mac_address)
        if self.data is None:  # may be called before data is available
            return
        # tell HA to refresh all entities
        self.async_set_updated_data(replace(self.data, available=False))
