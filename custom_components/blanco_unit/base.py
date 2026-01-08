"""Base entity to define common properties and methods for Blanco Unit BLE entities."""

from propcache.api import cached_property

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BlancoUnitCoordinator


class BlancoUnitBaseEntity(CoordinatorEntity[BlancoUnitCoordinator]):
    """Base Entity Class for all Entities."""

    _attr_has_entity_name: bool = True

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            name=self.coordinator.name,
            manufacturer="Blanco",
            model="Unit",
            identifiers={(DOMAIN, self.coordinator.address)},
        )

    @property
    def available(self) -> bool:
        """Set availability of the entities only when the BLE device is available."""
        return self.coordinator.data is not None and self.coordinator.data.available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        self.async_write_ha_state()
