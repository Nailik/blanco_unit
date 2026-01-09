"""Tests for the Blanco Unit config flow."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blanco_unit.const import (
    CONF_ERROR,
    CONF_MAC,
    CONF_NAME,
    CONF_PIN,
    DOMAIN,
)
from homeassistant.config_entries import (
    SOURCE_BLUETOOTH,
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    SOURCE_USER,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

MOCKED_CONF_MAC = "AA:BB:CC:DD:EE:FF"
MOCKED_CONF_NAME = "Test Blanco Unit"
MOCKED_CONF_PIN = 12345

MOCKED_CONFIG: dict[str, Any] = {
    CONF_MAC: MOCKED_CONF_MAC,
    CONF_NAME: MOCKED_CONF_NAME,
    CONF_PIN: MOCKED_CONF_PIN,
}


@pytest.fixture
def mock_bluetooth_device():
    """Create a mock Bluetooth device."""
    device = AsyncMock()
    device.address = MOCKED_CONF_MAC
    device.name = MOCKED_CONF_NAME
    return device


@pytest.fixture
def mock_bleak_client():
    """Create a mock Bleak client."""
    client = AsyncMock()
    client.is_connected = True
    client.disconnect = AsyncMock()
    return client


@pytest.fixture
def mock_discovery():
    """Mock Bluetooth discovery info."""
    discovery = AsyncMock()
    discovery.address = MOCKED_CONF_MAC
    discovery.name = MOCKED_CONF_NAME
    return discovery


# -------------------------------
# User Flow Tests
# -------------------------------


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_user_flow_success(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test successful user configuration flow."""
    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.return_value = (True, None)

    # Initialize flow
    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert flow_result["type"] is FlowResultType.FORM
    assert flow_result["step_id"] == "user"

    # Configure with valid data
    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        MOCKED_CONFIG,
    )

    mock_validate_pin.assert_awaited_once()

    assert configure_result["type"] is FlowResultType.CREATE_ENTRY
    assert configure_result["title"] == MOCKED_CONF_NAME
    assert configure_result["data"][CONF_MAC] == MOCKED_CONF_MAC
    assert configure_result["data"][CONF_PIN] == MOCKED_CONF_PIN


async def test_user_flow_already_configured(hass: HomeAssistant) -> None:
    """Test user flow aborts when device is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCKED_CONF_MAC,
        data=MOCKED_CONFIG,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.blanco_unit.config_flow.validate_pin",
            return_value=(True, None),
        ),
        patch(
            "custom_components.blanco_unit.config_flow.establish_connection",
            return_value=AsyncMock(is_connected=True, disconnect=AsyncMock()),
        ),
        patch(
            "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address",
            return_value=AsyncMock(address=MOCKED_CONF_MAC, name=MOCKED_CONF_NAME),
        ),
    ):
        flow_result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        configure_result = await hass.config_entries.flow.async_configure(
            flow_result["flow_id"],
            MOCKED_CONFIG,
        )

        assert configure_result["type"] is FlowResultType.ABORT
        assert configure_result["reason"] == "already_configured"


async def test_user_flow_invalid_mac(hass: HomeAssistant) -> None:
    """Test user flow with invalid MAC address."""
    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        {**MOCKED_CONFIG, CONF_MAC: "INVALID-MAC"},
    )

    assert configure_result["type"] is FlowResultType.FORM
    assert configure_result["errors"][CONF_ERROR] == "invalid_mac_code"


async def test_user_flow_invalid_pin_format(hass: HomeAssistant) -> None:
    """Test user flow with invalid PIN format."""
    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        {**MOCKED_CONFIG, CONF_PIN: 123},  # Only 3 digits
    )

    assert configure_result["type"] is FlowResultType.FORM
    assert configure_result["errors"][CONF_ERROR] == "invalid_pin_format"


@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_user_flow_device_not_found(
    mock_device_from_address: AsyncMock,
    hass: HomeAssistant,
) -> None:
    """Test user flow when device is not found."""
    mock_device_from_address.return_value = None

    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        MOCKED_CONFIG,
    )

    assert configure_result["type"] is FlowResultType.FORM
    assert configure_result["errors"][CONF_ERROR] == "error_device_not_found"


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_user_flow_invalid_authentication(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test user flow with invalid authentication."""
    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.return_value = (False, None)

    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        MOCKED_CONFIG,
    )

    assert configure_result["type"] is FlowResultType.FORM
    assert configure_result["errors"][CONF_ERROR] == "error_invalid_authentication"


@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_user_flow_unknown_error(
    mock_device_from_address: AsyncMock,
    hass: HomeAssistant,
) -> None:
    """Test user flow with unknown error."""
    mock_device_from_address.side_effect = Exception("Unknown error")

    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        MOCKED_CONFIG,
    )

    assert configure_result["type"] is FlowResultType.FORM
    assert configure_result["errors"][CONF_ERROR] == "error_unknown"


# -------------------------------
# Bluetooth Discovery Flow Tests
# -------------------------------


async def test_bluetooth_discovery(
    hass: HomeAssistant,
    mock_discovery,
) -> None:
    """Test Bluetooth discovery flow."""
    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=mock_discovery,
    )

    assert flow_result["type"] is FlowResultType.FORM
    assert flow_result["step_id"] == "user"


async def test_bluetooth_discovery_already_configured(
    hass: HomeAssistant,
    mock_discovery,
) -> None:
    """Test Bluetooth discovery when device is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCKED_CONF_MAC,
        data=MOCKED_CONFIG,
    )
    entry.add_to_hass(hass)

    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=mock_discovery,
    )

    assert flow_result["type"] is FlowResultType.ABORT
    assert flow_result["reason"] == "already_configured"


# -------------------------------
# Reauth Flow Tests
# -------------------------------


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_reauth_flow_success(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test successful reauth flow."""
    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.return_value = (True, None)

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCKED_CONF_MAC,
        data=MOCKED_CONFIG,
    )
    entry.add_to_hass(hass)

    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
    )

    assert flow_result["type"] is FlowResultType.FORM

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        MOCKED_CONFIG,
    )

    assert configure_result["type"] is FlowResultType.ABORT
    assert configure_result["reason"] == "reauth_successful"


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_reauth_flow_wrong_device(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test reauth flow with wrong device MAC."""
    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.return_value = (True, None)

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCKED_CONF_MAC,
        data=MOCKED_CONFIG,
    )
    entry.add_to_hass(hass)

    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
    )

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        {**MOCKED_CONFIG, CONF_MAC: "11:22:33:44:55:66"},
    )

    assert configure_result["type"] is FlowResultType.ABORT
    assert configure_result["reason"] == "wrong_device"


# -------------------------------
# Reconfigure Flow Tests
# -------------------------------


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_reconfigure_flow_success(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test successful reconfigure flow."""
    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.return_value = (True, None)

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MOCKED_CONF_MAC,
        data=MOCKED_CONFIG,
    )
    entry.add_to_hass(hass)

    flow_result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )

    assert flow_result["type"] is FlowResultType.FORM

    configure_result = await hass.config_entries.flow.async_configure(
        flow_result["flow_id"],
        {**MOCKED_CONFIG, CONF_NAME: "New Name"},
    )

    assert configure_result["type"] is FlowResultType.ABORT
    assert configure_result["reason"] == "reconfigure_successful"


# -------------------------------
# Validation Tests
# -------------------------------


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_validate_input_success(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test successful input validation."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.return_value = (True, None)

    flow = BlancoUnitConfigFlow()
    flow.hass = hass

    result = await flow.validate_input(MOCKED_CONFIG)

    assert not result.errors
    assert result.description_placeholders is None


async def test_validate_input_value_error(hass: HomeAssistant) -> None:
    """Test input validation with value error."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    flow = BlancoUnitConfigFlow()
    flow.hass = hass

    result = await flow.validate_input({**MOCKED_CONFIG, CONF_PIN: "abc"})

    assert result.errors[CONF_ERROR] == "invalid_pin_format"


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_validate_input_disconnects_on_success(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test that validate_input disconnects client after success."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.return_value = (True, None)

    flow = BlancoUnitConfigFlow()
    flow.hass = hass

    await flow.validate_input(MOCKED_CONFIG)

    mock_bleak_client.disconnect.assert_awaited_once()


@patch("custom_components.blanco_unit.config_flow.validate_pin")
@patch("custom_components.blanco_unit.config_flow.establish_connection")
@patch(
    "custom_components.blanco_unit.config_flow.bluetooth.async_ble_device_from_address"
)
async def test_validate_input_disconnects_on_error(
    mock_device_from_address: AsyncMock,
    mock_establish_connection: AsyncMock,
    mock_validate_pin: AsyncMock,
    hass: HomeAssistant,
    mock_bluetooth_device,
    mock_bleak_client,
) -> None:
    """Test that validate_input disconnects client after error."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    mock_device_from_address.return_value = mock_bluetooth_device
    mock_establish_connection.return_value = mock_bleak_client
    mock_validate_pin.side_effect = Exception("Test error")

    flow = BlancoUnitConfigFlow()
    flow.hass = hass

    await flow.validate_input(MOCKED_CONFIG)

    mock_bleak_client.disconnect.assert_awaited_once()


# -------------------------------
# Prefilled Form Tests
# -------------------------------


async def test_prefilled_form_with_data(hass: HomeAssistant) -> None:
    """Test prefilled form with existing data."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    flow = BlancoUnitConfigFlow()
    flow.hass = hass

    schema = flow.prefilledForm(data=MOCKED_CONFIG)

    # Validate schema creates proper defaults
    validated = schema({CONF_PIN: 12345})
    assert validated[CONF_MAC] == MOCKED_CONF_MAC
    assert validated[CONF_NAME] == MOCKED_CONF_NAME
    assert validated[CONF_PIN] == 12345


async def test_prefilled_form_with_discovery_info(
    hass: HomeAssistant,
    mock_discovery,
) -> None:
    """Test prefilled form with discovery info."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    flow = BlancoUnitConfigFlow()
    flow.hass = hass
    flow._discovery_info = mock_discovery

    schema = flow.prefilledForm()

    # Validate schema uses discovery info
    validated = schema({CONF_PIN: 12345})
    assert validated[CONF_MAC] == MOCKED_CONF_MAC
    assert validated[CONF_NAME] == MOCKED_CONF_NAME


async def test_prefilled_form_without_data(hass: HomeAssistant) -> None:
    """Test prefilled form without data."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    flow = BlancoUnitConfigFlow()
    flow.hass = hass

    schema = flow.prefilledForm()

    # Schema should accept full input
    validated = schema(MOCKED_CONFIG)
    assert validated[CONF_MAC] == MOCKED_CONF_MAC
    assert validated[CONF_NAME] == MOCKED_CONF_NAME
    assert validated[CONF_PIN] == MOCKED_CONF_PIN


async def test_prefilled_form_mac_not_editable(
    hass: HomeAssistant,
    mock_discovery,
) -> None:
    """Test prefilled form with MAC not editable when discovery info present."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    flow = BlancoUnitConfigFlow()
    flow.hass = hass
    flow._discovery_info = mock_discovery

    schema = flow.prefilledForm()

    # Check that MAC field is read-only
    mac_field = schema.schema[CONF_MAC]
    assert hasattr(mac_field, "config")
    assert mac_field.config["read_only"] is True


async def test_prefilled_form_name_not_editable(hass: HomeAssistant) -> None:
    """Test prefilled form with name not editable."""
    from custom_components.blanco_unit.config_flow import BlancoUnitConfigFlow

    flow = BlancoUnitConfigFlow()
    flow.hass = hass

    schema = flow.prefilledForm(data=MOCKED_CONFIG, name_editable=False)

    # Check that name field is read-only
    name_field = schema.schema[CONF_NAME]
    assert hasattr(name_field, "config")
    assert name_field.config["read_only"] is True
