"""Diagnostics support for Blanco Unit BLE."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import BlancoUnitConfigEntry
from .const import CONF_MAC, CONF_PIN
from .coordinator import BlancoUnitCoordinator

TO_REDACT = {CONF_PIN, CONF_MAC}


async def async_get_config_entry_diagnostics(
    _: HomeAssistant, config_entry: BlancoUnitConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    return {
        "config_entry_data": async_redact_data(dict(config_entry.data), TO_REDACT),
        "blanco:unit_data": coordinator.data,
    }
