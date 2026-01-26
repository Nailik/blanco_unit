"""Home Assistant services provided by the Blanco Unit integration."""

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    CONF_PIN,
    DOMAIN,
    HA_SERVICE_ATTR_AMOUNT_ML,
    HA_SERVICE_ATTR_CO2_INTENSITY,
    HA_SERVICE_ATTR_CTRL_MAX,
    HA_SERVICE_ATTR_DEVICE_ID,
    HA_SERVICE_ATTR_EVT_TYPE_MAX,
    HA_SERVICE_ATTR_NEW_PIN,
    HA_SERVICE_ATTR_PARS_EVT_TYPE_MAX,
    HA_SERVICE_ATTR_SAVE_TO_FILE,
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
        vol.Optional(HA_SERVICE_ATTR_EVT_TYPE_MAX, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(HA_SERVICE_ATTR_CTRL_MAX, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(HA_SERVICE_ATTR_PARS_EVT_TYPE_MAX, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=255)
        ),
        vol.Optional(HA_SERVICE_ATTR_SAVE_TO_FILE, default=False): cv.boolean,
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

    async def handle_scan_protocol(call: ServiceCall) -> None:
        """Handle the scan_protocol_parameters service call."""
        import json
        from datetime import datetime

        _LOGGER.debug("Scan protocol service called with data: %s", call.data)
        coordinator = _get_coordinator(hass, call)

        evt_type_max = call.data[HA_SERVICE_ATTR_EVT_TYPE_MAX]
        ctrl_max = call.data[HA_SERVICE_ATTR_CTRL_MAX]
        pars_evt_type_max = call.data[HA_SERVICE_ATTR_PARS_EVT_TYPE_MAX]
        save_to_file = call.data[HA_SERVICE_ATTR_SAVE_TO_FILE]

        _LOGGER.info(
            "Starting protocol scan: evt_type=0-%d, ctrl=0-%d, pars_evt_type=0-%d",
            evt_type_max,
            ctrl_max,
            pars_evt_type_max,
        )

        results = []
        total_tests = 0
        successful_tests = 0

        # Scan evt_type values
        for evt_type in range(evt_type_max + 1):
            # Test without ctrl
            total_tests += 1
            response = await coordinator.client.test_protocol_parameters(
                evt_type, None, None
            )
            if response:
                successful_tests += 1
                results.append({
                    "evt_type": evt_type,
                    "ctrl": None,
                    "pars_evt_type": None,
                    "response": response,
                })
                _LOGGER.info(
                    "✓ Found data: evt_type=%d, ctrl=None, pars_evt_type=None",
                    evt_type,
                )

            # Test with ctrl values
            for ctrl in range(ctrl_max + 1):
                # Without pars evt_type
                total_tests += 1
                response = await coordinator.client.test_protocol_parameters(
                    evt_type, ctrl, None
                )
                if response:
                    successful_tests += 1
                    results.append({
                        "evt_type": evt_type,
                        "ctrl": ctrl,
                        "pars_evt_type": None,
                        "response": response,
                    })
                    _LOGGER.info(
                        "✓ Found data: evt_type=%d, ctrl=%d, pars_evt_type=None",
                        evt_type,
                        ctrl,
                    )

                # With pars evt_type values
                for pars_evt_type in range(pars_evt_type_max + 1):
                    total_tests += 1
                    response = await coordinator.client.test_protocol_parameters(
                        evt_type, ctrl, pars_evt_type
                    )
                    if response:
                        successful_tests += 1
                        results.append({
                            "evt_type": evt_type,
                            "ctrl": ctrl,
                            "pars_evt_type": pars_evt_type,
                            "response": response,
                        })
                        _LOGGER.info(
                            "✓ Found data: evt_type=%d, ctrl=%d, pars_evt_type=%d",
                            evt_type,
                            ctrl,
                            pars_evt_type,
                        )

        _LOGGER.info(
            "Protocol scan complete: %d/%d tests returned data", successful_tests, total_tests
        )

        # Log all results in formatted JSON
        if results:
            _LOGGER.info("=" * 70)
            _LOGGER.info("PROTOCOL SCAN RESULTS")
            _LOGGER.info("=" * 70)
            for i, result in enumerate(results, 1):
                _LOGGER.info(
                    "Result %d: evt_type=%s, ctrl=%s, pars_evt_type=%s",
                    i,
                    result["evt_type"],
                    result["ctrl"],
                    result["pars_evt_type"],
                )
                _LOGGER.info("Response: %s", json.dumps(result["response"], indent=2))
            _LOGGER.info("=" * 70)
        else:
            _LOGGER.warning("No meaningful data found in protocol scan")

        # Save to file if requested
        if save_to_file and results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"protocol_scan_{timestamp}.json"
            filepath = hass.config.path(filename)

            try:
                with open(filepath, "w") as f:
                    json.dump(
                        {
                            "timestamp": timestamp,
                            "scan_parameters": {
                                "evt_type_max": evt_type_max,
                                "ctrl_max": ctrl_max,
                                "pars_evt_type_max": pars_evt_type_max,
                            },
                            "summary": {
                                "total_tests": total_tests,
                                "successful_tests": successful_tests,
                            },
                            "results": results,
                        },
                        f,
                        indent=2,
                    )
                _LOGGER.info("Protocol scan results saved to: %s", filepath)
            except Exception as e:  # noqa: BLE001
                _LOGGER.error("Failed to save protocol scan results: %s", e)

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
