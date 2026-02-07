"""Tests for the Blanco Unit BLE client."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from bleak.backends.device import BLEDevice
import pytest

from custom_components.blanco_unit.client import (
    BlancoUnitAuthenticationError,
    BlancoUnitBluetoothClient,
    BlancoUnitClientError,
    BlancoUnitConnectionError,
    PinValidationResult,
    _AllowCloudServicesPars,
    _BlancoUnitProtocol,
    _ChangePinPars,
    _ConnectWifiPars,
    _DispensePars,
    _extract_device_id,
    _RequestBody,
    _RequestEnvelope,
    _RequestMeta,
    _SetCalibrationPars,
    _SetHeatingTemperaturePars,
    _SetTemperaturePars,
    _SetWaterHardnessPars,
    validate_pin,
)

# -------------------------------
# Exception Tests
# -------------------------------


def test_authentication_error_default_message():
    """Test BlancoUnitAuthenticationError with default message."""
    error = BlancoUnitAuthenticationError()
    assert str(error) == "Wrong PIN"


def test_authentication_error_custom_message():
    """Test BlancoUnitAuthenticationError with custom message."""
    error = BlancoUnitAuthenticationError("Custom auth error")
    assert str(error) == "Custom auth error"


def test_connection_error_default_message():
    """Test BlancoUnitConnectionError with default message."""
    error = BlancoUnitConnectionError()
    assert str(error) == "Connection failed"


def test_connection_error_custom_message():
    """Test BlancoUnitConnectionError with custom message."""
    error = BlancoUnitConnectionError("Custom connection error")
    assert str(error) == "Custom connection error"


def test_client_error_base():
    """Test BlancoUnitClientError base exception."""
    error = BlancoUnitClientError("Base error")
    assert str(error) == "Base error"


# -------------------------------
# Internal Data Model Tests
# -------------------------------


def test_request_meta_to_dict_with_dev_id():
    """Test _RequestMeta.to_dict() with dev_id."""
    meta = _RequestMeta(
        evt_type=1, dev_id="device123", dev_type=1, evt_ver=1, evt_ts=1234567890
    )
    result = meta.to_dict()
    assert result["evt_type"] == 1
    assert result["dev_id"] == "device123"
    assert result["dev_type"] == 1
    assert result["evt_ver"] == 1
    assert result["evt_ts"] == 1234567890


def test_request_meta_to_dict_without_dev_id():
    """Test _RequestMeta.to_dict() without dev_id."""
    meta = _RequestMeta(evt_type=10, dev_type=1, evt_ver=1, evt_ts=1234567890)
    result = meta.to_dict()
    assert result["evt_type"] == 10
    assert "dev_id" not in result
    assert result["dev_type"] == 1


def test_request_body_to_dict_with_opts_and_pars():
    """Test _RequestBody.to_dict() with opts and pars."""
    meta = _RequestMeta(evt_type=1, dev_id="device123")
    body = _RequestBody(meta=meta, opts={"opt1": 1}, pars={"par1": "value1"})
    result = body.to_dict()
    assert "meta" in result
    assert result["opts"] == {"opt1": 1}
    assert result["pars"] == {"par1": "value1"}


def test_request_body_to_dict_without_opts_and_pars():
    """Test _RequestBody.to_dict() without opts and pars."""
    meta = _RequestMeta(evt_type=1, dev_id="device123")
    body = _RequestBody(meta=meta)
    result = body.to_dict()
    assert "meta" in result
    assert "opts" not in result
    assert "pars" not in result


def test_request_envelope_to_dict():
    """Test _RequestEnvelope.to_dict()."""
    meta = _RequestMeta(evt_type=1, dev_id="device123")
    body = _RequestBody(meta=meta)
    envelope = _RequestEnvelope(
        session=123456,
        id=789,
        token="test_token",
        salt="test_salt",
        body=body,
        type=1,
    )
    result = envelope.to_dict()
    assert result["session"] == 123456
    assert result["id"] == 789
    assert result["type"] == 1
    assert result["token"] == "test_token"
    assert result["salt"] == "test_salt"
    assert "body" in result


def test_set_temperature_pars_to_pars():
    """Test _SetTemperaturePars.to_pars()."""
    pars = _SetTemperaturePars(cooling_celsius=7)
    result = pars.to_pars()
    assert result["set_point_cooling"]["val"] == 7


def test_set_heating_temperature_pars_to_pars():
    """Test _SetHeatingTemperaturePars.to_pars()."""
    pars = _SetHeatingTemperaturePars(heating_celsius=65)
    result = pars.to_pars()
    assert result["set_point_heating"]["val"] == 65


def test_set_water_hardness_pars_to_pars_valid():
    """Test _SetWaterHardnessPars.to_pars() with valid level."""
    pars = _SetWaterHardnessPars(level=5)
    result = pars.to_pars()
    assert result["wtr_hardness"]["val"] == 5


def test_set_water_hardness_pars_to_pars_invalid_low():
    """Test _SetWaterHardnessPars.to_pars() with level too low."""
    pars = _SetWaterHardnessPars(level=0)
    with pytest.raises(ValueError, match="Hardness level must be 1-9"):
        pars.to_pars()


def test_set_water_hardness_pars_to_pars_invalid_high():
    """Test _SetWaterHardnessPars.to_pars() with level too high."""
    pars = _SetWaterHardnessPars(level=10)
    with pytest.raises(ValueError, match="Hardness level must be 1-9"):
        pars.to_pars()


def test_change_pin_pars_to_pars_valid():
    """Test _ChangePinPars.to_pars() with valid PIN."""
    pars = _ChangePinPars(new_pin="12345")
    result = pars.to_pars()
    assert result["new_pass"] == "12345"


def test_change_pin_pars_to_pars_invalid_length():
    """Test _ChangePinPars.to_pars() with invalid PIN length."""
    pars = _ChangePinPars(new_pin="123")
    with pytest.raises(ValueError, match="PIN must be 5 digits"):
        pars.to_pars()


def test_change_pin_pars_to_pars_invalid_format():
    """Test _ChangePinPars.to_pars() with non-digit PIN."""
    pars = _ChangePinPars(new_pin="abcde")
    with pytest.raises(ValueError, match="PIN must be 5 digits"):
        pars.to_pars()


def test_dispense_pars_to_pars():
    """Test _DispensePars.to_pars()."""
    pars = _DispensePars(amount_ml=250, co2_intensity=3)
    result = pars.to_pars()
    assert result["disp_amt"] == 250
    assert result["co2_int"] == 3


def test_set_calibration_pars_to_pars_still():
    """Test _SetCalibrationPars.to_pars() for still water."""
    pars = _SetCalibrationPars(calib_type="calib_still_wtr", amount=5)
    result = pars.to_pars()
    assert result["calib_still_wtr"]["val"] == 5


def test_set_calibration_pars_to_pars_soda():
    """Test _SetCalibrationPars.to_pars() for soda water."""
    pars = _SetCalibrationPars(calib_type="calib_soda_wtr", amount=7)
    result = pars.to_pars()
    assert result["calib_soda_wtr"]["val"] == 7


# -------------------------------
# Protocol Tests
# -------------------------------


def test_protocol_init():
    """Test _BlancoUnitProtocol initialization."""
    protocol = _BlancoUnitProtocol(mtu=200)
    assert protocol.mtu == 200
    assert 1000000 <= protocol.session_id <= 9999999
    assert protocol.msg_id_counter == 1


def test_protocol_calculate_token():
    """Test token calculation."""
    protocol = _BlancoUnitProtocol()
    token = protocol.calculate_token("12345", "test_salt")
    assert len(token) == 64  # SHA256 hex digest
    assert isinstance(token, str)

    # Same inputs should produce same token
    token2 = protocol.calculate_token("12345", "test_salt")
    assert token == token2

    # Different inputs should produce different tokens
    token3 = protocol.calculate_token("12345", "different_salt")
    assert token != token3


def test_protocol_create_packets_single():
    """Test packet creation for small message (single packet)."""
    protocol = _BlancoUnitProtocol(mtu=200)
    data = {"test": "data"}
    packets = protocol.create_packets(data, msg_id=1)

    assert len(packets) == 1
    assert packets[0][0] == 0xFF  # Header marker
    assert packets[0][1] == 0x00  # Reserved
    assert packets[0][2] == 1  # Total packets
    assert packets[0][3] == 1  # Message ID


def test_protocol_create_packets_multiple():
    """Test packet creation for large message (multiple packets)."""
    protocol = _BlancoUnitProtocol(mtu=50)  # Small MTU to force fragmentation
    data = {"test": "x" * 200}  # Large data
    packets = protocol.create_packets(data, msg_id=5)

    assert len(packets) > 1
    assert packets[0][0] == 0xFF  # First packet header
    assert packets[0][3] == 5  # Message ID
    assert packets[1][0] == 5  # Continuation packet message ID
    assert packets[1][1] == 1  # Continuation packet index


def test_protocol_parse_response_single_packet():
    """Test parsing response from single packet."""
    protocol = _BlancoUnitProtocol()
    response_data = {"status": "ok"}
    json_str = json.dumps(response_data)
    packet = bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"

    result = protocol.parse_response([packet])
    assert result["status"] == "ok"


def test_protocol_parse_response_multiple_packets():
    """Test parsing response from multiple packets."""
    protocol = _BlancoUnitProtocol()
    response_data = {"status": "ok", "data": "test"}
    json_str = json.dumps(response_data)
    payload = json_str.encode("utf-8") + b"\x00\xff"

    # Split into two packets
    packet1 = bytes([0xFF, 0x00, 2, 10, 0x00]) + payload[:20]
    packet2 = bytes([10, 1]) + payload[20:]

    result = protocol.parse_response([packet1, packet2])
    assert result["status"] == "ok"
    assert result["data"] == "test"


def test_protocol_parse_response_invalid_header():
    """Test parsing response with invalid header."""
    protocol = _BlancoUnitProtocol()
    packet = bytes([0x00, 0x00, 1, 10, 0x00]) + b'{"test":"data"}\x00\xff'

    with pytest.raises(ValueError, match="Invalid chunk stream"):
        protocol.parse_response([packet])


def test_protocol_parse_response_message_id_mismatch():
    """Test parsing response with message ID mismatch."""
    protocol = _BlancoUnitProtocol()
    packet1 = bytes([0xFF, 0x00, 2, 10, 0x00]) + b'{"test":'
    packet2 = bytes([11, 1]) + b'"data"}\x00\xff'  # Wrong message ID

    with pytest.raises(ValueError, match="Chunk message ID mismatch"):
        protocol.parse_response([packet1, packet2])


def test_protocol_parse_response_invalid_json():
    """Test parsing response with invalid JSON."""
    protocol = _BlancoUnitProtocol()
    packet = bytes([0xFF, 0x00, 1, 10, 0x00]) + b"invalid json\x00\xff"

    with pytest.raises(ValueError, match="Failed to parse JSON response"):
        protocol.parse_response([packet])


def test_protocol_extract_pars():
    """Test extracting parameters from response."""
    protocol = _BlancoUnitProtocol()
    response = {"body": {"pars": {"temp": 25, "humidity": 60}}}

    result = protocol.extract_pars(response)
    assert result == {"temp": 25, "humidity": 60}


def test_protocol_extract_pars_missing():
    """Test extracting parameters when missing."""
    protocol = _BlancoUnitProtocol()
    response = {"body": {}}

    result = protocol.extract_pars(response)
    assert result == {}


def test_protocol_extract_errors():
    """Test extracting errors from response."""
    protocol = _BlancoUnitProtocol()
    response = {"body": {"pars": {"errs": [{"code": 1, "msg": "Error"}]}}}

    result = protocol.extract_errors(response)
    assert len(result) == 1
    assert result[0]["code"] == 1
    assert result[0]["msg"] == "Error"


def test_protocol_extract_errors_missing():
    """Test extracting errors when missing."""
    protocol = _BlancoUnitProtocol()
    response = {"body": {}}

    result = protocol.extract_errors(response)
    assert result == []


def test_protocol_extract_pars_with_results():
    """Test extracting parameters from response with results."""
    protocol = _BlancoUnitProtocol()
    response = {"body": {"results": [{"pars": {"temp": 30}}]}}

    result = protocol.extract_pars(response)
    assert result == {"temp": 30}


def test_protocol_extract_pars_with_empty_results():
    """Test extracting parameters from response with empty results."""
    protocol = _BlancoUnitProtocol()
    response = {"body": {"results": [{}]}}

    result = protocol.extract_pars(response)
    assert result == {}


@pytest.mark.asyncio
async def test_protocol_read_response_chunks_success():
    """Test reading response chunks successfully."""
    protocol = _BlancoUnitProtocol()
    mock_client = AsyncMock()

    # Mock single packet response
    packet = bytes([0xFF, 0x00, 1, 10, 0x00]) + b'{"status":"ok"}\x00\xff'
    mock_client.read_gatt_char = AsyncMock(return_value=packet)

    chunks = await protocol.read_response_chunks(mock_client)

    assert len(chunks) == 1
    assert chunks[0] == packet


@pytest.mark.asyncio
async def test_protocol_read_response_chunks_multiple():
    """Test reading multiple response chunks."""
    protocol = _BlancoUnitProtocol()
    mock_client = AsyncMock()

    # Mock multi-packet response
    packet1 = bytes([0xFF, 0x00, 2, 10, 0x00]) + b'{"status":'
    packet2 = bytes([10, 1]) + b'"ok"}\x00\xff'

    # Simulate reading chunks
    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return packet1
        return packet2

    mock_client.read_gatt_char = mock_read

    chunks = await protocol.read_response_chunks(mock_client)

    assert len(chunks) == 2
    assert chunks[0] == packet1
    assert chunks[1] == packet2


@pytest.mark.asyncio
async def test_protocol_read_response_chunks_timeout():
    """Test reading response chunks with timeout."""
    protocol = _BlancoUnitProtocol()
    mock_client = AsyncMock()

    # Mock incomplete response (expected 2 chunks, only get 1)
    packet1 = bytes([0xFF, 0x00, 2, 10, 0x00]) + b'{"status":'
    mock_client.read_gatt_char = AsyncMock(return_value=packet1)

    with pytest.raises(TimeoutError, match="Incomplete response"):
        await protocol.read_response_chunks(mock_client)


@pytest.mark.asyncio
async def test_protocol_read_response_chunks_error():
    """Test reading response chunks with read error."""
    protocol = _BlancoUnitProtocol()
    mock_client = AsyncMock()

    # Mock read error
    mock_client.read_gatt_char = AsyncMock(side_effect=Exception("Read error"))

    with pytest.raises(TimeoutError, match="Incomplete response"):
        await protocol.read_response_chunks(mock_client)


@pytest.mark.asyncio
async def test_protocol_send_pairing_request():
    """Test sending pairing request."""
    protocol = _BlancoUnitProtocol()
    mock_client = AsyncMock()

    # Mock response
    response_data = {
        "body": {"results": [{"pars": {"dev_id": "device123", "dev_type": 1}}]}
    }
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_client.write_gatt_char = AsyncMock()
    mock_client.read_gatt_char = AsyncMock(return_value=response_packet)

    result = await protocol.send_pairing_request(mock_client, "12345")

    assert result["body"]["results"][0]["pars"]["dev_id"] == "device123"
    mock_client.write_gatt_char.assert_called()


@pytest.mark.asyncio
async def test_protocol_send_request_with_ctrl():
    """Test sending request with ctrl parameter."""
    protocol = _BlancoUnitProtocol()
    mock_client = AsyncMock()

    # Mock response
    response_data = {"body": {"results": [{"pars": {"status": "ok"}}]}}
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_client.write_gatt_char = AsyncMock()
    mock_client.read_gatt_char = AsyncMock(return_value=response_packet)

    result = await protocol.send_request(
        mock_client, "12345", "device123", dev_type=1, evt_type=1, ctrl=2
    )

    assert result["body"]["results"][0]["pars"]["status"] == "ok"
    mock_client.write_gatt_char.assert_called()


@pytest.mark.asyncio
async def test_protocol_send_request_without_ctrl():
    """Test sending request without ctrl parameter."""
    protocol = _BlancoUnitProtocol()
    mock_client = AsyncMock()

    # Mock response
    response_data = {"body": {"results": [{"pars": {"status": "ok"}}]}}
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_client.write_gatt_char = AsyncMock()
    mock_client.read_gatt_char = AsyncMock(return_value=response_packet)

    result = await protocol.send_request(
        mock_client,
        "12345",
        "device123",
        1,
        evt_type=1,
        ctrl=None,
        pars={"test": "data"},
    )

    assert result["body"]["results"][0]["pars"]["status"] == "ok"
    mock_client.write_gatt_char.assert_called()


# -------------------------------
# Helper Function Tests
# -------------------------------


def test_extract_device_id_from_meta():
    """Test extracting device ID from meta field."""
    response = {"body": {"meta": {"dev_id": "device456"}}}
    assert _extract_device_id(response) == "device456"


def test_extract_device_id_missing_dev_id_in_meta():
    """Test extracting device ID when dev_id not in meta."""
    response = {"body": {"meta": {}}}
    assert _extract_device_id(response) is None


def test_extract_device_id_invalid_structure():
    """Test extracting device ID with invalid structure."""
    response = {"invalid": "structure"}
    assert _extract_device_id(response) is None


@pytest.mark.asyncio
async def test_validate_pin_success_with_dev_id():
    """Test validate_pin with successful PIN and device ID."""
    mock_client = AsyncMock()

    # Mock successful pairing response
    response_data = {
        "body": {
            "results": [{"pars": {}}],
            "meta": {"dev_id": "device123", "dev_type": 1},
        }
    }
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_client.write_gatt_char = AsyncMock()
    mock_client.read_gatt_char = AsyncMock(return_value=response_packet)

    validation = await validate_pin(mock_client, "12345")

    assert validation.is_valid is True
    assert validation.dev_id == "device123"
    assert validation.dev_type == 1


@pytest.mark.asyncio
async def test_validate_pin_wrong_pin_error_code():
    """Test validate_pin with wrong PIN (error code 4)."""
    mock_client = AsyncMock()

    # Mock auth error response
    response_data = {"body": {"results": [{"pars": {"errs": [{"err_code": 4}]}}]}}
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_client.write_gatt_char = AsyncMock()
    mock_client.read_gatt_char = AsyncMock(return_value=response_packet)

    validation = await validate_pin(mock_client, "99999")

    assert validation.is_valid is False


@pytest.mark.asyncio
async def test_validate_pin_no_device_id():
    """Test validate_pin when no device ID is returned."""
    mock_client = AsyncMock()

    # Mock response without device ID
    response_data = {"body": {"results": [{"pars": {}}]}}
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_client.write_gatt_char = AsyncMock()
    mock_client.read_gatt_char = AsyncMock(return_value=response_packet)

    validation = await validate_pin(mock_client, "12345")

    assert validation.is_valid is False


@pytest.mark.asyncio
async def test_validate_pin_invalid_format():
    """Test validate_pin with invalid PIN format."""
    mock_client = AsyncMock()

    with pytest.raises(ValueError, match="PIN must be exactly 5 digits"):
        await validate_pin(mock_client, "123")


@pytest.mark.asyncio
async def test_validate_pin_non_digit():
    """Test validate_pin with non-digit PIN."""
    mock_client = AsyncMock()

    with pytest.raises(ValueError, match="PIN must be exactly 5 digits"):
        await validate_pin(mock_client, "abcde")


@pytest.mark.asyncio
async def test_validate_pin_with_provided_protocol():
    """Test validate_pin with provided protocol instance."""
    mock_client = AsyncMock()
    protocol = _BlancoUnitProtocol()

    # Mock successful pairing response
    response_data = {
        "body": {
            "results": [{"pars": {}}],
            "meta": {"dev_id": "device789", "dev_type": 2},
        }
    }
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_client.write_gatt_char = AsyncMock()
    mock_client.read_gatt_char = AsyncMock(return_value=response_packet)

    validation = await validate_pin(mock_client, "12345", protocol=protocol)

    assert validation.is_valid is True
    assert validation.dev_id == "device789"
    assert validation.dev_type == 2


# -------------------------------
# BlancoUnitBluetoothClient Tests
# -------------------------------


def test_bluetooth_client_init_valid_pin():
    """Test BlancoUnitBluetoothClient initialization with valid PIN."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    assert client._pin == "12345"
    assert client._device == device
    assert client._connection_callback == callback
    assert client._session_data is None


def test_bluetooth_client_init_invalid_pin_length():
    """Test BlancoUnitBluetoothClient initialization with invalid PIN length."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    with pytest.raises(ValueError, match="PIN must be exactly 5 digits"):
        BlancoUnitBluetoothClient(
            pin="123", device=device, connection_callback=callback
        )


def test_bluetooth_client_init_invalid_pin_format():
    """Test BlancoUnitBluetoothClient initialization with non-digit PIN."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    with pytest.raises(ValueError, match="PIN must be exactly 5 digits"):
        BlancoUnitBluetoothClient(
            pin="abcde", device=device, connection_callback=callback
        )


def test_bluetooth_client_device_id_when_not_connected():
    """Test device_id property returns None when not connected."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    assert client.device_id is None


def test_bluetooth_client_device_id_when_connected():
    """Test device_id property returns device ID when connected."""
    from custom_components.blanco_unit.client import _BlancoUnitSessionData

    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock session data
    mock_client = AsyncMock()
    mock_protocol = MagicMock()
    client._session_data = _BlancoUnitSessionData(
        client=mock_client, dev_id="device123", dev_type=1, protocol=mock_protocol
    )

    assert client.device_id == "device123"


def test_bluetooth_client_is_connected_when_not_connected():
    """Test is_connected property returns False when not connected."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    assert client.is_connected is False


def test_bluetooth_client_is_connected_when_connected():
    """Test is_connected property returns True when connected."""
    from custom_components.blanco_unit.client import _BlancoUnitSessionData

    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock session data with connected client
    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_protocol = MagicMock()
    client._session_data = _BlancoUnitSessionData(
        client=mock_client, dev_id="device123", dev_type=1, protocol=mock_protocol
    )

    assert client.is_connected is True


@pytest.mark.asyncio
async def test_bluetooth_client_disconnect_when_connected():
    """Test disconnect method when client is connected."""
    from custom_components.blanco_unit.client import _BlancoUnitSessionData

    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock session data
    mock_client = AsyncMock()
    mock_protocol = MagicMock()
    client._session_data = _BlancoUnitSessionData(
        client=mock_client, dev_id="device123", dev_type=1, protocol=mock_protocol
    )

    await client.disconnect()

    mock_client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_bluetooth_client_disconnect_when_not_connected():
    """Test disconnect method when client is not connected."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Should not raise an error
    await client.disconnect()


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_connect_first_time(mock_establish):
    """Test _connect method on first connection."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock pairing response
    response_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = AsyncMock(return_value=response_packet)

    session_data = await client._connect()

    assert session_data.dev_id == "device123"
    assert client._session_data is not None
    assert client._session_data.dev_id == "device123"
    callback.assert_called_once_with(True)


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_connect_already_connected(mock_establish):
    """Test _connect method when already connected."""
    from custom_components.blanco_unit.client import _BlancoUnitSessionData

    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Pre-populate session data
    mock_ble_client = AsyncMock()
    mock_protocol = MagicMock()
    existing_session = _BlancoUnitSessionData(
        client=mock_ble_client, dev_id="device123", dev_type=1, protocol=mock_protocol
    )
    client._session_data = existing_session

    session_data = await client._connect()

    # Should return existing session without establishing new connection
    assert session_data == existing_session
    mock_establish.assert_not_called()


def test_bluetooth_client_handle_disconnect():
    """Test _handle_disconnect callback."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Set session data
    from custom_components.blanco_unit.client import _BlancoUnitSessionData

    mock_ble_client = AsyncMock()
    mock_protocol = MagicMock()
    client._session_data = _BlancoUnitSessionData(
        client=mock_ble_client, dev_id="device123", dev_type=1, protocol=mock_protocol
    )

    # Trigger disconnect
    client._handle_disconnect(mock_ble_client)

    assert client._session_data is None
    callback.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_bluetooth_client_perform_pairing_success():
    """Test _perform_pairing with successful authentication."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    mock_ble_client = AsyncMock()
    mock_protocol = _BlancoUnitProtocol()

    # Mock successful pairing response
    response_data = {
        "body": {
            "results": [{"pars": {}}],
            "meta": {"dev_id": "device456", "dev_type": 1},
        }
    }
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = AsyncMock(return_value=response_packet)

    result = await client._perform_pairing(mock_ble_client, mock_protocol)

    assert result.is_valid is True
    assert result.dev_id == "device456"
    assert result.dev_type == 1


@pytest.mark.asyncio
async def test_bluetooth_client_perform_pairing_wrong_pin():
    """Test _perform_pairing with wrong PIN (error code 4)."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="99999", device=device, connection_callback=callback
    )

    mock_ble_client = AsyncMock()
    mock_protocol = _BlancoUnitProtocol()

    # Mock auth error response
    response_data = {"body": {"results": [{"pars": {"errs": [{"err_code": 4}]}}]}}
    json_str = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + json_str.encode("utf-8") + b"\x00\xff"
    )

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = AsyncMock(return_value=response_packet)

    with pytest.raises(BlancoUnitAuthenticationError, match="Wrong PIN"):
        await client._perform_pairing(mock_ble_client, mock_protocol)


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.validate_pin")
async def test_bluetooth_client_perform_pairing_no_device_id(mock_validate_pin):
    """Test _perform_pairing when no device ID is returned."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    mock_ble_client = AsyncMock()
    mock_protocol = _BlancoUnitProtocol()

    # Mock validate_pin to return True but with a response that has no device ID
    mock_validate_pin.return_value = PinValidationResult(True, None, 1)

    with pytest.raises(
        BlancoUnitConnectionError, match="No device ID in pairing response"
    ):
        await client._perform_pairing(mock_ble_client, mock_protocol)


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_execute_transaction_success(mock_establish):
    """Test _execute_transaction with successful response."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock pairing response
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    # Mock transaction response
    transaction_data = {"body": {"results": [{"pars": {"status": "ok"}}]}, "type": 2}
    transaction_json = json.dumps(transaction_data)
    transaction_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00])
        + transaction_json.encode("utf-8")
        + b"\x00\xff"
    )

    # Simulate two reads: first for pairing, second for transaction
    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return transaction_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    response = await client._execute_transaction(
        evt_type=7, ctrl=3, pars={"test": "data"}
    )

    assert response["type"] == 2


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_execute_transaction_auth_error(mock_establish):
    """Test _execute_transaction with authentication error."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock pairing response
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    # Mock transaction response with auth error
    transaction_data = {"body": {"results": [{"pars": {"errs": [{"err_code": 4}]}}]}}
    transaction_json = json.dumps(transaction_data)
    transaction_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00])
        + transaction_json.encode("utf-8")
        + b"\x00\xff"
    )

    # Simulate two reads
    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return transaction_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    with pytest.raises(
        BlancoUnitAuthenticationError, match="Authentication error during operation"
    ):
        await client._execute_transaction(evt_type=7, ctrl=3)


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_get_system_info(mock_establish):
    """Test get_system_info method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    system_data = {
        "body": {
            "results": [
                {
                    "pars": {
                        "sw_ver_comm_con": {"val": "1.0.0"},
                        "sw_ver_elec_con": {"val": "2.0.0"},
                        "sw_ver_main_con": {"val": "3.0.0"},
                        "dev_name": {"val": "Test Device"},
                        "reset_cnt": {"val": 5},
                    }
                }
            ]
        }
    }
    system_json = json.dumps(system_data)
    system_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + system_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return system_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    info = await client.get_system_info()

    assert info.sw_ver_comm_con == "1.0.0"
    assert info.sw_ver_elec_con == "2.0.0"
    assert info.sw_ver_main_con == "3.0.0"
    assert info.dev_name == "Test Device"
    assert info.reset_cnt == 5


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_get_settings(mock_establish):
    """Test get_settings method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    settings_data = {
        "body": {
            "results": [
                {
                    "pars": {
                        "calib_still_wtr": {"val": 5},
                        "calib_soda_wtr": {"val": 6},
                        "filter_life_tm": {"val": 365},
                        "post_flush_quantity": {"val": 100},
                        "set_point_cooling": {"val": 7},
                        "wtr_hardness": {"val": 4},
                    }
                }
            ]
        }
    }
    settings_json = json.dumps(settings_data)
    settings_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + settings_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return settings_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    settings = await client.get_settings()

    assert settings.calib_still_wtr == 5
    assert settings.calib_soda_wtr == 6
    assert settings.filter_life_tm == 365
    assert settings.post_flush_quantity == 100
    assert settings.set_point_cooling == 7
    assert settings.wtr_hardness == 4


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_get_status(mock_establish):
    """Test get_status method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    status_data = {
        "body": {
            "results": [
                {
                    "pars": {
                        "tap_state": {"val": 2},
                        "filter_rest": {"val": 80},
                        "co2_rest": {"val": 90},
                        "wtr_disp_active": {"val": True},
                        "firm_upd_avlb": {"val": False},
                        "set_point_cooling": {"val": 7},
                        "clean_mode_state": {"val": 1},
                        "err_bits": {"val": 0},
                    }
                }
            ]
        }
    }
    status_json = json.dumps(status_data)
    status_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + status_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return status_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    status = await client.get_status()

    assert status.tap_state == 2
    assert status.filter_rest == 80
    assert status.co2_rest == 90
    assert status.wtr_disp_active is True
    assert status.firm_upd_avlb is False


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_get_device_identity(mock_establish):
    """Test get_device_identity method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    identity_data = {
        "body": {"results": [{"pars": {"ser_no": "123456", "serv_code": "ABCDEF"}}]}
    }
    identity_json = json.dumps(identity_data)
    identity_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + identity_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return identity_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    identity = await client.get_device_identity()

    assert identity.serial_no == "123456"
    assert identity.service_code == "ABCDEF"


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_get_wifi_info(mock_establish):
    """Test get_wifi_info method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    wifi_data = {
        "body": {
            "results": [
                {
                    "pars": {
                        "cloud_connect": {"val": True},
                        "ssid": {"val": "MyWiFi"},
                        "signal": {"val": -50},
                        "ip": {"val": "192.168.1.100"},
                        "b_mac": {"val": "AA:BB:CC:DD:EE:FF"},
                        "w_mac": {"val": "11:22:33:44:55:66"},
                        "default_gateway": {"val": "192.168.1.1"},
                        "default_gateway_mac": {"val": "AA:BB:CC:DD:EE:00"},
                        "subnet": {"val": "255.255.255.0"},
                    }
                }
            ]
        }
    }
    wifi_json = json.dumps(wifi_data)
    wifi_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + wifi_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return wifi_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    wifi_info = await client.get_wifi_info()

    assert wifi_info.cloud_connect is True
    assert wifi_info.ssid == "MyWiFi"
    assert wifi_info.signal == -50
    assert wifi_info.ip == "192.168.1.100"


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_set_temperature_success(mock_establish):
    """Test set_temperature method with valid temperature."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.set_temperature(cooling_celsius=7)

    assert result is True


@pytest.mark.asyncio
async def test_bluetooth_client_set_temperature_invalid_low():
    """Test set_temperature with temperature too low."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    with pytest.raises(ValueError, match="Temperature must be between 4 and 10"):
        await client.set_temperature(cooling_celsius=3)


@pytest.mark.asyncio
async def test_bluetooth_client_set_temperature_invalid_high():
    """Test set_temperature with temperature too high."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    with pytest.raises(ValueError, match="Temperature must be between 4 and 10"):
        await client.set_temperature(cooling_celsius=11)


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_set_water_hardness_success(mock_establish):
    """Test set_water_hardness method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.set_water_hardness(level=5)

    assert result is True


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_change_pin_success(mock_establish):
    """Test change_pin method with successful PIN change."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.change_pin(new_pin="54321")

    assert result is True
    assert client._pin == "54321"


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_change_pin_failure(mock_establish):
    """Test change_pin method when PIN change fails."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 1}  # Not type 2 = failure
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.change_pin(new_pin="54321")

    assert result is False
    assert client._pin == "12345"  # PIN should not change


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_dispense_water_success(mock_establish):
    """Test dispense_water method with valid parameters."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.dispense_water(amount_ml=500, co2_intensity=2)

    assert result is True


@pytest.mark.asyncio
async def test_bluetooth_client_dispense_water_invalid_amount_low():
    """Test dispense_water with amount too low."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    with pytest.raises(ValueError, match="Amount must be between 100ml and 1500ml"):
        await client.dispense_water(amount_ml=50, co2_intensity=1)


@pytest.mark.asyncio
async def test_bluetooth_client_dispense_water_invalid_amount_high():
    """Test dispense_water with amount too high."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    with pytest.raises(ValueError, match="Amount must be between 100ml and 1500ml"):
        await client.dispense_water(amount_ml=2000, co2_intensity=1)


@pytest.mark.asyncio
async def test_bluetooth_client_dispense_water_invalid_amount_not_multiple():
    """Test dispense_water with amount not a multiple of 100."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    with pytest.raises(ValueError, match="Amount must be a multiple of 100ml"):
        await client.dispense_water(amount_ml=150, co2_intensity=1)


@pytest.mark.asyncio
async def test_bluetooth_client_dispense_water_invalid_intensity():
    """Test dispense_water with invalid CO2 intensity."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    with pytest.raises(ValueError, match="CO2 intensity must be"):
        await client.dispense_water(amount_ml=500, co2_intensity=5)


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_set_calibration_still(mock_establish):
    """Test set_calibration_still method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.set_calibration_still(amount=5)

    assert result is True


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_set_calibration_soda(mock_establish):
    """Test set_calibration_soda method."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.set_calibration_soda(amount=7)

    assert result is True


def test_extract_device_id_exception_handling():
    """Test _extract_device_id with TypeError/KeyError exception."""
    # Test with response where meta is an object that doesn't support 'in' operator
    # Numbers, None, etc. will raise TypeError when using 'in' operator
    response = {
        "body": {
            "meta": 123  # This will cause TypeError on line 718: if "dev_id" in meta
        }
    }
    assert _extract_device_id(response) is None

    # Test with response where accessing meta["dev_id"] raises KeyError
    # Even though "dev_id" is in meta, accessing it could raise KeyError if meta is a custom class
    class BrokenDict:
        def __contains__(self, key):
            return True  # Pretend the key exists

        def __getitem__(self, key):
            raise KeyError("Broken!")  # But raise KeyError when accessing

    response2 = {"body": {"meta": BrokenDict()}}
    assert _extract_device_id(response2) is None


# -------------------------------
# WiFi & Device Management Pars Tests
# -------------------------------


def test_connect_wifi_pars_to_pars():
    """Test _ConnectWifiPars.to_pars() with valid SSID and password."""
    pars = _ConnectWifiPars(ssid="TestSSID", password="pass123")
    result = pars.to_pars()
    assert result == {"ssid": {"val": "TestSSID"}, "password": {"val": "pass123"}}


def test_connect_wifi_pars_to_pars_empty():
    """Test _ConnectWifiPars.to_pars() with empty strings."""
    pars = _ConnectWifiPars(ssid="", password="")
    result = pars.to_pars()
    assert result == {"ssid": {"val": ""}, "password": {"val": ""}}


def test_allow_cloud_services_pars_to_pars_default():
    """Test _AllowCloudServicesPars.to_pars() with default rca_id."""
    pars = _AllowCloudServicesPars()
    result = pars.to_pars()
    assert result == {"rca_id": ""}


def test_allow_cloud_services_pars_to_pars_with_id():
    """Test _AllowCloudServicesPars.to_pars() with specific rca_id."""
    pars = _AllowCloudServicesPars(rca_id="some_id")
    result = pars.to_pars()
    assert result == {"rca_id": "some_id"}


# -------------------------------
# WiFi & Device Management Client Tests
# -------------------------------


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_scan_wifi_networks(mock_establish):
    """Test scan_wifi_networks method returns list of networks."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    scan_data = {
        "body": {
            "pars": {
                "aps": [
                    {"ssid": "TestWiFi", "signal": 66, "auth_mode": 3},
                    {"ssid": "OtherWiFi", "signal": 40, "auth_mode": 3},
                ]
            }
        }
    }
    scan_json = json.dumps(scan_data)
    scan_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + scan_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return scan_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.scan_wifi_networks()

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].ssid == "TestWiFi"
    assert result[0].signal == 66
    assert result[0].auth_mode == 3


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_scan_wifi_networks_empty(mock_establish):
    """Test scan_wifi_networks method with empty access point list."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    scan_data = {"body": {"pars": {"aps": []}}}
    scan_json = json.dumps(scan_data)
    scan_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + scan_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return scan_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.scan_wifi_networks()

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_connect_wifi_success(mock_establish):
    """Test connect_wifi method with successful connection."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.connect_wifi("TestSSID", "password123")

    assert result is True


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_disconnect_wifi_success(mock_establish):
    """Test disconnect_wifi method with successful disconnection."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.disconnect_wifi()

    assert result is True


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_allow_cloud_services_success(mock_establish):
    """Test allow_cloud_services method with default rca_id."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.allow_cloud_services()

    assert result is True


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_allow_cloud_services_with_rca_id(mock_establish):
    """Test allow_cloud_services method with specific rca_id."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.allow_cloud_services(rca_id="test_id")

    assert result is True


@pytest.mark.asyncio
@patch("custom_components.blanco_unit.client.establish_connection")
async def test_bluetooth_client_factory_reset_success(mock_establish):
    """Test factory_reset method with successful reset."""
    device = BLEDevice(address="AA:BB:CC:DD:EE:FF", name="Test Device", details={})
    callback = MagicMock()

    client = BlancoUnitBluetoothClient(
        pin="12345", device=device, connection_callback=callback
    )

    # Mock establish_connection
    mock_ble_client = AsyncMock()
    mock_ble_client.is_connected = True
    mock_establish.return_value = mock_ble_client

    # Mock responses
    pairing_data = {"body": {"meta": {"dev_id": "device123", "dev_type": 1}}}
    pairing_json = json.dumps(pairing_data)
    pairing_packet = (
        bytes([0xFF, 0x00, 1, 10, 0x00]) + pairing_json.encode("utf-8") + b"\x00\xff"
    )

    response_data = {"type": 2}
    response_json = json.dumps(response_data)
    response_packet = (
        bytes([0xFF, 0x00, 1, 11, 0x00]) + response_json.encode("utf-8") + b"\x00\xff"
    )

    read_count = 0

    async def mock_read(*args, **kwargs):
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return pairing_packet
        return response_packet

    mock_ble_client.write_gatt_char = AsyncMock()
    mock_ble_client.read_gatt_char = mock_read

    result = await client.factory_reset()

    assert result is True
