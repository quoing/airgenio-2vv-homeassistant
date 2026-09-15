"""Tests for integration setup, entity states and write paths."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.airgenio_2vv.const import CONF_MODEL, MODEL_DAPHNE


def entity_id_for(hass: HomeAssistant, unique_suffix: str) -> str:
    """Resolve an entity_id from our unique-id scheme."""
    registry = er.async_get(hass)
    unique_id = f"192.168.1.100:502:1_{unique_suffix}"
    for entry in registry.entities.values():
        if entry.unique_id == unique_id:
            return entry.entity_id
    raise AssertionError(f"No entity with unique_id {unique_id}")


async def test_setup_and_sensor_states(hass: HomeAssistant, init_integration) -> None:
    """Live-sample registers decode into the expected entity states."""
    assert init_integration.state is ConfigEntryState.LOADED

    assert hass.states.get(entity_id_for(hass, "outside_temperature")).state == "25.3"
    assert hass.states.get(entity_id_for(hass, "extract_temperature")).state == "25.7"
    assert hass.states.get(entity_id_for(hass, "fan_power")).state == "20"
    assert hass.states.get(entity_id_for(hass, "filter_clogging")).state == "19"
    # Room sensor not connected -> sentinel -> unavailable
    assert (
        hass.states.get(entity_id_for(hass, "room_temperature")).state == "unavailable"
    )
    # ON bit + summer bit; door bit (9) not set in the fixture
    assert hass.states.get(entity_id_for(hass, "global_error")).state == "off"
    assert hass.states.get(entity_id_for(hass, "summer_mode")).state == "on"
    assert hass.states.get(entity_id_for(hass, "door_open")).state == "off"
    # Fan: on at 20 %
    fan_state = hass.states.get(entity_id_for(hass, "fan"))
    assert fan_state.state == "on"
    assert fan_state.attributes["percentage"] == 20
    assert fan_state.attributes["actual_power"] == 20
    # Setpoint number
    assert hass.states.get(entity_id_for(hass, "temperature_setpoint")).state == "22"
    # Select decoded from 25009 = 4
    assert (
        hass.states.get(entity_id_for(hass, "temperature_sensor_source")).state
        == "room_bms"
    )


async def test_fan_writes(hass: HomeAssistant, init_integration, mock_client) -> None:
    """Fan services write the expected registers."""
    fan_entity = entity_id_for(hass, "fan")

    await hass.services.async_call(
        "fan",
        "set_percentage",
        {"entity_id": fan_entity, "percentage": 60},
        blocking=True,
    )
    assert (21002, 600) in mock_client.writes

    await hass.services.async_call(
        "fan", "turn_off", {"entity_id": fan_entity}, blocking=True
    )
    assert (21001, 0) in mock_client.writes

    await hass.services.async_call(
        "fan", "turn_on", {"entity_id": fan_entity}, blocking=True
    )
    assert (21001, 1) in mock_client.writes


async def test_percentage_turns_off_unit_on(
    hass: HomeAssistant, init_integration, mock_client
) -> None:
    """Setting nonzero percentage also starts a stopped unit."""
    mock_client.holding_regs[21001] = 0
    await init_integration.runtime_data.async_refresh()

    await hass.services.async_call(
        "fan",
        "set_percentage",
        {"entity_id": entity_id_for(hass, "fan"), "percentage": 40},
        blocking=True,
    )

    assert mock_client.writes[-2:] == [(21002, 400), (21001, 1)]


async def test_switch_and_button_writes(
    hass: HomeAssistant, init_integration, mock_client
) -> None:
    """Switch and button entities write their registers."""
    day_night = entity_id_for(hass, "day_night_mode")
    await hass.services.async_call(
        "switch", "turn_on", {"entity_id": day_night}, blocking=True
    )
    assert (21009, 1) in mock_client.writes

    button = entity_id_for(hass, "filter_reset")
    await hass.services.async_call(
        "button", "press", {"entity_id": button}, blocking=True
    )
    assert (21016, 1) in mock_client.writes


async def test_number_write(hass: HomeAssistant, init_integration, mock_client) -> None:
    """Setting the setpoint writes plain °C."""
    setpoint = entity_id_for(hass, "temperature_setpoint")
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": setpoint, "value": 24},
        blocking=True,
    )
    assert (21003, 24) in mock_client.writes


async def test_write_failure_raises(
    hass: HomeAssistant, init_integration, mock_client
) -> None:
    """A failed write surfaces as HomeAssistantError."""
    mock_client.fail_writes = True
    fan_entity = entity_id_for(hass, "fan")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "fan", "turn_off", {"entity_id": fan_entity}, blocking=True
        )


async def test_coordinator_failure_makes_entities_unavailable(
    hass: HomeAssistant, init_integration, mock_client
) -> None:
    """A poll failure flips entities to unavailable; recovery restores them."""
    mock_client.fail_reads = True
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()
    assert (
        hass.states.get(entity_id_for(hass, "outside_temperature")).state
        == "unavailable"
    )

    mock_client.fail_reads = False
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=122))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id_for(hass, "outside_temperature")).state == "25.3"


async def test_regular_refresh_only_reads_runtime_blocks(
    init_integration, mock_client
) -> None:
    """Slow configuration registers are omitted from normal polling."""
    mock_client.input_reads.clear()
    mock_client.holding_reads.clear()

    await init_integration.runtime_data.async_refresh()

    assert mock_client.input_reads == [(18000, 17)]
    assert mock_client.holding_reads == [(21001, 9)]


async def test_unload(hass: HomeAssistant, init_integration, mock_client) -> None:
    """Unloading releases entities and shared connection ownership."""
    assert await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()
    assert init_integration.state is ConfigEntryState.NOT_LOADED


async def test_daphne_uses_boost_name(
    hass: HomeAssistant, mock_config_entry, mock_client
) -> None:
    """Daphne profile presents shared register as Boost."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data={**mock_config_entry.data, CONF_MODEL: MODEL_DAPHNE},
    )
    with patch(
        "custom_components.airgenio_2vv.AirgenioModbusClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(entity_id_for(hass, "day_night_mode"))
    assert state.attributes["friendly_name"].endswith("Boost")


async def test_unsupported_config_register(
    hass: HomeAssistant, mock_config_entry, mock_client
) -> None:
    """A register rejected by the unit only disables its own entity.

    Observed on a real VENUS AirGENIO Comfort: reading 25077 returns
    Modbus exception 2 (IllegalDataAddress) even though the official 2VV
    BMS example writes it.
    """
    mock_client.unsupported.add(25077)
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.airgenio_2vv.AirgenioModbusClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    # The affected switch is unavailable...
    assert (
        hass.states.get(entity_id_for(hass, "automatic_fan_control")).state
        == "unavailable"
    )
    # ...while everything else works.
    assert hass.states.get(entity_id_for(hass, "outside_temperature")).state == "25.3"
    assert (
        hass.states.get(entity_id_for(hass, "automatic_temperature_control")).state
        == "on"
    )
