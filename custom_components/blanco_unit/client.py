"""Defines the bluetooth client to control the Blanco Unit."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
import math
import random
import time
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import CHARACTERISTIC_UUID, MTU_SIZE
from .data import (
    BlancoUnitIdentity,
    BlancoUnitSettings,
    BlancoUnitStatus,
    BlancoUnitSystemInfo,
    BlancoUnitWifiInfo,
)

_LOGGER = logging.getLogger(__name__)

# -------------------------------
# region Exceptions
# -------------------------------


class BlancoUnitClientError(Exception):
    """Base exception for Blanco Unit client errors."""


class BlancoUnitAuthenticationError(BlancoUnitClientError):
    """Exception raised when authentication fails due to wrong PIN."""

    def __init__(self, message: str = "Wrong PIN") -> None:
        """Initialize BlancoUnitAuthenticationError."""
        super().__init__(message)


class BlancoUnitConnectionError(BlancoUnitClientError):
    """Exception raised when connection fails."""

    def __init__(self, message: str = "Connection failed") -> None:
        """Initialize BlancoUnitConnectionError."""
        super().__init__(message)


# -------------------------------
# region Internal Data Models
# -------------------------------


@dataclass
class _RequestMeta:
    """Internal: Request metadata."""

    evt_type: int
    dev_id: str | None = None
    dev_type: int = 1
    evt_ver: int = 1
    evt_ts: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, omitting None dev_id."""
        data = asdict(self)
        if self.dev_id is None:
            del data["dev_id"]
        return data


@dataclass
class _RequestBody:
    """Internal: Request body."""

    meta: _RequestMeta
    opts: dict[str, int] | None = None
    pars: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = {"meta": self.meta.to_dict()}
        if self.opts:
            data["opts"] = self.opts
        if self.pars:
            data["pars"] = self.pars
        return data


@dataclass
class _RequestEnvelope:
    """Internal: Complete request envelope."""

    session: int
    id: int
    token: str
    salt: str
    body: _RequestBody
    type: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session": self.session,
            "id": self.id,
            "type": self.type,
            "token": self.token,
            "salt": self.salt,
            "body": self.body.to_dict(),
        }


@dataclass
class _SetTemperaturePars:
    """Internal: Parameters for setting temperature."""

    cooling_celsius: int
    heating_celsius: int = 65

    def to_pars(self) -> dict[str, Any]:
        """Convert to parameters dictionary."""
        return {
            "set_point_cooling": {"val": self.cooling_celsius},
            "set_point_heating": {"val": self.heating_celsius},
        }


@dataclass
class _SetWaterHardnessPars:
    """Internal: Parameters for setting water hardness."""

    level: int

    def to_pars(self) -> dict[str, Any]:
        """Convert to parameters dictionary."""
        if not (1 <= self.level <= 9):
            raise ValueError("Hardness level must be 1-9")
        return {"wtr_hardness": {"val": self.level}}


@dataclass
class _ChangePinPars:
    """Internal: Parameters for changing PIN."""

    new_pin: str

    def to_pars(self) -> dict[str, Any]:
        """Convert to parameters dictionary."""
        if len(self.new_pin) != 5 or not self.new_pin.isdigit():
            raise ValueError("PIN must be 5 digits")
        return {"new_pass": self.new_pin}


@dataclass
class _DispensePars:
    """Internal: Parameters for dispensing water."""

    amount_ml: int
    co2_intensity: int

    def to_pars(self) -> dict[str, Any]:
        """Convert to parameters dictionary."""
        return {"disp_amt": self.amount_ml, "co2_int": self.co2_intensity}


@dataclass
class _SetCalibrationPars:
    """Internal: Parameters for setting calibration."""

    calib_type: str  # "calib_still_wtr" or "calib_soda_wtr"
    amount: int

    def to_pars(self) -> dict[str, Any]:
        """Convert to parameters dictionary."""
        return {self.calib_type: {"val": self.amount}}


# -------------------------------
# region Protocol Helper
# -------------------------------


class _BlancoUnitProtocol:
    """Internal protocol handler for packet creation, parsing, and communication."""

    def __init__(self, mtu: int = MTU_SIZE) -> None:
        """Initialize protocol handler."""
        self.mtu = mtu
        self.session_id = random.randint(1000000, 9999999)
        self.msg_id_counter = 1

    def calculate_token(self, pin: str, salt: str) -> str:
        """Calculate authentication token from PIN and salt."""
        pin_hash = hashlib.sha256(pin.encode("utf-8")).hexdigest()
        combined = pin_hash + salt
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def create_packets(self, json_data: dict[str, Any], msg_id: int) -> list[bytes]:
        """Create BLE packets from JSON data with fragmentation."""
        payload_str = json.dumps(json_data, separators=(",", ":"))
        payload_bytes = payload_str.encode("utf-8") + b"\x00\xff"

        packets = []
        first_cap = self.mtu - 5
        next_cap = self.mtu - 2

        if len(payload_bytes) <= first_cap:
            total = 1
        else:
            total = 1 + math.ceil((len(payload_bytes) - first_cap) / next_cap)

        # First packet with header
        packets.append(
            bytes([0xFF, 0x00, total, msg_id, 0x00]) + payload_bytes[:first_cap]
        )

        # Subsequent packets
        offset = first_cap
        idx = 1
        while offset < len(payload_bytes):
            end = offset + next_cap
            packets.append(bytes([msg_id, idx]) + payload_bytes[offset:end])
            offset = end
            idx += 1

        return packets

    def parse_response(self, raw_chunks: list[bytes]) -> dict[str, Any]:
        """Parse BLE response chunks into JSON."""
        if not raw_chunks or raw_chunks[0][0] != 0xFF:
            raise ValueError("Invalid chunk stream")

        msg_id = raw_chunks[0][3]
        payload = bytearray(raw_chunks[0][5:])

        for c in raw_chunks[1:]:
            if c[0] != msg_id:
                raise ValueError("Chunk message ID mismatch")
            payload.extend(c[2:])

        clean = payload.split(b"\x00")[0]
        try:
            return json.loads(clean.decode("utf-8"))
        except Exception as e:
            _LOGGER.error("JSON parse failed: %s", clean)
            raise ValueError("Failed to parse JSON response") from e

    def extract_pars(self, response: dict[str, Any]) -> dict[str, Any]:
        """Extract parameters from response body."""
        body = response.get("body", {})
        if "pars" in body:
            return body["pars"]
        if body.get("results"):
            return body["results"][0].get("pars", {})
        return {}

    def extract_errors(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract error list from response."""
        pars = self.extract_pars(response)
        return pars.get("errs", [])

    async def read_response_chunks(self, client: BleakClient) -> list[bytes]:
        """Read response chunks from the characteristic."""
        chunks = []
        expected = 1
        last_data = b""
        attempts = 0
        max_attempts = 40

        while len(chunks) < expected and attempts < max_attempts:
            try:
                data = await client.read_gatt_char(CHARACTERISTIC_UUID)
                if data != last_data:
                    last_data = data
                    chunks.append(data)
                    if data[0] == 0xFF:
                        expected = data[2]
                attempts += 1
            except Exception as e:  # noqa: BLE001
                _LOGGER.error("Read error: %s", e)
                break

        if len(chunks) != expected:
            raise TimeoutError(
                f"Incomplete response: got {len(chunks)}/{expected} chunks"
            )

        return chunks

    async def send_pairing_request(
        self, client: BleakClient, pin: str
    ) -> dict[str, Any]:
        """Send pairing request and return parsed response."""
        meta = _RequestMeta(evt_type=10, dev_id=None)
        body = _RequestBody(meta=meta, pars={})

        req_id = random.randint(1000000, 9999999)
        salt = f"{self.session_id}{req_id}"
        token = self.calculate_token(pin, salt)

        envelope = _RequestEnvelope(
            session=self.session_id, id=req_id, token=token, salt=salt, body=body
        )

        # Increment message ID counter (1-255)
        self.msg_id_counter = (self.msg_id_counter % 254) + 1

        request_dict = envelope.to_dict()
        packets = self.create_packets(request_dict, self.msg_id_counter)

        _LOGGER.debug("Sending pairing request (ReqID: %s)", req_id)

        # Send packets
        for packet in packets:
            await client.write_gatt_char(CHARACTERISTIC_UUID, packet, response=True)

        # Read response
        chunks = await self.read_response_chunks(client)
        return self.parse_response(chunks)

    async def send_request(
        self,
        client: BleakClient,
        pin: str,
        dev_id: str,
        evt_type: int,
        ctrl: int | None = None,
        pars: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a general request and return parsed response."""
        meta = _RequestMeta(evt_type=evt_type, dev_id=dev_id)
        opts_dict: dict[str, int] | None = {"ctrl": ctrl} if ctrl is not None else None
        body = _RequestBody(meta=meta, opts=opts_dict, pars=pars)

        req_id = random.randint(1000000, 9999999)
        salt = f"{self.session_id}{req_id}"
        token = self.calculate_token(pin, salt)

        envelope = _RequestEnvelope(
            session=self.session_id,
            id=req_id,
            token=token,
            salt=salt,
            body=body,
        )

        # Increment message ID counter (1-255)
        self.msg_id_counter = (self.msg_id_counter % 254) + 1

        request_dict = envelope.to_dict()
        packets = self.create_packets(request_dict, self.msg_id_counter)

        _LOGGER.debug("Sending request (ReqID: %s, %d packets)", req_id, len(packets))

        # Send packets
        for packet in packets:
            await client.write_gatt_char(CHARACTERISTIC_UUID, packet, response=True)

        # Read response
        chunks = await self.read_response_chunks(client)
        return self.parse_response(chunks)


# -------------------------------
# region Client Implementation
# -------------------------------


class BlancoUnitBluetoothClient:
    """Bluetooth client for controlling the Blanco Unit.

    Handles connection, authentication, and all device operations.
    """

    def __init__(
        self,
        pin: str,
        device: BLEDevice,
        connection_callback: Callable[[bool], None],
    ) -> None:
        """Initialize the Blanco Unit Bluetooth client.

        Args:
            pin: The 5-digit PIN code for authentication.
            device: The BLEDevice instance representing the Blanco Unit.
            connection_callback: Callback for connection state changes.
        """
        if len(pin) != 5 or not pin.isdigit():
            raise ValueError("PIN must be exactly 5 digits")

        self._pin = pin
        self._device = device
        self._connection_callback = connection_callback
        self._session_data: _BlancoUnitSessionData | None = None
        self._connect_lock = asyncio.Lock()

    @property
    def device_id(self) -> str | None:
        """Return the device ID from the current session, or None if not connected."""
        return self._session_data.dev_id if self._session_data else None

    # -------------------------------
    # region Connection Management
    # -------------------------------

    async def disconnect(self) -> None:
        """Disconnect from the Blanco Unit BLE device if connected."""
        if self._session_data:
            await self._session_data.client.disconnect()

    async def _connect(self) -> _BlancoUnitSessionData:
        """Connect to the device if not already connected and authenticate."""
        async with self._connect_lock:
            _LOGGER.debug("Connecting to device %s", self._device.address)
            if self._session_data:
                _LOGGER.debug("Already connected")
                return self._session_data

            client = await establish_connection(
                client_class=BleakClientWithServiceCache,
                device=self._device,
                name=self._device.name or "Unknown Device",
                disconnected_callback=self._handle_disconnect,
            )

            # Create protocol instance for this session
            protocol = _BlancoUnitProtocol(mtu=MTU_SIZE)

            # Perform initial pairing
            dev_id = await self._perform_pairing(client, protocol)

            _LOGGER.debug("Connected and paired with device ID: %s", dev_id)
            self._session_data = _BlancoUnitSessionData(
                client=client,
                dev_id=dev_id,
                protocol=protocol,
            )
            self._connection_callback(self._session_data.client.is_connected)
            return self._session_data

    def _handle_disconnect(self, _: BleakClient) -> None:
        """Reset session and call connection callback."""
        _LOGGER.debug("Device disconnected")
        self._session_data = None
        self._connection_callback(False)

    async def _perform_pairing(
        self, client: BleakClient, protocol: _BlancoUnitProtocol
    ) -> str:
        """Perform initial pairing to get device ID.

        Raises:
            BlancoUnitAuthenticationError: If PIN is wrong (error code 4).
            BlancoUnitConnectionError: If device ID cannot be extracted.
        """
        # Validate PIN and get response
        is_valid, response = await validate_pin(client, self._pin, protocol)
        if not is_valid:
            raise BlancoUnitAuthenticationError("Wrong PIN - Authentication failed")

        # Extract device ID using shared helper
        dev_id = _extract_device_id(response)
        if dev_id is None:
            raise BlancoUnitConnectionError("No device ID in pairing response")
        return dev_id

    async def _execute_transaction(
        self,
        evt_type: int,
        ctrl: int | None = None,
        pars: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a request-response transaction."""
        session_data = await self._connect()

        response = await session_data.protocol.send_request(
            client=session_data.client,
            pin=self._pin,
            dev_id=session_data.dev_id,
            evt_type=evt_type,
            ctrl=ctrl,
            pars=pars,
        )

        # Check for errors
        errors = session_data.protocol.extract_errors(response)
        for error in errors:
            if error.get("err_code") == 4:
                raise BlancoUnitAuthenticationError(
                    "Authentication error during operation"
                )

        return response

    # -------------------------------
    # region Read Operations
    # -------------------------------

    async def get_system_info(self) -> BlancoUnitSystemInfo:
        """Read and return system information (firmware versions, device name, reset count)."""
        session_data = await self._connect()
        resp = await self._execute_transaction(evt_type=7, ctrl=3, pars={"evt_type": 2})
        pars = session_data.protocol.extract_pars(resp)
        return BlancoUnitSystemInfo(
            sw_ver_comm_con=pars.get("sw_ver_comm_con", {}).get("val", "Unknown"),
            sw_ver_elec_con=pars.get("sw_ver_elec_con", {}).get("val", "Unknown"),
            sw_ver_main_con=pars.get("sw_ver_main_con", {}).get("val", "Unknown"),
            dev_name=pars.get("dev_name", {}).get("val", "Unknown"),
            reset_cnt=pars.get("reset_cnt", {}).get("val", 0),
        )

    async def get_settings(self) -> BlancoUnitSettings:
        """Read and return device configuration settings."""
        session_data = await self._connect()
        resp = await self._execute_transaction(evt_type=7, ctrl=3, pars={"evt_type": 5})
        pars = session_data.protocol.extract_pars(resp)
        return BlancoUnitSettings(
            calib_still_wtr=pars.get("calib_still_wtr", {}).get("val", 0),
            calib_soda_wtr=pars.get("calib_soda_wtr", {}).get("val", 0),
            filter_life_tm=pars.get("filter_life_tm", {}).get("val", 0),
            post_flush_quantity=pars.get("post_flush_quantity", {}).get("val", 0),
            set_point_cooling=pars.get("set_point_cooling", {}).get("val", 0),
            wtr_hardness=pars.get("wtr_hardness", {}).get("val", 0),
        )

    async def get_status(self) -> BlancoUnitStatus:
        """Read and return real-time device status."""
        session_data = await self._connect()
        resp = await self._execute_transaction(evt_type=7, ctrl=3, pars={"evt_type": 6})
        pars = session_data.protocol.extract_pars(resp)
        return BlancoUnitStatus(
            tap_state=pars.get("tap_state", {}).get("val", 0),
            filter_rest=pars.get("filter_rest", {}).get("val", 0),
            co2_rest=pars.get("co2_rest", {}).get("val", 0),
            wtr_disp_active=pars.get("wtr_disp_active", {}).get("val", False),
            firm_upd_avlb=pars.get("firm_upd_avlb", {}).get("val", False),
            set_point_cooling=pars.get("set_point_cooling", {}).get("val", 0),
            clean_mode_state=pars.get("clean_mode_state", {}).get("val", 0),
            err_bits=pars.get("err_bits", {}).get("val", 0),
        )

    async def get_device_identity(self) -> BlancoUnitIdentity:
        """Read and return device identity (serial number, service code)."""
        session_data = await self._connect()
        resp = await self._execute_transaction(evt_type=7, ctrl=2, pars={})
        pars = session_data.protocol.extract_pars(resp)
        return BlancoUnitIdentity(
            serial_no=pars.get("ser_no", "Unknown"),
            service_code=pars.get("serv_code", "Unknown"),
        )

    async def get_wifi_info(self) -> BlancoUnitWifiInfo:
        """Read and return WiFi and network information."""
        session_data = await self._connect()
        resp = await self._execute_transaction(evt_type=7, ctrl=10, pars={})
        pars = session_data.protocol.extract_pars(resp)
        return BlancoUnitWifiInfo(
            cloud_connect=pars.get("cloud_connect", {}).get("val", False),
            ssid=pars.get("ssid", {}).get("val", ""),
            signal=pars.get("signal", {}).get("val", 0),
            ip=pars.get("ip", {}).get("val", ""),
            ble_mac=pars.get("b_mac", {}).get("val", ""),
            wifi_mac=pars.get("w_mac", {}).get("val", ""),
            gateway=pars.get("default_gateway", {}).get("val", ""),
            gateway_mac=pars.get("default_gateway_mac", {}).get("val", ""),
            subnet=pars.get("subnet", {}).get("val", ""),
        )

    # -------------------------------
    # region Write Operations
    # -------------------------------

    async def set_temperature(self, cooling_celsius: int) -> bool:
        """Set cooling temperature (4-10°C).

        Args:
            cooling_celsius: Target cooling temperature in Celsius (4-10).

        Returns:
            True if successful.

        Raises:
            ValueError: If temperature is out of range.
        """
        if not (4 <= cooling_celsius <= 10):
            raise ValueError("Temperature must be between 4 and 10°C")

        _LOGGER.info("Setting temperature to %d°C", cooling_celsius)
        req = _SetTemperaturePars(cooling_celsius=cooling_celsius)
        resp = await self._execute_transaction(evt_type=7, ctrl=5, pars=req.to_pars())
        return resp.get("type") == 2

    async def set_water_hardness(self, level: int) -> bool:
        """Set water hardness level (1-9).

        Args:
            level: Water hardness level (1-9).

        Returns:
            True if successful.

        Raises:
            ValueError: If level is out of range.
        """
        _LOGGER.info("Setting water hardness to level %d", level)
        req = _SetWaterHardnessPars(level=level)
        resp = await self._execute_transaction(evt_type=7, ctrl=5, pars=req.to_pars())
        return resp.get("type") == 2

    async def change_pin(self, new_pin: str) -> bool:
        """Change the device PIN.

        Args:
            new_pin: New 5-digit PIN.

        Returns:
            True if successful.

        Raises:
            ValueError: If PIN format is invalid.
        """
        _LOGGER.info("Changing PIN")
        req = _ChangePinPars(new_pin=new_pin)
        resp = await self._execute_transaction(evt_type=7, ctrl=13, pars=req.to_pars())
        if resp.get("type") == 2:
            self._pin = new_pin
            return True
        return False

    async def dispense_water(self, amount_ml: int, co2_intensity: int) -> bool:
        """Dispense water with specified amount and carbonation.

        Args:
            amount_ml: Amount in milliliters (100-1500, must be multiple of 100).
            co2_intensity: CO2 carbonation level (1=still, 2=medium, 3=high).

        Returns:
            True if dispensing started successfully.

        Raises:
            ValueError: If amount or intensity is invalid.
        """
        if not (100 <= amount_ml <= 1500):
            raise ValueError("Amount must be between 100ml and 1500ml")
        if amount_ml % 100 != 0:
            raise ValueError("Amount must be a multiple of 100ml")
        if co2_intensity not in (1, 2, 3):
            raise ValueError("CO2 intensity must be 1 (still), 2 (medium), or 3 (high)")

        _LOGGER.info("Dispensing %dml with CO2 intensity %d", amount_ml, co2_intensity)
        req = _DispensePars(amount_ml=amount_ml, co2_intensity=co2_intensity)
        resp = await self._execute_transaction(
            evt_type=7, ctrl=1000, pars=req.to_pars()
        )
        return resp.get("type") == 2

    async def set_calibration_still(self, amount: int) -> bool:
        """Set calibration amount for still water.

        Args:
            amount: Calibration amount.

        Returns:
            True if successful.
        """
        _LOGGER.info("Setting still water calibration to %d", amount)
        req = _SetCalibrationPars(calib_type="calib_still_wtr", amount=amount)
        resp = await self._execute_transaction(evt_type=7, ctrl=5, pars=req.to_pars())
        return resp.get("type") == 2

    async def set_calibration_soda(self, amount: int) -> bool:
        """Set calibration amount for soda water.

        Args:
            amount: Calibration amount.

        Returns:
            True if successful.
        """
        _LOGGER.info("Setting soda water calibration to %d", amount)
        req = _SetCalibrationPars(calib_type="calib_soda_wtr", amount=amount)
        resp = await self._execute_transaction(evt_type=7, ctrl=5, pars=req.to_pars())
        return resp.get("type") == 2


# -------------------------------
# region Standalone Functions
# -------------------------------


def _extract_device_id(response: dict[str, Any]) -> str | None:
    """Extract device ID from a pairing response.

    Args:
        response: The response dictionary from a pairing request.

    Returns:
        The device ID if found, None otherwise.
    """
    try:
        body = response.get("body", {})
        meta = body.get("meta", {})
        if "dev_id" in meta:
            return meta["dev_id"]
    except (KeyError, TypeError):
        pass
    return None


async def validate_pin(
    client: BleakClient, pin: str, protocol: _BlancoUnitProtocol | None = None
) -> tuple[bool, dict[str, Any]]:
    """Test if a PIN is valid by attempting to pair with the device.

    This is a standalone function that works with an existing BleakClient.

    Args:
        client: An active BleakClient connection.
        pin: The 5-digit PIN to validate.
        protocol: Optional protocol instance. If None, creates a new one.

    Returns:
        Tuple of (is_valid, response_dict):
            - is_valid: True if PIN is valid, False if wrong PIN (error code 4)
            - response_dict: The full response from the pairing attempt

    Raises:
        ValueError: If PIN format is invalid.
        TimeoutError: If response chunks cannot be read completely.
        Any other exceptions are propagated (connection errors, etc.)
    """
    if len(pin) != 5 or not pin.isdigit():
        raise ValueError("PIN must be exactly 5 digits")

    _LOGGER.debug("Validating PIN %s", pin)

    # Use provided protocol or create new one
    if protocol is None:
        protocol = _BlancoUnitProtocol(mtu=MTU_SIZE)

    # Send pairing request and get response
    response = await protocol.send_pairing_request(client, pin)

    # Check for authentication error (error code 4)
    errors = protocol.extract_errors(response)
    for error in errors:
        if error.get("err_code") == 4:
            _LOGGER.debug("PIN validation failed: wrong PIN (error code 4)")
            return (False, response)

    # Check if we got a device ID in results (successful pairing)
    dev_id = _extract_device_id(response)
    if dev_id is not None:
        _LOGGER.debug("PIN validation successful")
        return (True, response)

    _LOGGER.debug("PIN validation failed: no device ID in response")
    return (False, response)


# -------------------------------
# region Session Data
# -------------------------------


@dataclass
class _BlancoUnitSessionData:
    """Internal: Session data stored during connection."""

    client: BleakClient
    dev_id: str
    protocol: _BlancoUnitProtocol
