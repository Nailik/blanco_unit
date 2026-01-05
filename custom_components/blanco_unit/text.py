"""Number entities to define properties that can be changed for Vogels Motion Mount BLE entities."""

from dataclasses import replace

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BlancoUnitConfigEntry
from .base import BlancoUnitBaseEntity
from .coordinator import BlancoUnitCoordinator


async def async_setup_entry(
    _: HomeAssistant,
    config_entry: BlancoUnitConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the TextEntities for name, preset names and pins."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    async_add_entities([])


'''class NameText(VogelsMotionMountBleBaseEntity, TextEntity):
    """Implementation of a the Name Text."""

    _attr_unique_id = "name"
    _attr_translation_key = _attr_unique_id
    _attr_native_min = 1
    _attr_native_max = 20
    _attr_icon = "mdi:rename-box-outline"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def native_value(self):
        """Return the state of the entity."""
        return self.coordinator.data.name

    @property
    def available(self) -> bool:
        """Set availability if user has permission."""
        return super().available and self.coordinator.data.permissions.change_name

    async def async_set_value(self, value: str) -> None:
        """Set the name value from the UI."""
        await self.coordinator.set_name(value)
'''
