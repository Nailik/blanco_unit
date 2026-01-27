"""Select entities to define properties for Blanco Unit BLE entities."""

from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorDeviceClass
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
) -> None:
    """Set up the Selectors for temperature and water hardness."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    async_add_entities(
        [
            TemperatureSelect(coordinator),
            HeatingTemperatureSelect(coordinator),
            WaterHardnessSelect(coordinator),
        ]
    )


class TemperatureSelect(BlancoUnitBaseEntity, SelectEntity):
    """Implementation of the Temperature Selector (4-10°C)."""

    _attr_unique_id = "temperature"
    _attr_translation_key = _attr_unique_id
    _attr_options = ["4", "5", "6", "7", "8", "9", "10"]
    _attr_device_class = SensorDeviceClass.TEMPERATURE
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


class HeatingTemperatureSelect(BlancoUnitBaseEntity, SelectEntity):
    """Implementation of the Heating Temperature Selector (60-100°C, CHOICE.All only)."""

    _attr_unique_id = "heating_temperature"
    _attr_translation_key = _attr_unique_id
    _attr_options = [str(t) for t in range(60, 101)]  # 60-100°C
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def entity_registry_visible_default(self) -> bool:
        """Return if the entity should be visible when first added."""
        return self.coordinator.data.device_type == 2

    @property
    def available(self) -> bool:
        """Set availability if settings are available and device supports heating."""
        return (
            super().available
            and self.coordinator.data.settings is not None
            and self.coordinator.data.settings.set_point_heating > 0
        )

    @property
    def current_option(self) -> str | None:
        """Return the current heating temperature setting."""
        if self.coordinator.data.settings is None:
            return None
        return str(self.coordinator.data.settings.set_point_heating)

    async def async_select_option(self, option: str) -> None:
        """Select a heating temperature option."""
        await self.coordinator.set_heating_temperature(int(option))


class WaterHardnessSelect(BlancoUnitBaseEntity, SelectEntity):
    """Implementation of the Water Hardness Selector (1-9)."""

    _attr_unique_id = "water_hardness"
    _attr_translation_key = _attr_unique_id
    _attr_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    _attr_icon = "mdi:water-opacity"
    _attr_entity_category = EntityCategory.CONFIG

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

    async def async_select_option(self, option: str) -> None:
        """Select a water hardness level."""
        await self.coordinator.set_water_hardness(int(option))
