"""Select entities to define properties for Blanco Unit BLE entities."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory, UnitOfTemperature
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
    """Set up the Selectors for temperature and water hardness."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    async_add_entities(
        [
            TemperatureSelect(coordinator),
            WaterHardnessSelect(coordinator),
        ]
    )


class TemperatureSelect(BlancoUnitBaseEntity, SelectEntity):
    """Implementation of the Temperature Selector (4-10°C)."""

    _attr_unique_id = "temperature"
    _attr_translation_key = _attr_unique_id
    _attr_options = ["4", "5", "6", "7", "8", "9", "10"]
    _attr_icon = "mdi:thermometer"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return (
            super().available
            and self.coordinator.data.settings is not None
        )

    @property
    def current_option(self) -> str | None:
        """Return the current temperature setting."""
        if self.coordinator.data.settings is None:
            return None
        return str(self.coordinator.data.settings.set_point_cooling)

    async def async_select_option(self, option: str) -> None:
        """Select a temperature option."""
        await self.coordinator.set_temperature(int(option))


class WaterHardnessSelect(BlancoUnitBaseEntity, SelectEntity):
    """Implementation of the Water Hardness Selector (1-9)."""

    _attr_unique_id = "water_hardness"
    _attr_translation_key = _attr_unique_id
    _attr_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    _attr_icon = "mdi:water-opacity"
    _attr_entity_category = EntityCategory.CONFIG

    # Water hardness level descriptions (in °dH - German hardness degrees)
    _HARDNESS_LEVELS = {
        1: "<8 °dH",
        2: "8-10 °dH",
        3: "11-13 °dH",
        4: "14-16 °dH",
        5: "17-19 °dH",
        6: "20-22 °dH",
        7: "23-25 °dH",
        8: "26-28 °dH",
        9: ">28 °dH",
    }

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return (
            super().available
            and self.coordinator.data.settings is not None
        )

    @property
    def current_option(self) -> str | None:
        """Return the current water hardness setting."""
        if self.coordinator.data.settings is None:
            return None
        return str(self.coordinator.data.settings.wtr_hardness)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return extra state attributes with hardness description."""
        if self.coordinator.data.settings is None:
            return None
        level = self.coordinator.data.settings.wtr_hardness
        return {
            "hardness_range": self._HARDNESS_LEVELS.get(level, "Unknown"),
        }

    async def async_select_option(self, option: str) -> None:
        """Select a water hardness level."""
        await self.coordinator.set_water_hardness(int(option))
