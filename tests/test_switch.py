"""Tests for the Blanco Unit switch entities."""

from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.blanco_unit.const import CONF_MAC, CONF_NAME, CONF_PIN, DOMAIN
from custom_components.blanco_unit.data import BlancoUnitData, BlancoUnitSettings
from custom_components.blanco_unit.switch import AwayModeSwitch, async_setup_entry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration  # noqa: TID251


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
        settings=BlancoUnitSettings(
            calib_still_wtr=5,
            calib_soda_wtr=6,
            filter_life_tm=365,
            post_flush_quantity=100,
            set_point_cooling=7,
            wtr_hardness=5,
            absence_mode_active=False,
        ),
    )
    coordinator.set_away_mode = AsyncMock()
    return coordinator


async def test_all_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_blanco_unit_data,
    mock_bluetooth_device,
) -> None:
    """Test all entities."""
    mock_blanco_unit_data.settings = replace(
        mock_blanco_unit_data.settings, absence_mode_active=False
    )
    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "Test Blanco Unit",
            CONF_PIN: 12345,
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )

    with (
        patch("custom_components.blanco_unit.PLATFORMS", [Platform.SWITCH]),
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=mock_bluetooth_device,
        ),
    ):
        await setup_integration(hass, mock_config_entry)

        await snapshot_platform(
            hass, entity_registry, snapshot, mock_config_entry.entry_id
        )


@pytest.mark.parametrize(
    ("absence_mode_active", "expected_count"),
    [
        (None, 0),
        (False, 1),
        (True, 1),
    ],
)
async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_coordinator,
    absence_mode_active,
    expected_count,
) -> None:
    """Test the switch is only created when the device reports an away mode."""
    mock_coordinator.data.settings.absence_mode_active = absence_mode_active
    config_entry = MagicMock()
    config_entry.runtime_data = mock_coordinator
    entities_added = []

    await async_setup_entry(hass, config_entry, entities_added.extend)

    assert len(entities_added) == expected_count


async def test_async_setup_entry_without_settings(
    hass: HomeAssistant, mock_coordinator
) -> None:
    """Test no switch is created before settings were read."""
    mock_coordinator.data.settings = None
    config_entry = MagicMock()
    config_entry.runtime_data = mock_coordinator
    entities_added = []

    await async_setup_entry(hass, config_entry, entities_added.extend)

    assert entities_added == []


async def test_away_mode_switch(mock_coordinator) -> None:
    """Test AwayModeSwitch state."""
    switch = AwayModeSwitch(mock_coordinator)

    assert switch.unique_id == "away_mode"
    assert switch.available is True
    assert switch.is_on is False

    mock_coordinator.data.settings.absence_mode_active = True
    assert switch.is_on is True


async def test_away_mode_switch_turn_on_off(mock_coordinator) -> None:
    """Test AwayModeSwitch turn on and off."""
    switch = AwayModeSwitch(mock_coordinator)

    await switch.async_turn_on()
    mock_coordinator.set_away_mode.assert_awaited_once_with(True)

    mock_coordinator.set_away_mode.reset_mock()
    await switch.async_turn_off()
    mock_coordinator.set_away_mode.assert_awaited_once_with(False)


async def test_away_mode_switch_unavailable(mock_coordinator) -> None:
    """Test AwayModeSwitch when settings are missing."""
    mock_coordinator.data.settings = None
    switch = AwayModeSwitch(mock_coordinator)

    assert switch.available is False
    assert switch.is_on is None
