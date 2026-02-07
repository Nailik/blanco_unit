# Blanco Unit Bluetooth Protocol Documentation

This document provides comprehensive technical documentation of the Bluetooth Low Energy (BLE) protocol used by Blanco Unit water dispensers. This information is intended for developers who want to understand the communication protocol or contribute to the integration.

## Table of Contents

- [Overview](#overview)
- [BLE GATT Service](#ble-gatt-service)
- [Authentication Mechanism](#authentication-mechanism)
- [Message Format](#message-format)
- [Packet Fragmentation](#packet-fragmentation)
- [Event Types](#event-types)
- [Request/Response Examples](#requestresponse-examples)
- [API Reference](#api-reference)
- [Data Structures](#data-structures)
- [Error Handling](#error-handling)

## Overview

The Blanco Unit uses Bluetooth Low Energy (BLE) GATT services for communication. All data is exchanged as JSON messages transmitted over a single characteristic. The protocol implements:

- **Authentication**: SHA256-based token authentication with salt
- **Fragmentation**: Large messages are split into multiple BLE packets
- **Session Management**: Session-based communication with unique message IDs
- **Request/Response Pattern**: All operations use a request-response pattern

## BLE GATT Service

### Service UUID

```
847bba10-a31f-41bf-a35f-3f73a22bb307
```

This service UUID is used for automatic device discovery via Home Assistant's Bluetooth integration.

### Characteristic UUID

```
3b531d4d-ed58-4677-b2fa-1c72a86082cf
```

This characteristic is used for both reading and writing all data. It supports:

- Write with response
- Read
- Notify (for responses)

### MTU Size

```
Default: 200 bytes
```

The Maximum Transmission Unit (MTU) is set to 200 bytes to accommodate larger messages while maintaining compatibility.

## Authentication Mechanism

### Overview

The Blanco Unit uses SHA256 hashing with salt for authentication. Every request must include a valid authentication token calculated from the PIN and a unique salt.

### Authentication Process

1. **PIN Hashing**: The 5-digit PIN is hashed using SHA256

   ```
   pin_hash = SHA256(pin)
   ```

2. **Salt Generation**: Each request generates a unique salt

   ```
   salt = session_id + request_id
   ```

3. **Token Calculation**: The token is calculated by combining the PIN hash with the salt
   ```
   combined = pin_hash + salt
   token = SHA256(combined)
   ```

### Initial Pairing

The first request after connection is a pairing request (event type 10) that validates the PIN and retrieves the device ID:

```python
{
  "session": 1234567,
  "id": 9876543,
  "type": 1,
  "token": "calculated_sha256_token",
  "salt": "12345679876543",
  "body": {
    "meta": {
      "evt_type": 10,
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123456789
    },
    "pars": {}
  }
}
```

**Response on success:**

```json
{
  "session": 1234567,
  "id": 9876543,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 10,
      "dev_id": "device_unique_id",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123456790
    },
    "results": [...]
  }
}
```

**Response on wrong PIN:**

```json
{
  "body": {
    "results": [
      {
        "pars": {
          "errs": [
            {
              "err_code": 4,
              "err_msg": "Authentication failed"
            }
          ]
        }
      }
    ]
  }
}
```

## Message Format

### Request Envelope

All requests follow this structure:

```json
{
  "session": <integer>,      // Unique session ID (stays same during connection)
  "id": <integer>,           // Unique request ID (changes per request)
  "type": 1,                 // Always 1 for requests
  "token": "<string>",       // Calculated authentication token
  "salt": "<string>",        // Salt used for token calculation
  "body": {
    "meta": {
      "evt_type": <integer>,     // Event type (see Event Types table)
      "dev_id": "<string>",      // Device ID (omitted in pairing request)
      "dev_type": 1,             // Always 1
      "evt_ver": 1,              // Always 1
      "evt_ts": <integer>        // Unix timestamp in milliseconds
    },
    "opts": {                    // Optional, only for certain operations
      "ctrl": <integer>          // Control code
    },
    "pars": {                    // Optional, parameters specific to operation
      // Operation-specific parameters
    }
  }
}
```

### Response Envelope

Responses follow this structure:

```json
{
  "session": <integer>,
  "id": <integer>,
  "type": 2,                 // Always 2 for responses
  "body": {
    "meta": {
      "evt_type": <integer>,
      "dev_id": "<string>",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": <integer>
    },
    "results": [               // Array of results
      {
        "pars": {              // Parameters with device data
          // Response data fields
        }
      }
    ]
  }
}
```

## Packet Fragmentation

Large JSON messages are fragmented into multiple BLE packets to fit within MTU constraints.

### First Packet Format

```
Byte 0:    0xFF (marker for first packet)
Byte 1:    0x00 (reserved)
Byte 2:    <total_packet_count>
Byte 3:    <message_id>
Byte 4:    0x00 (reserved)
Bytes 5+:  <payload_data>
```

**Payload capacity**: MTU - 5 bytes (typically 195 bytes for MTU=200)

### Subsequent Packet Format

```
Byte 0:    <message_id> (same as in first packet)
Byte 1:    <packet_index> (1, 2, 3, ...)
Bytes 2+:  <payload_data>
```

**Payload capacity**: MTU - 2 bytes (typically 198 bytes for MTU=200)

### Payload Format

The payload consists of:

1. UTF-8 encoded JSON string
2. Null terminator (`0x00`)
3. End marker (`0xFF`)

Example:

```
{"session":1234567,"id":...}\x00\xFF
```

### Reassembly Process

1. Read first packet, extract total packet count and message ID
2. Read subsequent packets matching the message ID
3. Concatenate all payload bytes from all packets
4. Split on `0x00` to extract JSON
5. Parse JSON string

## Event Types (Blanco Drink.soda)

### Main Event Types

| Event Type | Control Code | Description                    | Parameters (`pars`)                                                                                                               |
| ---------- | ------------ | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| 7          | 2            | Get device identity            | `{}` - Returns serial number and service code                                                                                     |
| 7          | 3            | Get device information         | `{"evt_type": <sub_evt_type>}` - See sub-event types below                                                                        |
| 7          | 5            | Set device settings            | See settings parameters below                                                                                                     |
| 7          | 10           | Get WiFi information           | `{}` - Returns WiFi SSID, signal, IP, MAC addresses, gateway, subnet                                                              |
| 7          | 13           | Change PIN                     | `{"new_pass": "<5_digit_pin>"}` - Changes device PIN (string)                                                                     |
| 7          | 7            | Connect/disconnect WiFi        | `{"ssid":{"val":"<ssid>"},"password":{"val":"<password>"}}` - Empty strings to disconnect                                         |
| 7          | 12           | Scan available WiFi networks   | `{}` - Returns list of access points with SSID, signal, auth_mode                                                                 |
| 7          | 14           | Allow cloud services           | `{"rca_id":"<id>"}` - Empty string to allow all                                                                                   |
| 7          | 15           | Factory reset                  | `{}` - Performs full software reset                                                                                               |
| 7          | 1000         | Dispense water                 | `{"disp_amt": <amount_ml>, "co2_int": <intensity>}` - Amount: 100-1500ml (multiples of 100), Intensity: 1=still, 2=medium, 3=high |
| 10         | N/A          | Initial pairing/authentication | `{}` - Returns device ID on successful authentication                                                                             |

### Sub-Event Types (evt_type in pars for ctrl=3)

When using event type 7 with control code 3, you must specify a sub-event type in the `pars` field:

| evt_type | Description        | Returns                                                                                                                                                                                                           |
| -------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2        | System information | Firmware versions (`sw_ver_comm_con`, `sw_ver_elec_con`, `sw_ver_main_con`), device name, reset count                                                                                                             |
| 4        | Error information  | Array of errors with `err_code` and `err_msg` (empty array if no errors)                                                                                                                                          |
| 5        | Device settings    | Calibration values, filter lifetime, post-flush quantity, temperature setpoint, water hardness. CHOICE.All adds: heating setpoint, hot water calibration, carbonation ratios                                      |
| 6        | Device status      | Tap state, filter/CO2 remaining percentage, water dispensing active, firmware update available, cleaning mode, error bits. CHOICE.All adds: boiler temperatures, compressor temperature, controller status values |

### Settings Parameters (evt_type=7, ctrl=5)

When setting device configuration, use event type 7 with control code 5 and one of these parameters:

| Setting                 | Parameter Format                         | Valid Values | Description                     |
| ----------------------- | ---------------------------------------- | ------------ | ------------------------------- |
| Cooling temperature     | `{"set_point_cooling": {"val": <temp>}}` | 4-10°C       | Set target cooling temperature  |
| Water hardness          | `{"wtr_hardness": {"val": <level>}}`     | 1-9          | Set water hardness level        |
| Still water calibration | `{"calib_still_wtr": {"val": <amount>}}` | 1-10         | Calibrate still water flow      |
| Soda water calibration  | `{"calib_soda_wtr": {"val": <amount>}}`  | 1-10         | Calibrate carbonated water flow |

## Event Types (Blanco Choice.all)

The Blanco CHOICE.All (device type `dev_type: 2`) uses the same event types, control codes, and message format as the Drink.soda (`dev_type: 1`). The key differences are additional parameters in responses and additional write operations.

### Device Type Identification

The device type is returned in the pairing response (`evt_type: 10`) in the `meta.dev_type` field:

- `dev_type: 1` = Blanco Drink.soda
- `dev_type: 2` = Blanco CHOICE.All

### Additional Status Fields (evt_type=6)

The CHOICE.All status response includes these additional fields alongside the standard Drink.soda fields:

| Parameter                | Type    | Description                                                                                |
| ------------------------ | ------- | ------------------------------------------------------------------------------------------ |
| `temp_boil_1`            | integer | Boiler temperature sensor 1 (°C)                                                           |
| `temp_boil_2`            | integer | Boiler temperature sensor 2 (°C)                                                           |
| `temp_comp`              | integer | Compressor/condenser temperature (°C) - idles at ~32-34°C, spikes to ~52-55°C when running |
| `main_controller_status` | integer | Main controller status bitmask (see bit definitions below)                                 |
| `conn_controller_status` | integer | Connection controller status value                                                         |

#### Main Controller Status Bitmask

The `main_controller_status` field is a bitmask. Known bits:

| Bit  | Hex Value | Description                                                       |
| ---- | --------- | ----------------------------------------------------------------- |
| 8+16 | 0x10100   | Base state bits, always set when device is running (value: 65792) |
| 13   | 0x2000    | Boiler heater element active (heating water to setpoint)          |
| 14   | 0x4000    | Cooling compressor active (compressor running to cool water)      |

**Note:** Heater and compressor never run simultaneously (load management).

### Additional Settings Fields (evt_type=5)

The CHOICE.All settings response includes these additional fields:

| Parameter               | Type  | Description                             |
| ----------------------- | ----- | --------------------------------------- |
| `set_point_heating`     | int   | Heating setpoint temperature (60-100°C) |
| `calib_hot_wtr`         | int   | Hot water calibration value (mL)        |
| `gbl_medium_wtr_ratio`  | float | Medium carbonation water ratio          |
| `gbl_classic_wtr_ratio` | float | Classic carbonation water ratio         |

### Additional Settings Parameters (evt_type=7, ctrl=5)

| Setting             | Parameter Format                         | Valid Values | Description                    |
| ------------------- | ---------------------------------------- | ------------ | ------------------------------ |
| Heating temperature | `{"set_point_heating": {"val": <temp>}}` | 60-100°C     | Set target heating temperature |

## Request/Response Examples

### 1. Initial Pairing

**Request:**

```json
{
  "session": 7780315,
  "id": 9077670,
  "type": 1,
  "token": "993223dcf15d3865439a66ea4b10c576ea485ccf989b6e9c235acdd27bda8634",
  "salt": "77803159077670",
  "body": {
    "meta": {
      "evt_type": 10,
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1767457215710
    },
    "pars": {}
  }
}
```

**Response:**

```json
{
  "session": 7780315,
  "id": 9077670,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 10,
      "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 2706416986,
      "res_type": 2
    }
  }
}
```

### 2. Get System Information

**Request:**

```json
{
  "session": 7780315,
  "id": 7604844,
  "type": 1,
  "token": "6cb618c3e6a95cef6a1178c68fb34d4fa44c0b6ec09142c073ab49bd70786311",
  "salt": "77803157604844",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1767457216910
    },
    "opts": {
      "ctrl": 3
    },
    "pars": {
      "evt_type": 2
    }
  }
}
```

**Response:**

```json
{
  "session": 7780315,
  "id": 7604844,
  "type": 2,
  "body": {
    "results": [
      {
        "meta": {
          "evt_type": 2,
          "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
          "dev_type": 1,
          "evt_ver": 1,
          "evt_ts": 2706418268
        },
        "pars": {
          "sw_ver_comm_con": { "val": "3.1.5" },
          "sw_ver_elec_con": { "val": "101" },
          "sw_ver_main_con": { "val": "112" },
          "dev_name": { "val": "SODA-210" },
          "reset_cnt": { "val": 5 }
        }
      }
    ]
  }
}
```

### 3. Get Device Settings

**Request:**

```json
{
  "session": 7780315,
  "id": 8284286,
  "type": 1,
  "token": "ac69ef6221d96ccdcbfbd301ed4c3dd7e9aadcbbda53ca96b766c4d9e2373c62",
  "salt": "77803158284286",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1767457218005
    },
    "opts": {
      "ctrl": 3
    },
    "pars": {
      "evt_type": 5
    }
  }
}
```

**Response:**

```json
{
  "session": 7780315,
  "id": 8284286,
  "type": 2,
  "body": {
    "results": [
      {
        "meta": {
          "evt_type": 5,
          "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
          "dev_type": 1,
          "evt_ver": 1,
          "evt_ts": 2706419558
        },
        "pars": {
          "calib_still_wtr": { "val": 500 },
          "calib_soda_wtr": { "val": 500 },
          "filter_life_tm": { "val": 560 },
          "post_flush_quantity": { "val": 40 },
          "set_point_cooling": { "val": 5 },
          "wtr_hardness": { "val": 1 }
        }
      }
    ]
  }
}
```

### 4. Get Device Identity

**Request:**

```json
{
  "session": 7780315,
  "id": 7594209,
  "type": 1,
  "token": "c0c5353ef58c1d9ab9e6895ceb68060ad592d2ca26df1612d3424a6c02f40697",
  "salt": "77803157594209",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1767457219648
    },
    "opts": {
      "ctrl": 2
    },
    "pars": {}
  }
}
```

**Response:**

```json
{
  "session": 7780315,
  "id": 7594209,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 3,
      "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 2706420995,
      "act_type": 4
    },
    "pars": {
      "ser_no": "25F2404-56210",
      "serv_code": "75895"
    }
  }
}
```

### 5. Get Device Status

**Request:**

```json
{
  "session": 7780315,
  "id": 3070034,
  "type": 1,
  "token": "17f4d66fcc9b9428e372450ecbb705fa1455de135d2a2c2ebcfaf9610ce52fb0",
  "salt": "77803153070034",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1767457220826
    },
    "opts": {
      "ctrl": 3
    },
    "pars": {
      "evt_type": 6
    }
  }
}
```

**Response:**

```json
{
  "session": 7780315,
  "id": 3070034,
  "type": 2,
  "body": {
    "results": [
      {
        "meta": {
          "evt_type": 6,
          "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
          "dev_type": 1,
          "evt_ver": 1,
          "evt_ts": 2706422191
        },
        "pars": {
          "tap_state": { "val": 0 },
          "filter_rest": { "val": 37 },
          "co2_rest": { "val": 90 },
          "wtr_disp_active": { "val": false },
          "firm_upd_avlb": { "val": false },
          "set_point_cooling": { "val": 5 },
          "clean_mode_state": { "val": 0 },
          "err_bits": { "val": 0 }
        }
      }
    ]
  }
}
```

### 6. Get Error Information

**Request:**

```json
{
  "session": 7780315,
  "id": 3469654,
  "type": 1,
  "token": "8233afd326d15d581e0ee2f31427156d5764c2bdf467251c9971a88db5f5d3cc",
  "salt": "77803153469654",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1767457221996
    },
    "opts": {
      "ctrl": 3
    },
    "pars": {
      "evt_type": 4
    }
  }
}
```

**Response:**

```json
{
  "session": 7780315,
  "id": 3469654,
  "type": 2,
  "body": {
    "results": [
      {
        "meta": {
          "evt_type": 4,
          "dev_id": "52a62a5263f77bd49ff9760b39e613db88293631d6b25561ac9500924a3ed039",
          "dev_type": 1,
          "evt_ver": 1,
          "evt_ts": 2706424036
        },
        "pars": {
          "errs": []
        }
      }
    ]
  }
}
```

### 7. Set Temperature

**Request:**

```json
{
  "session": 1234567,
  "id": 9876547,
  "type": 1,
  "token": "mno345...",
  "salt": "12345679876547",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457100
    },
    "opts": {
      "ctrl": 5
    },
    "pars": {
      "set_point_cooling": { "val": 6 },
      "set_point_heating": { "val": 65 }
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876547,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457101
    },
    "results": []
  }
}
```

### 8. Set Water Hardness

**Request:**

```json
{
  "session": 1234567,
  "id": 9876548,
  "type": 1,
  "token": "pqr678...",
  "salt": "12345679876548",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457200
    },
    "opts": {
      "ctrl": 5
    },
    "pars": {
      "wtr_hardness": { "val": 5 }
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876548,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457201
    },
    "results": []
  }
}
```

### 9. Dispense Water

**Request:**

```json
{
  "session": 1234567,
  "id": 9876549,
  "type": 1,
  "token": "stu901...",
  "salt": "12345679876549",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457300
    },
    "opts": {
      "ctrl": 1000
    },
    "pars": {
      "disp_amt": 250,
      "co2_int": 2
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876549,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457301
    },
    "results": []
  }
}
```

### 10. Change PIN

**Request:**

```json
{
  "session": 1234567,
  "id": 9876550,
  "type": 1,
  "token": "vwx234...",
  "salt": "12345679876550",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457400
    },
    "opts": {
      "ctrl": 13
    },
    "pars": {
      "new_pass": "54321"
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876550,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457401
    },
    "results": []
  }
}
```

### 11. Get WiFi Information

**Request:**

```json
{
  "session": 1234567,
  "id": 9876552,
  "type": 1,
  "token": "bcd890...",
  "salt": "12345679876552",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457600
    },
    "opts": {
      "ctrl": 10
    },
    "pars": {}
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876552,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457601
    },
    "results": [
      {
        "pars": {
          "cloud_connect": { "val": true },
          "ssid": { "val": "MyWiFi" },
          "signal": { "val": -45 },
          "ip": { "val": "192.168.1.100" },
          "b_mac": { "val": "AA:BB:CC:DD:EE:FF" },
          "w_mac": { "val": "11:22:33:44:55:66" },
          "default_gateway": { "val": "192.168.1.1" },
          "default_gateway_mac": { "val": "77:88:99:AA:BB:CC" },
          "subnet": { "val": "255.255.255.0" }
        }
      }
    ]
  }
}
```

### 12. Set Calibration

**Request (Still Water):**

```json
{
  "session": 1234567,
  "id": 9876553,
  "type": 1,
  "token": "efg123...",
  "salt": "12345679876553",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457700
    },
    "opts": {
      "ctrl": 5
    },
    "pars": {
      "calib_still_wtr": { "val": 7 }
    }
  }
}
```

**Request (Soda Water):**

```json
{
  "session": 1234567,
  "id": 9876554,
  "type": 1,
  "token": "hij456...",
  "salt": "12345679876554",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457800
    },
    "opts": {
      "ctrl": 5
    },
    "pars": {
      "calib_soda_wtr": { "val": 8 }
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876553,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457701
    },
    "results": []
  }
}
```

### 13. Scan WiFi Networks

**Request:**

```json
{
  "session": 1234567,
  "id": 9876555,
  "type": 1,
  "token": "klm789...",
  "salt": "12345679876555",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457900
    },
    "opts": {
      "ctrl": 12
    },
    "pars": {}
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876555,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123457901
    },
    "results": [
      {
        "pars": {
          "aps": [{ "ssid": "xxx", "signal": 66, "auth_mode": 3 }]
        }
      }
    ]
  }
}
```

### 14. Connect to WiFi

**Request:**

```json
{
  "session": 1234567,
  "id": 9876556,
  "type": 1,
  "token": "nop012...",
  "salt": "12345679876556",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123458000
    },
    "opts": {
      "ctrl": 7
    },
    "pars": {
      "ssid": { "val": "Wifi" },
      "password": { "val": "mypassword" }
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876556,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123458001
    },
    "results": [
      {
        "pars": {}
      }
    ]
  }
}
```

### 15. Disconnect from WiFi

**Request:**

```json
{
  "session": 1234567,
  "id": 9876557,
  "type": 1,
  "token": "qrs345...",
  "salt": "12345679876557",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123458100
    },
    "opts": {
      "ctrl": 7
    },
    "pars": {
      "ssid": { "val": "" },
      "password": { "val": "" }
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876557,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123458101
    },
    "results": [
      {
        "pars": {}
      }
    ]
  }
}
```

### 16. Allow Cloud Services

**Request:**

```json
{
  "session": 1234567,
  "id": 9876558,
  "type": 1,
  "token": "tuv678...",
  "salt": "12345679876558",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123458200
    },
    "opts": {
      "ctrl": 14
    },
    "pars": {
      "rca_id": ""
    }
  }
}
```

**Response:**

```json
{
  "session": 1234567,
  "id": 9876558,
  "type": 2,
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123458201
    },
    "results": [
      {
        "pars": {}
      }
    ]
  }
}
```

### 17. Factory Reset

**Request:**

```json
{
  "session": 1234567,
  "id": 9876559,
  "type": 1,
  "token": "wxy901...",
  "salt": "12345679876559",
  "body": {
    "meta": {
      "evt_type": 7,
      "dev_id": "ABC123DEF456",
      "dev_type": 1,
      "evt_ver": 1,
      "evt_ts": 1704123458300
    },
    "opts": {
      "ctrl": 15
    },
    "pars": {}
  }
}
```

**Response:** Device resets, no response expected.

## API Reference

### Authentication

#### `calculate_token(pin: str, salt: str) -> str`

Calculate authentication token from PIN and salt.

**Parameters:**

- `pin`: 5-digit PIN code as string
- `salt`: Salt string (typically `session_id + request_id`)

**Returns:** SHA256 hash as hexadecimal string

**Implementation:**

```python
pin_hash = hashlib.sha256(pin.encode('utf-8')).hexdigest()
combined = pin_hash + salt
token = hashlib.sha256(combined.encode('utf-8')).hexdigest()
```

### Read Operations

#### `get_system_info() -> BlancoUnitSystemInfo`

Retrieve firmware versions, device name, and reset count.

**Protocol:** Event type 7, control 3, pars `{"evt_type": 2}`

**Returns:**

- `sw_ver_comm_con`: Communication controller firmware version
- `sw_ver_elec_con`: Electronic controller firmware version
- `sw_ver_main_con`: Main controller firmware version
- `dev_name`: Device name
- `reset_cnt`: Number of device resets

#### `get_settings() -> BlancoUnitSettings`

Retrieve device configuration settings.

**Protocol:** Event type 7, control 3, pars `{"evt_type": 5}`

**Returns:**

- `calib_still_wtr`: Still water calibration (1-10)
- `calib_soda_wtr`: Soda water calibration (1-10)
- `filter_life_tm`: Filter lifetime in days
- `post_flush_quantity`: Post-flush quantity in mL
- `set_point_cooling`: Target cooling temperature (4-10°C)
- `wtr_hardness`: Water hardness level (1-9)
- `set_point_heating`: Heating setpoint temperature in °C (CHOICE.All only, 0 for drink.soda)
- `calib_hot_wtr`: Hot water calibration in mL (CHOICE.All only)
- `gbl_medium_wtr_ratio`: Medium carbonation water ratio (CHOICE.All only)
- `gbl_classic_wtr_ratio`: Classic carbonation water ratio (CHOICE.All only)

#### `get_status() -> BlancoUnitStatus`

Retrieve real-time device status.

**Protocol:** Event type 7, control 3, pars `{"evt_type": 6}`

**Returns:**

- `tap_state`: Current tap state
- `filter_rest`: Filter capacity remaining (0-100%)
- `co2_rest`: CO2 remaining (0-100%)
- `wtr_disp_active`: Water currently dispensing (boolean)
- `firm_upd_avlb`: Firmware update available (boolean)
- `set_point_cooling`: Current temperature setting
- `clean_mode_state`: Cleaning mode state
- `err_bits`: Error code bits
- `temp_boil_1`: Boiler temperature sensor 1 in °C (CHOICE.All only)
- `temp_boil_2`: Boiler temperature sensor 2 in °C (CHOICE.All only)
- `temp_comp`: Compressor/condenser temperature in °C (CHOICE.All only)
- `main_controller_status`: Main controller status bitmask (CHOICE.All only)
- `conn_controller_status`: Connection controller status (CHOICE.All only)

#### `get_device_identity() -> BlancoUnitIdentity`

Retrieve device serial number and service code.

**Protocol:** Event type 7, control 2, pars `{}`

**Returns:**

- `serial_no`: Device serial number
- `service_code`: Device service code

#### `get_wifi_info() -> BlancoUnitWifiInfo`

Retrieve WiFi and network information.

**Protocol:** Event type 7, control 10, pars `{}`

**Returns:**

- `cloud_connect`: Cloud connection status (boolean)
- `ssid`: WiFi network name
- `signal`: WiFi signal strength (dBm)
- `ip`: IP address
- `ble_mac`: Bluetooth MAC address
- `wifi_mac`: WiFi MAC address
- `gateway`: Gateway IP address
- `gateway_mac`: Gateway MAC address
- `subnet`: Subnet mask

### Write Operations

#### `set_temperature(cooling_celsius: int) -> bool`

Set cooling temperature.

**Protocol:** Event type 7, control 5, pars `{"set_point_cooling": {"val": <temp>}, "set_point_heating": {"val": 65}}`

**Parameters:**

- `cooling_celsius`: Temperature in Celsius (4-10)

**Returns:** True if successful

#### `set_heating_temperature(heating_celsius: int) -> bool`

Set heating/boiling temperature (CHOICE.All only).

**Protocol:** Event type 7, control 5, pars `{"set_point_heating": {"val": <temp>}}`

**Parameters:**

- `heating_celsius`: Temperature in Celsius (60-100)

**Returns:** True if successful

#### `set_water_hardness(level: int) -> bool`

Set water hardness level.

**Protocol:** Event type 7, control 5, pars `{"wtr_hardness": {"val": <level>}}`

**Parameters:**

- `level`: Hardness level (1-9)

**Returns:** True if successful

#### `change_pin(new_pin: str) -> bool`

Change device PIN.

**Protocol:** Event type 7, control 13, pars `{"new_pass": "<new_pin>"}`

**Parameters:**

- `new_pin`: New 5-digit PIN as string

**Returns:** True if successful

**Note:** After changing PIN, reconnection with new PIN is required.

#### `dispense_water(amount_ml: int, co2_intensity: int) -> bool`

Dispense water with specified amount and carbonation.

**Protocol:** Event type 7, control 1000, pars `{"disp_amt": <amount>, "co2_int": <intensity>}`

**Parameters:**

- `amount_ml`: Amount in milliliters (100-1500, must be multiple of 100)
- `co2_intensity`: Carbonation level (1=still, 2=medium, 3=high)

**Returns:** True if dispensing started successfully

#### `set_calibration_still(amount: int) -> bool`

Set calibration for still water.

**Protocol:** Event type 7, control 5, pars `{"calib_still_wtr": {"val": <amount>}}`

**Parameters:**

- `amount`: Calibration amount (1-10)

**Returns:** True if successful

#### `set_calibration_soda(amount: int) -> bool`

Set calibration for soda water.

**Protocol:** Event type 7, control 5, pars `{"calib_soda_wtr": {"val": <amount>}}`

**Parameters:**

- `amount`: Calibration amount (1-10)

**Returns:** True if successful

#### `scan_wifi_networks() -> list[BlancoUnitWifiNetwork]`

Scan for available WiFi networks.

**Protocol:** Event type 7, control 12, pars `{}`

**Returns:** List of `BlancoUnitWifiNetwork` with ssid, signal, auth_mode

#### `connect_wifi(ssid: str, password: str) -> bool`

Connect the device to a WiFi network.

**Protocol:** Event type 7, control 7, pars `{"ssid":{"val":"<ssid>"},"password":{"val":"<password>"}}`

**Parameters:**

- `ssid`: WiFi network name
- `password`: WiFi password

**Returns:** True if successful

#### `disconnect_wifi() -> bool`

Disconnect the device from WiFi.

**Protocol:** Event type 7, control 7, pars `{"ssid":{"val":""},"password":{"val":""}}`

**Returns:** True if successful

#### `allow_cloud_services(rca_id: str = "") -> bool`

Allow cloud services.

**Protocol:** Event type 7, control 14, pars `{"rca_id":"<rca_id>"}`

**Parameters:**

- `rca_id`: RCA identifier (empty string to allow all)

**Returns:** True if successful

#### `factory_reset() -> bool`

Perform full software reset.

**Protocol:** Event type 7, control 15, pars `{}`

**Returns:** True if successful

**Note:** Device will reset after this command. No response is expected. Reconnection will be required.

## Data Structures

### BlancoUnitSystemInfo

```python
@dataclass
class BlancoUnitSystemInfo:
    sw_ver_comm_con: str      # Communication controller firmware
    sw_ver_elec_con: str      # Electronic controller firmware
    sw_ver_main_con: str      # Main controller firmware
    dev_name: str             # Device name
    reset_cnt: int            # Reset count
```

### BlancoUnitSettings

```python
@dataclass
class BlancoUnitSettings:
    calib_still_wtr: int      # Still water calibration (1-10)
    calib_soda_wtr: int       # Soda water calibration (1-10)
    filter_life_tm: int       # Filter lifetime (days)
    post_flush_quantity: int  # Post-flush quantity (mL)
    set_point_cooling: int    # Temperature setting (4-10°C)
    wtr_hardness: int         # Water hardness level (1-9)
    # CHOICE.All specific fields (default to 0 for drink.soda)
    set_point_heating: int = 0       # Heating setpoint (60-100°C)
    calib_hot_wtr: int = 0           # Hot water calibration (mL)
    gbl_medium_wtr_ratio: float = 0.0  # Medium carbonation water ratio
    gbl_classic_wtr_ratio: float = 0.0 # Classic carbonation water ratio
```

### BlancoUnitStatus

```python
@dataclass
class BlancoUnitStatus:
    tap_state: int            # Tap state code
    filter_rest: int          # Filter remaining (0-100%)
    co2_rest: int             # CO2 remaining (0-100%)
    wtr_disp_active: bool     # Water dispensing active
    firm_upd_avlb: bool       # Firmware update available
    set_point_cooling: int    # Current temperature
    clean_mode_state: int     # Cleaning mode state
    err_bits: int             # Error bits
    # CHOICE.All specific fields (default to 0 for drink.soda)
    temp_boil_1: int = 0              # Boiler temperature sensor 1 (°C)
    temp_boil_2: int = 0              # Boiler temperature sensor 2 (°C)
    temp_comp: int = 0                # Compressor/condenser temperature (°C)
    main_controller_status: int = 0   # Main controller status bitmask
    conn_controller_status: int = 0   # Connection controller status
```

### BlancoUnitIdentity

```python
@dataclass
class BlancoUnitIdentity:
    serial_no: str            # Serial number
    service_code: str         # Service code
```

### BlancoUnitWifiInfo

```python
@dataclass
class BlancoUnitWifiInfo:
    cloud_connect: bool       # Cloud connection status
    ssid: str                 # WiFi SSID
    signal: int               # Signal strength (dBm)
    ip: str                   # IP address
    ble_mac: str              # Bluetooth MAC address
    wifi_mac: str             # WiFi MAC address
    gateway: str              # Gateway IP
    gateway_mac: str          # Gateway MAC address
    subnet: str               # Subnet mask
```

### BlancoUnitWifiNetwork

```python
@dataclass
class BlancoUnitWifiNetwork:
    ssid: str        # WiFi network name
    signal: int      # Signal strength (0-100)
    auth_mode: int   # Authentication mode (3 = WPA/WPA2)
```

## Error Handling

### Error Response Format

Errors are returned in the `pars.errs` array of the response:

```json
{
  "body": {
    "results": [{
      "pars": {
        "errs": [{
          "err_code": <integer>,
          "err_msg": "<string>"
        }]
      }
    }]
  }
}
```

### Error Codes

| Code  | Description           | Action                           |
| ----- | --------------------- | -------------------------------- |
| 4     | Authentication failed | Wrong PIN - verify PIN and retry |
| Other | Various device errors | Check device status and logs     |

### Error Handling Best Practices

1. **Authentication Errors (Code 4)**:

   - Verify PIN is correct
   - Re-authenticate with correct PIN
   - Update configuration if PIN was changed

2. **Connection Errors**:

   - Check Bluetooth connectivity
   - Verify device is powered on
   - Ensure device is in range
   - Retry with exponential backoff

3. **Timeout Errors**:

   - Maximum 40 read attempts (configurable)
   - Wait between read attempts
   - Reconnect if timeouts persist

4. **Incomplete Responses**:
   - Verify packet count matches expected
   - Check message ID consistency
   - Re-request data if fragmentation fails

## Implementation Notes

### Session Management

- Generate a unique session ID on connection (7-digit random number)
- Session ID remains constant during the connection
- Generate unique request ID for each message (7-digit random number)
- Message ID for packet fragmentation cycles from 1-255

### Threading and Concurrency

- Use async/await for BLE operations
- Implement connection lock to prevent concurrent connection attempts
- Single connection per device instance

### Performance Optimization

- Cache session data during connection
- Reuse protocol instance for multiple requests
- Implement request queue if needed

### Security Considerations

- PIN is never transmitted in plain text
- Token is regenerated for each request with unique salt
- SHA256 provides strong authentication
- Session-based communication prevents replay attacks

## Contributing

If you discover additional protocol features, error codes, or event types not documented here, please contribute by:

1. Opening an issue with detailed information
2. Submitting a pull request with documentation updates
3. Providing packet captures or logs (with sensitive data removed)

## References

- **Integration Repository**: https://github.com/Nailik/blanco_unit
- **Bleak Documentation**: https://bleak.readthedocs.io/
- **Home Assistant Bluetooth**: https://www.home-assistant.io/integrations/bluetooth/
