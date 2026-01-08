"""Tests for the Blanco Unit base entity."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.blanco_unit.base import BlancoUnitBaseEntity
from custom_components.blanco_unit.data import BlancoUnitData
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = BlancoUnitData(
        connected=True,
        available=True,
        device_id="test_device_id",
    )
    coordinator.name = "Test Blanco Unit"
    coordinator.address = "AA:BB:CC:DD:EE:FF"
    return coordinator


class TestEntity(BlancoUnitBaseEntity):
    """Test entity class for testing base entity."""

    _attr_unique_id = "test_entity"


async def test_base_entity_device_info(mock_coordinator) -> None:
    """Test BlancoUnitBaseEntity device_info property."""
    entity = TestEntity(mock_coordinator)

    device_info = entity.device_info

    assert device_info["name"] == "Test Blanco Unit"
    assert device_info["manufacturer"] == "Blanco"
    assert device_info["model"] == "Unit"
    assert ("blanco_unit", "AA:BB:CC:DD:EE:FF") in device_info["identifiers"]


async def test_base_entity_available(mock_coordinator) -> None:
    """Test BlancoUnitBaseEntity available property."""
    entity = TestEntity(mock_coordinator)

    assert entity.available is True


async def test_base_entity_unavailable_when_data_none(mock_coordinator) -> None:
    """Test BlancoUnitBaseEntity is unavailable when data is None."""
    mock_coordinator.data = None
    entity = TestEntity(mock_coordinator)

    assert entity.available is False


async def test_base_entity_unavailable_when_data_unavailable(mock_coordinator) -> None:
    """Test BlancoUnitBaseEntity is unavailable when data.available is False."""
    mock_coordinator.data.available = False
    entity = TestEntity(mock_coordinator)

    assert entity.available is False


async def test_base_entity_handle_coordinator_update(
    hass: HomeAssistant, mock_coordinator
) -> None:
    """Test BlancoUnitBaseEntity _handle_coordinator_update method."""
    entity = TestEntity(mock_coordinator)

    # Mock async_write_ha_state
    with patch.object(entity, "async_write_ha_state") as mock_write_state:
        entity._handle_coordinator_update()

        mock_write_state.assert_called_once()


async def test_base_entity_has_entity_name(mock_coordinator) -> None:
    """Test BlancoUnitBaseEntity has_entity_name attribute."""
    entity = TestEntity(mock_coordinator)

    assert entity.has_entity_name is True


async def test_base_entity_unique_id(mock_coordinator) -> None:
    """Test BlancoUnitBaseEntity unique_id attribute."""
    entity = TestEntity(mock_coordinator)

    assert entity.unique_id == "test_entity"


async def test_base_entity_coordinator_property(mock_coordinator) -> None:
    """Test BlancoUnitBaseEntity coordinator property."""
    entity = TestEntity(mock_coordinator)

    assert entity.coordinator == mock_coordinator


async def test_base_entity_device_info_cached(mock_coordinator) -> None:
    """Test that device_info is cached (uses cached_property)."""
    entity = TestEntity(mock_coordinator)

    # Call device_info multiple times
    info1 = entity.device_info
    info2 = entity.device_info

    # Should be the same object (cached)
    assert info1 is info2


async def test_base_entity_available_changes_with_data(mock_coordinator) -> None:
    """Test that available property changes when data changes."""
    entity = TestEntity(mock_coordinator)

    # Initially available
    assert entity.available is True

    # Change data availability
    mock_coordinator.data.available = False
    assert entity.available is False

    # Change back
    mock_coordinator.data.available = True
    assert entity.available is True


async def test_base_entity_device_info_identifiers(mock_coordinator) -> None:
    """Test device_info identifiers format."""
    entity = TestEntity(mock_coordinator)

    device_info = entity.device_info
    identifiers = device_info["identifiers"]

    # Should be a set with one tuple
    assert isinstance(identifiers, set)
    assert len(identifiers) == 1

    # Extract the tuple
    identifier = next(iter(identifiers))
    assert identifier[0] == "blanco_unit"
    assert identifier[1] == "AA:BB:CC:DD:EE:FF"


async def test_base_entity_device_info_all_fields(mock_coordinator) -> None:
    """Test all fields in device_info."""
    entity = TestEntity(mock_coordinator)

    device_info = entity.device_info

    assert "name" in device_info
    assert "manufacturer" in device_info
    assert "model" in device_info
    assert "identifiers" in device_info

    assert device_info["name"] == "Test Blanco Unit"
    assert device_info["manufacturer"] == "Blanco"
    assert device_info["model"] == "Unit"


async def test_base_entity_multiple_instances_same_coordinator(
    mock_coordinator,
) -> None:
    """Test multiple entity instances with same coordinator."""
    entity1 = TestEntity(mock_coordinator)
    entity2 = TestEntity(mock_coordinator)

    # Both should reference the same coordinator
    assert entity1.coordinator == entity2.coordinator

    # Both should have same availability
    assert entity1.available == entity2.available

    # Device info should be cached separately for each instance
    info1 = entity1.device_info
    info2 = entity2.device_info

    # Should be different objects (cached per instance)
    assert info1 is not info2

    # But should have same content
    assert info1 == info2


async def test_base_entity_available_with_connected_false(mock_coordinator) -> None:
    """Test that available property is True even when connected is False."""
    mock_coordinator.data.connected = False
    entity = TestEntity(mock_coordinator)

    # Should still be available as long as data.available is True
    assert entity.available is True


async def test_base_entity_available_edge_cases(mock_coordinator) -> None:
    """Test available property edge cases."""
    entity = TestEntity(mock_coordinator)

    # Normal case: data exists and is available
    assert entity.available is True

    # Edge case: data is None
    mock_coordinator.data = None
    assert entity.available is False

    # Edge case: data exists but available is False
    mock_coordinator.data = BlancoUnitData(
        connected=True,
        available=False,
        device_id="test",
    )
    assert entity.available is False

    # Edge case: data exists but available is True, connected is False
    mock_coordinator.data = BlancoUnitData(
        connected=False,
        available=True,
        device_id="test",
    )
    assert entity.available is True
