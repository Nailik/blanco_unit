"""Holds the data that is stored in memory by the Vogels Motion Mount Integration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass
class BlancoUnitData:
    """Holds the data of the device."""

    connected: bool
    device_id: str
