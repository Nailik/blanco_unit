"""Number entities to define properties that can be changed for Blanco Unit BLE entities."""

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
) -> None:
    """Set up the Number entities for calibration."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    async_add_entities(
        [
            CalibrationStillNumber(coordinator),
            CalibrationSodaNumber(coordinator),
        ]
    )


class CalibrationStillNumber(BlancoUnitBaseEntity, NumberEntity):
    """NumberEntity to set the still water calibration."""

    _attr_unique_id = "calibration_still"
    _attr_translation_key = _attr_unique_id
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 1000
    _attr_native_step = 1
    _attr_icon = "mdi:water"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = "mL"

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> float | None:
        """Return the state of the entity."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.calib_still_wtr

    async def async_set_native_value(self, value: float) -> None:
        """Set the calibration value from the UI."""
        await self.coordinator.set_calibration_still(int(value))


class CalibrationSodaNumber(BlancoUnitBaseEntity, NumberEntity):
    """NumberEntity to set the soda water calibration."""

    _attr_unique_id = "calibration_soda"
    _attr_translation_key = _attr_unique_id
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 1000
    _attr_native_step = 1
    _attr_icon = "mdi:cup-water"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_unit_of_measurement = "mL"

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> float | None:
        """Return the state of the entity."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.calib_soda_wtr

    async def async_set_native_value(self, value: float) -> None:
        """Set the calibration value from the UI."""
        await self.coordinator.set_calibration_soda(int(value))
