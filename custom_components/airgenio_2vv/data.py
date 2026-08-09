"""Decoded data snapshot for the 2VV AirGENIO integration."""

from __future__ import annotations

from dataclasses import dataclass

from .const import TEMP_SCALE, TEMP_SENTINEL_MIN

_INT16_SIGN_BIT = 0x8000
_UINT16_RANGE = 0x10000


def decode_int16(raw: int) -> int:
    """Decode a raw 16-bit register as a signed integer (two's complement)."""
    return raw - _UINT16_RANGE if raw >= _INT16_SIGN_BIT else raw


def decode_temperature(raw: int) -> float | None:
    """Decode a x10 temperature register; None when out of sensor range."""
    value = decode_int16(raw) * TEMP_SCALE
    if value < TEMP_SENTINEL_MIN:
        return None
    return round(value, 1)


@dataclass(frozen=True, slots=True)
class AirgenioData:
    """One decoded polling snapshot of the unit."""

    # Status block (input registers)
    status_bits: int
    error_bits: int
    sensor_status_bits: int
    output_bits: int
    fan_actual_permille: int
    temp_outside: float | None
    temp_supply: float | None
    temp_extract: float | None
    temp_water_return: float | None
    temp_room: float | None
    preheater_power: int
    bms_outside_readback: float | None
    bms_room_readback: float | None
    filter_percent: int

    # Share block (holding registers)
    switch_on: bool
    airflow_target_permille: int
    temp_setpoint: int
    day_night: bool

    # Config registers (holding)
    bms_outside_enable: bool
    ventilation_mode_raw: int
    temp_sensor_selection: int
    auto_temp_control: bool
    auto_fan_control: bool

    def status_bit(self, bit: int) -> bool:
        """Return a bit of the unit global status register."""
        return bool(self.status_bits & (1 << bit))

    def error_bit(self, bit: int) -> bool:
        """Return a bit of the software error register."""
        return bool(self.error_bits & (1 << bit))

    @property
    def heat_recovery_efficiency(self) -> float | None:
        """Compute heat recovery efficiency in % from the three air temps.

        efficiency = (supply - outside) / (extract - outside) * 100

        Unavailable when a temperature is missing or the extract/outside
        delta is below 1 K (division noise).
        """
        if self.temp_outside is None or self.temp_supply is None:
            return None
        if self.temp_extract is None:
            return None
        delta = self.temp_extract - self.temp_outside
        if abs(delta) < 1.0:
            return None
        efficiency = (self.temp_supply - self.temp_outside) / delta * 100
        return round(min(max(efficiency, 0.0), 100.0))
