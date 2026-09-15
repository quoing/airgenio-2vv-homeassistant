# 2VV Daphne / AirGENIO Implementation Plan

## Purpose

Extend this integration for 2VV Daphne while preserving VENUS compatibility.
Priorities are reliable fan writes, conservative Modbus TCP behavior, and only
exposing features backed by documentation or live-device validation.

Phases A, B, and C1 were approved for implementation. Remaining phases can be
selected or deferred independently, subject to dependencies noted below.

## Confirmed Address Mapping

Daphne observations use raw, zero-based Modbus addresses. This integration
stores one-based addresses printed in 2VV documentation and subtracts one in
the Modbus client. Current addresses therefore already match Daphne:

| Function | Daphne raw address | Integration address | Status |
|---|---:|---:|---|
| Unit power | `21000` | `21001` | Correct |
| Fan target | `21001` | `21002` | Correct |
| Temperature target | `21002` | `21003` | Correct |
| Boost | `21008` | `21009` | Correct |
| Actual fan percentage | `18005` | `18006` | Correct |
| Outside temperature | `18006` | `18007` | Correct |
| Supply/outlet temperature | `18007` | `18008` | Correct |
| Extract/inlet temperature | `18008` | `18009` | Correct |
| Heater output candidate | `18012` | `18013` | Address correct; name uncertain |
| Filter candidate | `18015` | `18016` | Address correct; semantics need confirmation |

Constants must not be changed to raw addresses while centralized BASE+1
conversion remains in place.

## Fan Write Investigation

Fan percentage write failures are probably behavioral rather than addressing
errors. Current potential causes:

- Automatic fan regulation may overwrite or ignore manual target values.
- Immediate read-back verification may observe a normalized or reverted value.
- A write currently triggers verification followed by a full coordinator
  refresh, creating a rapid request burst.
- Changing percentage while unit is off writes target but does not turn unit
  on.
- Current errors do not clearly distinguish rejected writes, read-back
  mismatches, connection failures, or controller overrides.

## Phase A: Shared Connection And Stability

Recommended foundation for all further work.

### A1. Adopt Home Assistant 2026.9 Shared Modbus API

Use:

- `async_get_unit()` for loaded config entries
- `async_get_temporary_unit()` during config flow
- `ModbusTcpParams`
- `ModbusUnit`

Keep a thin AirGENIO client wrapper for address conversion and domain-specific
errors, but remove direct connection ownership and direct `pymodbus` usage.

Expected benefits:

- One connection shared by integrations using same endpoint
- Globally serialized requests
- Automatic reconnect on next request
- Per-unit message spacing through `set_message_spacing()`
- Stale-link recycling through `disconnect()`
- No separate YAML Modbus hub required

Required project changes:

- Raise minimum Home Assistant version to `2026.9`
- Remove direct `pymodbus` manifest requirement
- Use temporary shared unit for config-flow connection validation
- Bind shared unit lifetime to config entry

### A2. Conservative Request Behavior

- Default polling interval: 60 seconds
- Minimum configurable polling interval: 30 seconds
- Initial message spacing: 100-250 ms, subject to testing
- Disconnect unit after timeout or connection/protocol failure
- Let next scheduled request reconnect
- Do not implement aggressive internal retries
- Do not reload config entry solely because communication failed

### A3. Fast And Slow Polling

Fast polling, every 30-60 seconds:

- Runtime input block
- Common holding/control block

Slow polling, at startup and every 30-60 minutes:

- `20044`
- `25000`
- `25009`
- `25033`
- `25077`
- Future filter/service registers

Current coordinator reads five individual configuration registers on every
refresh. Separating slow values should reduce normal polling from seven
transactions to two.

**Recommendation:** implement A1-A3 together.

## Phase B: Fan Write Repair

Highest functional priority.

### B1. Percentage Behavior

For percentage `1..100`:

1. Validate or clamp percentage.
2. Write integration address `21002`, producing raw write to `21001`.
3. Request targeted runtime refresh.
4. Do not refresh slow configuration values.

DAPHNE running percentages are constrained to `20..100`. A dedicated
DAPHNE-only Fan speed number entity exposes that range in the device Controls
section because Home Assistant fan entities cannot advertise a nonzero minimum.

For percentage `0`:

1. Write power off.
2. Refresh runtime state.

Behavior when setting nonzero percentage while unit is off:

- **Recommended:** write percentage, then turn unit on.
- Alternative: update stored target but leave unit off.

### B2. Write Verification

Options:

1. **Recommended:** write once, perform one runtime block refresh, and verify
   against refreshed block.
2. Keep direct single-register verification, then refresh.
3. Do not verify immediately; rely on next scheduled poll.

Option 1 confirms state without a separate read transaction.

### B3. Automatic Fan Control

Options:

1. **Recommended:** never disable automatic control implicitly. If target does
   not persist, report that automatic fan control may own setpoint.
2. Disable automatic fan control before manual percentage write.
3. Make this behavior configurable.

Option 2 changes controller operating mode and should not be default.

### B4. Write Diagnostics

Errors and debug logs should include:

- Documentation address
- Raw address
- Attempted value
- Returned value, when available
- Exception category
- Automatic fan-control state
- Connection state

**Recommendation:** implement B1-B4 using recommended options.

## Phase C: Daphne Boost

Current address mapping is already correct: integration address `21009`
becomes Daphne raw address `21008`.

### C1. Explicit Boost Switch

- Keep raw address `21008` / integration address `21009`.
- Display entity as `Boost` once Daphne semantics are confirmed.
- Read state from runtime holding block.
- Preserve existing unique ID initially to avoid breaking entity registry and
  automations.

### C2. Live Validation

Determine:

- Whether writing `1` remains `1`
- Whether controller clears it after a timer
- Whether fan target changes
- Whether writing `0` cancels Boost
- Whether Daphne panel identifies function as Boost
- Whether VENUS behavior remains DAY/NIGHT rather than Boost

### C3. Fan Preset

Optionally add `Boost` fan preset after semantics are confirmed. Explicit
switch should remain available.

**Recommendation:** implement C1 after validation; defer C3.

## Phase D: Confirmed Runtime Entities

### D1. Temperatures

Keep existing outside, supply/outlet, extract/inlet, room, and water-return
channels. Review display names against official Daphne airflow terminology.
Absent sensors must remain unavailable through signed-int16 sentinel handling.

### D2. Actual Fan Percentage

Existing implementation is correct:

- Daphne raw address `18005`
- Divide raw value by ten
- Unit is percent, not `m3/h`

Retaining separate sensor is useful for history and graphs even though fan
entity also exposes actual value as an attribute.

### D3. Heater Output

Current raw address matches `18012`, but entity is called `preheater_power`.

Options:

1. Rename to generic `heater_output`.
2. Keep `preheater_power` if official documentation confirms that meaning.
3. Expose separate outputs only if documentation proves separate registers.

### D4. Flow Alarm

Code defines corresponding register but does not expose it directly. Add
diagnostic binary sensor after confirming documented encoding.

## Phase E: Filters

Candidate raw addresses:

- Runtime `18015`
- Service `25018`
- Service `25019`

Before implementation, confirm:

- Whether runtime value means clogging percentage, condition, or state
- Units for working time
- Units for replacement interval
- Which values are writable

Potential entities:

- Filter condition
- Filter working time
- Filter replacement interval

Observed Daphne values need care: raw `18015 = 2`, while raw `18016 = 100`.
These values alone do not prove semantics.

**Recommendation:** defer until official register rows are reviewed. Poll
service values using slow schedule.

## Phase F: Capabilities And Model Detection

Introduce capability structure when first genuinely optional entity is added,
not before:

```python
@dataclass(frozen=True)
class AirgenioCapabilities:
    boost: bool
    day_night: bool
    heater_output: bool
    bypass_position: bool
    filter_timing: bool
    extended_runtime_block: bool
```

Discovery order:

1. Try Modbus device identification function `0x2B/0x0E`.
2. Interpret official model/controller identifier if returned.
3. Probe explicitly documented optional registers individually.
4. Fall back to generic AirGENIO.

Do not infer Daphne from ordinary register values or from presence of raw
address `21008`.

## Phase G: Optional Or Deferred Features

### G1. Climate Entity

Defer initially. Existing target-temperature number is simpler and accurate.
Climate requires decisions about current-temperature source, HVAC modes, power
ownership, fan entity interaction, and unavailable configured sensors.

### G2. Bypass Percentage

Defer until exact documented register and scale are known. Observed raw
`18016 = 100` is interesting but insufficient proof.

### G3. Separate Preheater And Reheater Outputs

Defer until documentation proves separate registers.

### G4. Extended Raw Blocks

Do not blindly expand generic polling to raw `17999..18019` and
`20999..21026`. Daphne accepts them, but another AirGENIO model may reject part
of a block. Read common blocks by default and enable documented extensions
through capabilities.

## Suggested Delivery

1. Release 1: A1-A3, B1-B4, C1, and address tests.
2. Release 2: confirmed temperature naming, heater output, and flow alarm.
3. Release 3: filters after documentation validation.
4. Later: model detection, capabilities, climate, bypass, and separate heater
   stages.

Recommended immediate scope is **Phase A + Phase B + C1**. This directly
addresses fan writes and TCP lockups without adding speculative entities.

## Decisions Needed

- [x] Approve Phase A shared connection and polling changes.
- [x] Setting nonzero fan percentage while off starts the unit.
- [x] Verify fan writes through refreshed runtime block.
- [x] Leave automatic fan control unchanged and explain mismatches.
- [x] Expose Boost for entries explicitly configured as DAPHNE.
- [ ] Decide whether heater naming should wait for documentation review.
- [ ] Decide whether flow alarm should wait for documentation review.
- [ ] Supply or review official filter register rows before Phase E.
- [ ] Decide whether climate entity is wanted later.
- [ ] Supply exact documented bypass register before G2.
