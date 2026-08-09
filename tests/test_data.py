"""Unit tests for register decoding."""

from __future__ import annotations

from custom_components.airgenio_2vv.data import (
    AirgenioData,
    decode_int16,
    decode_temperature,
)


def make_data(**overrides) -> AirgenioData:
    defaults = dict(  # noqa: C408 - keyword style mirrors the dataclass
        status_bits=1,
        error_bits=0,
        sensor_status_bits=0,
        output_bits=0,
        fan_actual_permille=200,
        temp_outside=16.7,
        temp_supply=24.5,
        temp_extract=25.7,
        temp_water_return=None,
        temp_room=None,
        preheater_power=0,
        bms_outside_readback=17.0,
        bms_room_readback=32.5,
        filter_percent=19,
        switch_on=True,
        airflow_target_permille=200,
        temp_setpoint=22,
        day_night=False,
        bms_outside_enable=True,
        ventilation_mode_raw=0,
        temp_sensor_selection=4,
        auto_temp_control=True,
        auto_fan_control=True,
    )
    defaults.update(overrides)
    return AirgenioData(**defaults)


def test_decode_int16_positive() -> None:
    assert decode_int16(253) == 253


def test_decode_int16_negative() -> None:
    assert decode_int16(65486) == -50  # -5.0 °C x10


def test_decode_temperature_scaling() -> None:
    assert decode_temperature(253) == 25.3


def test_decode_temperature_negative() -> None:
    assert decode_temperature(65486) == -5.0


def test_decode_temperature_sentinel_unconnected_sensor() -> None:
    # Observed on the live unit with TempRoom not connected.
    assert decode_temperature(65097) is None


def test_status_and_error_bits() -> None:
    data = make_data(status_bits=0b100000001, error_bits=0b10000000)
    assert data.status_bit(0) is True
    assert data.status_bit(8) is True
    assert data.status_bit(3) is False
    assert data.error_bit(7) is True


def test_heat_recovery_efficiency() -> None:
    data = make_data(temp_outside=16.7, temp_supply=24.5, temp_extract=25.7)
    # (24.5 - 16.7) / (25.7 - 16.7) * 100 = 86.7 -> 87
    assert data.heat_recovery_efficiency == 87


def test_heat_recovery_efficiency_small_delta_is_none() -> None:
    data = make_data(temp_outside=25.0, temp_supply=25.2, temp_extract=25.5)
    assert data.heat_recovery_efficiency is None


def test_heat_recovery_efficiency_missing_sensor_is_none() -> None:
    data = make_data(temp_outside=None)
    assert data.heat_recovery_efficiency is None


def test_heat_recovery_efficiency_clamped() -> None:
    data = make_data(temp_outside=10.0, temp_supply=30.0, temp_extract=20.0)
    assert data.heat_recovery_efficiency == 100


def test_sensor_fault_ignores_bms_and_absent_sensors() -> None:
    # BMS status bits (5, 6) flap during feed pauses - never a fault.
    data = make_data(sensor_status_bits=0b01100000)
    assert data.sensor_fault is False
    # Absent optional sensors (room, water return read as sentinel) ignored.
    data = make_data(sensor_status_bits=0b00011000, temp_room=None)
    assert data.sensor_fault is False
    # Core air-stream sensor error always counts.
    data = make_data(sensor_status_bits=0b00000001)
    assert data.sensor_fault is True
    # Optional sensor error counts while the sensor delivers values.
    data = make_data(sensor_status_bits=0b00010000, temp_room=22.0)
    assert data.sensor_fault is True
