"""Tests for the Blanco Unit button entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.blanco_unit.button import (
    DisconnectButton,
    RefreshDataButton,
    async_setup_entry,
)
from custom_components.blanco_unit.const import CONF_MAC, CONF_NAME, CONF_PIN, DOMAIN
from custom_components.blanco_unit.data import BlancoUnitData
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import setup_integration  # noqa: TID251


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.config_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
    )
    coordinator.disconnect = AsyncMock()
    coordinator.refresh_data = AsyncMock()
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    return entry


async def test_all_entities(
    hass: HomeAssistant,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    mock_blanco_unit_data,
    mock_bluetooth_device,
) -> None:
    """Test all entities."""
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
        patch("custom_components.blanco_unit.PLATFORMS", [Platform.BUTTON]),
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=mock_bluetooth_device,
        ),
    ):
        await setup_integration(hass, mock_config_entry)

        await snapshot_platform(
            hass, entity_registry, snapshot, mock_config_entry.entry_id
        )


async def test_async_setup_entry(
    hass: HomeAssistant, mock_config_entry, mock_coordinator
) -> None:
    """Test async_setup_entry creates all buttons."""
    mock_config_entry.runtime_data = mock_coordinator
    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Verify both buttons were added
    assert len(entities_added) == 2

    # Verify button types
    button_types = [type(entity).__name__ for entity in entities_added]
    assert "DisconnectButton" in button_types
    assert "RefreshDataButton" in button_types


async def test_disconnect_button(mock_coordinator) -> None:
    """Test DisconnectButton."""
    button = DisconnectButton(mock_coordinator)

    assert button.available is True
    assert button.unique_id == "AA:BB:CC:DD:EE:FF_disconnect"


async def test_disconnect_button_press(mock_coordinator) -> None:
    """Test DisconnectButton async_press method."""
    button = DisconnectButton(mock_coordinator)

    await button.async_press()

    mock_coordinator.disconnect.assert_called_once()


async def test_disconnect_button_unavailable_when_disconnected(
    mock_coordinator,
) -> None:
    """Test DisconnectButton is unavailable when device is disconnected."""
    mock_coordinator.data.connected = False
    button = DisconnectButton(mock_coordinator)

    assert button.available is False


async def test_disconnect_button_unavailable_when_data_unavailable(
    mock_coordinator,
) -> None:
    """Test DisconnectButton is unavailable when data is unavailable."""
    mock_coordinator.data.available = False
    button = DisconnectButton(mock_coordinator)

    assert button.available is False


async def test_refresh_data_button(mock_coordinator) -> None:
    """Test RefreshDataButton."""
    button = RefreshDataButton(mock_coordinator)

    assert button.available is True
    assert button.unique_id == "AA:BB:CC:DD:EE:FF_refresh_data"


async def test_refresh_data_button_press(mock_coordinator) -> None:
    """Test RefreshDataButton async_press method."""
    button = RefreshDataButton(mock_coordinator)

    await button.async_press()

    mock_coordinator.refresh_data.assert_called_once()


async def test_refresh_data_button_available_when_disconnected(
    mock_coordinator,
) -> None:
    """Test RefreshDataButton is available even when disconnected."""
    mock_coordinator.data.connected = False
    button = RefreshDataButton(mock_coordinator)

    # RefreshDataButton should be available as long as data is available
    assert button.available is True


async def test_refresh_data_button_unavailable_when_data_unavailable(
    mock_coordinator,
) -> None:
    """Test RefreshDataButton is unavailable when data is unavailable."""
    mock_coordinator.data.available = False
    button = RefreshDataButton(mock_coordinator)

    assert button.available is False


async def test_disconnect_button_multiple_presses(mock_coordinator) -> None:
    """Test DisconnectButton can be pressed multiple times."""
    button = DisconnectButton(mock_coordinator)

    await button.async_press()
    await button.async_press()
    await button.async_press()

    assert mock_coordinator.disconnect.call_count == 3


async def test_refresh_data_button_multiple_presses(mock_coordinator) -> None:
    """Test RefreshDataButton can be pressed multiple times."""
    button = RefreshDataButton(mock_coordinator)

    await button.async_press()
    await button.async_press()

    assert mock_coordinator.refresh_data.call_count == 2
