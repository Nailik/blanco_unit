"""Tests for the Blanco Unit number entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.blanco_unit.const import CONF_MAC, CONF_NAME, CONF_PIN, DOMAIN
from custom_components.blanco_unit.data import BlancoUnitData, BlancoUnitSettings
from custom_components.blanco_unit.number import (
    CalibrationSodaNumber,
    CalibrationStillNumber,
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
    coordinator.set_calibration_still = AsyncMock()
    coordinator.set_calibration_soda = AsyncMock()
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
        patch("custom_components.blanco_unit.PLATFORMS", [Platform.NUMBER]),
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
    """Test async_setup_entry creates all number entities."""
    mock_config_entry.runtime_data = mock_coordinator
    entities_added = []

    def mock_add_entities(entities):
        entities_added.extend(entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    # Verify both number entities were added
    assert len(entities_added) == 2

    # Verify entity types
    entity_types = [type(entity).__name__ for entity in entities_added]
    assert "CalibrationStillNumber" in entity_types
    assert "CalibrationSodaNumber" in entity_types


async def test_calibration_still_number(mock_coordinator) -> None:
    """Test CalibrationStillNumber."""
    number = CalibrationStillNumber(mock_coordinator)

    assert number.available is True
    assert number.native_value == 5
    assert number.unique_id == "calibration_still"


async def test_calibration_still_number_set_value(mock_coordinator) -> None:
    """Test CalibrationStillNumber async_set_native_value method."""
    number = CalibrationStillNumber(mock_coordinator)

    await number.async_set_native_value(7.0)

    mock_coordinator.set_calibration_still.assert_called_once_with(7)


async def test_calibration_still_number_unavailable(mock_coordinator) -> None:
    """Test CalibrationStillNumber when settings is None."""
    mock_coordinator.data.settings = None
    number = CalibrationStillNumber(mock_coordinator)

    assert number.available is False
    assert number.native_value is None


async def test_calibration_soda_number(mock_coordinator) -> None:
    """Test CalibrationSodaNumber."""
    number = CalibrationSodaNumber(mock_coordinator)

    assert number.available is True
    assert number.native_value == 6
    assert number.unique_id == "calibration_soda"


async def test_calibration_soda_number_set_value(mock_coordinator) -> None:
    """Test CalibrationSodaNumber async_set_native_value method."""
    number = CalibrationSodaNumber(mock_coordinator)

    await number.async_set_native_value(8.0)

    mock_coordinator.set_calibration_soda.assert_called_once_with(8)


async def test_calibration_soda_number_unavailable(mock_coordinator) -> None:
    """Test CalibrationSodaNumber when settings is None."""
    mock_coordinator.data.settings = None
    number = CalibrationSodaNumber(mock_coordinator)

    assert number.available is False
    assert number.native_value is None


async def test_calibration_still_number_min_max_values(mock_coordinator) -> None:
    """Test CalibrationStillNumber min and max values."""
    number = CalibrationStillNumber(mock_coordinator)

    assert number.native_min_value == 1
    assert number.native_max_value == 1000
    assert number.native_step == 1


async def test_calibration_soda_number_min_max_values(mock_coordinator) -> None:
    """Test CalibrationSodaNumber min and max values."""
    number = CalibrationSodaNumber(mock_coordinator)

    assert number.native_min_value == 1
    assert number.native_max_value == 1000
    assert number.native_step == 1


async def test_calibration_still_number_set_multiple_values(mock_coordinator) -> None:
    """Test CalibrationStillNumber can set multiple values."""
    number = CalibrationStillNumber(mock_coordinator)

    await number.async_set_native_value(1.0)
    await number.async_set_native_value(5.0)
    await number.async_set_native_value(10.0)

    assert mock_coordinator.set_calibration_still.call_count == 3
    mock_coordinator.set_calibration_still.assert_any_call(1)
    mock_coordinator.set_calibration_still.assert_any_call(5)
    mock_coordinator.set_calibration_still.assert_any_call(10)


async def test_calibration_soda_number_set_multiple_values(mock_coordinator) -> None:
    """Test CalibrationSodaNumber can set multiple values."""
    number = CalibrationSodaNumber(mock_coordinator)

    await number.async_set_native_value(2.0)
    await number.async_set_native_value(6.0)
    await number.async_set_native_value(9.0)

    assert mock_coordinator.set_calibration_soda.call_count == 3
    mock_coordinator.set_calibration_soda.assert_any_call(2)
    mock_coordinator.set_calibration_soda.assert_any_call(6)
    mock_coordinator.set_calibration_soda.assert_any_call(9)


async def test_number_entity_when_data_unavailable(mock_coordinator) -> None:
    """Test number entity when data is unavailable."""
    mock_coordinator.data.available = False
    number = CalibrationStillNumber(mock_coordinator)

    assert number.available is False


async def test_calibration_still_number_float_to_int_conversion(
    mock_coordinator,
) -> None:
    """Test that CalibrationStillNumber converts float to int."""
    number = CalibrationStillNumber(mock_coordinator)

    await number.async_set_native_value(7.5)

    # Should convert to int
    mock_coordinator.set_calibration_still.assert_called_once_with(7)


async def test_calibration_soda_number_float_to_int_conversion(
    mock_coordinator,
) -> None:
    """Test that CalibrationSodaNumber converts float to int."""
    number = CalibrationSodaNumber(mock_coordinator)

    await number.async_set_native_value(8.9)

    # Should convert to int
    mock_coordinator.set_calibration_soda.assert_called_once_with(8)
