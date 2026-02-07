"""Tests for Blanco Unit services."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import voluptuous as vol

from custom_components.blanco_unit.const import (
    CONF_PIN,
    DOMAIN,
    HA_SERVICE_ALLOW_CLOUD,
    HA_SERVICE_ATTR_AMOUNT_ML,
    HA_SERVICE_ATTR_CO2_INTENSITY,
    HA_SERVICE_ATTR_DEVICE_ID,
    HA_SERVICE_ATTR_NEW_PIN,
    HA_SERVICE_ATTR_PASSWORD,
    HA_SERVICE_ATTR_RCA_ID,
    HA_SERVICE_ATTR_SSID,
    HA_SERVICE_ATTR_UPDATE_CONFIG,
    HA_SERVICE_CHANGE_PIN,
    HA_SERVICE_CONNECT_WIFI,
    HA_SERVICE_DISCONNECT_WIFI,
    HA_SERVICE_DISPENSE_WATER,
    HA_SERVICE_FACTORY_RESET,
    HA_SERVICE_SCAN_WIFI,
)
from custom_components.blanco_unit.coordinator import BlancoUnitCoordinator
from custom_components.blanco_unit.data import BlancoUnitWifiNetwork
from custom_components.blanco_unit.services import (
    SERVICE_ALLOW_CLOUD_SCHEMA,
    SERVICE_CHANGE_PIN_SCHEMA,
    SERVICE_CONNECT_WIFI_SCHEMA,
    SERVICE_DEVICE_ONLY_SCHEMA,
    SERVICE_DISPENSE_WATER_SCHEMA,
    _get_coordinator,
    _validate_amount_ml,
    async_setup_services,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError


def test_validate_amount_ml_valid():
    """Test _validate_amount_ml with valid multiples of 100."""
    assert _validate_amount_ml(100) == 100
    assert _validate_amount_ml(200) == 200
    assert _validate_amount_ml(1500) == 1500


def test_validate_amount_ml_invalid():
    """Test _validate_amount_ml with invalid values."""
    with pytest.raises(vol.Invalid, match="Amount must be a multiple of 100ml"):
        _validate_amount_ml(150)
    with pytest.raises(vol.Invalid, match="Amount must be a multiple of 100ml"):
        _validate_amount_ml(99)
    with pytest.raises(vol.Invalid, match="Amount must be a multiple of 100ml"):
        _validate_amount_ml(1550)


def test_dispense_water_schema_valid():
    """Test dispense water schema with valid data."""
    valid_data = {
        HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
        HA_SERVICE_ATTR_AMOUNT_ML: 500,
        HA_SERVICE_ATTR_CO2_INTENSITY: 2,
    }
    result = SERVICE_DISPENSE_WATER_SCHEMA(valid_data)
    assert result[HA_SERVICE_ATTR_DEVICE_ID] == "test_device_id"
    assert result[HA_SERVICE_ATTR_AMOUNT_ML] == 500
    assert result[HA_SERVICE_ATTR_CO2_INTENSITY] == 2


def test_dispense_water_schema_invalid_amount():
    """Test dispense water schema with invalid amount."""
    # Not a multiple of 100
    with pytest.raises(vol.Invalid):
        SERVICE_DISPENSE_WATER_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_AMOUNT_ML: 150,
                HA_SERVICE_ATTR_CO2_INTENSITY: 2,
            }
        )

    # Below minimum
    with pytest.raises(vol.Invalid):
        SERVICE_DISPENSE_WATER_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_AMOUNT_ML: 50,
                HA_SERVICE_ATTR_CO2_INTENSITY: 2,
            }
        )

    # Above maximum
    with pytest.raises(vol.Invalid):
        SERVICE_DISPENSE_WATER_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_AMOUNT_ML: 1600,
                HA_SERVICE_ATTR_CO2_INTENSITY: 2,
            }
        )


def test_dispense_water_schema_invalid_co2_intensity():
    """Test dispense water schema with invalid CO2 intensity."""
    with pytest.raises(vol.Invalid):
        SERVICE_DISPENSE_WATER_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_AMOUNT_ML: 500,
                HA_SERVICE_ATTR_CO2_INTENSITY: 4,  # Must be 1, 2, or 3
            }
        )


def test_change_pin_schema_valid():
    """Test change PIN schema with valid data."""
    valid_data = {
        HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
        HA_SERVICE_ATTR_NEW_PIN: "12345",
        HA_SERVICE_ATTR_UPDATE_CONFIG: True,
    }
    result = SERVICE_CHANGE_PIN_SCHEMA(valid_data)
    assert result[HA_SERVICE_ATTR_DEVICE_ID] == "test_device_id"
    assert result[HA_SERVICE_ATTR_NEW_PIN] == "12345"
    assert result[HA_SERVICE_ATTR_UPDATE_CONFIG] is True


def test_change_pin_schema_default_update_config():
    """Test change PIN schema with default update_config value."""
    data = {
        HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
        HA_SERVICE_ATTR_NEW_PIN: "54321",
    }
    result = SERVICE_CHANGE_PIN_SCHEMA(data)
    assert result[HA_SERVICE_ATTR_UPDATE_CONFIG] is False


def test_change_pin_schema_invalid_pin_length():
    """Test change PIN schema with invalid PIN length."""
    # Too short
    with pytest.raises(vol.Invalid):
        SERVICE_CHANGE_PIN_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_NEW_PIN: "1234",
            }
        )

    # Too long
    with pytest.raises(vol.Invalid):
        SERVICE_CHANGE_PIN_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_NEW_PIN: "123456",
            }
        )


def test_change_pin_schema_invalid_pin_format():
    """Test change PIN schema with non-numeric PIN."""
    with pytest.raises(vol.Invalid):
        SERVICE_CHANGE_PIN_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_NEW_PIN: "abcde",
            }
        )


async def test_async_setup_services_registers_once(hass: HomeAssistant) -> None:
    """Test that services are only registered once."""
    assert not hass.services.has_service(DOMAIN, HA_SERVICE_DISPENSE_WATER)
    assert not hass.services.has_service(DOMAIN, HA_SERVICE_CHANGE_PIN)

    # First registration
    async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, HA_SERVICE_DISPENSE_WATER)
    assert hass.services.has_service(DOMAIN, HA_SERVICE_CHANGE_PIN)

    # Second registration should not duplicate
    async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, HA_SERVICE_DISPENSE_WATER)
    assert hass.services.has_service(DOMAIN, HA_SERVICE_CHANGE_PIN)


async def test_handle_dispense_water(hass: HomeAssistant) -> None:
    """Test dispense water service handler."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.dispense_water = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_DISPENSE_WATER,
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_AMOUNT_ML: 500,
                HA_SERVICE_ATTR_CO2_INTENSITY: 2,
            },
            blocking=True,
        )

        mock_coordinator.dispense_water.assert_called_once_with(500, 2)


async def test_handle_change_pin_without_config_update(hass: HomeAssistant) -> None:
    """Test change PIN service handler without config update."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.change_pin = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_CHANGE_PIN,
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_NEW_PIN: "12345",
                HA_SERVICE_ATTR_UPDATE_CONFIG: False,
            },
            blocking=True,
        )

        mock_coordinator.change_pin.assert_called_once_with("12345")


async def test_handle_change_pin_with_config_update(hass: HomeAssistant) -> None:
    """Test change PIN service handler with config update."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.change_pin = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"
    mock_entry.runtime_data = mock_coordinator
    mock_entry.data = {CONF_PIN: 54321}

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
        patch.object(hass.config_entries, "async_update_entry") as mock_update_entry,
        patch.object(hass.config_entries, "async_reload") as mock_reload,
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_CHANGE_PIN,
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_NEW_PIN: "12345",
                HA_SERVICE_ATTR_UPDATE_CONFIG: True,
            },
            blocking=True,
        )

        mock_coordinator.change_pin.assert_called_once_with("12345")
        mock_update_entry.assert_called_once()
        mock_reload.assert_called_once_with("test_entry_id")

        # Verify the updated data
        call_args = mock_update_entry.call_args
        assert call_args[1]["data"][CONF_PIN] == 12345


async def test_get_coordinator_missing_device_id(hass: HomeAssistant) -> None:
    """Test _get_coordinator with missing device_id."""
    call = ServiceCall(hass, DOMAIN, "test", {})

    with pytest.raises(ServiceValidationError) as exc_info:
        _get_coordinator(hass, call)

    assert exc_info.value.translation_key == "device_id_not_specified"


async def test_get_coordinator_device_not_found(hass: HomeAssistant) -> None:
    """Test _get_coordinator when device is not found."""
    from homeassistant.helpers import device_registry as dr

    mock_device_registry = MagicMock()
    mock_device_registry.async_get.return_value = None

    call = ServiceCall(hass, DOMAIN, "test", {"device_id": "nonexistent_device"})

    with patch.object(dr, "async_get", return_value=mock_device_registry):
        with pytest.raises(ServiceValidationError) as exc_info:
            _get_coordinator(hass, call)

        assert exc_info.value.translation_key == "device_not_found"


async def test_get_coordinator_config_entry_not_found(hass: HomeAssistant) -> None:
    """Test _get_coordinator when config entry is not found."""
    from homeassistant.helpers import device_registry as dr

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    call = ServiceCall(hass, DOMAIN, "test", {"device_id": "test_device_id"})

    with (
        patch.object(dr, "async_get", return_value=mock_device_registry),
        patch.object(hass.config_entries, "async_get_entry", return_value=None),
    ):
        with pytest.raises(ServiceValidationError) as exc_info:
            _get_coordinator(hass, call)

        assert exc_info.value.translation_key == "config_entry_not_found"


async def test_get_coordinator_invalid_runtime_data(hass: HomeAssistant) -> None:
    """Test _get_coordinator with invalid runtime data."""
    from homeassistant.helpers import device_registry as dr

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = "invalid_data"  # Not a BlancoUnitCoordinator

    call = ServiceCall(hass, DOMAIN, "test", {"device_id": "test_device_id"})

    with (
        patch.object(dr, "async_get", return_value=mock_device_registry),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        with pytest.raises(ServiceValidationError) as exc_info:
            _get_coordinator(hass, call)

        assert exc_info.value.translation_key == "invalid_runtime_data"


async def test_get_coordinator_success(hass: HomeAssistant) -> None:
    """Test _get_coordinator with valid data."""
    from homeassistant.helpers import device_registry as dr

    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    call = ServiceCall(hass, DOMAIN, "test", {"device_id": "test_device_id"})

    with (
        patch.object(dr, "async_get", return_value=mock_device_registry),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        result = _get_coordinator(hass, call)
        assert result == mock_coordinator


# ──────────────────────────────────────────────────────────────────────
# Schema validation tests for WiFi / device management services
# ──────────────────────────────────────────────────────────────────────


def test_connect_wifi_schema_valid():
    """Test SERVICE_CONNECT_WIFI_SCHEMA with valid data."""
    valid_data = {
        HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
        HA_SERVICE_ATTR_SSID: "TestSSID",
        HA_SERVICE_ATTR_PASSWORD: "password123",
    }
    result = SERVICE_CONNECT_WIFI_SCHEMA(valid_data)
    assert result[HA_SERVICE_ATTR_SSID] == "TestSSID"
    assert result[HA_SERVICE_ATTR_PASSWORD] == "password123"


def test_connect_wifi_schema_missing_ssid():
    """Test SERVICE_CONNECT_WIFI_SCHEMA with missing ssid raises vol.Invalid."""
    with pytest.raises(vol.Invalid):
        SERVICE_CONNECT_WIFI_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_PASSWORD: "password123",
            }
        )


def test_connect_wifi_schema_missing_password():
    """Test SERVICE_CONNECT_WIFI_SCHEMA with missing password raises vol.Invalid."""
    with pytest.raises(vol.Invalid):
        SERVICE_CONNECT_WIFI_SCHEMA(
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_SSID: "TestSSID",
            }
        )


def test_device_only_schema_valid():
    """Test SERVICE_DEVICE_ONLY_SCHEMA with valid device_id."""
    valid_data = {
        HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
    }
    result = SERVICE_DEVICE_ONLY_SCHEMA(valid_data)
    assert result[HA_SERVICE_ATTR_DEVICE_ID] == "test_device_id"


def test_allow_cloud_schema_valid():
    """Test SERVICE_ALLOW_CLOUD_SCHEMA with device_id and rca_id."""
    valid_data = {
        HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
        HA_SERVICE_ATTR_RCA_ID: "test_rca_id",
    }
    result = SERVICE_ALLOW_CLOUD_SCHEMA(valid_data)
    assert result[HA_SERVICE_ATTR_DEVICE_ID] == "test_device_id"
    assert result[HA_SERVICE_ATTR_RCA_ID] == "test_rca_id"


def test_allow_cloud_schema_default_rca_id():
    """Test SERVICE_ALLOW_CLOUD_SCHEMA without rca_id defaults to empty string."""
    data = {
        HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
    }
    result = SERVICE_ALLOW_CLOUD_SCHEMA(data)
    assert result[HA_SERVICE_ATTR_RCA_ID] == ""


# ──────────────────────────────────────────────────────────────────────
# Service handler tests for WiFi / device management services
# ──────────────────────────────────────────────────────────────────────


async def test_handle_scan_wifi_networks(hass: HomeAssistant) -> None:
    """Test scan WiFi networks service handler."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.scan_wifi_networks = AsyncMock(
        return_value=[BlancoUnitWifiNetwork(ssid="TestWiFi", signal=66, auth_mode=3)]
    )

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        response = await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_SCAN_WIFI,
            {HA_SERVICE_ATTR_DEVICE_ID: "test_device_id"},
            blocking=True,
            return_response=True,
        )

        mock_coordinator.scan_wifi_networks.assert_called_once()
        assert "networks" in response
        assert len(response["networks"]) == 1
        assert response["networks"][0]["ssid"] == "TestWiFi"
        assert response["networks"][0]["signal"] == 66
        assert response["networks"][0]["auth_mode"] == 3


async def test_handle_connect_wifi(hass: HomeAssistant) -> None:
    """Test connect WiFi service handler."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.connect_wifi = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_CONNECT_WIFI,
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_SSID: "TestSSID",
                HA_SERVICE_ATTR_PASSWORD: "password123",
            },
            blocking=True,
        )

        mock_coordinator.connect_wifi.assert_called_once_with("TestSSID", "password123")


async def test_handle_disconnect_wifi(hass: HomeAssistant) -> None:
    """Test disconnect WiFi service handler."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.disconnect_wifi = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_DISCONNECT_WIFI,
            {HA_SERVICE_ATTR_DEVICE_ID: "test_device_id"},
            blocking=True,
        )

        mock_coordinator.disconnect_wifi.assert_called_once()


async def test_handle_allow_cloud_services(hass: HomeAssistant) -> None:
    """Test allow cloud services handler with rca_id."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.allow_cloud_services = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_ALLOW_CLOUD,
            {
                HA_SERVICE_ATTR_DEVICE_ID: "test_device_id",
                HA_SERVICE_ATTR_RCA_ID: "test_rca_id",
            },
            blocking=True,
        )

        mock_coordinator.allow_cloud_services.assert_called_once_with("test_rca_id")


async def test_handle_allow_cloud_services_default_rca_id(
    hass: HomeAssistant,
) -> None:
    """Test allow cloud services handler with default (empty) rca_id."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.allow_cloud_services = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_ALLOW_CLOUD,
            {HA_SERVICE_ATTR_DEVICE_ID: "test_device_id"},
            blocking=True,
        )

        mock_coordinator.allow_cloud_services.assert_called_once_with("")


async def test_handle_factory_reset(hass: HomeAssistant) -> None:
    """Test factory reset service handler."""
    mock_coordinator = MagicMock(spec=BlancoUnitCoordinator)
    mock_coordinator.factory_reset = AsyncMock()

    mock_device_registry = MagicMock()
    mock_device = MagicMock()
    mock_device.config_entries = {"test_entry_id"}
    mock_device_registry.async_get.return_value = mock_device

    mock_entry = MagicMock()
    mock_entry.runtime_data = mock_coordinator

    with (
        patch(
            "custom_components.blanco_unit.services.dr.async_get",
            return_value=mock_device_registry,
        ),
        patch.object(hass.config_entries, "async_get_entry", return_value=mock_entry),
    ):
        async_setup_services(hass)

        await hass.services.async_call(
            DOMAIN,
            HA_SERVICE_FACTORY_RESET,
            {HA_SERVICE_ATTR_DEVICE_ID: "test_device_id"},
            blocking=True,
        )

        mock_coordinator.factory_reset.assert_called_once()


async def test_async_setup_services_registers_new_services(
    hass: HomeAssistant,
) -> None:
    """Test that all new WiFi and device management services are registered."""
    assert not hass.services.has_service(DOMAIN, HA_SERVICE_SCAN_WIFI)
    assert not hass.services.has_service(DOMAIN, HA_SERVICE_CONNECT_WIFI)
    assert not hass.services.has_service(DOMAIN, HA_SERVICE_DISCONNECT_WIFI)
    assert not hass.services.has_service(DOMAIN, HA_SERVICE_ALLOW_CLOUD)
    assert not hass.services.has_service(DOMAIN, HA_SERVICE_FACTORY_RESET)

    async_setup_services(hass)

    assert hass.services.has_service(DOMAIN, HA_SERVICE_SCAN_WIFI)
    assert hass.services.has_service(DOMAIN, HA_SERVICE_CONNECT_WIFI)
    assert hass.services.has_service(DOMAIN, HA_SERVICE_DISCONNECT_WIFI)
    assert hass.services.has_service(DOMAIN, HA_SERVICE_ALLOW_CLOUD)
    assert hass.services.has_service(DOMAIN, HA_SERVICE_FACTORY_RESET)
