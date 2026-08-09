# Decision log

- **2026-08-09 · Domain `airgenio_2vv`** — "airgenio" alone risks collision
  with other 2VV product lines (air curtains use the same controls family);
  suffix disambiguates and matches the brand order used in HA domains.
- **2026-08-09 · DOC addresses everywhere, −1 in one place** — the whole
  code base uses the addresses printed in the 2VV manual; only
  `modbus_client.py` subtracts 1. Prevents the classic off-by-one class of
  bugs that plagued the original YAML config.
- **2026-08-09 · No fan preset modes in v1.0** — the unit's user modes
  (presence/boost/night ventilation, MENU 14-16) are panel menus without
  Modbus registers; faking them as presets would imply control we don't
  have. Register 21009 exposed as a plain "night profile" switch instead.
- **2026-08-09 · No climate entity in v1.0** — setpoint semantics (range and
  meaning) depend on the selected control sensor; a number + select is
  honest. Climate can be layered on later without breaking entities.
- **2026-08-09 · 25000 read-only** — MANUAL/CAV/DCV/VAV enum values are not
  printed in the available PDF; per the safety rule we never guess write
  values (docs/open-questions.md #1).
- **2026-08-09 · BMS push clamped to ≥ 0 °C** — sub-zero encoding for
  23000/23002 undocumented (open-questions.md #3).
- **2026-08-09 · Entry unique_id = host:port:unit_id** — the unit exposes no
  serial number register; the INFO block's IP/MAC proved unreliable on the
  reference install (stale DHCP data).
- **2026-08-09 · pymodbus>=3.10 requirement** — 3.10 renamed `slave=` →
  `device_id=`; a floor (not a pin) avoids fighting HA core's own pymodbus
  pin (3.13.x in 2026).
- **2026-08-09 · hacs.json homeassistant: 2025.11.0** — the code relies on
  `OptionsFlowWithReload` (2025.8) and coordinator `config_entry=`
  enforcement semantics (2025.11); older cores are untested.
- **2026-08-09 · Local hassfest/HACS validation deferred to CI** — hassfest
  is only distributed inside the HA core repo / GitHub action; cloning core
  locally adds nothing over the authoritative CI run, which gates the
  release (Checkpoint 5 requires green workflows).
- **2026-08-09 · Brand images bundled in `brand/`** (HA 2026.3+ local brands
  API) + brands-repo PR prepared as follow-up for older cores and HACS
  default-store eligibility.
