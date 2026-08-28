"""Constants for the 2VV AirGENIO integration.

All register addresses are DOC addresses exactly as printed in the official
2VV "AirGENIO Modbus RTU/TCP guide". The Modbus client subtracts 1 to get
the on-wire address (PLC BASE1 -> 0-based), in exactly one place.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "airgenio_2vv"

MANUFACTURER: Final = "2VV"
MODEL: Final = "VENUS AirGENIO"

CONF_UNIT_ID: Final = "unit_id"

DEFAULT_PORT: Final = 502
DEFAULT_UNIT_ID: Final = 1
DEFAULT_SCAN_INTERVAL: Final = 30
MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 300

# --- INPUT registers (FC04) — status block -------------------------------
REG_STATUS_GLOBAL: Final = 18000  # bitfield, see STATUS_BIT_*
REG_STATUS_ERRORS: Final = 18001  # bitfield, see ERROR_BIT_*
REG_STATUS_SENSORS: Final = 18003  # bitfield, 0 = all sensors OK
REG_STATUS_INPUTS: Final = 18004  # bitfield (DI + tacho)
REG_STATUS_OUTPUTS: Final = 18005  # bitfield (DO, damper, exchanger)
REG_FAN_ACTUAL: Final = 18006  # ‰ of fan power
REG_TEMP_OUTSIDE: Final = 18007  # TempEXT1, °C x10, int16
REG_TEMP_SUPPLY: Final = 18008  # TempEXT3 (outlet air), °C x10, int16
REG_TEMP_EXTRACT: Final = 18009  # TempINT1 (inlet air), °C x10, int16
REG_TEMP_WATER_RETURN: Final = 18010  # TempWOut, °C x10, int16
REG_TEMP_ROOM: Final = 18011  # TempRoom, °C x10, int16 (sentinel if absent)
REG_SENSOR_FLOW_ALARM: Final = 18012
REG_PREHEATER_POWER: Final = 18013  # %
REG_BMS_OUTSIDE_READBACK: Final = 18014  # °C x10, int16
REG_BMS_ROOM_READBACK: Final = 18015  # °C x10, int16
REG_FILTER_PERCENT: Final = 18016  # %

STATUS_BLOCK_START: Final = REG_STATUS_GLOBAL
STATUS_BLOCK_COUNT: Final = REG_FILTER_PERCENT - REG_STATUS_GLOBAL + 1  # 17

# --- INPUT registers (FC04) — INFO block (diagnostics only) --------------
REG_INFO_FW_MODULE_A: Final = 16029
REG_INFO_FW_MODULE_B: Final = 16030
INFO_BLOCK_START: Final = 16008
INFO_BLOCK_COUNT: Final = 22  # 16008..16029 (IP/mask/gw/DHCP/port/MAC/HW/FW)

# Unit global status bits (18000)
STATUS_BIT_ON: Final = 0
STATUS_BIT_AUTO_HEAT: Final = 1
STATUS_BIT_AUTO_FLOW: Final = 2
STATUS_BIT_NIGHT_REDUCTION: Final = 3
STATUS_BIT_TIMESWITCH: Final = 4
STATUS_BIT_COOLDOWN: Final = 5
STATUS_BIT_SUMMER: Final = 8
# Bit 9 = unit service door open (not a bypass flap). Verified against a
# parallel YAML Modbus hub reading the same bit as mask 512 on wire 17999.
STATUS_BIT_DOOR_OPEN: Final = 9

# Software error bits (18001)
ERROR_BIT_FAN: Final = 0
ERROR_BIT_FAN1: Final = 1
ERROR_BIT_FILTER_ERROR: Final = 2
ERROR_BIT_FILTER_WARNING: Final = 3
ERROR_BIT_HEATER: Final = 4
ERROR_BIT_GLOBAL: Final = 7

# --- HOLDING registers (FC03/06) — SHARE block ----------------------------
REG_SWITCH_ON: Final = 21001  # 0=OFF, 1=ON
REG_AIRFLOW_MANUAL: Final = 21002  # ‰ of fan power
REG_TEMP_SETPOINT: Final = 21003  # °C (plain, NOT x10)
REG_DAY_NIGHT: Final = 21009  # BoostMode / DAY-NIGHT (0=DAY, 1=NIGHT)
REG_FILTER_RESET: Final = 21016  # write 1 = reset filter timer

SHARE_BLOCK_START: Final = REG_SWITCH_ON
SHARE_BLOCK_COUNT: Final = REG_DAY_NIGHT - REG_SWITCH_ON + 1  # 9

# --- HOLDING registers — SERVICE / SERVICE HARD ---------------------------
REG_BMS_OUTSIDE_ENABLE: Final = 20044  # 0/1
REG_VENTILATION_MODE: Final = 25000  # enum not confirmed -> read-only
REG_TEMP_SENSOR_SELECTION: Final = 25009  # 0-4, see TEMP_SENSOR_OPTIONS
REG_AUTO_TEMP_CONTROL: Final = 25033  # 0 manual / 1 automatic
REG_AUTO_FAN_CONTROL: Final = 25077  # 0/1

CONFIG_REGISTERS: Final = (
    REG_BMS_OUTSIDE_ENABLE,
    REG_VENTILATION_MODE,
    REG_TEMP_SENSOR_SELECTION,
    REG_AUTO_TEMP_CONTROL,
    REG_AUTO_FAN_CONTROL,
)

# --- HOLDING registers — BMS TEMP SENSORS ---------------------------------
REG_BMS_ROOM_WRITE: Final = 23000  # °C x10
REG_BMS_OUTSIDE_WRITE: Final = 23002  # °C x10

# Temperature sensor source (25009)
TEMP_SENSOR_OPTIONS: Final = {
    0: "supply_duct",
    1: "extract_duct",
    2: "room",
    3: "thermostat",
    4: "room_bms",
}

TEMP_SCALE: Final = 0.1
# Values below the documented sensor minimum (-40 °C) are treated as
# "sensor not connected" (observed sentinel 65097 ~ -43.9 °C).
TEMP_SENTINEL_MIN: Final = -40.0

SETPOINT_MIN: Final = 15
SETPOINT_MAX: Final = 45
