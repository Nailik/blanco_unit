"""Button entities to define actions for Vogels Motion Mount BLE entities."""

from dataclasses import replace
from typing import Any

from homeassistant.components.switch import SwitchEntity
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

    async_add_entities([])


'''class MultiPinFeatureChangePresetsSwitch(VogelsMotionMountBleBaseEntity, SwitchEntity):
    """Set up the Switch to change multi pin feature change presets."""

    _attr_unique_id = "change_presets"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:security"
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self) -> bool:
        """Set availability of multi pin features."""
        return super().available and self.coordinator.data.permissions.change_settings

    @property
    def is_on(self) -> bool:
        """Returns on if change_presets is enabled."""
        return self.coordinator.data.multi_pin_features.change_presets

    async def async_turn_on(self, **_: Any):
        """Turn the entity on."""
        await self.async_toggle()

    async def async_turn_off(self, **_: Any):
        """Turn the entity off."""
        await self.async_toggle()

    async def async_toggle(self, **_: Any):
        """Toggle if change presets is on or off."""
        await self.coordinator.set_multi_pin_features(
            replace(
                self.coordinator.data.multi_pin_features, change_presets=not self.is_on
            )
        )
'''
