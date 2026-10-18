"""Diagnostics support for Blanco Unit BLE."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BlancoUnitConfigEntry
from .const import CLOUD_COORDINATOR, CONF_CLOUD_APP_ID, CONF_MAC, CONF_PIN, DOMAIN
from .coordinator import BlancoUnitCoordinator

TO_REDACT = {CONF_PIN, CONF_MAC, CONF_CLOUD_APP_ID}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data
    cloud = (
        hass.data.get(DOMAIN, {}).get(config_entry.entry_id, {}).get(CLOUD_COORDINATOR)
    )

    return {
        "config_entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "config_entry_options": async_redact_data(
            dict(config_entry.options), TO_REDACT
        ),
        "blanco:unit_data": coordinator.data,
        "blanco:cloud_data": cloud.data if cloud else None,
    }
