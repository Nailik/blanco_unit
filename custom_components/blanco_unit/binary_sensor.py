"""Binary sensor entities to define properties for Blanco Unit BLE entities."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import BlancoUnitConfigEntry
from .base import BlancoUnitBaseEntity
from .coordinator import BlancoUnitCoordinator

# Main controller status bitmask constants (CHOICE.All)
# Base state (bits 8 + 16) = 65792 is always set when device is running
STATUS_BIT_HEATER = 0x2000  # Bit 13 (8192) - Boiler heater element active
STATUS_BIT_COMPRESSOR = 0x4000  # Bit 14 (16384) - Cooling compressor active


async def async_setup_entry(
    _: HomeAssistant,
    config_entry: BlancoUnitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data
    entities = [
            ConnectionBinarySensor(coordinator),
            WaterDispensingBinarySensor(coordinator),
            FirmwareUpdateBinarySensor(coordinator),
            CloudConnectBinarySensor(coordinator),
    ]

    # CHOICE.All binary sensors (decoded from main_controller_status)
    entitiesExtended = [
        HeaterActiveBinarySensor(coordinator),
        CompressorActiveBinarySensor(coordinator),
    ]
    if coordinator.data.device_type == 2:
        entities.extend(entitiesExtended)
    async_add_entities(entities)


class ConnectionBinarySensor(BlancoUnitBaseEntity, BinarySensorEntity):
    """Sensor to indicate if the Blanco Unit is connected."""

    _attr_unique_id = "connection"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return if the device is currently connected."""
        return self.coordinator.data.connected

    @property
    def icon(self) -> str:
        """Return icon."""
        return "mdi:bluetooth-connect" if self.is_on else "mdi:bluetooth-off"


class WaterDispensingBinarySensor(BlancoUnitBaseEntity, BinarySensorEntity):
    """Sensor to indicate if water is currently being dispensed."""

    _attr_unique_id = "water_dispensing"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:water-pump"

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return (
            super().available
            and self.coordinator.data.status is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return if water is currently being dispensed."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.wtr_disp_active


class FirmwareUpdateBinarySensor(BlancoUnitBaseEntity, BinarySensorEntity):
    """Sensor to indicate if a firmware update is available."""

    _attr_unique_id = "firmware_update"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:update"

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return (
            super().available
            and self.coordinator.data.status is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return if a firmware update is available."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.firm_upd_avlb


class CloudConnectBinarySensor(BlancoUnitBaseEntity, BinarySensorEntity):
    """Sensor to indicate if the device is connected to cloud."""

    _attr_unique_id = "cloud_connection"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cloud"

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return (
            super().available
            and self.coordinator.data.wifi_info is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return if the device is connected to cloud."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.cloud_connect


class HeaterActiveBinarySensor(BlancoUnitBaseEntity, BinarySensorEntity):
    """Sensor to indicate if the boiler heater is active (CHOICE.All only).

    Decoded from main_controller_status bit 13 (0x2000).
    When active, the boiler heater element is on to heat water to setpoint.
    """

    _attr_unique_id = "heater_active"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:fire"

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def is_on(self) -> bool | None:
        """Return if the heater is currently active."""
        if self.coordinator.data.status is None:
            return None
        return bool(
            self.coordinator.data.status.main_controller_status & STATUS_BIT_HEATER
        )


class CompressorActiveBinarySensor(BlancoUnitBaseEntity, BinarySensorEntity):
    """Sensor to indicate if the cooling compressor is active (CHOICE.All only).

    Decoded from main_controller_status bit 14 (0x4000).
    When active, the compressor is running to cool the water compartment.
    Note: Heater and compressor never run simultaneously (load management).
    """

    _attr_unique_id = "compressor_active"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:snowflake"

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def is_on(self) -> bool | None:
        """Return if the compressor is currently active."""
        if self.coordinator.data.status is None:
            return None
        return bool(
            self.coordinator.data.status.main_controller_status & STATUS_BIT_COMPRESSOR
        )
