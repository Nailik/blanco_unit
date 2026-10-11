"""Tests for the Blanco Unit options flow (cloud statistics)."""

from unittest.mock import AsyncMock, MagicMock, patch

from blanco_smart_home_api_client import BlancoAuthError, BlancoConnectionError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blanco_unit.const import (
    CONF_CLOUD_APP_ID,
    CONF_CLOUD_DEV_ID,
    CONF_CLOUD_ENABLED,
    CONF_MAC,
    CONF_NAME,
    CONF_PIN,
    DOMAIN,
)
from custom_components.blanco_unit.data import BlancoUnitIdentity
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

DEV_ID = "7fe2c1442b9ca25a1ce4ed2e8b430f94588e43ae94985be28d884785f70a7cc8"


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    """Config entry whose BLE coordinator already knows the device identity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MAC: "AA:BB:CC:DD:EE:FF", CONF_NAME: "Test", CONF_PIN: "12345"},
    )
    entry.add_to_hass(hass)
    coordinator = MagicMock()
    coordinator.data.identity = BlancoUnitIdentity(
        serial_no="005276602520B50172", service_code="11154"
    )
    entry.runtime_data = coordinator
    return entry


@pytest.fixture
def mock_api() -> MagicMock:
    """Mock BlancoApiClient."""
    api = MagicMock()
    api.register_app = AsyncMock(return_value={"app_id": "new-app-id"})
    api.authenticate = AsyncMock(
        return_value={"token": "t", "token_type": "Bearer", "dev_type": 2}
    )
    with patch(
        "custom_components.blanco_unit.cloud.BlancoApiClient",
        return_value=api,
    ):
        yield api


async def test_enable_cloud(
    hass: HomeAssistant, entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Enabling registers one app id and checks access for the derived dev_id."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CLOUD_ENABLED: True}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    mock_api.register_app.assert_awaited_once()
    mock_api.authenticate.assert_awaited_once_with(DEV_ID)
    assert entry.options == {
        CONF_CLOUD_ENABLED: True,
        CONF_CLOUD_APP_ID: "new-app-id",
        CONF_CLOUD_DEV_ID: DEV_ID,
    }


async def test_enable_reuses_existing_app_id(
    hass: HomeAssistant, entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """A previously registered app id is reused instead of registering again."""
    hass.config_entries.async_update_entry(
        entry, options={CONF_CLOUD_ENABLED: False, CONF_CLOUD_APP_ID: "old-app-id"}
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CLOUD_ENABLED: True}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    mock_api.register_app.assert_not_awaited()
    assert entry.options[CONF_CLOUD_APP_ID] == "old-app-id"


async def test_access_not_granted_keeps_app_id_for_retry(
    hass: HomeAssistant, entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Without the grant the form shows an error, and a retry reuses the app id."""
    mock_api.authenticate.side_effect = BlancoAuthError("401")
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CLOUD_ENABLED: True}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cloud_access_not_granted"}

    # A new flow after the grant must not register a second app id.
    mock_api.authenticate.side_effect = None
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CLOUD_ENABLED: True}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    mock_api.register_app.assert_awaited_once()


async def test_cannot_connect(
    hass: HomeAssistant, entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Network errors are reported on the form."""
    mock_api.register_app.side_effect = BlancoConnectionError("boom")
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CLOUD_ENABLED: True}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cloud_cannot_connect"}


async def test_disable_keeps_app_id(
    hass: HomeAssistant, entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Disabling stops polling but keeps the app id for a later re-enable."""
    hass.config_entries.async_update_entry(
        entry,
        options={
            CONF_CLOUD_ENABLED: True,
            CONF_CLOUD_APP_ID: "old-app-id",
            CONF_CLOUD_DEV_ID: DEV_ID,
        },
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CLOUD_ENABLED: False}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    mock_api.register_app.assert_not_awaited()
    mock_api.authenticate.assert_not_awaited()
    assert entry.options == {
        CONF_CLOUD_ENABLED: False,
        CONF_CLOUD_APP_ID: "old-app-id",
        CONF_CLOUD_DEV_ID: DEV_ID,
    }


async def test_device_not_ready(
    hass: HomeAssistant, entry: MockConfigEntry, mock_api: MagicMock
) -> None:
    """Without BLE data the serial number is unknown, so enabling is refused."""
    entry.runtime_data.data = None
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_CLOUD_ENABLED: True}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cloud_device_not_ready"}
    mock_api.register_app.assert_not_awaited()
