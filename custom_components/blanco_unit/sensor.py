"""Sensor entities to define properties for Vogels Motion Mount BLE entities."""

from homeassistant.components.sensor import SensorEntity
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
    """Set up the Sensors for Distance, Rotation, Pin and Versions."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    async_add_entities([])


'''class DistanceSensor(VogelsMotionMountBleBaseEntity, SensorEntity):
    """Sensor for current distance, may be different from requested distance."""

    _attr_unique_id = "current_distance"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:ruler"
    _attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        """Return the current value."""
        return self.coordinator.data.distance'''
