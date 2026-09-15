"""Tests for the config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.airgenio_2vv import async_migrate_entry
from custom_components.airgenio_2vv.const import (
    CONF_MODEL,
    CONF_UNIT_ID,
    DOMAIN,
    MODEL_DAPHNE,
    MODEL_VENUS,
)
from custom_components.airgenio_2vv.modbus_client import AirgenioConnectionError

USER_INPUT = {
    CONF_HOST: "192.168.1.100",
    CONF_PORT: 502,
    CONF_UNIT_ID: 1,
    CONF_MODEL: MODEL_DAPHNE,
}


async def test_user_flow_happy_path(hass: HomeAssistant, mock_client) -> None:
    """A successful connection creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    with (
        patch(
            "custom_components.airgenio_2vv.config_flow.AirgenioModbusClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.airgenio_2vv.AirgenioModbusClient",
            return_value=mock_client,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "AirGENIO 192.168.1.100"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == "192.168.1.100:502:1"


async def test_user_flow_cannot_connect(hass: HomeAssistant, mock_client) -> None:
    """A connection failure shows an error and allows retrying."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.airgenio_2vv.config_flow.AirgenioModbusClient",
        return_value=mock_client,
    ):
        mock_client.fail_reads = True

        async def raise_connection(*args, **kwargs):
            raise AirgenioConnectionError("nope")

        mock_client.read_input = raise_connection
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_duplicate_aborts(hass: HomeAssistant, mock_client) -> None:
    """Configuring the same unit twice aborts."""
    MockConfigEntry(
        domain=DOMAIN, unique_id="192.168.1.100:502:1", data=USER_INPUT
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, init_integration, mock_client) -> None:
    """The options flow stores the scan interval."""
    entry = init_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    # OptionsFlowWithReload reloads the entry; keep the fake client in place.
    with patch(
        "custom_components.airgenio_2vv.AirgenioModbusClient",
        return_value=mock_client,
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 60}
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_SCAN_INTERVAL] == 60


async def test_migrate_existing_entry_to_venus(hass: HomeAssistant) -> None:
    """Version 1 entries retain historical VENUS behavior."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.100", CONF_PORT: 502, CONF_UNIT_ID: 1},
        version=1,
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert entry.data[CONF_MODEL] == MODEL_VENUS
