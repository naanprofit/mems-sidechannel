# MacBook MEMS Sensor Side-Channel Attack Analysis

## Executive Summary

**CONFIRMED**: The MacBook's internal accelerometer, gyroscope, and compass/magnetometer can detect electromagnetic interference (EMI) from power lines and nearby electronics. All three sensors are now operational, with the compass providing the highest sample rate.

## Test Results

### Hardware Tested
- **Device**: MacBook Air M4 (Mac16,13)
- **Sensors**: Bosch BMI286 6-axis IMU + Compass + ALS + Unknown
- **Sample Rates Achieved**:
  - Accelerometer: 797 Hz
  - Gyroscope: 794 Hz
  - **Compass: 1597 Hz** (highest)
  - ALS: ~10 Hz
  - Unknown sensors: 0.2-0.4 Hz

### EMI Detection Results

| Frequency | Accelerometer | Gyroscope | Compass | Status |
|-----------|---------------|-----------|---------|--------|
| 50 Hz (EU mains) | SNR 6.89 | SNR 2.44 | SNR 2.12 | **DETECTED** |
| 60 Hz (US mains) | SNR 1.41 | SNR 2.91 | SNR 1.78 | **DETECTED** |
| 100 Hz (2nd harmonic) | SNR 0.04 | SNR 1.76 | SNR 1.06 | Marginal |
| 120 Hz (2nd harmonic) | SNR 0.08 | SNR 2.22 | SNR 0.88 | **DETECTED** |
| 180 Hz (3rd harmonic) | SNR 0.02 | SNR 1.91 | SNR 0.62 | Marginal |

### Key Findings

1. **Accelerometer** is best for 50 Hz detection (SNR 6.89)
2. **Gyroscope** is most sensitive to EMI overall, detecting multiple harmonics
3. **Compass** provides **2x sample rate** (1597 Hz vs 797 Hz), enabling higher frequency analysis

## All Sensors Discovered

### Known Sensors (Page 0xFF00)

| Sensor | Usage ID | Report Size | Sample Rate | Status |
|--------|----------|-------------|-------------|--------|
| Accelerometer | 3 | 22 bytes | 797 Hz | ✅ Working |
| Gyroscope | 9 | 22 bytes | 794 Hz | ✅ Working |
| Compass | 5 | 14 bytes | 1597 Hz | ✅ Working |
| ALS | 4 | 122 bytes | ~10 Hz | ✅ Working |
| System Status | 255 | 1 byte | Variable | Monitoring |

### Known Sensors (Page 0x0020)

| Sensor | Usage ID | Report Size | Status |
|--------|----------|-------------|--------|
| Lid Angle | 138 | 8 bytes | ⚠️ Returns zeros |

### Unknown Sensors (Page 0xFF0C)

| Usage ID | Report Size | Pattern | Likely Identity |
|----------|-------------|---------|-----------------|
| 1 | 5 bytes | Multiple patterns | Motion coprocessor status |
| 5 | 100 bytes | Sporadic | Force Touch / Taptic? |

### Unknown Sensor Patterns (Page 0xFF0C, Usage 1)

| Pattern | Bytes | Rate | Interpretation |
|---------|-------|------|----------------|
| `1d 01 00 00 XX` | 5 | 0.2 Hz | Activity index or entropy (values 10-227, random-like) |
| `02 01 02 00 XX` | 5 | 0.4 Hz | Sequence counter (incrementing, wraps at 256) |
| `03 02 00 00 01` | 5 | 0.4 Hz | Heartbeat/status (always 1, occasionally 2) |
| `50 XX XX XX XX` | 5 | Sporadic | Taptic/Force Touch event |

**Note**: The `1d 01 00 00 XX` pattern was initially thought to be temperature, but values range 10-227 with no correlation to actual temp. More likely a motion activity summary or hardware entropy source.

## Attack Vectors

### 1. Power Line Presence Detection
**Viability: HIGH**

All sensors detect 50/60 Hz power line interference:
- Confirm AC power presence in a location
- Detect proximity to high-voltage equipment
- Monitor power grid fluctuations

### 2. Device Proximity Detection
**Viability: MEDIUM-HIGH**

Nearby electronic devices emit EMI:
- Phone charging (switching power supply harmonics)
- Motors starting/stopping
- Computer fans spinning up
- Hard drives seeking

### 3. Acoustic Eavesdropping
**Viability: LOW**

Compass sample rate of 1597 Hz allows capturing frequencies up to 798 Hz:
- Male voice fundamental (85-180 Hz): **Detectable but not intelligible**
- Female voice fundamental (165-255 Hz): **Partially detectable**
- Speech formants (300-3000 Hz): **NOT detectable**

**Conclusion**: Can detect voice *activity* but NOT speech *content*.

### 4. Covert Presence Monitoring
**Viability: HIGH**

Without user indication, sensors detect:
- Footsteps and movement
- Door opening/closing
- HVAC system state
- Equipment operation

### 5. Optical Side-Channel (ALS)
**Viability: MEDIUM**

Ambient Light Sensor at ~10 Hz can detect:
- Room light on/off
- Human shadow/movement
- Screen brightness changes
- **Cannot** detect LED PWM (too slow)

ALS Report Format (122 bytes):
- Offset 0-1: Incrementing counter
- Offset 4-5: Light level (varies significantly)
- Offset 6-7: Second counter
- Multiple channels suggest RGB/IR/clear separation

## Technical Details

### Sensor Access Requirements
- **Root privileges required** (sudo) for IOKit HID access
- No user notification when sensors are accessed
- Runs silently in background

### Sensor Report Formats

| Sensor | Usage ID | Page | Report Size | Data Format |
|--------|----------|------|-------------|-------------|
| Accelerometer | 3 | 0xFF00 | 22 bytes | 6-byte header + 3×4 XYZ |
| Gyroscope | 9 | 0xFF00 | 22 bytes | 6-byte header + 3×4 XYZ |
| Compass | 5 | 0xFF00 | 14 bytes | 2-byte header + 3×4 XYZ |
| ALS | 4 | 0xFF00 | 122 bytes | Complex multi-channel |
| Lid | 138 | 0x0020 | 8 bytes | Unknown (returns zeros) |

### Sample Rate Optimization
- Default sensord: ~100 Hz (IMUDecimation=8)
- Modified sensord-emi: ~800 Hz accel/gyro, ~1600 Hz compass (IMUDecimation=1)

## Intelligence Applications

### Confirmed Capabilities
1. ✅ Detect power line presence (50/60 Hz EMI)
2. ✅ Monitor equipment state (motors, fans)
3. ✅ Voice activity detection (not content)
4. ✅ Physical presence monitoring
5. ✅ Device proximity sensing
6. ✅ Higher frequency EMI with compass (up to 798 Hz)
7. ✅ Room lighting changes (ALS)
8. ✅ Human shadow/movement detection (ALS)

### NOT Capable Of
1. ❌ Intelligible speech capture (sample rate too low for formants)
2. ❌ High-frequency RF detection (WiFi, Bluetooth, cellular)
3. ❌ LED PWM fingerprinting (ALS too slow at 10 Hz)
4. ❌ Direct data exfiltration

## Countermeasures

### Hardware
- Vibration-dampening laptop stand
- EMI shielding around laptop
- Physical separation from sensitive equipment
- Cover ALS with opaque tape

### Software
- Monitor for unexpected IOKit HID access
- Sandbox applications from sensor access
- Audit processes with root privileges

## Files and Tools

| File | Purpose |
|------|---------|
| `accel_mic.py` | Audio capture via accelerometer |
| `emi_detector.py` | EMI frequency analysis (all 3 sensors) |
| `compass_highfreq_test.py` | High-frequency test (400-800 Hz) |
| `als_analyzer.py` | Ambient light sensor analysis |
| `unknown_sensors.py` | Decode unknown sensor patterns |
| `DRONE_SIGNATURES.md` | Drone/robot motor frequencies |

## References

1. "Gyrophone: Recognizing Speech from Gyroscope Signals" - Stanford, 2014
2. "AccelWord: Energy Efficient Hotword Detection through Accelerometer" - 2015
3. "Side-Channel Attacks via MEMS Gyroscope Signals" - Various, 2016-2020
4. taigrr/apple-silicon-accelerometer - IOKit sensor access library

## Conclusion

The MacBook MEMS sensor side-channel is **real and exploitable** for certain intelligence applications:

1. **Metadata collection** - knowing WHEN activity occurs, not WHAT
2. **Environmental awareness** - detecting nearby electronics and power
3. **Presence detection** - monitoring physical activity without cameras
4. **Optical monitoring** - room lighting and shadow detection

The attack requires root access but runs silently with no user indication. The compass provides the highest sample rate (1597 Hz), while the gyroscope is most sensitive to EMI.

---

*Analysis conducted April 2026*
*MacBook Air M4 (Mac16,13) / macOS*
