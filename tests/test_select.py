"""Tests for the Blanco Unit select entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.blanco_unit.const import CONF_MAC, CONF_NAME, CONF_PIN, DOMAIN
from custom_components.blanco_unit.data import BlancoUnitData, BlancoUnitSettings
from custom_components.blanco_unit.select import (
    TemperatureSelect,
    WaterHardnessSelect,
    async_setup_entry,
)
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
        ),
    )
    coordinator.set_temperature = AsyncMock()
    coordinator.set_water_hardness = AsyncMock()
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
        patch("custom_components.blanco_unit.PLATFORMS", [Platform.SELECT]),
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
    ("device_type", "expected_count"),
    [
        (1, 2),
        (2, 3),
    ],
)
async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_config_entry,
    mock_coordinator,
    device_type,
    expected_count,
) -> None:
    """Test async_setup_entry creates correct select entities per device type."""
    mock_coordinator.data.device_type = device_type
    mock_config_entry.runtime_data = mock_coordinator
    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    assert len(entities_added) == expected_count

    entity_types = [type(entity).__name__ for entity in entities_added]
    assert "TemperatureSelect" in entity_types
    assert "WaterHardnessSelect" in entity_types
    if device_type == 2:
        assert "HeatingTemperatureSelect" in entity_types


async def test_temperature_select(mock_coordinator) -> None:
    """Test TemperatureSelect."""
    select = TemperatureSelect(mock_coordinator)

    assert select.available is True
    assert select.current_option == "7"
    assert select.unique_id == "temperature"


async def test_temperature_select_options(mock_coordinator) -> None:
    """Test TemperatureSelect has correct options."""
    select = TemperatureSelect(mock_coordinator)

    expected_options = ["4", "5", "6", "7", "8", "9", "10"]
    assert select.options == expected_options


async def test_temperature_select_option(mock_coordinator) -> None:
    """Test TemperatureSelect async_select_option method."""
    select = TemperatureSelect(mock_coordinator)

    await select.async_select_option("8")

    mock_coordinator.set_temperature.assert_called_once_with(8)


async def test_temperature_select_unavailable(mock_coordinator) -> None:
    """Test TemperatureSelect when settings is None."""
    mock_coordinator.data.settings = None
    select = TemperatureSelect(mock_coordinator)

    assert select.available is False
    assert select.current_option is None


async def test_water_hardness_select(mock_coordinator) -> None:
    """Test WaterHardnessSelect."""
    select = WaterHardnessSelect(mock_coordinator)

    assert select.available is True
    assert select.current_option == "5"
    assert select.unique_id == "water_hardness"


async def test_water_hardness_select_options(mock_coordinator) -> None:
    """Test WaterHardnessSelect has correct options."""
    select = WaterHardnessSelect(mock_coordinator)

    expected_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
    assert select.options == expected_options


async def test_water_hardness_select_option(mock_coordinator) -> None:
    """Test WaterHardnessSelect async_select_option method."""
    select = WaterHardnessSelect(mock_coordinator)

    await select.async_select_option("7")

    mock_coordinator.set_water_hardness.assert_called_once_with(7)


async def test_water_hardness_select_unavailable(mock_coordinator) -> None:
    """Test WaterHardnessSelect when settings is None."""
    mock_coordinator.data.settings = None
    select = WaterHardnessSelect(mock_coordinator)

    assert select.available is False
    assert select.current_option is None


async def test_temperature_select_all_options(mock_coordinator) -> None:
    """Test TemperatureSelect can select all valid options."""
    select = TemperatureSelect(mock_coordinator)

    for temp in ["4", "5", "6", "7", "8", "9", "10"]:
        await select.async_select_option(temp)

    assert mock_coordinator.set_temperature.call_count == 7
    mock_coordinator.set_temperature.assert_any_call(4)
    mock_coordinator.set_temperature.assert_any_call(5)
    mock_coordinator.set_temperature.assert_any_call(6)
    mock_coordinator.set_temperature.assert_any_call(7)
    mock_coordinator.set_temperature.assert_any_call(8)
    mock_coordinator.set_temperature.assert_any_call(9)
    mock_coordinator.set_temperature.assert_any_call(10)


async def test_water_hardness_select_all_options(mock_coordinator) -> None:
    """Test WaterHardnessSelect can select all valid options."""
    select = WaterHardnessSelect(mock_coordinator)

    for hardness in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
        await select.async_select_option(hardness)

    assert mock_coordinator.set_water_hardness.call_count == 9
    for i in range(1, 10):
        mock_coordinator.set_water_hardness.assert_any_call(i)


async def test_select_entity_when_data_unavailable(mock_coordinator) -> None:
    """Test select entity when data is unavailable."""
    mock_coordinator.data.available = False
    select = TemperatureSelect(mock_coordinator)

    assert select.available is False


async def test_temperature_select_different_values(mock_coordinator) -> None:
    """Test TemperatureSelect with different current values."""
    select = TemperatureSelect(mock_coordinator)

    # Test with different temperature values
    mock_coordinator.data.settings.set_point_cooling = 4
    assert select.current_option == "4"

    mock_coordinator.data.settings.set_point_cooling = 10
    assert select.current_option == "10"


async def test_water_hardness_select_different_values(mock_coordinator) -> None:
    """Test WaterHardnessSelect with different current values."""
    select = WaterHardnessSelect(mock_coordinator)

    # Test with different hardness values
    mock_coordinator.data.settings.wtr_hardness = 1
    assert select.current_option == "1"

    mock_coordinator.data.settings.wtr_hardness = 9
    assert select.current_option == "9"


async def test_temperature_select_string_to_int_conversion(mock_coordinator) -> None:
    """Test that TemperatureSelect converts string to int."""
    select = TemperatureSelect(mock_coordinator)

    await select.async_select_option("8")

    # Should convert to int
    mock_coordinator.set_temperature.assert_called_once_with(8)


async def test_water_hardness_select_string_to_int_conversion(mock_coordinator) -> None:
    """Test that WaterHardnessSelect converts string to int."""
    select = WaterHardnessSelect(mock_coordinator)

    await select.async_select_option("7")

    # Should convert to int
    mock_coordinator.set_water_hardness.assert_called_once_with(7)
