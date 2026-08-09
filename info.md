# 2VV AirGENIO

Local Modbus TCP integration for **2VV VENUS AirGENIO** heat recovery
ventilation units. No cloud.

- Fan control (on/off + airflow %), temperature setpoint
- Outside / supply / extract / room temperatures + heat recovery efficiency
- Filter clogging sensor, filter reset button, error binary sensors
- Automatic control switches, temperature sensor source select
- Optional BMS feed: push real outdoor/room temperatures into the unit
- Full Czech translations, diagnostics download

**Setup:** Add integration → enter the unit's IP address (panel: Service →
Network), port 502, unit ID 1.

**Limitation:** summer night ventilation (panel MENU 16) has no Modbus
register and must be configured on the unit's panel.
