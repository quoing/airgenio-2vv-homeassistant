# Design: airgenio_2vv integration

## 1. Domain

`airgenio_2vv` — no collision found (HA core has no `airgenio*`; HACS search
shows no existing 2VV/AirGENIO integration as of 2026-08).

Display name: **2VV AirGENIO**.

## 2. Entity model (final)

Doc addresses per ground-truth.md; the Modbus layer subtracts 1 on the wire.
`EC` = entity_category (`c`=config, `d`=diagnostic), `Dis` = disabled by
default.

| Key | Platform | Register(s) | R/W | Scale | Device class / unit | EC | Dis |
|---|---|---|---|---|---|---|---|
| `fan` (main) | fan | 21001 on/off, 21002 target ‰, 18006 actual ‰ | R/W | ‰→% | — | — | — |
| `temperature_setpoint` | number | 21003 | R/W | ×1 °C, 15-45 | temperature | — | — |
| `outside_temperature` | sensor | 18007 | R | ×0.1 int16 | temperature, measurement | — | — |
| `supply_temperature` | sensor | 18008 | R | ×0.1 int16 | temperature, measurement | — | — |
| `extract_temperature` | sensor | 18009 | R | ×0.1 int16 | temperature, measurement | — | — |
| `room_temperature` | sensor | 18011 | R | ×0.1 int16; <−40 °C → unavailable | temperature, measurement | — | — |
| `water_return_temperature` | sensor | 18010 | R | ×0.1 int16; <−40 °C → unavailable | temperature, measurement | d | ✓ |
| `fan_power` | sensor | 18006 | R | ‰→% | power_factor-like, % measurement | — | — |
| `preheater_power` | sensor | 18013 | R | % | % measurement | — | — |
| `filter_clogging` | sensor | 18016 | R | % | % measurement | — | — |
| `heat_recovery_efficiency` | sensor | computed (18007,18008,18009) | R | % | % measurement | — | — |
| `ventilation_mode_raw` | sensor | 25000 | R | raw | — | d | ✓ |
| `bms_outside_readback` | sensor | 18014 | R | ×0.1 int16 | temperature | d | ✓ |
| `bms_room_readback` | sensor | 18015 | R | ×0.1 int16 | temperature | d | ✓ |
| `global_error` | binary_sensor | 18001 bit7 | R | — | problem | — | — |
| `fan_error` | binary_sensor | 18001 bit0\|bit1 | R | — | problem | d | — |
| `filter_warning` | binary_sensor | 18001 bit2\|bit3 | R | — | problem | — | — |
| `preheater_active` | binary_sensor | 18013 > 0 | R | — | heat | d | — |
| `summer_mode` | binary_sensor | 18000 bit8 | R | — | — | d | — |
| `night_reduction` | binary_sensor | 18000 bit3 | R | — | — | d | ✓ |
| `sensor_fault` | binary_sensor | 18003 != 0 | R | — | problem | d | — |
| `day_night_mode` | switch | 21009 | R/W | — | — | — | — |
| `filter_reset` | button | 21016 ← 1 | W | — | — | c | — |
| `automatic_temperature_control` | switch | 25033 | R/W | — | — | c | — |
| `automatic_fan_control` | switch | 25077 | R/W | — | — | c | — |
| `temperature_sensor_source` | select | 25009 (0/1/2/3/4) | R/W | enum | — | c | — |
| `bms_outside_enable` | switch | 20044 | R/W | — | — | c | — |
| `bms_outside_temperature` | number | 23002 W / 18014 R | R/W | ×10, 0.0-60.0 | temperature | c | ✓ |
| `bms_room_temperature` | number | 23000 W / 18015 R | R/W | ×10, 0.0-60.0 | temperature | c | ✓ |

Notes:
- Fan: `FanEntityFeature.SET_SPEED | TURN_ON | TURN_OFF`; percentage maps
  1:1 to ‰/10 (range 10-100 %); `percentage` reads target 21002, attribute
  `actual_power` from 18006. No preset_modes in v1.0 (unit's modes are not
  writable via Modbus — ground-truth §10.2).
- Setpoint range 15-45 °C follows the widest documented range; the effective
  range depends on the selected sensor (documented in README).
- `heat_recovery_efficiency` = `(supply − outside) / (extract − outside)`
  ×100, clamped 0-100, unavailable when |extract − outside| < 1 K (avoids
  division noise; same approach as remmob/comfoair).
- BMS numbers are config+disabled: enabling them is an explicit opt-in;
  their state is the readback register, so a stale push is visible.

## 3. Architecture

```
custom_components/airgenio_2vv/
├── __init__.py          # async_setup_entry: client + coordinator → runtime_data
├── manifest.json        # v1.0.0, pymodbus>=3.10, local_polling, device
├── config_flow.py       # user step (host/port/unit_id) + test connection,
│                        #   reconfigure step, OptionsFlowWithReload (scan interval)
├── coordinator.py       # AirgenioCoordinator(DataUpdateCoordinator[AirgenioData])
├── modbus_client.py     # AirgenioModbusClient: AsyncModbusTcpClient wrapper,
│                        #   doc→wire offset, lock, reconnect+backoff, typed errors
├── const.py             # DOMAIN, register constants (DOC addresses, named),
│                        #   defaults, enums
├── entity.py            # AirgenioEntity(CoordinatorEntity) base: device_info,
│                        #   _attr_has_entity_name, unique_id scheme
├── data.py              # AirgenioData frozen dataclass (decoded snapshot)
├── diagnostics.py       # redacted entry data + raw register dump + INFO block
├── fan.py sensor.py binary_sensor.py number.py select.py switch.py button.py
├── strings.json + translations/en.json + translations/cs.json
├── brand/icon.png (+ icon@2x.png)
└── quality_scale.yaml
```

- **ConfigEntry.runtime_data**: `type Airgenio2vvConfigEntry =
  ConfigEntry[AirgenioCoordinator]`.
- **Coordinator cycle** (default 30 s, options 10-300 s):
  1. FC04 read 18000..18016 (17 regs, one call, wire 17999)
  2. FC03 read 21001..21009 (9 regs, one call)
  3. FC03 read of scattered config regs: 20044, 25000, 25009, 25033, 25077
     (5 single reads — non-consecutive)
  Decode into `AirgenioData`; any Modbus failure → `UpdateFailed` (entities
  unavailable, coordinator logs once — Silver rules).
- **Writes** (`modbus_client.write_verified`): FC06 write → FC03 read-back →
  mismatch → log warning + raise `HomeAssistantError`; success →
  `coordinator.async_request_refresh()`.
- **Unique IDs**: config entry unique_id = `"{host}:{port}:{unit_id}"`
  (unit has no readable serial; INFO MAC is unreliable per ground-truth §9).
  Entity unique_id = `"{entry.unique_id}_{key}"`. Device identifiers
  `{(DOMAIN, entry.unique_id)}`, manufacturer "2VV", model "VENUS AirGENIO",
  sw_version from INFO 16029/16030 read once at setup (best effort).
- **PARALLEL_UPDATES = 0** in every platform module (coordinator-driven).
- **Config flow**: host (required), port (default 502), unit id (default 1)
  → `test-before-configure`: connect + FC04 read 18000 (1 reg). Errors:
  `cannot_connect`, `timeout`, `invalid_response`. Dedupe via
  `_async_abort_entries_match({host, port, unit_id})` + unique_id.
  Reconfigure step reuses the same schema/validation.
- **Options flow**: `OptionsFlowWithReload`, single `init` step:
  `scan_interval` (10-300 s, default 30).

## 4. Error handling

| Failure | Behavior |
|---|---|
| TCP connect refused/timeout at setup | `ConfigEntryNotReady` (HA retries with backoff) |
| Poll failure mid-run | `UpdateFailed` → all entities unavailable; auto-recovery on next success |
| Client disconnected | reconnect before next transaction; exponential backoff 1→2→4→…→60 s inside client |
| Write verify mismatch | `HomeAssistantError` (shows in UI), warning log, refresh |
| Modbus exception response | typed `AirgenioModbusError` with function/address context |

## 5. Checkpoint 2 — quality scale checklist (target ≥ Silver behaviors)

Bronze:
- [x] config-flow (UI setup, strings + translations)
- [x] test-before-configure (connection test reads a real register)
- [x] test-before-setup (`ConfigEntryNotReady` on failure)
- [x] unique-config-entry (unique_id + entries-match abort)
- [x] entity-unique-id (per-entity stable IDs)
- [x] has-entity-name (`_attr_has_entity_name = True` + translation_key)
- [x] runtime-data (`entry.runtime_data`)
- [x] appropriate-polling (30 s default, single batched cycle)
- [x] common-modules (coordinator.py, entity.py, const.py, data.py)
- [x] dependency-transparency (pymodbus from PyPI, pinned range)
- [x] config-flow-test-coverage (tests: happy path, cannot_connect, dedupe)
- [x] brands (bundled brand/ folder; brands-repo PR prepared in docs)
- [x] action-setup / docs-* (no custom services in v1.0; README covers docs rules)

Silver:
- [x] config-entry-unloading (`async_unload_platforms`, client close)
- [x] entity-unavailable + log-when-unavailable (coordinator built-ins)
- [x] parallel-updates (0 in all platforms)
- [x] action-exceptions (writes raise `HomeAssistantError`)
- [x] reauthentication-flow — N/A (no credentials); documented as exempt in
      quality_scale.yaml
- [x] integration-owner (codeowners)
- [ ] test-coverage > 95 % — target > 80 % on core logic per project brief;
      recorded honestly in quality_scale.yaml as todo
- [x] docs-configuration-parameters / docs-installation-parameters (README)

Additional (Gold-tier picks): diagnostics.py, entity-category, device-class,
entity-disabled-by-default, entity-translations (en + cs), icon-translations
(icons.json), reconfiguration-flow.

No blocking I/O in the event loop: pymodbus async client only; no sync file
reads at runtime (manifest/strings loaded by HA itself).

## 6. Out of scope for v1.0 (recorded)

- `climate` entity (setpoint semantics depend on sensor selection).
- Ventilation-mode select (enum unconfirmed — open-questions #1).
- Weekly/yearly schedule registers, RTC sync, error-log block, NETWORK
  writes, slave/air-curtain blocks, door-contact logic.
- RTU-over-serial transport (TCP + RTU-over-TCP gateways only; RTU direct
  can come later — config flow schema keeps room for it).
