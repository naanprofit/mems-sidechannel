# MEMS-Sidechannel

**Electromagnetic and acoustic side-channel attacks via MacBook MEMS sensors**

This project explores using Apple Silicon MacBook's built-in MEMS sensors (accelerometer, gyroscope, and magnetometer) for covert intelligence gathering, including EMI detection and acoustic eavesdropping.

## Overview

Apple Silicon MacBooks contain a Bosch BMI286 6-axis IMU that can be accessed via IOKit HID. This project demonstrates that these sensors can:

1. **Detect electromagnetic interference (EMI)** from power lines and electronics
2. **Detect voice activity** (presence of speech, not content)
3. **Monitor physical presence** via vibrations
4. **Potentially enable keystroke timing analysis**

## Key Findings

| Capability | Viability | Notes |
|------------|-----------|-------|
| 50/60 Hz EMI Detection | **HIGH** | SNR 3.64 (accel), 3.12 (gyro) |
| Voice Activity Detection | **MEDIUM** | Detects presence, not content |
| Keystroke Timing | **MEDIUM** | Vibration patterns detectable |
| Speech Content | **LOW** | Sample rate too low for formants |

## Requirements

- Apple Silicon MacBook (M1/M2/M3/M4)
- macOS
- Root privileges (sudo)
- Go 1.26+ (for sensord)
- Python 3.11+ with numpy, scipy, posix_ipc

## Installation

```bash
# Install the sensor daemon
go install github.com/taigrr/apple-silicon-accelerometer/cmd/sensord@latest

# Install Python dependencies
pip install numpy scipy posix_ipc
```

## Usage

### Basic EMI Detection

```bash
# Terminal 1: Start sensor daemon
sudo sensord

# Terminal 2: Run EMI detector
sudo python3 emi_detector.py
```

### Audio Capture

```bash
# Terminal 1: Start sensor daemon
sudo sensord

# Terminal 2: Capture accelerometer "audio"
sudo python3 accel_mic.py --duration 10 --output recording.wav --analyze
```

## Files

| File | Description |
|------|-------------|
| `accel_mic.py` | Accelerometer audio capture and analysis |
| `emi_detector.py` | EMI frequency detection (50/60 Hz) |
| `FINDINGS.md` | Detailed analysis and results |
| `start_capture.sh` | Quick-start wrapper script |

## Technical Details

### Sensors Available

- **Accelerometer** (Usage 3): ~800 Hz sample rate
- **Gyroscope** (Usage 9): ~800 Hz sample rate  
- **Magnetometer** (Usage 5): Exists but not fully accessible
- **Ambient Light Sensor** (Usage 4): Available
- **Lid Angle Sensor** (Usage 138): Available

### Shared Memory Layout

The sensor daemon writes to POSIX shared memory:
- `/vib_detect_shm` - Accelerometer ring buffer
- `/vib_detect_shm_gyro` - Gyroscope ring buffer
- `/vib_detect_shm_compass` - Magnetometer (if available)

Ring buffer format: 16-byte header + 8000 entries × 12 bytes (3× int32)

## Limitations

- Sample rate (~800 Hz) limits audio capture to <400 Hz
- Cannot capture intelligible speech (formants at 300-3000 Hz)
- Requires root privileges
- Magnetometer not fully accessible via current IOKit method

## Security Implications

This attack:
- Runs silently with no user notification
- Only requires root access (no special entitlements)
- Can detect EMI, presence, and activity patterns
- Cannot directly exfiltrate speech content

## Countermeasures

1. Use vibration-dampening laptop stands
2. Monitor for unexpected IOKit HID access
3. Physical separation from sensitive equipment
4. EMI shielding

## References

- "Gyrophone: Recognizing Speech from Gyroscope Signals" (Stanford, 2014)
- "AccelWord: Energy Efficient Hotword Detection through Accelerometer" (2015)
- taigrr/apple-silicon-accelerometer - IOKit sensor access library

## License

MIT License - For security research and educational purposes only.

## Disclaimer

This tool is provided for security research and educational purposes. Using it to monitor others without consent may violate wiretapping laws. Always obtain proper authorization before conducting any monitoring activities.
