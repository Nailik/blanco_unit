"""Defines the bluetooth client to control the Vogels Motion Mount."""

from __future__ import annotations
import json

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
import logging
import struct

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from sqlalchemy import Boolean
import time
import random
import hashlib
from .const import (
    CHAR_X,
)
import hashlib
import json
from typing import Dict
import hashlib
import json
import math
import asyncio
import logging
from typing import List, Dict, Any, Optional

_LOGGER = logging.getLogger(__name__)

# -------------------------------
# region Setup
# -------------------------------


class BlancoUnitBluetoothClient:
    """Bluetooth client for controlling the Blanco Unit.

    Handles connection, authentication, reading and writing characteristics.
    """

    def __init__(
        self,
        pin: str,
        device: BLEDevice,
        connection_callback: Callable[[bool], None],
    ) -> None:
        """Initialize the Blanco Unit client.

        Args:
            pin: The PIN code for authentication, or None.
            device: The BLEDevice instance representing the mount.
            connection_callback: Callback for connection state changes.
        """
        self._pin = pin
        self._device = device
        self._connection_callback = connection_callback
        self._client: BleakClient | None = None
        self._connect_lock = asyncio.Lock()

    # -------------------------------
    # region Read
    # -------------------------------

    def sha256_hex(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def compute_token(self, pin: str, session: int, request_id: int) -> str:
        salt = f"{session}{request_id}"
        pin_hash = self.sha256_hex(pin.encode("ascii"))
        return self.sha256_hex((pin_hash + salt).encode("ascii"))

    def build_ble_frame(self, seq_hi: int, seq_lo: int, payload: bytes) -> bytes:
        return b"\xff\x00" + bytes([seq_hi, seq_lo]) + b"\x00" + payload + b"\x00\xff"

    def build_pairing_request(
        self, pin: str, session: int, request_id: int, timestamp_ms: int
    ) -> Dict:
        token = self.compute_token(pin, session, request_id)

        return {
            "session": session,
            "id": request_id,
            "type": 1,
            "token": token,
            "salt": f"{session}{request_id}",
            "body": {
                "meta": {
                    "dev_type": 1,
                    "evt_ts": timestamp_ms,
                    "evt_type": 10,
                    "evt_ver": 1,
                },
                "pars": {},
            },
        }

    async def send_pairing_request(
        self,
        client: BleakClient,
        char_uuid: str,
        pin: str,
        session: int,
        request_id: int,
        timestamp_ms: int,
        seq_hi: int = 0x02,
        seq_lo: int = 0x04,
        mtu: int = 20,
    ):
        request = self.build_pairing_request(pin, session, request_id, timestamp_ms)

        payload = json.dumps(request, separators=(",", ":")).encode("utf-8")

        frame = self.build_ble_frame(seq_hi, seq_lo, payload)

        # BLE fragmentation
        for i in range(0, len(frame), mtu):
            await client.write_gatt_char(char_uuid, frame[i : i + mtu], response=False)

    def generate_token(self, pin: str, salt: str) -> str:
        # Step 1: SHA256 of the pin → hex digest
        pin_hash_hex = hashlib.sha256(
            pin.encode("utf-8")
        ).hexdigest()  # 64-char hex string

        # Step 2: Concatenate pin_hash_hex (as bytes) + salt (as bytes)
        combined = pin_hash_hex.encode("utf-8") + salt.encode("utf-8")

        # Step 3: SHA256 of the combined bytes → final token
        token = hashlib.sha256(combined).hexdigest()
        return token

    async def read_data(self):
        """Read and return the current permissions for the connected Vogels Motion Mount."""
        client = await self._connect()
        _LOGGER.debug(f"SodaClient with pin {str(self._pin)}")
        soda = SodaClient(client, str(self._pin))

        # 1. Pair (Required first)
        await soda.pair()

        # 2. Fetch Data Sequence (matches log flow)
        sys_info = await soda.get_system_info()
        _LOGGER.debug(f"System: {json.dumps(sys_info, indent=2)}")

        settings = await soda.get_settings()
        _LOGGER.debug(f"Settings: {json.dumps(settings, indent=2)}")

        # Wait a moment between heavy requests
        await asyncio.sleep(0.5)

        dev_info = await soda.get_device_info()
        _LOGGER.debug(f"Serial: {json.dumps(dev_info, indent=2)}")

        status = await soda.get_status()
        _LOGGER.debug(f"Status: {json.dumps(status, indent=2)}")

        errors = await soda.get_errors()
        _LOGGER.debug(f"Errors: {json.dumps(errors, indent=2)}")

    async def _read(self, char_uuid: str) -> bytes:
        """Read data by first connecting and then returning the read data."""
        client = await self._connect()
        data = await client.read_gatt_char(char_uuid)
        _LOGGER.debug("Read data %s | %s", char_uuid, data)
        return data

    async def _write(self, char_uuid: str, data: dict):
        """Writes data by first connecting, checking permission status and then writing data. Also reads updated data that is then returned to be verified."""
        _LOGGER.debug("_write before connect")
        client = await self._connect()
        _LOGGER.debug("_write after connect")

        await self.send_ble_json(client, CHAR_X, data)

        _LOGGER.debug("Wrote data %s | %s", char_uuid, data)

    async def send_ble_json(
        self,
        client: BleakClient,
        char_uuid: str,
        data_dict: dict,
        start_chunk_id=0x53,
        max_chunk_size=200,
    ):
        """
        Sends JSON over BLE with chunking.
        Only the first chunk has the full header; subsequent chunks have 2-byte prefix.
        """
        json_bytes = json.dumps(data_dict, separators=(",", ":")).encode("utf-8")
        total_len = len(json_bytes)
        chunk_id = start_chunk_id
        sequence = 0

        for start in range(0, total_len, max_chunk_size):
            end = start + max_chunk_size
            payload = json_bytes[start:end]

            if start == 0:
                # First chunk: full header
                header = bytes([0xFF, 0x00, 0x02, chunk_id & 0xFF, 0x00])
                chunk = header + payload
            else:
                # Subsequent chunks: just 2-byte prefix
                chunk = bytes([chunk_id & 0xFF, sequence & 0xFF]) + payload

            # Append end-of-packet marker for last chunk
            if end >= total_len:
                chunk += bytes([0x00, 0xFF])

            # Send chunk
            await client.write_gatt_char(char_uuid, chunk, response=True)
            _LOGGER.debug("Wrote chunk %s", chunk.hex(" "))

            sequence += 1  # increment sequence for next chunk

    # -------------------------------
    # region Write
    # -------------------------------

    # -------------------------------
    # region Notifications
    # -------------------------------

    # -------------------------------
    # region Connection
    # -------------------------------

    async def disconnect(self):
        """Disconnect from the Vogels Motion Mount BLE device if connected."""
        if self._client:
            await self._client.disconnect()

    async def _connect(self) -> BleakClient:
        """Connect to the device if not already connected. Read auth status and store it in session data."""
        async with self._connect_lock:
            _LOGGER.debug(f"check device exists {self._device}")
            if self._device:
                _LOGGER.debug(
                    f"Connecting to device name {self._device.name} address {self._device.address} details {self._device.details}"
                )
            else:
                _LOGGER.debug("No device to connect to")

            if self._client:
                _LOGGER.debug("Already connected")
                return self._client

            _LOGGER.debug(f"creat bleak client with {self._device}")

            self._client = BleakClient(
                address_or_ble_device=self._device,
                disconnected_callback=self._handle_disconnect,
                timeout=40.0,
                pairing=False,
            )
            await self._client.connect()
            """self._client = await establish_connection(
                client_class=BleakClientWithServiceCache,
                device=self._device,
                name=self._device.name or "Unknown Device",
                use_services_cache=True,
                disconnected_callback=self._handle_disconnect,
            )
            await self._client.pair()"""

            _LOGGER.debug(
                f"Connecting ended {self._client} and {self._client.is_connected}"
            )

            return self._client

    def _handle_disconnect(self, _: BleakClient):
        """Reset session and call connection callback."""
        _LOGGER.debug(f"_handle_disconnect")
        self._client = None
        self._connection_callback(False)


async def validate_pin(client: BleakClient, pin: int | None) -> bool:
    return True


CHARACTERISTIC_UUID = "3b531d4d-ed58-4677-b2fa-1c72a86082cf"


class SodaProtocol:
    """Handles low-level fragmentation and hashing."""

    def __init__(self, mtu: int = 200):
        self.mtu = mtu

    def calculate_token(self, pin: str, salt: str) -> str:
        pin_hash = hashlib.sha256(pin.encode("utf-8")).hexdigest()
        combined = pin_hash + salt
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def create_packets(self, json_data: Dict[str, Any], msg_id: int) -> List[bytes]:
        payload_str = json.dumps(json_data, separators=(",", ":"))
        payload_bytes = payload_str.encode("utf-8") + b"\x00\xff"

        packets = []
        first_cap = self.mtu - 5
        next_cap = self.mtu - 2

        if len(payload_bytes) <= first_cap:
            total = 1
        else:
            total = 1 + math.ceil((len(payload_bytes) - first_cap) / next_cap)

        # Chunk 0
        packets.append(
            bytes([0xFF, 0x00, total, msg_id, 0x00]) + payload_bytes[:first_cap]
        )

        # Chunk N
        offset = first_cap
        idx = 1
        while offset < len(payload_bytes):
            end = offset + next_cap
            packets.append(bytes([msg_id, idx]) + payload_bytes[offset:end])
            offset = end
            idx += 1

        return packets

    def parse_response(self, raw_chunks: List[bytes]) -> Dict[str, Any]:
        if not raw_chunks or raw_chunks[0][0] != 0xFF:
            raise ValueError("Invalid chunk stream")

        msg_id = raw_chunks[0][3]
        payload = bytearray(raw_chunks[0][5:])

        for c in raw_chunks[1:]:
            if c[0] != msg_id:
                raise ValueError("Chunk mismatch")
            payload.extend(c[2:])

        clean = payload.split(b"\x00")[0]
        return json.loads(clean.decode("utf-8"))


class SodaClient:
    """High-level client for the Soda device."""

    def __init__(self, client: BleakClient, pin: str):
        self.client = client
        self.pin = pin
        self.protocol = SodaProtocol(mtu=200)

        # State
        self.session_id = random.randint(1000000, 9999999)
        self.dev_id: Optional[str] = None
        self.msg_id_counter = 1

    async def _send_request(self, body_content: Dict[str, Any]) -> Dict[str, Any]:
        """Generic handler for request/response cycle."""

        # 1. Prepare Request Metadata
        req_id = random.randint(1000000, 9999999)
        salt = f"{self.session_id}{req_id}"
        token = self.protocol.calculate_token(self.pin, salt)

        # Increment internal message ID (1-255)
        self.msg_id_counter = (self.msg_id_counter % 254) + 1

        # Construct specific 'body' based on whether we are authenticated
        # Note: 'evt_ts' matches current time in ms
        current_ts = int(time.time() * 1000)

        # Merge the specific body content with the generic envelope
        full_body = {
            "meta": {
                "dev_type": 1,
                "evt_ts": current_ts,
                "evt_ver": 1,
                # evt_type 7 is standard for commands, 10 is for pairing
                "evt_type": body_content.get("meta", {}).get("evt_type", 7),
            },
            **{k: v for k, v in body_content.items() if k != "meta"},
        }

        # Inject dev_id if we have it (required for all non-pairing requests)
        if self.dev_id:
            full_body["meta"]["dev_id"] = self.dev_id

        payload = {
            "session": self.session_id,
            "id": req_id,
            "type": 1,
            "token": token,
            "salt": salt,
            "body": full_body,
        }

        # 2. Write
        packets = self.protocol.create_packets(payload, self.msg_id_counter)
        _LOGGER.debug(f"Sending ReqID {req_id} ({len(packets)} chunks)...")

        for p in packets:
            await self.client.write_gatt_char(CHARACTERISTIC_UUID, p, response=True)

        # 3. Read (Poll Loop)
        chunks = []
        expected = 1
        last_data = b""
        attempts = 0

        while len(chunks) < expected and attempts < 30:
            try:
                data = await self.client.read_gatt_char(CHARACTERISTIC_UUID)
                if data != last_data:
                    last_data = data
                    chunks.append(data)
                    if data[0] == 0xFF:
                        expected = data[2]
                else:
                    await asyncio.sleep(0.05)
                attempts += 1
            except Exception as e:
                _LOGGER.error(f"Read error: {e}")
                break

        if len(chunks) != expected:
            raise TimeoutError("Failed to receive complete response")

        return self.protocol.parse_response(chunks)

    async def pair(self):
        """Initial Pairing Request (evt_type: 10)."""
        _LOGGER.info("Pairing...")

        # Pairing has specific meta requirements
        body = {"meta": {"evt_type": 10}, "pars": {}}

        resp = await self._send_request(body)

        # Capture the dev_id for future requests
        try:
            self.dev_id = resp["body"]["meta"]["dev_id"]
            _LOGGER.info(f"Paired! Device ID: {self.dev_id}")
        except KeyError:
            # Fallback if structure varies
            try:
                # Sometimes results are in a list?
                self.dev_id = resp["body"]["results"][0]["meta"]["dev_id"]
                _LOGGER.info(f"Paired! Device ID (from results): {self.dev_id}")
            except:
                _LOGGER.warning("Could not extract dev_id from pairing response")

        return resp

    async def get_system_info(self):
        """(evt_type: 2, ctrl: 3) - Versions, Name, Reset Count"""
        _LOGGER.info("Fetching System Info...")
        return await self._send_request({"opts": {"ctrl": 3}, "pars": {"evt_type": 2}})

    async def get_settings(self):
        """(evt_type: 5, ctrl: 3) - Calibration, Filter Life"""
        _LOGGER.info("Fetching Settings...")
        return await self._send_request({"opts": {"ctrl": 3}, "pars": {"evt_type": 5}})

    async def get_device_info(self):
        """(ctrl: 2, empty pars) - Serial Number, Service Code"""
        _LOGGER.info("Fetching Device Serial/Info...")
        # Note: This uses ctrl 2 and empty pars, unlike the others
        return await self._send_request({"opts": {"ctrl": 2}, "pars": {}})

    async def get_status(self):
        """(evt_type: 6, ctrl: 3) - Tap State, CO2, Filter Rest"""
        _LOGGER.info("Fetching Status...")
        return await self._send_request({"opts": {"ctrl": 3}, "pars": {"evt_type": 6}})

    async def get_errors(self):
        """(evt_type: 4, ctrl: 3) - Error Log"""
        _LOGGER.info("Fetching Errors...")
        return await self._send_request({"opts": {"ctrl": 3}, "pars": {"evt_type": 4}})
