"""Button entities to define actions for Vogels Motion Mount BLE entities."""

from dataclasses import replace

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
):
    """Set up the RefreshData and SelectPreset buttons."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    async_add_entities(
        [
            DisconnectButton(coordinator),
            UpdateButton(coordinator),
        ]
    )


class DisconnectButton(BlancoUnitBaseEntity, ButtonEntity):
    """Set up the Button that provides an action to disconnect data."""

    _attr_unique_id = "disconnect"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:power-plug-off"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability only if device is connected currently."""
        return self.coordinator.data.connected

    async def async_press(self):
        """Execute disconnect."""
        await self.coordinator.disconnect()


class UpdateButton(BlancoUnitBaseEntity, ButtonEntity):
    """Set up the Button that provides an action to disconnect data."""

    _attr_unique_id = "update"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:power-plug-off"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability only if device is connected currently."""
        return True

    async def async_press(self):
        """Execute disconnect."""
        await self.coordinator.read_data()
