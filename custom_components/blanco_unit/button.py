"""Button entities to define actions for Blanco Unit BLE entities."""

from homeassistant.components.button import ButtonEntity
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
) -> None:
    """Set up the Disconnect and RefreshData buttons."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    async_add_entities(
        [
            DisconnectButton(coordinator),
            RefreshDataButton(coordinator),
        ]
    )


class DisconnectButton(BlancoUnitBaseEntity, ButtonEntity):
    """Button that provides an action to disconnect from the device."""

    _attr_unique_id = "disconnect"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:connection"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability only if device is connected currently."""
        return super().available and self.coordinator.data.connected

    async def async_press(self) -> None:
        """Execute disconnect."""
        await self.coordinator.disconnect()


class RefreshDataButton(BlancoUnitBaseEntity, ButtonEntity):
    """Button that provides an action to refresh device data."""

    _attr_unique_id = "refresh_data"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    async def async_press(self) -> None:
        """Execute data refresh."""
        await self.coordinator.refresh_data()
