"""Home Assistant services provided by the Blanco Unit integration."""

import json
import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    CONF_PIN,
    DOMAIN,
    HA_SERVICE_ATTR_AMOUNT_ML,
    HA_SERVICE_ATTR_CO2_INTENSITY,
    HA_SERVICE_ATTR_DATA,
    HA_SERVICE_ATTR_DEVICE_ID,
    HA_SERVICE_ATTR_NEW_PIN,
    HA_SERVICE_ATTR_UPDATE_CONFIG,
    HA_SERVICE_CHANGE_PIN,
    HA_SERVICE_DISPENSE_WATER,
    HA_SERVICE_SCAN_PROTOCOL,
)
from .coordinator import BlancoUnitCoordinator

_LOGGER = logging.getLogger(__name__)

# Service schemas
def _validate_amount_ml(value: int) -> int:
    """Validate amount is a multiple of 100."""
    if value % 100 != 0:
        raise vol.Invalid("Amount must be a multiple of 100ml")
    return value


SERVICE_DISPENSE_WATER_SCHEMA = vol.Schema(
    {
        vol.Required(HA_SERVICE_ATTR_DEVICE_ID): cv.string,
        vol.Required(HA_SERVICE_ATTR_AMOUNT_ML): vol.All(
            vol.Coerce(int),
            vol.Range(min=100, max=1500),
            _validate_amount_ml,
        ),
        vol.Required(HA_SERVICE_ATTR_CO2_INTENSITY): vol.All(
            vol.Coerce(int), vol.In([1, 2, 3])
        ),
    }
)

SERVICE_CHANGE_PIN_SCHEMA = vol.Schema(
    {
        vol.Required(HA_SERVICE_ATTR_DEVICE_ID): cv.string,
        vol.Required(HA_SERVICE_ATTR_NEW_PIN): vol.All(
            cv.string,
            vol.Length(min=5, max=5),
            vol.Match(r"^\d{5}$"),
        ),
        vol.Optional(HA_SERVICE_ATTR_UPDATE_CONFIG, default=False): cv.boolean,
    }
)

SERVICE_SCAN_PROTOCOL_SCHEMA = vol.Schema(
    {
        vol.Required(HA_SERVICE_ATTR_DEVICE_ID): cv.string,
        vol.Required(HA_SERVICE_ATTR_DATA): dict,
    }
)


def async_setup_services(hass: HomeAssistant) -> None:
    """Set up Blanco Unit integration services."""
    _LOGGER.debug("async_setup_services called")

    # Only register services once
    if hass.services.has_service(DOMAIN, HA_SERVICE_DISPENSE_WATER):
        _LOGGER.debug("Services already registered, skipping")
        return

    async def handle_dispense_water(call: ServiceCall) -> None:
        """Handle the dispense_water service call."""
        _LOGGER.debug("Dispense water service called with data: %s", call.data)
        coordinator = _get_coordinator(hass, call)
        amount_ml = call.data[HA_SERVICE_ATTR_AMOUNT_ML]
        co2_intensity = call.data[HA_SERVICE_ATTR_CO2_INTENSITY]

        await coordinator.dispense_water(amount_ml, co2_intensity)

    async def handle_change_pin(call: ServiceCall) -> None:
        """Handle the change_pin service call."""
        _LOGGER.debug("Change PIN service called with data: %s", call.data)
        coordinator = _get_coordinator(hass, call)
        new_pin = call.data[HA_SERVICE_ATTR_NEW_PIN]
        update_config = call.data[HA_SERVICE_ATTR_UPDATE_CONFIG]

        # Change the PIN on the device
        await coordinator.change_pin(new_pin)

        # If update_config is True, update the config entry with the new PIN
        if update_config:
            device_id = call.data[HA_SERVICE_ATTR_DEVICE_ID]
            registry = dr.async_get(hass)
            device = registry.async_get(device_id)
            if device:
                entry_id = next(iter(device.config_entries))
                entry = hass.config_entries.async_get_entry(entry_id)
                if entry:
                    # Update the config entry with the new PIN
                    hass.config_entries.async_update_entry(
                        entry,
                        data={**entry.data, CONF_PIN: int(new_pin)},
                    )
                    _LOGGER.info("Updated config entry with new PIN")
                    # Reload the config entry to reconnect with new PIN
                    await hass.config_entries.async_reload(entry_id)

    async def handle_scan_protocol(call: ServiceCall) -> dict:
        """Handle the scan_protocol_parameters service call."""

        _LOGGER.debug("Scan protocol service called with data: %s", call.data)
        coordinator = _get_coordinator(hass, call)

        # Extract parameters from the data object
        data = call.data[HA_SERVICE_ATTR_DATA]
        evt_type = data.get("evt_type", 7)
        ctrl = data.get("ctrl")
        pars = data.get("pars")

        _LOGGER.info(
            "Testing protocol parameters: evt_type=%d, ctrl=%s, pars=%s",
            evt_type,
            ctrl,
            pars,
        )

        # Test the specific parameter combination
        response = await coordinator.test_protocol_parameters(
            evt_type, ctrl, pars
        )

        result = {
            "evt_type": evt_type,
            "ctrl": ctrl,
            "pars": pars,
            "success": response is not None,
            "response": response if response else None,
        }

        _LOGGER.info("Response: %s", json.dumps(response, indent=2))
        return result

    hass.services.async_register(
        DOMAIN,
        HA_SERVICE_DISPENSE_WATER,
        handle_dispense_water,
        schema=SERVICE_DISPENSE_WATER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        HA_SERVICE_CHANGE_PIN,
        handle_change_pin,
        schema=SERVICE_CHANGE_PIN_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        HA_SERVICE_SCAN_PROTOCOL,
        handle_scan_protocol,
        schema=SERVICE_SCAN_PROTOCOL_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def _get_coordinator(hass: HomeAssistant, call: ServiceCall) -> BlancoUnitCoordinator:
    """Extract device_id from service call and return the coordinator."""
    device_id = call.data.get(HA_SERVICE_ATTR_DEVICE_ID)
    if not device_id:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_id_not_specified",
        )

    registry = dr.async_get(hass)
    device = registry.async_get(device_id)
    if not device:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={
                "device_id": str(device_id),
            },
        )

    entry_id = next(iter(device.config_entries))
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={
                "device_id": str(device_id),
            },
        )

    runtime_data = entry.runtime_data
    if not isinstance(runtime_data, BlancoUnitCoordinator):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_runtime_data",
            translation_placeholders={
                "device_id": str(device_id),
            },
        )

    return runtime_data
