"""BlueZ NoInputNoOutput pairing agent for BLE Just Works pairing.

BlueZ requires a registered org.bluez.Agent1 D-Bus agent to handle BLE pairing
ceremonies. Without one, Pair() immediately fails with AuthenticationFailed.

This module registers a minimal NoInputNoOutput agent that auto-accepts
Just Works pairing requests, which is the pairing method used by Blanco Unit
devices.

Note: `from __future__ import annotations` is intentionally NOT used here because
dbus-fast reads type annotations at runtime to derive D-Bus method signatures.
PEP 563 (stringified annotations) breaks this introspection.
"""

import logging

_LOGGER = logging.getLogger(__name__)

AGENT_PATH = "/org/blanco_unit/agent"

_agent_registered = False


async def async_register_agent() -> bool:
    """Register a NoInputNoOutput BlueZ pairing agent if not already registered.

    Returns True if agent was registered successfully or was already registered.
    Returns False if registration failed (non-Linux, D-Bus unavailable, etc).
    """
    global _agent_registered  # noqa: PLW0603

    if _agent_registered:
        return True

    try:
        from dbus_fast import BusType  # noqa: PLC0415
        from dbus_fast.aio import MessageBus  # noqa: PLC0415
        from dbus_fast.service import ServiceInterface, method  # noqa: PLC0415
    except ImportError:
        _LOGGER.debug("dbus-fast not available, skipping agent registration")
        return False

    class _NoInputNoOutputAgent(ServiceInterface):
        """Minimal BlueZ pairing agent for Just Works pairing."""

        def __init__(self) -> None:
            super().__init__("org.bluez.Agent1")

        @method()
        def Release(self) -> None:
            """Agent released by BlueZ."""
            _LOGGER.debug("BlueZ agent released")

        @method()
        def RequestConfirmation(self, device: "o", passkey: "u") -> None:  # noqa: F821
            """Auto-confirm numeric comparison (Just Works)."""
            _LOGGER.debug("Auto-confirming pairing for %s", device)

        @method()
        def RequestAuthorization(self, device: "o") -> None:  # noqa: F821
            """Auto-authorize pairing request."""
            _LOGGER.debug("Auto-authorizing pairing for %s", device)

        @method()
        def AuthorizeService(self, device: "o", uuid: "s") -> None:  # noqa: F821
            """Auto-authorize service access."""
            _LOGGER.debug("Auto-authorizing service %s for %s", uuid, device)

        @method()
        def Cancel(self) -> None:
            """Pairing cancelled."""
            _LOGGER.debug("Pairing cancelled")

    try:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        agent = _NoInputNoOutputAgent()
        bus.export(AGENT_PATH, agent)

        # Register with BlueZ AgentManager
        introspection = await bus.introspect("org.bluez", "/org/bluez")
        proxy = bus.get_proxy_object("org.bluez", "/org/bluez", introspection)
        agent_manager = proxy.get_interface("org.bluez.AgentManager1")
        await agent_manager.call_register_agent(AGENT_PATH, "NoInputNoOutput")
        await agent_manager.call_request_default_agent(AGENT_PATH)

        _agent_registered = True
        _LOGGER.debug(
            "Registered NoInputNoOutput BlueZ pairing agent at %s", AGENT_PATH
        )

    except Exception as err:  # noqa: BLE001
        err_str = str(err)
        if "AlreadyExists" in err_str:
            _LOGGER.debug("BlueZ agent already registered (by another component)")
            _agent_registered = True
            return True
        _LOGGER.warning(
            "Failed to register BlueZ pairing agent: %s. "
            "BLE pairing may fail. Ensure a pairing agent is available "
            "(e.g. run 'bt-agent -c NoInputNoOutput' or use bluetoothctl)",
            err,
        )
        return False
    else:
        return True
