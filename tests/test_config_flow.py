"""Tests for the Blanco Unit config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow
from custom_components.blanco_unit.const import CONF_MAC, CONF_NAME, CONF_PIN, DOMAIN
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


@pytest.fixture(autouse=True)
def mock_setup_entry():
    """Mock async_setup_entry for all config flow tests."""
    with patch(
        "custom_components.blanco_unit.async_setup_entry",
        return_value=True,
    ):
        yield


@pytest.fixture
def mock_bluetooth_service_info():
    """Create a mock Bluetooth service info."""
    info = MagicMock(spec=BluetoothServiceInfoBleak)
    info.address = "AA:BB:CC:DD:EE:FF"
    info.name = "Blanco Unit Test"
    return info


@pytest.fixture
def mock_ble_device():
    """Create a mock BLE device."""
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "Blanco Unit Test"
    return device


@pytest.fixture
def mock_bleak_client():
    """Create a mock Bleak client."""
    client = MagicMock()
    client.is_connected = True
    client.disconnect = AsyncMock()
    return client


async def test_user_flow_success(
    hass: HomeAssistant, mock_ble_device, mock_bleak_client
) -> None:
    """Test successful user configuration flow."""
    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Test Device"
        assert result["data"][CONF_MAC] == "AA:BB:CC:DD:EE:FF"
        assert result["data"][CONF_PIN] == 12345


async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_ble_device, mock_bleak_client
) -> None:
    """Test user flow when device is already configured."""
    # Create an existing entry
    from homeassistant.config_entries import ConfigEntry

    existing_entry = MagicMock(spec=ConfigEntry)
    existing_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    existing_entry.domain = DOMAIN
    hass.config_entries._entries[("test_entry_id",)] = existing_entry

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_user_flow_invalid_mac(hass: HomeAssistant) -> None:
    """Test user flow with invalid MAC address format."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MAC: "INVALID_MAC",
            CONF_NAME: "Test Device",
            CONF_PIN: 12345,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_mac_code"}


async def test_user_flow_invalid_pin_format(hass: HomeAssistant) -> None:
    """Test user flow with invalid PIN format."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )

    # Test with 4 digits (too short)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_MAC: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "Test Device",
            CONF_PIN: 1234,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_pin_format"}


async def test_user_flow_device_not_found(hass: HomeAssistant) -> None:
    """Test user flow when device is not found."""
    with patch(
        "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "error_device_not_found"}


async def test_user_flow_invalid_authentication(
    hass: HomeAssistant, mock_ble_device, mock_bleak_client
) -> None:
    """Test user flow with invalid authentication."""
    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(False, None),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "error_invalid_authentication"}


async def test_user_flow_unknown_error(hass: HomeAssistant, mock_ble_device) -> None:
    """Test user flow with unknown error."""
    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            side_effect=Exception("Unknown error"),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"] == {"base": "error_unknown"}
        assert result["description_placeholders"]["error"] == "Unknown error"


async def test_bluetooth_discovery(
    hass: HomeAssistant, mock_bluetooth_service_info
) -> None:
    """Test Bluetooth discovery flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "bluetooth"},
        data=mock_bluetooth_service_info,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_bluetooth_discovery_already_configured(
    hass: HomeAssistant, mock_bluetooth_service_info
) -> None:
    """Test Bluetooth discovery when device is already configured."""
    from homeassistant.config_entries import ConfigEntry

    existing_entry = MagicMock(spec=ConfigEntry)
    existing_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    existing_entry.domain = DOMAIN
    hass.config_entries._entries[("test_entry_id",)] = existing_entry

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "bluetooth"},
        data=mock_bluetooth_service_info,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_success(
    hass: HomeAssistant, mock_ble_device, mock_bleak_client
) -> None:
    """Test successful reauth flow."""
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_NAME: "Test Device",
        CONF_PIN: 12345,
    }

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": "reauth",
                "entry_id": "test_entry",
                "unique_id": "AA:BB:CC:DD:EE:FF",
            },
            data=mock_entry.data,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 54321,
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reauth_successful"


async def test_reauth_flow_wrong_device(
    hass: HomeAssistant, mock_ble_device, mock_bleak_client
) -> None:
    """Test reauth flow with wrong device."""
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_NAME: "Test Device",
        CONF_PIN: 12345,
    }

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": "reauth",
                "entry_id": "test_entry",
                "unique_id": "AA:BB:CC:DD:EE:FF",
            },
            data=mock_entry.data,
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "11:22:33:44:55:66",  # Different MAC
                CONF_NAME: "Test Device",
                CONF_PIN: 54321,
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "wrong_device"


async def test_reconfigure_flow_success(
    hass: HomeAssistant, mock_ble_device, mock_bleak_client
) -> None:
    """Test successful reconfigure flow."""
    mock_entry = MagicMock()
    mock_entry.data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_NAME: "Test Device",
        CONF_PIN: 12345,
    }

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": "reconfigure",
                "entry_id": "test_entry",
                "unique_id": "AA:BB:CC:DD:EE:FF",
            },
            data=mock_entry.data,
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Updated Device Name",
                CONF_PIN: 54321,
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"


async def test_prefilled_form_with_data() -> None:
    """Test prefilledForm with provided data."""
    flow = BlancoUnitConfigFlow()
    flow._discovery_info = None

    data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_NAME: "Test Device",
        CONF_PIN: 12345,
    }

    schema = flow.prefilledForm(data=data)
    assert schema is not None


async def test_prefilled_form_with_discovery_info(mock_bluetooth_service_info) -> None:
    """Test prefilledForm with discovery info."""
    flow = BlancoUnitConfigFlow()
    flow._discovery_info = mock_bluetooth_service_info

    schema = flow.prefilledForm()
    assert schema is not None


async def test_prefilled_form_without_data() -> None:
    """Test prefilledForm without any data."""
    flow = BlancoUnitConfigFlow()
    flow._discovery_info = None

    schema = flow.prefilledForm()
    assert schema is not None


async def test_prefilled_form_mac_not_editable() -> None:
    """Test prefilledForm with MAC not editable."""
    flow = BlancoUnitConfigFlow()
    flow._discovery_info = None

    data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_NAME: "Test Device",
        CONF_PIN: 12345,
    }

    schema = flow.prefilledForm(data=data, mac_editable=False)
    assert schema is not None


async def test_prefilled_form_name_not_editable() -> None:
    """Test prefilledForm with name not editable."""
    flow = BlancoUnitConfigFlow()
    flow._discovery_info = None

    data = {
        CONF_MAC: "AA:BB:CC:DD:EE:FF",
        CONF_NAME: "Test Device",
        CONF_PIN: 12345,
    }

    schema = flow.prefilledForm(data=data, name_editable=False)
    assert schema is not None


async def test_validate_input_success(mock_ble_device, mock_bleak_client) -> None:
    """Test validate_input with valid data."""
    flow = BlancoUnitConfigFlow()
    flow.hass = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
    ):
        result = await flow.validate_input(
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            }
        )

        assert result.errors == {}
        assert result.description_placeholders is None


async def test_validate_input_value_error(mock_ble_device, mock_bleak_client) -> None:
    """Test validate_input with ValueError from PIN validation."""
    flow = BlancoUnitConfigFlow()
    flow.hass = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            side_effect=ValueError("Invalid PIN"),
        ),
    ):
        result = await flow.validate_input(
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            }
        )

        assert result.errors == {"base": "invalid_pin_format"}


async def test_validate_input_disconnects_on_success(
    mock_ble_device, mock_bleak_client
) -> None:
    """Test that validate_input disconnects client on success."""
    flow = BlancoUnitConfigFlow()
    flow.hass = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
    ):
        await flow.validate_input(
            {
                CONF_MAC: "AA:BB:CC:DD:EE:FF",
                CONF_NAME: "Test Device",
                CONF_PIN: 12345,
            }
        )

        mock_bleak_client.disconnect.assert_called_once()


async def test_validate_input_disconnects_on_error(
    mock_ble_device, mock_bleak_client
) -> None:
    """Test that validate_input disconnects client on error."""
    flow = BlancoUnitConfigFlow()
    flow.hass = MagicMock()

    with (
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=mock_bleak_client,
        ),
        patch(
            "custom_components.blanco_unit.config_flow.authenticate",
            side_effect=ValueError("Test error"),
        ),
    ):
        result = await flow._validate_input(
            {"mac": "AA:BB:CC:DD:EE:FF", "pin": "12345"}
        )

        # Should have error
        assert "error" in result

        # Should still disconnect on error
        mock_bleak_client.disconnect.assert_called_once()
