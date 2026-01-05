"""Binary sensor entities to define properties for Vogels Motion Mount BLE entities."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the connection Sensors."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data
    async_add_entities([])


'''
class ConnectionBinarySensor(BlancoUnitBaseEntity, BinarySensorEntity):
    """Sensor to indicate if the Vogels Motion Mount is connected."""

    _attr_unique_id = "connection"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self):
        """Return if the MotionMount is currently connected."""
        return self.coordinator.data.connected

    @property
    def icon(self):
        """Return icon."""
        return "mdi:wifi" if self.is_on else "mdi:wifi-off"'''
