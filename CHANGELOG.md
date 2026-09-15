# Changelog

All notable changes to this project are documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

## [2.0.0] - 2026-09-15

### Changed

- Generalized device metadata and documentation for AirGENIO-controlled units,
  including DAPHNE compatibility.
- Added VENUS/DAPHNE model selection. Existing entries migrate to VENUS.
- DAPHNE presents shared register 21009 as Boost; VENUS retains Night profile.
- Migrated to Home Assistant 2026.9 shared Modbus connections with serialized,
  paced requests and stale-link recycling after communication failures.
- Changed default polling to 60 seconds and cached configuration registers for
  30 minutes, reducing regular polling from seven transactions to two.
- Fan percentage writes now start a stopped unit and verify state through one
  refreshed runtime block instead of an extra single-register read.

### Tests

- Added coverage proving the DAPHNE Boost and airflow raw-address mappings.

## [1.1.0] - 2026-08-28

### Added

- Service door binary sensor (`door_open`) decoding bit 9 of the unit
  global status register (DOC 18000). Verified against a parallel YAML
  Modbus hub reading the same bit as mask 512. Diagnostic category,
  `door` device class, open/closed icon states.

## [1.0.0] - 2026-08-09

### Added

- Initial release: Modbus TCP integration for 2VV VENUS AirGENIO HRV units.
- Config flow (host / port / unit ID) with connection test, reconfigure
  step and options flow (polling interval).
- Fan entity (on/off + airflow percentage) with actual-power attribute.
- Sensors: outside / supply / extract / room / water-return temperatures,
  fan power, preheater power, filter clogging, computed heat recovery
  efficiency, BMS readbacks, raw ventilation mode.
- Binary sensors: global error, fan error, filter warning, sensor fault,
  preheater active, summer mode, night reduction.
- Switches: night profile (DAY/NIGHT), automatic temperature control,
  automatic fan control, BMS outside sensor enable.
- Select: temperature sensor source (incl. Room BMS).
- Numbers: temperature setpoint, BMS outside/room temperature push
  (disabled by default).
- Button: filter timer reset.
- Diagnostics endpoint with redacted register dump.
- English + Czech translations, icon translations.
- Write verification (read-back after every write) and reconnect with
  exponential backoff.
- Per-register unsupported detection: SERVICE registers rejected by a
  unit (observed with 25077) disable only their own entity instead of
  failing the whole integration.
- Sensor-fault logic that ignores BMS status flapping and absent optional
  sensors (validated against a real VENUS AirGENIO Comfort — see
  docs/validation-report.md).
