"""Constants for the Blanco Unit integration."""

DOMAIN = "blanco_unit"
# for this version read_only was added to config selectors
MIN_HA_VERSION = "2025.6.0"

# Config Entry Keys
CONF_MAC = "conf_mac"
CONF_NAME = "conf_name"
CONF_PIN = "conf_pin"
CONF_ERROR = "base"
BLE_CALLBACK = "unregister_ble_callback"

# BLE Protocol Constants
CHARACTERISTIC_UUID = "3b531d4d-ed58-4677-b2fa-1c72a86082cf"
MTU_SIZE = 200

# Service Names
HA_SERVICE_DISPENSE_WATER = "dispense_water"
HA_SERVICE_CHANGE_PIN = "change_pin"
HA_SERVICE_SCAN_PROTOCOL = "scan_protocol_parameters"

# Service Attributes
HA_SERVICE_ATTR_DEVICE_ID = "device_id"
HA_SERVICE_ATTR_AMOUNT_ML = "amount_ml"
HA_SERVICE_ATTR_CO2_INTENSITY = "co2_intensity"
HA_SERVICE_ATTR_NEW_PIN = "new_pin"
HA_SERVICE_ATTR_UPDATE_CONFIG = "update_config"
HA_SERVICE_ATTR_DATA = "data"
