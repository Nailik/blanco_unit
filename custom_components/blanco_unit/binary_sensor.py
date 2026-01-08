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


async def async_setup_entry(
    _: HomeAssistant,
    config_entry: BlancoUnitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data
    async_add_entities(
        [
            ConnectionBinarySensor(coordinator),
            WaterDispensingBinarySensor(coordinator),
            FirmwareUpdateBinarySensor(coordinator),
            CloudConnectBinarySensor(coordinator),
        ]
    )


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
