# 2VV AirGENIO for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/zanyscz/airgenio-2vv-homeassistant.svg)](https://github.com/zanyscz/airgenio-2vv-homeassistant/releases)
[![Validate](https://github.com/zanyscz/airgenio-2vv-homeassistant/actions/workflows/validate.yml/badge.svg)](https://github.com/zanyscz/airgenio-2vv-homeassistant/actions/workflows/validate.yml)

Local-polling Home Assistant integration for **2VV AirGENIO-controlled** heat
recovery ventilation (HRV) units, communicating over **Modbus TCP** — no
cloud, no extra hardware beyond the unit's LAN port.

Requires Home Assistant **2026.9 or newer**. Connections use Home Assistant's
shared Modbus infrastructure, preventing integrations from opening competing
sockets to the same controller.

> Unofficial community integration. Not affiliated with or endorsed by
> 2VV s.r.o. Register documentation courtesy of the official 2VV
> "AirGENIO Modbus RTU/TCP guide" (thanks to 2VV/Multivac).

## Supported hardware

| Unit | Control | Status |
|---|---|---|
| VENUS AirGENIO Comfort (e.g. HRV-30EC-E-74-AG) | SUPERIOR / IC3 / SC board with LAN | ✅ developed & validated against a real unit |
| DAPHNE with AirGENIO | board with Modbus TCP | Compatible shared controls; live-unit reports welcome |
| Other AirGENIO-controlled HRU/AHU units | boards with Modbus TCP | Likely works (same register map) — reports welcome |
| AirGENIO air curtains | COMFORT (RS-485 only) | ❌ not supported (no TCP; different feature set) |

## Features / entities

| Entity | Type | Notes |
|---|---|---|
| Ventilation unit | `fan` | on/off + airflow 0-100 % (maps to the unit's ‰ register); `actual_power` attribute |
| Fan speed | `number` | DAPHNE only; 20-100 % slider shown in device Controls |
| Temperature setpoint | `number` | 15-45 °C (effective range depends on the selected sensor) |
| Outside / supply / extract / room temperature | `sensor` | room shows *unavailable* when no room sensor is connected |
| Water return temperature | `sensor` (diagnostic, disabled) | only meaningful with a water heater |
| Fan power, preheater power, filter clogging | `sensor` | |
| Heat recovery efficiency | `sensor` | computed from the three air temperatures |
| Problem / fan / filter / sensor fault | `binary_sensor` | decoded from the unit's error bitfields |
| Summer mode, night reduction, preheater | `binary_sensor` (diagnostic) | |
| Service door | `binary_sensor` (diagnostic) | the unit's own door contact (status bit 9) |
| Boost / day-night profile | `switch` | shown as Boost for DAPHNE and Night profile for VENUS; documentation address 21009 (raw address 21008) |
| Automatic temperature / fan control | `switch` (config) | registers 25033 / 25077 |
| Temperature sensor source | `select` (config) | supply duct / extract duct / room / thermostat / room BMS |
| BMS outside sensor enable | `switch` (config) | register 20044 |
| BMS outside / room temperature | `number` (config, disabled) | push real temperatures into the unit, see below |
| Reset filter timer | `button` | after replacing filters |
| Ventilation mode (raw) | `sensor` (diagnostic, disabled) | raw register 25000 |

Plus a **diagnostics download** (redacted register dump) on the device page.

Register addresses in this project follow the 1-based addresses printed in
the 2VV guide. The Modbus client converts them to 0-based wire addresses. For
example, fan airflow `21002` writes raw address `21001`, while Boost/day-night
`21009` writes raw address `21008`.

## Installation

### HACS (recommended)

1. HACS → three-dot menu → **Custom repositories**
2. Add `https://github.com/zanyscz/airgenio-2vv-homeassistant` as category
   **Integration**
3. Search for **2VV AirGENIO**, install, restart Home Assistant

### Manual

1. Copy `custom_components/airgenio_2vv/` into your `config/custom_components/`
2. Restart Home Assistant

### Removal

Settings → Devices & services → 2VV AirGENIO → three-dot menu → Delete.
Then remove the folder (manual install) or uninstall via HACS, and restart.

## Configuration

Settings → Devices & services → **Add integration** → search **2VV AirGENIO**.

| Field | Default | Description |
|---|---|---|
| Host | — | IP address of the unit (control panel: Service code 1616 → menu 21 Network; enable Modbus TCP there if needed) |
| Port | 502 | Modbus TCP port |
| Modbus unit ID | 1 | Slave address (Service → menu 20 Modbus RTU) |
| Unit model | VENUS | Select VENUS or DAPHNE; this controls model-specific entities and naming |

Options (gear icon): polling interval 30-300 s (default 60).

## Feeding real temperatures into the unit (BMS)

The unit can take outside/room temperatures from Home Assistant instead of
its own sensors — useful when the built-in intake sensor reads high due to
duct placement. Enable the disabled-by-default entities and set up an
automation, e.g.:

```yaml
automation:
  - alias: Feed outside temperature to AirGENIO
    triggers:
      - trigger: time_pattern
        seconds: "/25"
    actions:
      - action: number.set_value
        target:
          entity_id: number.airgenio_bms_outside_temperature
        data:
          value: "{{ states('sensor.your_outdoor_sensor') }}"
```

Requirements from the 2VV manual:

- Write the value at least **every 30 s**, or the unit falls back to its
  physical sensor (a safe default when HA goes down).
- The unit only *uses* BMS values with automatic control active
  (`Automatic temperature control` + `Automatic fan control` on, sensor
  source set to `Room (BMS)` or the BMS outside switch enabled).

## Known limitations

- **Night ventilation (summer free-cooling, panel MENU 16) cannot be
  controlled over Modbus.** That is a limitation of the unit's firmware —
  no register exists for it; configure it on the control panel.
- Ventilation mode (MANUAL/CAV/DCV/VAV) is exposed read-only — the register
  enum is not documented for HRU units.
- BMS temperature push accepts **0.0-60.0 °C** — sub-zero encoding for
  those two registers is not documented and therefore not guessed.
- **Temperature setpoint writes may be silently ignored by the unit**
  while manual temperature control is active (observed on a VENUS
  Comfort with register 25033 = 0). The integration detects this via
  read-back verification and shows an error instead of pretending the
  write worked.
- Some SERVICE registers (e.g. 25077) are rejected by some units; the
  corresponding entity then shows as unavailable — that is expected.
- The unit has one small PLC. Runtime values use two batched requests every
  60 seconds by default; service configuration is cached for 30 minutes.
  Requests are serialized and spaced by 150 ms through Home Assistant's shared
  Modbus connection. Avoid running an independent Modbus TCP master.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Failed to connect` in setup | check IP (panel menu 21 — note the *actual* DHCP address; the INFO register can be stale), port 502 open, unit on the same VLAN or routed |
| Entities `unavailable` after working | unit unreachable — the integration reconnects automatically with backoff; check network/power |
| Timeouts with another Modbus master running | remove the other master (e.g. an old YAML `modbus:` hub polling the same unit) |
| Writes rejected | verify the Modbus unit ID matches panel menu 20 |

## Development

```bash
uv sync
uv run pytest
uv run ruff check custom_components tests
uv run mypy custom_components
```

Register map ground truth, design decisions and open questions live in
[`docs/`](docs/).

## Poznámka česky

Integrace pro rekuperační jednotky 2VV VENUS AirGENIO přes Modbus TCP.
Kompletní české překlady jsou součástí (HA je zobrazí automaticky).
Instalace: HACS → Custom repositories → přidat toto repo → nainstalovat →
restart HA → Přidat integraci „2VV AirGENIO" → zadat IP jednotky.
Známá omezení: NOČNÍ VĚTRÁNÍ nejde přes Modbus zapnout (omezení firmwaru
jednotky, nastavuje se na panelu, MENU 16).

## License

[MIT](LICENSE)
