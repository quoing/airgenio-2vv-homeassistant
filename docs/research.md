# Research: Best Practices for the airgenio_2vv Integration

Research date: 2026-08-09. Two tracks: (A) how the best HRV/Modbus
integrations are built, (B) current HA developer + HACS publishing
requirements. Full source list at the end.

## A. Reference integrations studied

### comfoconnect (HA Core, Zehnder ComfoAirQ)
Legacy-style (YAML, dispatcher push, no config flow) — outdated architecture,
but the canonical *entity list* for an HRV: 4-stream temperatures/humidity,
fan RPM + duty, airflow, bypass %, days-to-replace-filter, preheater power.
Fan entity: speeds via `percentage_to_ranged_value`, preset `auto`.

### michaelarnauts/home-assistant-comfoconnect (HACS, modern rebuild)
Best reference for HRV *entity modeling*: fan carries only speed +
AUTO/MANUAL presets; **bypass, boost, balance, temperature profile are
`select` entities**, each description holding `get_value_fn`/`set_value_fn`.
Diagnostic binary sensors default-disabled. Config flow with discovery +
manual host, unique_id = bridge UUID, reauth step. Two linked devices via
`via_device`.

### veista/nilan (Modbus HRV/heat pump)
Models the whole unit as `climate` (HVAC modes + fan_modes "0"-"4" + presets).
Uses HA core ModbusHub. Device-capability map filters entities per model.
**Anti-patterns to avoid:** one Modbus call per entity `async_update()`
(hammers the bus), no unique_id in config flow.

### remmob/comfoair (Modbus TCP/RTU HRV)
Closest analogue. `DataUpdateCoordinator` hub with **batched range reads**
(`(start, count)` tuples), 3 retries per range, signed two's-complement
decoding, computed sensors (heat-recovery efficiency, dew point) derived in
the hub, forced client reset after 5 min of failures, filter/alarm binary
sensors. unique_id = `"{mode}:{host}:{port}:{device_id}"`. Weakness: read-only.

### samuolis/brink
UX trick worth copying: **setting a fan speed implicitly switches the unit to
MANUAL mode**; optimistic `async_set_updated_data()` then refresh.

### wills106/homeassistant-solax-modbus + wlcrs/huawei_solar (Modbus heavyweights)
- solax: async pymodbus behind a transport abstraction + compat shim; block
  building only for enabled entities; write queue; slowdown factor when the
  device stops responding; CI with hassfest + HACS action + pytest matrix +
  strict mypy.
- huawei_solar: cleanest modern HA side — `entry.runtime_data`, multiple
  coordinators with distinct intervals, typed exceptions → `UpdateFailed`
  with actionable messages, diagnostics with `async_redact_data`,
  unique_id = device serial.

## B. Publishing requirements (2026)

- **manifest.json** (custom integration): `domain`, `name`, `codeowners`,
  `config_flow`, `dependencies`, `documentation`, `integration_type`,
  `iot_class`, `issue_tracker`, `requirements`, `version` (mandatory for
  custom). For this unit: `integration_type: device`,
  `iot_class: local_polling`.
- **Config flow**: `async_step_user` + test-before-configure; unique-entry
  dedupe (`_async_abort_entries_match` on host fallback); reconfigure step;
  **OptionsFlow must NOT set `self.config_entry`** (removed 2025.12) — use
  `OptionsFlowWithReload`.
- **Coordinator**: must pass `config_entry=` explicitly (mandatory since HA
  2025.11); store in `entry.runtime_data`
  (`type Airgenio2vvConfigEntry = ConfigEntry[AirgenioCoordinator]`).
- **Quality scale**: Bronze/Silver rule names tracked in
  `quality_scale.yaml`; for custom integrations self-declared. We target
  Silver behaviors: entity-unavailable, log-when-unavailable (coordinator
  gives both), parallel-updates, config-entry-unloading, action-exceptions,
  test coverage.
- **pymodbus**: HA core pins 3.13.x in 2026.x. API since 3.10: `device_id=`
  kwarg (was `slave=`), keyword-only `count=`. `AsyncModbusTcpClient`,
  `client.connected`, `rr.isError()`, `rr.registers`. Requirement pin:
  `pymodbus>=3.10` so we never fight the core pin.
- **HACS**: repo root `hacs.json` (`name`, `homeassistant` min version),
  integration at `custom_components/<domain>/`, GitHub Releases (HACS shows
  latest 5), topics + description + issues enabled, CI = `hacs/action@main`
  (category integration) + `home-assistant/actions/hassfest@master`. Default
  store inclusion = PR to `hacs/default` (needs brands assets + ≥1 release).
- **Brands**: since HA 2026.3 a bundled `brand/icon.png` (256×256, +@2x)
  inside `custom_components/<domain>/` is served locally and takes priority
  over the CDN; brands-repo PR still the safe route for older HA + default
  store.

## C. Architecture decision for airgenio_2vv

- Async **pymodbus `AsyncModbusTcpClient`** wrapped in a small
  `AirgenioModbusClient` (single `asyncio.Lock`, connected-check before each
  transaction, reconnect with exponential backoff, doc→wire −1 offset applied
  in exactly this layer).
- **One `DataUpdateCoordinator`** (default 30 s, options-configurable
  10-300 s) doing **3 batched reads per cycle**: status block
  18000-18016 (FC04), share block 21001-21009 (FC03), service snapshot
  20044 + 25009/25033/25077 (FC03, lower frequency not needed — 4 registers
  is cheap). Decode/scale/bit-extract in the coordinator; `coordinator.data`
  = flat dataclass.
- **Writes**: write → read-back verify → `async_request_refresh()`; raise
  `HomeAssistantError` on mismatch (Silver `action-exceptions`).
- **Entity model** (per community consensus): fan = primary (speed % +
  on/off, no fake presets); selects for config enums; numbers for setpoints;
  buttons for filter reset; diagnostic sensors default-disabled where niche.
- Optional **BMS temperature feed**: two `number` entities (config category,
  disabled by default) that push to 23000/23002; the unit's <30 s refresh
  contract is the user's automation responsibility (documented in README) —
  the integration never invents temperatures.

## Checkpoint 1 (self-review)

**Q1: Does the entity model cover 100 % of the verified Ground Truth
registers?**
Yes — every register marked *Verified* in ground-truth.md §4-§8 maps to an
entity or diagnostics (see §11 of ground-truth.md). Documented-only registers
(TIME, schedules, NETWORK, NORDIC, slave AC blocks, air-curtain door logic)
are deliberately excluded from v1.0; INFO block appears only in the
diagnostics dump.

**Q2: Is the design consistent with top integrations (familiar UX)?**
Yes — fan-as-primary + selects/numbers/buttons mirrors
michaelarnauts/comfoconnect; coordinator + batched reads mirrors
remmob/huawei_solar; runtime_data/options/diagnostics mirror huawei_solar.
One deviation: no `climate` entity (nilan style) because the unit's setpoint
semantics depend on the selected sensor and the temperature *control* is
better exposed as a number + mode select; a climate entity can be added in
v1.x if users ask.

**Q3: Registers I am not sure about → read-only or omitted?**
- 25000 ventilation mode enum → read-only diagnostic sensor
  (open-questions #1).
- 21009 Boost/Day-Night ambiguity → single switch, documented dual meaning
  (open-questions #2).
- Negative BMS writes → clamped at 0.0 °C + warning (open-questions #3).
- 21024/21025 heater manual power, door-contact block, slave blocks →
  omitted (air-curtain features).

No gaps found; proceeding to design.

## Sources

- github.com/home-assistant/core (components/comfoconnect, components/modbus)
- github.com/michaelarnauts/home-assistant-comfoconnect
- github.com/veista/nilan · github.com/remmob/comfoair · github.com/samuolis/brink
- github.com/wills106/homeassistant-solax-modbus · github.com/wlcrs/huawei_solar
- developers.home-assistant.io: creating_integration_manifest,
  config_entries_config_flow_handler, config_entries_options_flow_handler,
  core/integration-quality-scale (+checklist), blog 2024-11-12 options-flow,
  blog 2024-08-05 coordinator _async_setup, blog 2026-02-24 brands proxy API
- hacs.xyz/docs/publish/{start,integration,include}
- github.com/pymodbus-dev/pymodbus (API_changes.rst)
- github.com/home-assistant/brands (README)
