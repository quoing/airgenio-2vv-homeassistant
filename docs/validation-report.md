# Validation report — real unit

Validated 2026-08-09 against a VENUS AirGENIO Comfort (HRV-30EC-E-74-AG),
SUPERIOR/IC3-class board, Modbus TCP, unit id 1, HA 2026.7.4. The legacy
YAML `modbus:` hub kept polling the same unit during the whole test (the
unit handles two concurrent TCP masters without issues).

## Read entities — side-by-side (same instant)

| Value | Legacy YAML entity | New integration entity | Match |
|---|---|---|---|
| Outside temperature | 25.3 °C | 25.3 °C | ✅ |
| Supply temperature | 25.1 °C | 25.1 °C | ✅ |
| Extract temperature | 25.5 °C | 25.5 °C | ✅ |
| Room temperature (BMS-fed) | 32.5 °C | 32.5 °C | ✅ |
| Fan power | 20 % | 20 % | ✅ |
| Filter clogging | 19 % | 19 % | ✅ |
| Preheater power | 0 % | 0 % | ✅ |
| Global error | off | off | ✅ |
| Filter warning | off | off | ✅ |
| Unit on/off | on | fan `on` | ✅ |
| Day/night (21009) | off | off | ✅ |
| Temp sensor selection (25009) | 4 | `room_bms` | ✅ |
| BMS outside enable (20044) | 1 | on | ✅ |
| Heat recovery efficiency | 97 % | unavailable | ✅ (intentional deviation: legacy computes even at ΔT = 0.2 K, which is measurement noise; the integration requires ΔT ≥ 1 K) |

**Result: 100 % match on every comparable read entity.**

## Write tests

| Test | Result |
|---|---|
| `fan.set_percentage` 20 → 25 % (doc 21002 ← 250) | ✅ written, read-back verified, unit ramped |
| Restore 25 → 20 % | ✅ |
| `number.set_value` setpoint 15 → 16 °C (doc 21003 ← 16) | ⚠️ FC06 accepted but the unit **keeps 15** (silently ignores the write; confirmed with direct probes at +0.05…+2 s). The integration's read-back verification correctly raised an error to the UI instead of pretending success. Likely requires automatic temperature control (25033 = 1) to be active — currently 0 on the reference unit. Not flipped during validation (would change the unit's control mode). Recorded in open-questions.md #8. |

## Findings that changed the code (Checkpoint 4 loop)

1. **Register 25077 rejects READs** on this unit (Modbus exception 2,
   IllegalDataAddress) although 2VV's official BMS example writes it.
   → coordinator now marks per-register unsupported state instead of
   failing the whole update; the affected entity becomes unavailable.
2. **Sensor-status register 18003 flaps BMS bits** whenever a BMS feed
   pauses > 30 s (the unit falls back to physical sensors — by design).
   → the sensor-fault binary sensor now ignores BMS status bits and
   counts optional sensors (room, water return) only while they deliver
   values.

## Recovery behavior

- Connect test at config-flow time verified against the live unit
  (an earlier coordinator failure produced `setup_retry` with a precise
  reason string — observed live).
- Unavailability/recovery cycle covered by unit tests; live unit stayed
  reachable throughout, so cable-pull testing was not performed against
  production hardware. (See README troubleshooting for expected behavior.)

## Post-validation state

- Integration entry **loaded** and left in place.
- Unit restored to its pre-test state (fan 20 %, setpoint untouched at 15).
- Legacy YAML package left untouched — both run in parallel; migration of
  automations to the new entities is a follow-up (see final report).
