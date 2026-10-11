"""Water statistics from the BLANCO Smart Home cloud."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from blanco_smart_home_api_client import (
    BlancoApiClient,
    BlancoApiError,
    BlancoAuthError,
    BlancoErrorType,
    BlancoWaterType,
    client as _api_client_module,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as ha_version
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import CONF_CLOUD_APP_ID, CONF_CLOUD_DEV_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Lifetime totals change only when water is drawn, so poll sparingly.
CLOUD_UPDATE_INTERVAL = timedelta(minutes=15)


def compute_dev_id(serial_no: str, service_code: str) -> str:
    """Return the cloud device id the BLANCO Smart Home API expects."""
    return _api_client_module.BlancoApiClient.compute_dev_id(serial_no, service_code)


async def async_create_api_client(
    hass: HomeAssistant, app_id: str = "", dev_id: str = ""
) -> BlancoApiClient:
    """Create an API client that identifies itself as this integration."""
    integration = await async_get_integration(hass, DOMAIN)
    return BlancoApiClient(
        async_get_clientsession(hass),
        app_id=app_id,
        dev_id=dev_id,
        app_version=str(integration.version),
        app_build="1",
        os_version=ha_version,
    )


@dataclass
class BlancoCloudData:
    """Lifetime water statistics and error summary."""

    water_total: float
    water_still: float
    water_medium: float
    water_classic: float
    water_hot: float
    errors_critical: int
    errors_warning: int
    last_error_code: int | None
    last_error_type: str | None
    last_error_ts: int | None


def _litres(millilitres: float) -> float:
    return round(millilitres / 1000, 3)


def _parse_stats(stats: dict[str, Any]) -> dict[str, Any]:
    """Extract lifetime volume in total and per water type."""
    totals = {item["par"]: item for item in stats["ranges"][0]["total"]}
    dispensed = totals.get("disp_wtr_amt", {})
    by_type = {
        entry["val"]: entry["cnt"]
        for entry in totals.get("tap_state", {}).get("val", [])
    }
    return {
        "water_total": _litres(dispensed.get("val", 0)),
        "water_still": _litres(by_type.get(BlancoWaterType.STILL, 0)),
        "water_medium": _litres(by_type.get(BlancoWaterType.MEDIUM, 0)),
        "water_classic": _litres(by_type.get(BlancoWaterType.CLASSIC, 0)),
        "water_hot": _litres(by_type.get(BlancoWaterType.HOT, 0)),
    }


def _parse_errors(result: dict[str, Any]) -> dict[str, Any]:
    """Count critical errors and warnings and pick the most recent entry."""
    errors = result.get("errors", [])
    latest = max(errors, key=lambda e: e.get("err_ts") or 0, default=None)
    return {
        "errors_critical": sum(
            e["err_type"] == BlancoErrorType.CRITICAL for e in errors
        ),
        "errors_warning": sum(e["err_type"] == BlancoErrorType.WARNING for e in errors),
        "last_error_code": latest["err_code"] if latest else None,
        "last_error_type": (
            BlancoErrorType(latest["err_type"]).name.lower() if latest else None
        ),
        "last_error_ts": latest["err_ts"] if latest else None,
    }


class BlancoCloudCoordinator(DataUpdateCoordinator[BlancoCloudData]):
    """Poll lifetime statistics and errors from the BLANCO Smart Home cloud."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator from the options set in the options flow."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{config_entry.title} cloud",
            config_entry=config_entry,
            update_interval=CLOUD_UPDATE_INTERVAL,
        )
        self._app_id: str = config_entry.options[CONF_CLOUD_APP_ID]
        self._dev_id: str = config_entry.options[CONF_CLOUD_DEV_ID]
        self._api: BlancoApiClient | None = None

    async def _async_update_data(self) -> BlancoCloudData:
        """Fetch lifetime statistics and the error list."""
        try:
            if self._api is None:
                # The token is only held in memory; persisting it would reload
                # the entry through its update listener on every renewal.
                api = await async_create_api_client(
                    self.hass, self._app_id, self._dev_id
                )
                await api.authenticate(self._dev_id)
                self._api = api
            now_ms = int(dt_util.utcnow().timestamp() * 1000)
            stats_status, stats = await self._api.get_device_stats(
                self._dev_id, [{"from": 0, "to": now_ms}]
            )
            errors_status, errors = await self._api.get_device_errors(self._dev_id)
        except BlancoAuthError as err:
            raise UpdateFailed(translation_key="cloud_access_not_granted") from err
        except BlancoApiError as err:
            raise UpdateFailed(
                translation_key="cloud_update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

        if stats_status != 200 or errors_status != 200:
            raise UpdateFailed(
                translation_key="cloud_update_failed",
                translation_placeholders={
                    "error": f"HTTP {stats_status}/{errors_status}"
                },
            )
        return BlancoCloudData(**_parse_stats(stats), **_parse_errors(errors))
