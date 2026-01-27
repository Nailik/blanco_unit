"""Sensor entities to define properties for Blanco Unit BLE entities."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
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
    """Set up the sensors for Blanco Unit."""
    coordinator: BlancoUnitCoordinator = config_entry.runtime_data

    entities = [
            # Status sensors
            FilterRemainingSensor(coordinator),
            CO2RemainingSensor(coordinator),
            TapStateSensor(coordinator),
            CleanModeStateSensor(coordinator),
            ErrorBitsSensor(coordinator),
            # Settings sensors
            FilterLifetimeSensor(coordinator),
            PostFlushQuantitySensor(coordinator),
            # System info sensors
            FirmwareMainSensor(coordinator),
            FirmwareCommSensor(coordinator),
            FirmwareElecSensor(coordinator),
            DeviceNameSensor(coordinator),
            ResetCountSensor(coordinator),
            DeviceTypeSensor(coordinator),
            DeviceIdSensor(coordinator),
            # Identity sensors
            SerialNumberSensor(coordinator),
            ServiceCodeSensor(coordinator),
            # WiFi sensors
            WiFiSSIDSensor(coordinator),
            WiFiSignalSensor(coordinator),
            IPAddressSensor(coordinator),
            BLEMacSensor(coordinator),
            WiFiMacSensor(coordinator),
            GatewaySensor(coordinator),
            GatewayMacSensor(coordinator),
            SubnetSensor(coordinator),
        ]
    # CHOICE.All status sensors
    entitiesExtended = [
        BoilerTemp1Sensor(coordinator),
        BoilerTemp2Sensor(coordinator),
        CoolingTempSensor(coordinator),
        MainControllerStatusSensor(coordinator),
        ConnControllerStatusSensor(coordinator),
        MediumCarbonationRatioSensor(coordinator),
        ClassicCarbonationRatioSensor(coordinator),
        HeatingSetpointSensor(coordinator),
        HotWaterCalibrationSensor(coordinator),
    ]
    if coordinator.data.device_type == 2:
        entities.extend(entitiesExtended)
    async_add_entities(entities)


# -------------------------------
# Status Sensors
# -------------------------------


class FilterRemainingSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for remaining filter capacity."""

    _attr_unique_id = "filter_remaining"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the filter remaining percentage."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.filter_rest


class CO2RemainingSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for remaining CO2 capacity."""

    _attr_unique_id = "co2_remaining"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the CO2 remaining percentage."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.co2_rest


class TapStateSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for tap state."""

    _attr_unique_id = "tap_state"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:water-pump"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the tap state."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.tap_state


class CleanModeStateSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for clean mode state."""

    _attr_unique_id = "clean_mode_state"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:spray"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the clean mode state."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.clean_mode_state


class ErrorBitsSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for error bits."""

    _attr_unique_id = "error_bits"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:alert-circle"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the error bits."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.err_bits


# -------------------------------
# CHOICE.All Status Sensors
# -------------------------------


class BoilerTemp1Sensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for boiler temperature 1 (CHOICE.All only)."""

    _attr_unique_id = "boiler_temp_1"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-water"

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the boiler temperature 1."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.temp_boil_1


class BoilerTemp2Sensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for boiler temperature 2 (CHOICE.All only)."""

    _attr_unique_id = "boiler_temp_2"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-water"

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the boiler temperature 2."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.temp_boil_2


class CoolingTempSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for compressor temperature (CHOICE.All only).

    Measures the compressor/condenser temperature (hot side of cooling system).
    Idles at ~32-34°C, spikes to ~52-55°C when compressor is running.
    """

    _attr_unique_id = "cooling_temp"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heat-wave"

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the cooling compartment temperature."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.temp_comp


class MainControllerStatusSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for main controller status (CHOICE.All only)."""

    _attr_unique_id = "main_controller_status"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the main controller status."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.main_controller_status


class ConnControllerStatusSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for connection controller status (CHOICE.All only)."""

    _attr_unique_id = "conn_controller_status"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if status is available."""
        return super().available and self.coordinator.data.status is not None

    @property
    def native_value(self) -> int | None:
        """Return the connection controller status."""
        if self.coordinator.data.status is None:
            return None
        return self.coordinator.data.status.conn_controller_status


# -------------------------------
# Settings Sensors
# -------------------------------


class FilterLifetimeSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for filter lifetime."""

    _attr_unique_id = "filter_lifetime"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_icon = "mdi:calendar-clock"
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> int | None:
        """Return the filter lifetime."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.filter_life_tm


class PostFlushQuantitySensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for post flush quantity."""

    _attr_unique_id = "post_flush_quantity"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_icon = "mdi:water"
    _attr_native_unit_of_measurement = "mL"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> int | None:
        """Return the post flush quantity."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.post_flush_quantity


# -------------------------------
# CHOICE.All Settings Sensors
# -------------------------------


class HeatingSetpointSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for heating setpoint temperature (CHOICE.All only)."""

    _attr_unique_id = "heating_setpoint"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_icon = "mdi:thermometer-high"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> int | None:
        """Return the heating setpoint temperature."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.set_point_heating


class HotWaterCalibrationSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for hot water calibration (CHOICE.All only)."""

    _attr_unique_id = "hot_water_calibration"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.VOLUME
    _attr_icon = "mdi:water-thermometer"
    _attr_native_unit_of_measurement = "mL"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> int | None:
        """Return the hot water calibration."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.calib_hot_wtr


class MediumCarbonationRatioSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for medium carbonation water ratio (CHOICE.All only)."""

    _attr_unique_id = "medium_carbonation_ratio"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:gas-cylinder"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> float | None:
        """Return the medium carbonation water ratio."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.gbl_medium_wtr_ratio


class ClassicCarbonationRatioSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for classic carbonation water ratio (CHOICE.All only)."""

    _attr_unique_id = "classic_carbonation_ratio"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:gas-cylinder"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if settings are available."""
        return super().available and self.coordinator.data.settings is not None

    @property
    def native_value(self) -> float | None:
        """Return the classic carbonation water ratio."""
        if self.coordinator.data.settings is None:
            return None
        return self.coordinator.data.settings.gbl_classic_wtr_ratio


# -------------------------------
# System Info Sensors
# -------------------------------


class FirmwareMainSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for main controller firmware version."""

    _attr_unique_id = "firmware_main"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if system info is available."""
        return super().available and self.coordinator.data.system_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the main firmware version."""
        if self.coordinator.data.system_info is None:
            return None
        return self.coordinator.data.system_info.sw_ver_main_con


class FirmwareCommSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for communication controller firmware version."""

    _attr_unique_id = "firmware_comm"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if system info is available."""
        return super().available and self.coordinator.data.system_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the comm firmware version."""
        if self.coordinator.data.system_info is None:
            return None
        return self.coordinator.data.system_info.sw_ver_comm_con


class FirmwareElecSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for electronic controller firmware version."""

    _attr_unique_id = "firmware_elec"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:chip"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if system info is available."""
        return super().available and self.coordinator.data.system_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the elec firmware version."""
        if self.coordinator.data.system_info is None:
            return None
        return self.coordinator.data.system_info.sw_ver_elec_con


class DeviceNameSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for device name."""

    _attr_unique_id = "device_name"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:label"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if system info is available."""
        return super().available and self.coordinator.data.system_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the device name."""
        if self.coordinator.data.system_info is None:
            return None
        return self.coordinator.data.system_info.dev_name


class ResetCountSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for reset count."""

    _attr_unique_id = "reset_count"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def available(self) -> bool:
        """Set availability if system info is available."""
        return super().available and self.coordinator.data.system_info is not None

    @property
    def native_value(self) -> int | None:
        """Return the reset count."""
        if self.coordinator.data.system_info is None:
            return None
        return self.coordinator.data.system_info.reset_cnt


class DeviceTypeSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for device type."""

    _attr_unique_id = "device_type"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:information"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | None:
        """Return the device type."""
        return self.coordinator.data.device_type


class DeviceIdSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for device id."""

    _attr_unique_id = "device_id"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:information"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> str | None:
        """Return the device id."""
        return self.coordinator.data.device_id


# -------------------------------
# Identity Sensors
# -------------------------------


class SerialNumberSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for device serial number."""

    _attr_unique_id = "serial_number"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:barcode"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if identity is available."""
        return super().available and self.coordinator.data.identity is not None

    @property
    def native_value(self) -> str | None:
        """Return the serial number."""
        if self.coordinator.data.identity is None:
            return None
        return self.coordinator.data.identity.serial_no


class ServiceCodeSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for device service code."""

    _attr_unique_id = "service_code"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:barcode-scan"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if identity is available."""
        return super().available and self.coordinator.data.identity is not None

    @property
    def native_value(self) -> str | None:
        """Return the service code."""
        if self.coordinator.data.identity is None:
            return None
        return self.coordinator.data.identity.service_code


# -------------------------------
# WiFi Sensors
# -------------------------------


class WiFiSSIDSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for WiFi SSID."""

    _attr_unique_id = "wifi_ssid"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:wifi"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the WiFi SSID."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.ssid


class WiFiSignalSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for WiFi signal strength."""

    _attr_unique_id = "wifi_signal"
    _attr_translation_key = _attr_unique_id
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> int | None:
        """Return the WiFi signal strength."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.signal


class IPAddressSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for IP address."""

    _attr_unique_id = "ip_address"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:ip-network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the IP address."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.ip


class BLEMacSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for BLE MAC address."""

    _attr_unique_id = "ble_mac"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:bluetooth"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the BLE MAC address."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.ble_mac


class WiFiMacSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for WiFi MAC address."""

    _attr_unique_id = "wifi_mac"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the WiFi MAC address."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.wifi_mac


class GatewaySensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for gateway IP address."""

    _attr_unique_id = "gateway"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:router-network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the gateway IP."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.gateway


class GatewayMacSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for gateway MAC address."""

    _attr_unique_id = "gateway_mac"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:router-network"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the gateway MAC."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.gateway_mac


class SubnetSensor(BlancoUnitBaseEntity, SensorEntity):
    """Sensor for subnet mask."""

    _attr_unique_id = "subnet"
    _attr_translation_key = _attr_unique_id
    _attr_icon = "mdi:ip-network-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Set availability if wifi info is available."""
        return super().available and self.coordinator.data.wifi_info is not None

    @property
    def native_value(self) -> str | None:
        """Return the subnet mask."""
        if self.coordinator.data.wifi_info is None:
            return None
        return self.coordinator.data.wifi_info.subnet
