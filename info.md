# 2VV AirGENIO

Local Modbus TCP integration for **2VV AirGENIO-controlled** heat recovery
ventilation units, including VENUS and compatible DAPHNE controls. No cloud.

Requires Home Assistant 2026.9 or newer.

- Fan control (on/off + airflow %), temperature setpoint
- Outside / supply / extract / room temperatures + heat recovery efficiency
- Filter clogging sensor, filter reset button, error binary sensors
- Boost / day-night and automatic control switches, temperature sensor source select
- Optional BMS feed: push real outdoor/room temperatures into the unit
- Full Czech translations, diagnostics download

**Setup:** Add integration → select VENUS or DAPHNE → enter the unit's IP
address (panel: Service → Network), port 502, unit ID 1.

**Limitation:** summer night ventilation (panel MENU 16) has no Modbus
register and must be configured on the unit's panel.
