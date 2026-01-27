# Blanco Unit Integration for Home Assistant

[![Open Blanco Unit in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Nailik&repository=blanco_unit&category=integration)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/github/v/release/Nailik/blanco_unit)](https://github.com/Nailik/vogels_motblanco_unition_mount_ble/releases/latest)
![Downloads latest](https://img.shields.io/github/downloads/nailik/blanco_unit/latest/total.svg)
![Downloads](https://img.shields.io/github/downloads/nailik/blanco_unit/total)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

A Home Assistant custom integration for Blanco water dispensers with Bluetooth Low Energy (BLE) connectivity. Control and monitor your Blanco Unit water dispenser directly from Home Assistant.

## Overview

This integration allows you to:

- Monitor filter and CO2 cylinder levels
- Adjust water temperature (4-10°C) and hardness settings (1-9)
- Dispense water programmatically with custom amounts and carbonation levels
- Monitor device status including tap state, cleaning mode, and error codes
- View comprehensive device information including firmware versions and network details
- Create automations based on water dispenser events

## Supported Devices

- **Blanco drink.soda** - Fully tested and supported
- **Blanco Choice** - May work (untested, community feedback welcome)
- **Blanco hot water models** - Not supported

## Requirements

- **Home Assistant**: Version 2025.6.0 or newer
- **Bluetooth**: Your Home Assistant instance must have Bluetooth support enabled
- **Dependencies**: `bleak>=0.21.1` (automatically installed)
- **Device PIN**: The 5-digit PIN code for your Blanco Unit (found in device documentation)

## Installation

### HACS Installation (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add repository URL: `https://github.com/Nailik/blanco_unit`
6. Select category: "Integration"
7. Click "Add"
8. Search for "Blanco Unit" in HACS
9. Click "Download"
10. Restart Home Assistant

### Manual Installation

1. Download the latest release from GitHub
2. Copy the `custom_components/blanco_unit` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Setup

### Automatic Discovery

The integration supports automatic Bluetooth discovery:

1. Navigate to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. If your Blanco Unit is powered on and in Bluetooth range, it should appear in the discovered devices list
4. Select your Blanco Unit
5. Enter your device information:
   - **MAC Address**: Pre-filled from discovery
   - **Device Name**: Choose a friendly name
   - **PIN**: Enter your 5-digit PIN code
6. Click **Submit**

### Manual Setup

If automatic discovery doesn't work:

1. Navigate to **Settings** > **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Blanco Unit"
4. Enter your device information:
   - **MAC Address**: The Bluetooth MAC address of your device (format: XX:XX:XX:XX:XX:XX)
   - **Device Name**: Choose a friendly name
   - **PIN**: Your 5-digit PIN code
5. Click **Submit**

## Data Updates

The integration polls the device every **60 seconds** to update sensor values and status information. You can also trigger manual updates using the "Refresh Data" button entity.

## Entities

Once configured, the integration creates the following entities:

### Sensors (32 total)

#### Status Sensors

- **Filter Capacity Remaining** - Percentage of filter life remaining
- **CO2 Cylinder Remaining** - Percentage of CO2 remaining
- **Tap State** - Current state of the water tap
- **Cleaning Mode State** - Current cleaning mode status
- **Error Code** - Error bits indicating device issues

#### Settings Sensors

- **Filter Lifetime** - Configured filter lifetime in days
- **Post-Flush Quantity** - Post-flush water quantity in mL

#### CHOICE.All Status Sensors

- **Boiler Temperature 1** - Boiler temperature sensor 1 (°C)
- **Boiler Temperature 2** - Boiler temperature sensor 2 (°C)
- **Cooling Temperature** - Compressor/condenser temperature (°C), idles at ~32-34°C, spikes to ~52-55°C when compressor is running
- **Main Controller Status** - Raw main controller status value
- **Connection Controller Status** - Raw connection controller status value

#### Firmware Sensors

- **Main Controller Firmware** - Main controller firmware version
- **Communication Controller Firmware** - Communication controller firmware version
- **Electronic Controller Firmware** - Electronic controller firmware version

#### Device Information Sensors

- **Device Name** - Configured device name
- **Reset Count** - Number of device resets
- **Serial Number** - Device serial number
- **Service Code** - Device service code

#### Network Sensors

- **WiFi Network Name** - Connected WiFi SSID
- **WiFi Signal Strength** - WiFi signal strength in dBm
- **IP Address** - Device IP address
- **Bluetooth MAC Address** - BLE MAC address
- **WiFi MAC Address** - WiFi MAC address
- **Network Gateway** - Gateway IP address
- **Gateway MAC Address** - Gateway MAC address
- **Subnet Mask** - Network subnet mask

### Binary Sensors (6 total)

- **BLE Connection** - Bluetooth connection status
- **Water Dispensing** - Whether water is currently being dispensed
- **Firmware Update Available** - Whether a firmware update is available
- **Cloud Connection** - Cloud service connection status

#### CHOICE.All Binary Sensors

- **Heater Active** - Whether the boiler heater element is currently active (decoded from main controller status bit 13)
- **Compressor Active** - Whether the cooling compressor is currently running (decoded from main controller status bit 14)

### Buttons (2 total)

- **Disconnect** - Manually disconnect from the device
- **Refresh Data** - Manually trigger a data refresh

### Number Entities (2 total)

- **Still Water Calibration** - Calibration value for still water (1-10 mL)
- **Soda Water Calibration** - Calibration value for carbonated water (1-10 mL)

### Select Entities (3 total)

- **Cooling Temperature** - Target water temperature (4-10°C)
  - Options: 4°C (coldest), 5°C, 6°C, 7°C (recommended), 8°C, 9°C, 10°C (warmest)
- **Water Hardness Level** - Water hardness setting (1-9)

#### CHOICE.All Select Entities

- **Heating Temperature** - Target hot water temperature (60-100°C)
  - Level 1: <8°dH
  - Level 2: 8-10°dH
  - Level 3: 11-13°dH
  - Level 4: 14-16°dH
  - Level 5: 17-19°dH
  - Level 6: 20-22°dH
  - Level 7: 23-25°dH
  - Level 8: 26-28°dH
  - Level 9: >28°dH

## Services

### blanco_unit.dispense_water

Dispense water with specified amount and carbonation level.

**Parameters:**

- `device_id` (required): The Blanco Unit device to dispense water from
- `amount_ml` (required): Amount of water in milliliters (100-1500, must be multiple of 100)
- `co2_intensity` (required): Carbonation level
  - `1` = Still water
  - `2` = Medium carbonation
  - `3` = High carbonation

**Example:**

```yaml
service: blanco_unit.dispense_water
data:
  device_id: abc123def456
  amount_ml: 250
  co2_intensity: 2
```

### blanco_unit.change_pin

Change the device PIN code.

**Parameters:**

- `device_id` (required): The Blanco Unit device to change the PIN for
- `new_pin` (required): New 5-digit PIN code (00000-99999)
- `update_config` (optional, default: false): When enabled, automatically updates the integration configuration with the new PIN and reconnects. When disabled, you'll need to manually reconfigure the integration.

**Example:**

```yaml
service: blanco_unit.change_pin
data:
  device_id: abc123def456
  new_pin: "54321"
  update_config: true
```

### blanco_unit.scan_protocol_parameters

Test protocol parameters by sending custom BLE commands to the device. This is a diagnostic tool for developers and advanced users to discover supported device commands or test protocol behavior. Results are returned in the service response and logged to the debug log.

**Parameters:**

- `device_id` (required): The Blanco Unit device to test
- `data` (required): JSON object containing the protocol parameters
  - `evt_type` (required): Event type value (0-255)
  - `ctrl` (optional): Control code value (0-255)
  - `pars` (optional): Parameters dictionary to send with the request

**Example - Get System Information for Blanco Drink.soda:**

See [Event Types](BLUETOOTH_PROTOCOL.md#event-types-blanco-drinksoda) in the protocol documentation for complete details.

```yaml
service: blanco_unit.scan_protocol_parameters
data:
  device_id: abc123def456
  data:
    evt_type: 7
    ctrl: 3
    pars:
      evt_type: 2
response_variable: result
```

**Example - Get Device Status:**

```yaml
service: blanco_unit.scan_protocol_parameters
data:
  device_id: abc123def456
  data:
    evt_type: 7
    ctrl: 3
    pars:
      evt_type: 6
response_variable: status
```

The service returns a response with the following structure:

```yaml
evt_type: 7
ctrl: 3
pars:
  evt_type: 2
success: true
response:
  # Device response data
```

## Example Automations

### Low Filter Notification

```yaml
automation:
  - alias: "Blanco Unit - Low Filter Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.blanco_unit_filter_capacity_remaining
        below: 20
    action:
      - service: notify.mobile_app
        data:
          title: "Water Filter Low"
          message: "Blanco Unit filter is at {{ states('sensor.blanco_unit_filter_capacity_remaining') }}%. Time to order a replacement."
```

### Low CO2 Notification

```yaml
automation:
  - alias: "Blanco Unit - Low CO2 Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.blanco_unit_co2_cylinder_remaining
        below: 15
    action:
      - service: notify.mobile_app
        data:
          title: "CO2 Cylinder Low"
          message: "Blanco Unit CO2 is at {{ states('sensor.blanco_unit_co2_cylinder_remaining') }}%. Consider replacing the cylinder."
```

### Morning Water Routine

```yaml
automation:
  - alias: "Blanco Unit - Morning Water"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.blanco_unit_ble_connection
        state: "on"
    action:
      - service: blanco_unit.dispense_water
        data:
          device_id: abc123def456
          amount_ml: 500
          co2_intensity: 1
```

### Temperature Adjustment Based on Season

```yaml
automation:
  - alias: "Blanco Unit - Seasonal Temperature"
    trigger:
      - platform: state
        entity_id: sensor.season
    action:
      - service: select.select_option
        target:
          entity_id: select.blanco_unit_cooling_temperature
        data:
          option: >
            {% if states('sensor.season') == 'summer' %}
              4
            {% else %}
              7
            {% endif %}
```

### Error Code Alert

```yaml
automation:
  - alias: "Blanco Unit - Error Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.blanco_unit_error_code
        above: 0
    action:
      - service: notify.mobile_app
        data:
          title: "Blanco Unit Error"
          message: "Error code {{ states('sensor.blanco_unit_error_code') }} detected. Please check the device."
```

## Troubleshooting

### Device Not Discovered

1. Ensure your Blanco Unit is powered on
2. Verify the device is within Bluetooth range (typically 10 meters)
3. Check that Home Assistant has Bluetooth enabled
4. Try restarting the Blanco Unit
5. Restart Home Assistant's Bluetooth service

### Authentication Failed

1. Verify you're using the correct 5-digit PIN
2. The PIN should be exactly 5 digits (00000-99999)
3. Check your device documentation for the default PIN
4. Try resetting the device PIN (refer to device manual)

### Connection Drops Frequently

1. Check Bluetooth signal strength (WiFi signal sensor)
2. Move Home Assistant closer to the device
3. Check for Bluetooth interference from other devices
4. Consider using a Bluetooth proxy for extended range

### Entities Showing "Unavailable"

1. Check the "BLE Connection" binary sensor status
2. Use the "Refresh Data" button to manually trigger an update
3. Check Home Assistant logs for specific error messages
4. Verify the device is still powered on and responding

### Data Not Updating

1. The integration polls every 60 seconds - wait for the next update cycle
2. Use the "Refresh Data" button for immediate updates
3. Check the "BLE Connection" sensor to ensure connectivity
4. Review Home Assistant logs for connection errors

### Service Calls Not Working

1. Ensure the device is connected (check BLE Connection sensor)
2. Verify you're using the correct device_id
3. Check parameter values are within valid ranges
4. Review Home Assistant logs for specific error messages

## Technical Details

For developers and advanced users interested in the Bluetooth protocol implementation, message formats, and authentication mechanism, see [BLUETOOTH_PROTOCOL.md](BLUETOOTH_PROTOCOL.md).

## Support

- **Issues**: [GitHub Issues](https://github.com/Nailik/blanco_unit/issues)
- **Documentation**: [GitHub Repository](https://github.com/Nailik/blanco_unit)

## License

This integration is provided as-is under the MIT License. See the LICENSE file for details.

## Disclaimer

This is an unofficial integration and is not affiliated with, endorsed by, or connected to Blanco GmbH + Co KG. All product names, logos, and brands are property of their respective owners.
