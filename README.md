# Blanco Unit Home Assistant Integratioon

[![Open Blanco Unit in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Nailik&repository=blanco_unit&category=integration)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/github/v/release/Nailik/blanco_unit)](https://github.com/Nailik/vogels_motblanco_unition_mount_ble/releases/latest)
![Downloads latest](https://img.shields.io/github/downloads/nailik/blanco_unit/latest/total.svg)
![Downloads](https://img.shields.io/github/downloads/nailik/blanco_unit/total)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

Home Assistant integration allows to control the Blanco Unit over Bluetooth Low Energy (BLE).

## High-level description & use cases

This integration exposes the Blanco Unit as local devices and entities in Home Assistant so you can:

- TODO

Use cases:

- TODO

## Supported device(s)

- [Blanco Unit](https://www.blanco.de/specials/the-blanco-unit/)
  > Tested with Blanco drink.soda FW Versions CC 3.1.5 and MC 1.1.2
  > Other versions like new Blanco Choice may work
  > Hot water not yet supported

## Requirements & prerequisites

- Home Assistant **2025.6.0 or newer**
- Bluetooth support on the host (integration depends on HA’s `bluetooth` integration)
- Python package: **`bleak>=0.21.1`**

## Installation

### Recommended: HACS

1. Use the “Open in HACS” badge above.
2. Install the integration from HACS → Integrations.
3. Restart Home Assistant.

### Manual installation

1. Copy the `custom_components/blanco_unit` folder into `<config>/custom_components/`.
2. Restart Home Assistant.
3. Configure via **Settings → Devices & Services → Add integration → Blanco Unit**.

## Setup

During setup, the integration asks for:

- **MAC** — the BLE MAC address of the device.
- **Device name** — a friendly name for the device (optional).
- **PIN** — PIN to be used

- The integration can **automatically detect the Unit via Bluetooth**.

> **Note**: Ensure your Bluetooth adapter is working and within range of the mount.

## Data updates

- TODO define update rate

## Entities

- TODO define entities

## Actions

- TODO define actions

## Example

- TODO define examples

## Known limitations

The Blanco Unit integration currently has the following limitations:

- Hot water not yet supported
- Blanco Choice not fully supported / tested

## Troubleshooting

If you're experiencing issues with your Blanco Unit integration, try these general troubleshooting steps:

Make sure your Blanco Unit is in range, is powered on and properly also the Bluetooth connection is turned on. Validate if your Bluetooth devices can find the Motion Mount via it's exposed discoveries.

## Removing the integration

This integration follows standard integration removal, no extra steps are required.
