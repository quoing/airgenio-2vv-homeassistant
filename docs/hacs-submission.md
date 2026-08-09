# HACS default store submission (prepared)

Inclusion in the HACS default store is done via a **pull request to
`hacs/default`** (not an issue): fork https://github.com/hacs/default,
add the line `zanyscz/airgenio-2vv-homeassistant` to the `integration`
file (alphabetical order), open the PR from a personal fork (must be
editable by maintainers).

## Pre-submission checklist (state 2026-08-09)

- [x] Public repo, description set, issues enabled, topics set
      (home-assistant, hacs, custom-integration, modbus, hrv,
      heat-recovery-ventilation, 2vv, ventilation)
- [x] Exactly one integration at `custom_components/airgenio_2vv/`
- [x] `hacs.json` with `name` + minimum HA version
- [x] `README.md` + `info.md`
- [x] Passing `hacs/action` (category integration) and hassfest on main
- [x] GitHub Release published (HACS installs releases, not branches)
- [ ] Brands assets — bundled `brand/` folder ships with the integration
      (HA ≥ 2026.3 serves it locally); for the default store and older
      cores also open a PR to `home-assistant/brands` (see below)

## home-assistant/brands PR (materials ready)

Create `custom_integrations/airgenio_2vv/` in a fork of
https://github.com/home-assistant/brands containing the files already
prepared in `custom_components/airgenio_2vv/brand/`:

- `icon.png` (256×256) and `icon@2x.png` (512×512)
- `logo.png` / `logo@2x.png` (same artwork; replace with a landscape
  variant if 2VV ever provides usable official art — do NOT use 2VV's
  trademarked logo without permission)

PR title: `Add airgenio_2vv (custom integration)`.

## Suggested PR text for hacs/default

> Adds **2VV AirGENIO** — a local-polling Modbus TCP integration for 2VV
> VENUS AirGENIO heat recovery ventilation units. Config flow, fan +
> 20 entities, diagnostics, EN/CS translations, validated against real
> hardware (docs/validation-report.md). CI: hassfest + HACS action +
> pytest (30 tests) + ruff/mypy, all green.
