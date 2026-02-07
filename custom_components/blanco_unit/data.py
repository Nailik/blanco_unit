"""Holds the data that is stored in memory by the Blanco Unit Integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BlancoUnitSystemInfo:
    """System information from Blanco Unit."""

    sw_ver_comm_con: str
    sw_ver_elec_con: str
    sw_ver_main_con: str
    dev_name: str
    reset_cnt: int


@dataclass
class BlancoUnitSettings:
    """Configuration settings from Blanco Unit."""

    calib_still_wtr: int
    calib_soda_wtr: int
    filter_life_tm: int
    post_flush_quantity: int
    set_point_cooling: int
    wtr_hardness: int
    # CHOICE.All specific fields (defaults for drink.soda compatibility)
    set_point_heating: int = 0
    calib_hot_wtr: int = 0
    gbl_medium_wtr_ratio: float = 0.0
    gbl_classic_wtr_ratio: float = 0.0


@dataclass
class BlancoUnitStatus:
    """Real-time status from Blanco Unit."""

    tap_state: int
    filter_rest: int
    co2_rest: int
    wtr_disp_active: bool
    firm_upd_avlb: bool
    set_point_cooling: int
    clean_mode_state: int
    err_bits: int
    # CHOICE.All specific fields (defaults for drink.soda compatibility)
    temp_boil_1: int = 0
    temp_boil_2: int = 0
    temp_comp: int = 0
    main_controller_status: int = 0
    conn_controller_status: int = 0


@dataclass
class BlancoUnitIdentity:
    """Device identity information."""

    serial_no: str
    service_code: str


@dataclass
class BlancoUnitWifiInfo:
    """WiFi and network information."""

    cloud_connect: bool
    ssid: str
    signal: int
    ip: str
    ble_mac: str
    wifi_mac: str
    gateway: str
    gateway_mac: str
    subnet: str


@dataclass
class BlancoUnitWifiNetwork:
    """A discovered WiFi access point."""

    ssid: str
    signal: int
    auth_mode: int


@dataclass
class BlancoUnitData:
    """Holds the data of the device."""

    connected: bool
    available: bool
    device_id: str
    device_type: int | None = None
    system_info: BlancoUnitSystemInfo | None = None
    settings: BlancoUnitSettings | None = None
    status: BlancoUnitStatus | None = None
    identity: BlancoUnitIdentity | None = None
    wifi_info: BlancoUnitWifiInfo | None = None
