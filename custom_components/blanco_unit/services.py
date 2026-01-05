"""Home Assistant services provided by the Vogels Motion Mount integration."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import BlancoUnitCoordinator

_LOGGER = logging.getLogger(__name__)

HA_SERVICE_DEVICE_ID = "device_id"
HA_SERVICE_SET_AUTHORISED_USER_PIN = "set_authorised_user_pin"
HA_SERVICE_SET_SUPERVISIOR_PIN = "set_supervisior_pin"
HA_SERVICE_PIN_ID = "pin"

PARALLEL_UPDATES = 1


def async_setup_services(hass: HomeAssistant):
    """Set up my integration services."""
    _LOGGER.debug("async_setup_services calledx ")

    """hass.services.async_register(
        DOMAIN,
        HA_SERVICE_SET_AUTHORISED_USER_PIN,
        _set_authorised_user_pin,
    )

    hass.services.async_register(
        DOMAIN,
        HA_SERVICE_SET_SUPERVISIOR_PIN,
        _set_supervisior_pin,
    )"""


'''
def _get_coordinator(call: ServiceCall) -> VogelsMotionMountBleCoordinator:
    """Extract device_ids from service call and return list of coordinators."""
    device_id = call.data.get(HA_SERVICE_DEVICE_ID)
    if not device_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_id_not_specified",
        )
    hass: HomeAssistant = call.hass
    registry = dr.async_get(hass)
    device = registry.async_get(device_id)
    if not device:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_missing_entry",
            translation_placeholders={
                "device_id": str(device_id),
            },
        )
    entry_id = next(iter(device.config_entries))
    entry: ConfigEntry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_missing_entry",
            translation_placeholders={
                "device_id": str(device_id),
            },
        )
    runtime_data = entry.runtime_data
    if not isinstance(runtime_data, VogelsMotionMountBleCoordinator):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_invalid_runtime_data",
            translation_placeholders={
                "device_id": str(device_id),
                "runtime_data": str(runtime_data),
            },
        )
    return runtime_data


async def _set_authorised_user_pin(call: ServiceCall) -> None:
    _LOGGER.debug("Set authorised user pin service called with data: %s", call.data)
    try:
        await _get_coordinator(call).set_authorised_user_pin(
            call.data[HA_SERVICE_PIN_ID]
        )
    except VogelsMotionMountClientAuthenticationError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="missing_permission",
        ) from err


async def _set_supervisior_pin(call: ServiceCall) -> None:
    _LOGGER.debug("Set supervisior pin service called with data: %s", call.data)
    try:
        await _get_coordinator(call).set_supervisior_pin(call.data[HA_SERVICE_PIN_ID])
    except VogelsMotionMountClientAuthenticationError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="missing_permission",
        ) from err
'''
