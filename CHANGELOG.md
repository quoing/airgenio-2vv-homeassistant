# Changelog

All notable changes to this project are documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org/).

## [Unreleased]

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
