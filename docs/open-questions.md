# Open Questions

Items where the official documentation is incomplete or ambiguous. Per the
project safety rule, uncertain registers are read-only or omitted in v1.0 —
we never guess write values.

## 1. Register 25000 — ventilation mode enum values

The AC-oriented PDF names the modes (MANUAL / CAV / DCV / VAV) via the
AirFlowManual description but does not print the numeric enum for 25000.
The live unit runs in MANUAL. → v1.0: exposed as a **read-only diagnostic
sensor** with raw value; no select entity until the enum is confirmed from
the 2VV HRU XLS or empirically.

## 2. Register 21009 — Boost vs DAY/NIGHT semantics

The SHARE table calls it "BoostMode / DAY-NIGHT mode (SC controls)". On the
reference VENUS Comfort HRV it switches the DAY/NIGHT ventilation profile
(reduced speed + setpoint shift), not a boost ramp. → v1.0: exposed as a
switch named "Day/night mode" (translation notes explain the dual meaning).
No separate "boost" entity is created to avoid implying behavior the unit
may not have.

## 3. Negative temperatures in BMS writes (23000/23002)

Manual says "write temperature *10" without specifying signedness. Winter
sub-zero values would need two's-complement encoding (e.g. −5.0 °C → 65486)
if the register is consumed as int16 — unconfirmed. → v1.0: the optional BMS
push numbers clamp at 0.0 °C minimum and log a warning; documented in README
"Known limitations". (Readback registers 18014/18015 are decoded as int16.)

## 4. Setpoint scaling asymmetry (21003)

Status temperatures are ×10, but the setpoint 21003 is written in plain °C
(verified on the live unit: writing 22 yields 22 °C on the panel). The 2VV
COMFORT example ("21003 - set to 22 for setpoint temp. 22°C") confirms plain
°C. Kept as verified fact; noted here because the asymmetry is surprising.

## 5. TempRoom sentinel value

With no CT-ROOM sensor connected, 18011 returns ~65097 (would decode to
−43.9 °C). We treat any decoded value below −40 °C (the documented sensor
minimum) as "not connected" → entity unavailable. The exact sentinel
constant is not documented by 2VV.

## 6. Register 25077 (automatic fan speed) not in the AC PDF tables

It appears in 2VV's own worked examples (SUPERIOR/SC BMS examples) and is
accepted by the live unit, but the PDF's SERVICE HARD table ends at 25048.
Treated as verified-by-example + live use. The HRU-specific XLS would
confirm the full SERVICE HARD range.

## 8. Setpoint writes (21003) silently ignored (observed 2026-08-09)

On the reference unit, FC06 writes to 21003 are ACKed but the register
keeps its value (probed at +0.05…+2 s). The unit runs with
TemperatureControlMode 25033 = 0 (manual heat control); the setpoint is
likely only writable with automatic control active — the 2VV COMFORT
example that writes 21003 also sets 25033 = 1 first. Not verified by
flipping 25033 (would change the reference unit's control mode). The
number entity surfaces the rejection honestly via read-back verification.

## 9. Register 25077 read-rejected on the reference unit

Reading 25077 returns Modbus exception 2 (IllegalDataAddress) although
2VV's own BMS example writes it. The integration treats it (and any other
config register the unit rejects) as unsupported → entity unavailable.
Whether a *write* would be accepted is untested — never write registers
whose read the unit refuses.

## 7. Filter reset path

Two mechanisms exist: 21016 FilterClogedTimerReset (share, documented for all
products) and 25019 FilterWorkingHours = 0 (service hard). v1.0 uses 21016
only. Read-back verification: 18016 FilterPercent should drop after reset.
