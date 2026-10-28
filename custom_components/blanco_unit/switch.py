"""Switch entities for Blanco Unit BLE entities."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up the away mode switch if the device reports one."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    settings = coordinator.data.settings
    if settings is not None and settings.absence_mode_active is not None:
        async_add_entities([AwayModeSwitch(coordinator)])


class AwayModeSwitch(BlancoUnitBaseEntity, SwitchEntity):
    """Implementation of the away mode switch."""

    _attr_unique_id = "away_mode"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:bag-suitcase"

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return (
            super().available
            and self.coordinator.data.settings is not None
            and self.coordinator.data.settings.absence_mode_active is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return whether the away mode is active."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.absence_mode_active

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Switch the away mode on."""
        await self.coordinator.set_away_mode(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch the away mode off."""
        await self.coordinator.set_away_mode(False)
