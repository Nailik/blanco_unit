"""Tests for the Blanco Unit cloud statistics."""

from unittest.mock import AsyncMock, MagicMock, patch

from blanco_smart_home_api_client import (
    BlancoAuthError,
    BlancoConnectionError,
    BlancoErrorType,
)
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.blanco_unit.cloud import (
    BlancoCloudCoordinator,
    BlancoCloudData,
    compute_dev_id,
)
from custom_components.blanco_unit.const import (
    CLOUD_COORDINATOR,
    CONF_CLOUD_APP_ID,
    CONF_CLOUD_DEV_ID,
    CONF_CLOUD_ENABLED,
    CONF_MAC,
    CONF_NAME,
    CONF_PIN,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

# Lifetime stats and errors as returned by the BLANCO Smart Home API for a
# CHOICE.All on 2026-10-11, trimmed to the fields the integration reads.
STATS_RESPONSE = {
    "ranges": [
        {
            "range": {"from": 0, "to": 1791738510535},
            "total": [
                {"par": "disp_wtr_amt", "func": 3, "cnt": 7843, "val": 2941534},
                {
                    "par": "tap_state",
                    "func": 5,
                    "cnt": 2941534,
                    "val": [
                        {"cnt": 351442, "val": 1},
                        {"cnt": 6237, "val": 2},
                        {"cnt": 1900885, "val": 3},
                        {"cnt": 682970, "val": 4},
                    ],
                    "calc_base": "disp_wtr_amt",
                },
                {"par": "wtr_flow", "func": 3, "cnt": 0, "val": 0},
            ],
            "details": [],
        }
    ],
    "info": {"dev_type": 2, "online": 1791737206687, "connected": True},
}
ERRORS_RESPONSE = {
    "errors": [
        {"err_code": 2230, "err_type": BlancoErrorType.INFO, "err_ts": 1791736812728},
        {
            "err_code": 1105,
            "err_type": BlancoErrorType.WARNING,
            "err_ts": 1791700000000,
        },
    ],
    "info": {"dev_type": 2, "online": 1791737206687, "connected": True},
}

APP_ID = "app-id-1"
DEV_ID = "a" * 64


def _entry(options: dict | None = None) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MAC: "AA:BB:CC:DD:EE:FF", CONF_NAME: "Test", CONF_PIN: "12345"},
        options=options
        if options is not None
        else {
            CONF_CLOUD_ENABLED: True,
            CONF_CLOUD_APP_ID: APP_ID,
            CONF_CLOUD_DEV_ID: DEV_ID,
        },
    )


@pytest.fixture
def mock_api() -> MagicMock:
    """Mock BlancoApiClient returning the recorded responses."""
    api = MagicMock()
    api.authenticate = AsyncMock(
        return_value={"token": "t", "token_type": "Bearer", "dev_type": 2}
    )
    api.get_device_stats = AsyncMock(return_value=(200, STATS_RESPONSE))
    api.get_device_errors = AsyncMock(return_value=(200, ERRORS_RESPONSE))
    return api


def test_compute_dev_id() -> None:
    """dev_id is sha256 over serial number and service code."""
    assert compute_dev_id("005276602520B50172", "11154") == (
        "7fe2c1442b9ca25a1ce4ed2e8b430f94588e43ae94985be28d884785f70a7cc8"
    )


async def test_update_parses_stats_and_errors(
    hass: HomeAssistant, mock_api: MagicMock
) -> None:
    """First update authenticates once, then reads lifetime stats and errors."""
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.blanco_unit.cloud.BlancoApiClient", return_value=mock_api
    ):
        coordinator = BlancoCloudCoordinator(hass, entry)
        data = await coordinator._async_update_data()
        await coordinator._async_update_data()

    assert mock_api.authenticate.await_count == 1
    mock_api.authenticate.assert_awaited_with(DEV_ID)
    ranges = mock_api.get_device_stats.await_args.args[1]
    assert ranges[0]["from"] == 0
    assert data == BlancoCloudData(
        water_total=2941.534,
        water_still=351.442,
        water_medium=6.237,
        water_classic=1900.885,
        water_hot=682.97,
        errors_critical=0,
        errors_warning=1,
        last_error_code=2230,
        last_error_type="info",
        last_error_ts=1791736812728,
    )


async def test_update_access_not_granted(
    hass: HomeAssistant, mock_api: MagicMock
) -> None:
    """A missing grant in the UNIT app is an update failure, not a BLE reauth."""
    mock_api.authenticate.side_effect = BlancoAuthError("401")
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.blanco_unit.cloud.BlancoApiClient", return_value=mock_api
    ):
        coordinator = BlancoCloudCoordinator(hass, entry)
        with pytest.raises(UpdateFailed) as err:
            await coordinator._async_update_data()
    assert err.value.translation_key == "cloud_access_not_granted"


async def test_update_connection_error(
    hass: HomeAssistant, mock_api: MagicMock
) -> None:
    """Network problems surface as UpdateFailed."""
    mock_api.get_device_stats.side_effect = BlancoConnectionError("boom")
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.blanco_unit.cloud.BlancoApiClient", return_value=mock_api
    ):
        coordinator = BlancoCloudCoordinator(hass, entry)
        with pytest.raises(UpdateFailed) as err:
            await coordinator._async_update_data()
    assert err.value.translation_key == "cloud_update_failed"


async def test_update_interval_is_15_minutes(
    hass: HomeAssistant, mock_api: MagicMock
) -> None:
    """The cloud is polled sparingly."""
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.blanco_unit.cloud.BlancoApiClient", return_value=mock_api
    ):
        coordinator = BlancoCloudCoordinator(hass, entry)
    assert coordinator.update_interval.total_seconds() == 15 * 60


CLOUD_DATA = BlancoCloudData(
    water_total=2941.534,
    water_still=351.442,
    water_medium=6.237,
    water_classic=1900.885,
    water_hot=682.97,
    errors_critical=0,
    errors_warning=1,
    last_error_code=2230,
    last_error_type="info",
    last_error_ts=1791736812728,
)


async def _cloud_sensors(hass: HomeAssistant, cloud: MagicMock | None) -> list:
    from custom_components.blanco_unit.sensor import async_setup_entry

    entry = _entry()
    entry.add_to_hass(hass)
    ble = MagicMock()
    ble.data.device_type = 2
    ble.address = "AA:BB:CC:DD:EE:FF"
    entry.runtime_data = ble
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = (
        {CLOUD_COORDINATOR: cloud} if cloud else {}
    )
    added: list = []
    await async_setup_entry(hass, entry, added.extend)
    return [e for e in added if type(e).__name__.startswith("Cloud")]


async def test_no_cloud_sensors_without_option(hass: HomeAssistant) -> None:
    """Existing installations get no cloud entities."""
    assert await _cloud_sensors(hass, None) == []


async def test_cloud_sensors(hass: HomeAssistant) -> None:
    """Cloud sensors expose the parsed statistics."""
    cloud = MagicMock()
    cloud.data = CLOUD_DATA
    cloud.last_update_success = True
    sensors = {e.unique_id: e for e in await _cloud_sensors(hass, cloud)}

    assert {k: v.native_value for k, v in sensors.items()} == {
        "cloud_water_total": 2941.534,
        "cloud_water_still": 351.442,
        "cloud_water_medium": 6.237,
        "cloud_water_classic": 1900.885,
        "cloud_water_hot": 682.97,
        "cloud_errors_critical": 0,
        "cloud_errors_warning": 1,
        "cloud_last_error": 2230,
    }
    total = sensors["cloud_water_total"]
    assert total.device_class == "water"
    assert total.state_class == "total_increasing"
    assert total.native_unit_of_measurement == "L"
    assert sensors["cloud_last_error"].extra_state_attributes == {
        "type": "info",
        "timestamp": "2026-10-11T16:40:12.728000+00:00",
    }


async def test_setup_creates_cloud_coordinator_when_enabled(
    hass: HomeAssistant,
) -> None:
    """With the option on, setup polls the cloud once before adding platforms."""
    from custom_components.blanco_unit import async_setup_entry

    entry = _entry()
    entry.add_to_hass(hass)
    cloud = MagicMock()
    cloud.async_refresh = AsyncMock()
    ble = MagicMock()
    ble.async_refresh = AsyncMock()
    order: list[str] = []
    cloud.async_refresh.side_effect = lambda: order.append("cloud")

    bg_tasks: list = []
    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=MagicMock(address="AA:BB:CC:DD:EE:FF"),
        ),
        patch("custom_components.blanco_unit.BlancoUnitCoordinator", return_value=ble),
        patch(
            "custom_components.blanco_unit.BlancoCloudCoordinator", return_value=cloud
        ),
        patch.object(
            entry,
            "async_create_background_task",
            side_effect=lambda _h, coro, _n: bg_tasks.append(coro),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            side_effect=lambda *_: order.append("platforms"),
        ),
    ):
        assert await async_setup_entry(hass, entry)
        assert hass.data[DOMAIN][entry.entry_id][CLOUD_COORDINATOR] is cloud
        await bg_tasks[0]

    assert order == ["cloud", "platforms"]


async def test_setup_without_option_has_no_cloud(hass: HomeAssistant) -> None:
    """Existing installations never talk to the cloud."""
    from custom_components.blanco_unit import async_setup_entry

    entry = _entry(options={})
    entry.add_to_hass(hass)
    ble = MagicMock()
    ble.async_refresh = AsyncMock()
    with (
        patch(
            "custom_components.blanco_unit.bluetooth.async_ble_device_from_address",
            return_value=MagicMock(address="AA:BB:CC:DD:EE:FF"),
        ),
        patch("custom_components.blanco_unit.BlancoUnitCoordinator", return_value=ble),
        patch("custom_components.blanco_unit.BlancoCloudCoordinator") as cloud_cls,
        patch.object(entry, "async_create_background_task"),
    ):
        assert await async_setup_entry(hass, entry)
    cloud_cls.assert_not_called()
    assert CLOUD_COORDINATOR not in hass.data[DOMAIN][entry.entry_id]


async def test_update_non_200(hass: HomeAssistant, mock_api: MagicMock) -> None:
    """An unexpected HTTP status is an update failure."""
    mock_api.get_device_errors.return_value = (500, {})
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.blanco_unit.cloud.BlancoApiClient", return_value=mock_api
    ):
        coordinator = BlancoCloudCoordinator(hass, entry)
        with pytest.raises(UpdateFailed) as err:
            await coordinator._async_update_data()
    assert err.value.translation_key == "cloud_update_failed"


async def test_last_error_without_errors(hass: HomeAssistant) -> None:
    """Without errors the last-error sensor is empty and has no attributes."""
    from dataclasses import replace

    cloud = MagicMock()
    cloud.data = replace(
        CLOUD_DATA, last_error_code=None, last_error_type=None, last_error_ts=None
    )
    cloud.last_update_success = True
    sensors = {e.unique_id: e for e in await _cloud_sensors(hass, cloud)}
    last = sensors["cloud_last_error"]
    assert last.available
    assert last.native_value is None
    assert last.extra_state_attributes is None
