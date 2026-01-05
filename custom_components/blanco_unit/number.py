"""Number entities to define properties that can be changed for Vogels Motion Mount BLE entities."""

from dataclasses import replace

from homeassistant.components.number import NumberEntity, NumberMode
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
    """Set up the Numbers for distance, rotation, tv width and preset (distance, rotation)."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    # Enumerate all the sensors in your data value from your DataUpdateCoordinator and add an instance of your sensor class
    # to a list for each one.
    # This maybe different in your specific case, depending on how your data is structured
    async_add_entities([])


'''class DistanceNumber(VogelsMotionMountBleBaseEntity, NumberEntity):
    """NumberEntity to set the distance."""

    _attr_unique_id = "distance"
    _attr_translation_key = _attr_unique_id
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_icon = "mdi:ruler"

    @property
    def native_value(self):
        """Return the state of the entity."""
        if not self.coordinator.data:
            return None
        if self.coordinator.data.requested_distance is not None:
            return self.coordinator.data.requested_distance
        return self.coordinator.data.distance

    async def async_set_native_value(self, value: float) -> None:
        """Set the value from the UI."""
        await self.coordinator.request_distance(int(value))
'''
