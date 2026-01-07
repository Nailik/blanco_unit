"""Text entities for Blanco Unit BLE entities."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BlancoUnitConfigEntry


async def async_setup_entry(
    _: HomeAssistant,
    config_entry: BlancoUnitConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Text entities."""
    # No text entities currently configured
    async_add_entities([])
