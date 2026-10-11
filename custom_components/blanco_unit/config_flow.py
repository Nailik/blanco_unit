"""Config flow and options flow for Blanco Unit BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from blanco_smart_home_api_client import BlancoApiError, BlancoAuthError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
import voluptuous as vol
from voluptuous.schema_builder import UNDEFINED

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .client import validate_pin
from .cloud import async_create_api_client, compute_dev_id
from .const import (
    CLOUD_PENDING_APP_IDS,
    CONF_CLOUD_APP_ID,
    CONF_CLOUD_DEV_ID,
    CONF_CLOUD_ENABLED,
    CONF_DEV_ID,
    CONF_ERROR,
    CONF_MAC,
    CONF_NAME,
    CONF_PIN,
    DOMAIN,
    RANDOM_MAC_PLACEHOLDER,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of the validation, errors is empty if successful."""

    errors: dict[str, str]
    dev_id: str | None = None
    mac_address: str | None = None
    description_placeholders: dict[str, Any] | None = None


class BlancoUnitConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Blanco Unit Integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BlancoUnitOptionsFlow:
        """Return the options flow."""
        return BlancoUnitOptionsFlow()

    _discovery_info: BluetoothServiceInfoBleak | None = None

    def prefilledForm(
        self,
        data: dict[str, Any] | None = None,
        mac_editable: bool = True,
        name_editable: bool = True,
    ) -> vol.Schema:
        """Return a form schema with prefilled values from data."""
        _LOGGER.debug(
            "Load prefilled form with: %s and info %s", data, self._discovery_info
        )
        # Setup Values
        mac: Any = UNDEFINED
        name: Any = UNDEFINED
        pin: Any = UNDEFINED

        # Read values from data if provided
        if data is not None:
            mac = data.get(CONF_MAC, UNDEFINED)
            name = data.get(CONF_NAME, f"Blanco Unit ({mac})")
            pin = data.get(CONF_PIN, UNDEFINED)

        # If discovery_info is set, use its address as the MAC and for the name if not provided
        if self._discovery_info is not None:
            _LOGGER.debug("Set mac not editable")
            mac_editable = False
            mac = self._discovery_info.address
            name = self._discovery_info.name

        # Provide Schema
        return vol.Schema(
            {
                vol.Required(CONF_MAC, default=mac): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=False,
                        read_only=not mac_editable,
                    )
                ),
                vol.Required(CONF_NAME, default=name): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=False,
                        read_only=not name_editable,
                    )
                ),
                vol.Required(CONF_PIN, default=pin): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=False,
                        read_only=False,
                    )
                ),
            },
        )

    async def validate_input(self, user_input: dict[str, Any]) -> ValidationResult:
        """Set up the entry from user data."""
        _LOGGER.debug("validate_input %s", user_input)

        # Validate MAC address format
        if not bool(
            re.match(
                r"^([0-9A-Fa-f]{2}([-:])){5}([0-9A-Fa-f]{2})$", user_input[CONF_MAC]
            )
        ):
            _LOGGER.error("Invalid MAC code: %s", user_input[CONF_MAC])
            return ValidationResult({CONF_ERROR: "invalid_mac_code"})

        # Validate PIN format (5 digits)
        pin_str = str(user_input[CONF_PIN])
        if len(pin_str) != 5 or not pin_str.isdigit():
            _LOGGER.error("Invalid PIN: must be exactly 5 digits")
            return ValidationResult({CONF_ERROR: "invalid_pin_format"})

        client = None
        try:
            # Use device from discovery_info if available
            if self._discovery_info is not None:
                _LOGGER.debug("Using device from discovery_info")
                device = self._discovery_info.device
            else:
                _LOGGER.debug("await async_ble_device_from_address")
                device = bluetooth.async_ble_device_from_address(
                    hass=self.hass,
                    address=user_input[CONF_MAC],
                    connectable=True,
                )

            if device is None:
                return ValidationResult({CONF_ERROR: "error_device_not_found"})

            # Check if device has randomized MAC address
            # BLEDevice.address can be random if device uses BLE privacy
            address_type = getattr(device.details, "address_type", "").lower()
            has_random_mac = address_type in (
                "random",
                "random_static",
                "random_resolvable",
            )
            mac_to_store = (
                RANDOM_MAC_PLACEHOLDER if has_random_mac else device.address
            )

            _LOGGER.debug(
                "Device name %s, address_type %s, MAC: %s, Random: %s, Storing as: %s",
                device.name,
                address_type,
                device.address,
                has_random_mac,
                mac_to_store,
            )

            _LOGGER.debug("await establish_connection")
            client = await establish_connection(
                client_class=BleakClientWithServiceCache,
                device=device,
                name=device.name or "Unknown Device",
                timeout=120,
            )

            _LOGGER.debug("await validate_pin")
            validation = await validate_pin(client, pin_str)
            _LOGGER.debug(
                "validate_pin returned %s, dev_id: %s, dev_type: %s",
                validation.is_valid,
                validation.dev_id,
                validation.dev_type,
            )

            if not validation.is_valid:
                return ValidationResult({CONF_ERROR: "error_invalid_authentication"})

            if validation.dev_id is None or validation.dev_type is None:
                return ValidationResult({CONF_ERROR: "error_device_not_found"})

            _LOGGER.debug(
                "Successfully tested connection to %s (dev_id: %s, dev_type: %s)",
                mac_to_store,
                validation.dev_id,
                validation.dev_type,
            )
            return ValidationResult(
                {}, dev_id=validation.dev_id, mac_address=mac_to_store
            )
        except ValueError as err:
            _LOGGER.error("Validation error: %s", err)
            return ValidationResult({CONF_ERROR: "invalid_pin_format"})
        except Exception as err:
            _LOGGER.exception("Unexpected error during validation")
            return ValidationResult(
                errors={CONF_ERROR: "error_unknown"},
                description_placeholders={"error": str(err)},
            )
        finally:
            # Always disconnect the client
            if client is not None and client.is_connected:
                await client.disconnect()

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a bluetooth device being discovered."""
        _LOGGER.debug("async_step_bluetooth called with %s and advertisement %s", discovery_info, discovery_info.advertisement)
        # Check if the device already exists.
        await self._async_handle_discovery_without_unique_id()
        self._abort_if_unique_id_configured()

        _LOGGER.debug("async_step_bluetooth %s", discovery_info)
        self._discovery_info = discovery_info

        return self.async_show_form(
            step_id="user",
            data_schema=self.prefilledForm(),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the entry with unique id if not already configured."""
        _LOGGER.debug("async_step_user %s", user_input)
        result = ValidationResult(errors={})
        if user_input is not None:
            result = await self.validate_input(user_input)
            if not result.errors:
                # Validation was successful, create a unique id and create the config entry.
                # Use MAC as unique_id for static MAC, dev_id for random MAC
                if result.mac_address == RANDOM_MAC_PLACEHOLDER:
                    await self.async_set_unique_id(result.dev_id)
                else:
                    await self.async_set_unique_id(result.mac_address)
                self._abort_if_unique_id_configured()

                # Store MAC address and dev_id in config
                config_data = user_input.copy()
                config_data[CONF_MAC] = result.mac_address
                config_data[CONF_DEV_ID] = result.dev_id

                _LOGGER.debug("Create entry with %s", config_data)
                # Clean up discovery_info after successful validation
                self._discovery_info = None
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=config_data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.prefilledForm(data=user_input),
            errors=result.errors,
            description_placeholders=result.description_placeholders,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        _LOGGER.debug("async_step_reauth %s", user_input)
        result = ValidationResult(errors={})
        config_entry = self._get_reauth_entry()
        if user_input is not None:
            result = await self.validate_input(user_input)
            if not result.errors:
                # Verify this is the same device
                if result.mac_address == RANDOM_MAC_PLACEHOLDER:
                    await self.async_set_unique_id(result.dev_id)
                else:
                    await self.async_set_unique_id(result.mac_address)
                self._abort_if_unique_id_mismatch(reason="wrong_device")

                # Update config with new PIN and potentially updated MAC
                data_updates = user_input.copy()
                data_updates[CONF_MAC] = result.mac_address
                data_updates[CONF_DEV_ID] = result.dev_id

                # Clean up discovery_info after successful validation
                self._discovery_info = None
                return self.async_update_reload_and_abort(
                    entry=self._get_reauth_entry(),
                    data_updates=data_updates,
                )
        return self.async_show_form(
            step_id="reauth",
            data_schema=self.prefilledForm(
                data=dict(config_entry.data),
                mac_editable=False,
                name_editable=False,
            ),
            errors=result.errors,
            description_placeholders=result.description_placeholders,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-configuration."""
        _LOGGER.debug("async_step_reconfigure %s", user_input)
        result = ValidationResult(errors={})
        config_entry = self._get_reconfigure_entry()
        if user_input is not None:
            result = await self.validate_input(user_input)
            if not result.errors:
                # Verify this is the same device
                if result.mac_address == RANDOM_MAC_PLACEHOLDER:
                    await self.async_set_unique_id(result.dev_id)
                else:
                    await self.async_set_unique_id(result.mac_address)
                self._abort_if_unique_id_mismatch(reason="wrong_device")

                # Update config with potentially updated MAC and dev_id
                data_updates = user_input.copy()
                data_updates[CONF_MAC] = result.mac_address
                data_updates[CONF_DEV_ID] = result.dev_id

                # Clean up discovery_info after successful validation
                self._discovery_info = None
                return self.async_update_reload_and_abort(
                    entry=self._get_reconfigure_entry(),
                    data_updates=data_updates,
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.prefilledForm(
                data=dict(config_entry.data),
                mac_editable=False,
            ),
            errors=result.errors,
            description_placeholders=result.description_placeholders,
        )


class BlancoUnitOptionsFlow(OptionsFlow):
    """Opt in to water statistics from the BLANCO Smart Home cloud."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Enable or disable the cloud statistics."""
        options = dict(self.config_entry.options)
        errors: dict[str, str] = {}
        if user_input is not None:
            if not user_input[CONF_CLOUD_ENABLED]:
                # Keep the app id so a later re-enable does not register again.
                return self.async_create_entry(
                    data={**options, CONF_CLOUD_ENABLED: False}
                )
            errors = await self._async_enable_cloud(options)
            if not errors:
                return self.async_create_entry(
                    data={**options, CONF_CLOUD_ENABLED: True}
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CLOUD_ENABLED,
                        default=options.get(CONF_CLOUD_ENABLED, False),
                    ): bool
                }
            ),
            errors=errors,
        )

    async def _async_enable_cloud(self, options: dict[str, Any]) -> dict[str, str]:
        """Register (once) and check access, filling in app id and dev id."""
        coordinator = getattr(self.config_entry, "runtime_data", None)
        identity = getattr(getattr(coordinator, "data", None), "identity", None)
        if identity is None:
            return {CONF_ERROR: "cloud_device_not_ready"}
        dev_id = compute_dev_id(identity.serial_no, identity.service_code)

        # An app id registered in an earlier, unfinished attempt is reused, so
        # retrying until access is granted does not register new app ids.
        pending = self.hass.data.setdefault(DOMAIN, {}).setdefault(
            CLOUD_PENDING_APP_IDS, {}
        )
        app_id = options.get(CONF_CLOUD_APP_ID) or pending.get(
            self.config_entry.entry_id, ""
        )
        try:
            api = await async_create_api_client(self.hass, app_id, dev_id)
            if not app_id:
                app_id = (await api.register_app(self.hass.config.language))["app_id"]
                pending[self.config_entry.entry_id] = app_id
            await api.authenticate(dev_id)
        except BlancoAuthError:
            return {CONF_ERROR: "cloud_access_not_granted"}
        except BlancoApiError:
            _LOGGER.debug("Cloud check failed", exc_info=True)
            return {CONF_ERROR: "cloud_cannot_connect"}

        pending.pop(self.config_entry.entry_id, None)
        options[CONF_CLOUD_APP_ID] = app_id
        options[CONF_CLOUD_DEV_ID] = dev_id
        return {}
