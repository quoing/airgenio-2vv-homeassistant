# Ground Truth: 2VV VENUS AirGENIO Modbus Register Map

> Single source of truth for the `airgenio_2vv` integration. Compiled from the
> official 2VV "AirGENIO Modbus RTU/TCP guide" (doc 02-03-20 v1, 64 pages) and
> verified against a live VENUS AirGENIO Comfort (HRV-30EC-E-74-AG) unit
> running via Home Assistant `modbus` YAML since 2026-05.
>
> **Verified** = value read/written on the real unit and cross-checked against
> an independent reference (panel display, external sensor, or documented
> behavior). **Documented** = present in the official register spec but not
> independently exercised on this unit.

## 1. Addressing convention

- The 2VV documentation uses **PLC BASE1** (1-based) addresses.
- On the wire, Modbus is 0-based: **`wire = doc − 1`**. *(Verified 2026-05-25
  by measurement; also confirmed by 2VV's own IC guide describing the share
  block as 0-based.)*
- **All addresses in this document and in `const.py` are DOC addresses**
  (as printed in the 2VV manual). The integration's Modbus client subtracts 1
  in exactly one place.

## 2. Connection

| Parameter | Default (2VV) | Notes |
|---|---|---|
| Transport | Modbus TCP, port 502 | RTU (RS-485 9600 8O1) exists on COMFORT module-B; TCP only on SUPERIOR/IC3/SC module-A boards |
| Unit/slave id | 1 | configurable 1-247 via doc 25021 |
| Polling | unit tolerates 30 s scan; local install uses `delay: 2`, `timeout: 5`, `message_wait_milliseconds: 30` | conservative pacing recommended |

- Function codes: input registers FC04; holding registers FC03 read / FC06,
  FC16 write.

## 3. Temperature scaling

- All temperature registers hold **°C × 10** (uint16 on the wire; readings can
  be negative in winter → interpret as **int16 two's complement** when
  reading). *(×10 verified 2026-05-25: raw 253 = 25.3 °C on panel.)*
- BMS write registers (23000/23002) take **°C × 10** as well ("write
  temperature *10" per manual p. 63). Negative values for BMS writes are an
  open question (see open-questions.md #3).
- Airflow registers are in **‰ (per mille), 0–1000** = 0-100 % fan power.

## 4. INPUT registers (FC04, read-only) — STATUS block

Doc addresses. All **Verified** on the live unit unless noted.

| Doc | Name | Type | Notes |
|---|---|---|---|
| 18000 | Unit global status (bitfield) | uint16 | bit0 OFF/ON · bit1 AutoHeat · bit2 AutoFlow · bit3 NightReduction · bit4 Timeswitch · bit5 Cooldown · bit6 WaterHeater antifreeze · bit7 waiting for hot water · bit8 SummerHeat (0=winter,1=summer) · bit9 OpenDoor · bit10 DoorAfterRunning · bit11 HeaterUnderPower · bit12 Savana Day/Night |
| 18001 | Software error (bitfield) | uint16 | bit0 SwFanError · bit1 SwFanError1 · bit2 SwFilterError · bit3 SwFilterWarning · bit4 SwHeaterError · bit5 SwDXError · bit6 SwDXDefrost · bit7 **SwGlobalError** · bit8 CfgFileError · bit9 IBUSGatewayError · bit10 Alarm temp room |
| 18003 | Sensor status (bitfield) | uint16 | bit0 TempEXT1St · bit1 TempEXT3St · bit2 TempINT1St · bit3 TempWOutSt · bit4 TempRoomSt · bit5 OutsideTempSensorBmsSt · bit6 RoomTempSensorBmsSt · bit7 SensorFlowAlarmSt (0=OK, 1=ERROR) |
| 18004 | Input status (bitfield) | uint16 | DI states + tacho bits (documented) |
| 18005 | Output status (bitfield) | uint16 | bit0/1 Heat1/Heat2 · bit2 Run indication · bit3 Error · **bit4 EXCHANGER_COOL/HEAT** · bit5 Water pump · **bit6 Damper** (⚠ preheater damper flap — this unit has NO physical summer bypass) |
| 18006 | AirFlowFanManual | uint16 ‰ | actual fan power, 0–1000 ‰ |
| 18007 | TempEXT1 — Outside air | int16 ×10 | physical intake sensor (known to read high on some installs — sensor placement, not scaling) |
| 18008 | TempEXT3 — Outlet air | int16 ×10 | supply air after the exchanger |
| 18009 | TempINT1 — Inlet air | int16 ×10 | extract air from the building |
| 18010 | TempWOut — Water return | int16 ×10 | only with water heater option |
| 18011 | TempRoom — Room | int16 ×10 | ⚠ if the CT-ROOM sensor is physically not connected the register returns a sentinel (observed 65097 ≈ −43.9 °C) — treat values < −40 °C as "sensor not connected" → entity unavailable |
| 18012 | SensorFlowAlarm | uint16 0/1 | |
| 18013 | PowerHeater | uint16 % | preheater output 0-100 % |
| 18014 | TempOutsideBMS (readback) | int16 ×10 | echoes value written to 23002 |
| 18015 | RoomBMS (readback) | int16 ×10 | echoes value written to 23000 |
| 18016 | FilterPercent | uint16 % | filter clogging 0-100 % (timer-based, doc 25019/25020) |
| 18019 | Temperature Setpoint (panel) | uint16 | control panel setpoint readback (documented) |

## 5. HOLDING registers — SHARE block (FC03/06, R/W, user-level control)

| Doc | Name | R/W | Values | Status |
|---|---|---|---|---|
| 21000 | Language | R/W | 0-10 enum | documented, DO NOT expose |
| 21001 | SwitchON | R/W | 0=OFF, 1=ON | **Verified write + readback** (live `switch.rekuperace_zapnuto`) |
| 21002 | AirFlowManual | R/W | ‰ of fan power (MANUAL mode); factory range per 10110-10119 | **Verified write** (fan speed) |
| 21003 | Temperature setpoint | R/W | °C, plain (range depends on selected sensor: supply 15-45, extract/room 15-30) | **Verified read**; ⚠ write is ACKed but IGNORED on the reference unit while 25033=0 (see open-questions #8). Setpoint is °C ×1 (not ×10) |
| 21004 | TimeSwGlobalEnable | R/W | 0/1 | documented |
| 21005-21008 | TimeSw mode/flow/temp/onoff | R | read-only timer state | documented |
| 21009 | BoostMode / DAY-NIGHT | R/W | 0/1 — on SC controls this is Boost; on this HRV it switches DAY/NIGHT profile, NOT free-cooling | **Verified write**; semantics per install ambiguous → expose as documented "Boost / Day-Night" switch, see open-questions #2 |
| 21016 | FilterClogedTimerReset | R/W | write 1 = reset filter timer | documented (official reset mechanism) |
| 21024 | ACR_ManualHeat | R/W | 0-100 % heater power (manual heat mode) | documented, air-curtain oriented |
| 21025 | TimeSwHeat | R/W | 0-100 | documented |
| 21027 | Temperature Night | R/W | 5-30 °C | documented |

## 6. HOLDING registers — SERVICE block (FC03/06, configuration)

| Doc | Name | Values | Status |
|---|---|---|---|
| 20044 | OutsideTempSensorBMS enable | 0/1 | **Verified** (=1 on live unit, BMS feed active) |
| 20053 | SummerHeatEnable | 0/1 | documented |
| 20054/20055 | WinterMonthStart/Stop | 1-12 | documented |
| 20056 | SummerTempHeaterEnable | 10-20 °C | documented |
| 20057 | AutoSpeedControlEnable | 0/1 | **Verified** (used by live install) |
| 20058 | AutoSpeedControlDeltaT | 1-5 K | **Verified** (used by live install) |
| 20059 | NightTempReductionEnable | 0/1 | documented |
| 20060 | NightTempReductionSetpointShift | −1..−5 | documented |
| 20061-20064 | Night start/stop hour/minute | | documented |
| 20065-20074 | Door contact settings | | air curtain oriented, not exposed |

## 7. HOLDING registers — SERVICE HARD block

| Doc | Name | Values | Status |
|---|---|---|---|
| 25000 | Ventilation mode | MANUAL / CAV / DCV / VAV (unit-dependent) | **Verified read** (live install polls it); exact enum values not in the AC-oriented PDF → v1.0 read-only diagnostic, see open-questions #1 |
| 25005 | Postheat_2_external | 0 none / 1 electric / 2 water / 3 wco / 4 DX | documented |
| 25009 | TempSensorSelection | 0 supply / 1 extract / 2 room / 3 thermostat / 4 Room BMS | **Verified write** (=4 on live unit). ⚠ PDF table caps max at 2 but its own Info text and the official 2VV BMS example use 3/4 |
| 25019 | FilterWorkingHours | 0-3000 h | documented |
| 25020 | FilterMaxHours | 200-3000 h (default 1440) | documented |
| 25021 | Modbus address | 1-247 | documented, not exposed |
| 25022/25023 | Modbus baudrate/parity | | documented, not exposed |
| 25033 | TemperatureControlMode | 0 manual / 1 automatic | **Verified write** (=1 on live unit) |
| 25042-25048 | Slave units config | | air curtain oriented |
| 25077 | Automatic fan speed control | 0/1 | ⚠ Reference unit REJECTS READS (Modbus exc. 2, observed 2026-08-09); register exists only in 2VV's worked examples, not in the PDF tables. Treated as unsupported when rejected (open-questions #9) |

## 8. HOLDING registers — BMS TEMP SENSORS block (FC03/06)

| Doc | Name | R/W | Notes |
|---|---|---|---|
| 23000 | RoomBms | W | room temperature ×10; **must be refreshed < 30 s** or unit falls back to physical sensor. **Verified write + readback via 18015** |
| 23001 | RoomBms-Status | R | sensor status |
| 23002 | OutsideBms | W | outside temperature ×10; same < 30 s refresh rule. **Verified write + readback via 18014** |
| 23003 | OutsideBms-Status | R | sensor status |

**Official 2VV set-once sequence** ("Automatic fan and temperature control +
BMS outside temperature sensor"):

```
25033 = 1   automatic heat control
25077 = 1   automatic fan speed control
25009 = 2   ROOM sensor  (or 4 = Room BMS when feeding room temp via 23000)
20044 = 1   enable BMS outside sensor
then write 23002 (and 23000) at least every 30 s
```

## 9. Other documented blocks (not exposed in v1.0)

- **INFO 16008-16069** (FC04): IP/mask/gateway/MAC, FW versions, DHCP,
  BACnet port. Used only in diagnostics dump. ⚠ INFO IP registers may report
  a stale DHCP address (observed: register says .111, unit reachable on .207).
- **TIME 17000-17006, TIME DRIVER 17000-17009** (RTC).
- **TIME SWITCH WEEK 27000-27335, TIME SWITCH YEAR 28000-28080** (schedules).
- **ERROR LOG AC 30000-30024** (last-error snapshot incl. temps + status).
- **NETWORK 26000-26013** (write side of IP config — NEVER write).
- **NORDIC SERVICE 43000-43025** (valve/door/damper service params).

## 10. Semantics & behavior notes (verified on live HRV)

1. **No physical summer bypass damper.** VENUS Comfort = fan + exchanger +
   filter + condensate + preheater. "Night ventilation" (panel MENU 16) =
   supply fan only, extract off → overpressure free-cooling. Status bit6
   "Damper" is the preheater flap.
2. **Night ventilation cannot be triggered via Modbus.** MENU numbers 14-17
   are panel menus, not register values. Register 25000 holds only
   MANUAL/CAV/DCV/VAV. No "SummerNightCooling" register exists. The unit
   stops free-cooling when extract ≤ supply (two physical sensors, no BMS
   override).
3. **BMS feed is consumed only by the automatic control logic** (25033=1,
   25077=1 and sensor selection 25009 pointing at a BMS source). In pure
   manual mode the unit ignores BMS temperatures (readback stays 0).
4. **A new Modbus TCP connection requires nothing special on the unit**, but
   HA's YAML modbus hub needed a full restart — irrelevant for this
   integration (own client).
5. **Write pacing:** unit is a small PLC; keep ≤ ~30 writes/min, sequential,
   with ~30 ms gaps (matches `message_wait_milliseconds: 30` in the proven
   YAML config).
6. **Filter**: FilterPercent (18016) is derived from working hours
   (25019/25020). Reset officially via 21016 (share) after filter change.

## 11. Register → entity mapping (target for v1.0)

| Entity | Platform | Register(s) | R/W |
|---|---|---|---|
| Fan (power + on/off) | fan | 21001 SwitchON, 21002 AirFlowManual, 18006 actual | R/W |
| Temperature setpoint | number | 21003 | R/W |
| Outside temperature | sensor | 18007 | R |
| Supply temperature | sensor | 18008 | R |
| Extract temperature | sensor | 18009 | R |
| Room temperature | sensor | 18011 | R (unavailable if sentinel) |
| Water return temperature | sensor | 18010 | R (only if water heater present) |
| Fan power actual | sensor | 18006 | R |
| Preheater power | sensor | 18013 | R |
| Filter clogging | sensor | 18016 | R |
| Heat-recovery efficiency | sensor | computed (18007/18008/18009) | R |
| BMS outside readback | sensor (diagnostic) | 18014 | R |
| BMS room readback | sensor (diagnostic) | 18015 | R |
| Global error | binary_sensor | 18001 bit7 | R |
| Filter warning/error | binary_sensor | 18001 bit2|bit3 | R |
| Fan error | binary_sensor | 18001 bit0|bit1 | R |
| Preheater active | binary_sensor | 18013 > 0 | R |
| Summer mode | binary_sensor (diagnostic) | 18000 bit8 | R |
| Night reduction active | binary_sensor (diagnostic) | 18000 bit3 | R |
| Sensor fault | binary_sensor (diagnostic) | 18003 != 0 | R |
| Boost / Day-Night | switch | 21009 | R/W |
| Filter reset | button | 21016 (write 1) | W |
| Temperature control mode | select (config) | 25033 manual/automatic | R/W |
| Auto fan speed | switch (config) | 25077 | R/W |
| Temp sensor selection | select (config) | 25009 | R/W |
| BMS outside feed enable | switch (config) | 20044 | R/W |
| BMS outside temperature push | number (config, optional) | 23002 | W |
| BMS room temperature push | number (config, optional) | 23000 | W |
| Status bitfields | diagnostics dump | 18000/18001/18003/18004/18005 + INFO | R |
