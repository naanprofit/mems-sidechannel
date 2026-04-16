# MEMS-Sidechannel

**Electromagnetic, acoustic, and optical side-channel attacks via MacBook sensors**

This project explores using Apple Silicon MacBook's built-in sensors (accelerometer, gyroscope, magnetometer, ambient light sensor, lid angle) for covert intelligence gathering.

## Overview

Apple Silicon MacBooks contain multiple sensors accessible via IOKit HID:
- **Bosch BMI286** 6-axis IMU (accelerometer + gyroscope)
- **Compass/Magnetometer** (1597 Hz - highest sample rate)
- **Ambient Light Sensor** (122-byte reports, multiple channels)
- **Lid Angle Sensor** (8-byte reports)

This project demonstrates these sensors can:

1. **Detect electromagnetic interference (EMI)** from power lines and electronics
2. **Detect drone/robot motor signatures** (see DRONE_SIGNATURES.md)
3. **Detect voice activity** (presence of speech, not content)
4. **Monitor physical presence** via vibrations
5. **Detect lighting conditions and LED PWM frequencies**
6. **Track lid state and subtle movements**

## Key Findings

| Capability | Viability | Sensor | Notes |
|------------|-----------|--------|-------|
| 50/60 Hz EMI Detection | **HIGH** | All | SNR 6.89 (accel), 2.91 (gyro) |
| Drone Motor Detection | **MEDIUM** | Compass | 400-800 Hz range |
| Voice Activity Detection | **MEDIUM** | IMU | Detects presence, not content |
| LED PWM Detection | **MEDIUM** | ALS | Identifies light sources |
| Speech Content | **LOW** | - | Sample rate too low |

## Sensors & Sample Rates

| Sensor | Usage ID | Page | Sample Rate | Nyquist Limit |
|--------|----------|------|-------------|---------------|
| Accelerometer | 3 | 0xFF00 | 797 Hz | 398 Hz |
| Gyroscope | 9 | 0xFF00 | 794 Hz | 397 Hz |
| Compass | 5 | 0xFF00 | 1597 Hz | **798 Hz** |
| ALS | 4 | 0xFF00 | Variable | - |
| Lid Angle | 138 | 0x0020 | On-change | - |

## Requirements

- Apple Silicon MacBook (M1/M2/M3/M4)
- macOS
- Root privileges (sudo)
- Go 1.21+ (for sensord-emi)
- Python 3.11+ with numpy, scipy, posix_ipc

## Installation

```bash
# Clone the modified sensor daemon (with compass + ALS support)
git clone https://github.com/naanprofit/mems-sidechannel
cd mems-sidechannel

# Or build sensord-emi from source (see /tmp/apple-silicon-accelerometer-mod)
# go build -o sensord-emi ./cmd/sensord

# Install Python dependencies
pip install numpy scipy posix_ipc
```

## Usage

### Start Sensor Daemon

```bash
# Basic mode
sudo ~/go/bin/sensord-emi

# Debug mode (shows all sensors including unknown)
sudo ~/go/bin/sensord-emi --debug
```

### EMI Detection

```bash
sudo python3 emi_detector.py
```

### High-Frequency Test (400-800 Hz via Compass)

```bash
sudo python3 compass_highfreq_test.py
```

### Ambient Light Analysis

```bash
sudo python3 als_analyzer.py
```

### Audio Capture

```bash
sudo python3 accel_mic.py --duration 10 --output recording.wav --analyze
```

## Files

| File | Description |
|------|-------------|
| `accel_mic.py` | Accelerometer audio capture and analysis |
| `emi_detector.py` | EMI frequency detection (all 3 IMU sensors) |
| `compass_highfreq_test.py` | High-frequency test (400-800 Hz) |
| `als_analyzer.py` | Ambient light sensor analysis |
| `FINDINGS.md` | Detailed EMI detection results |
| `DRONE_SIGNATURES.md` | Drone/robot motor frequency reference |

## Shared Memory Layout

The sensor daemon writes to POSIX shared memory:

| Segment | Type | Format |
|---------|------|--------|
| `/vib_detect_shm` | Ring buffer | 16B header + 8000×12B entries |
| `/vib_detect_shm_gyro` | Ring buffer | Same as above |
| `/vib_detect_shm_compass` | Ring buffer | Same as above |
| `/vib_detect_shm_als` | Snapshot | 8B header + 122B payload |
| `/vib_detect_shm_lid` | Snapshot | 8B header + 8B payload |

## Attack Vectors

### EMI Side-Channel
- Detect 50/60 Hz power line presence
- Monitor equipment state (motors, fans)
- Identify nearby electronics

### Acoustic Side-Channel
- Voice activity detection
- Keystroke timing analysis
- Physical presence monitoring

### Optical Side-Channel (ALS)
- LED PWM frequency detection (fingerprint lighting)
- Screen content inference via reflections
- Presence detection via light changes

### Drone/Robot Detection
- Consumer drones: 80-400 Hz
- FPV/attack drones: 400-750 Hz (compass only)
- Robot actuators: 50-300 Hz

See `DRONE_SIGNATURES.md` for detailed frequency tables.

## Security Implications

This attack:
- Runs silently with no user notification
- Only requires root access (no special entitlements)
- Can detect EMI, presence, light, and activity patterns
- Cannot directly exfiltrate speech content

## Countermeasures

1. Vibration-dampening laptop stands
2. Monitor for unexpected IOKit HID access
3. Physical separation from sensitive equipment
4. EMI shielding
5. Consistent lighting (defeats ALS fingerprinting)

## References

- "Gyrophone: Recognizing Speech from Gyroscope Signals" (Stanford, 2014)
- "AccelWord: Energy Efficient Hotword Detection through Accelerometer" (2015)
- "Side-Channel Attacks via MEMS Gyroscope Signals" (Various, 2016-2020)
- taigrr/apple-silicon-accelerometer - IOKit sensor access library

## License

MIT License - For security research and educational purposes only.

## Disclaimer

This tool is provided for security research and educational purposes. Using it to monitor others without consent may violate wiretapping laws. Always obtain proper authorization before conducting any monitoring activities.
