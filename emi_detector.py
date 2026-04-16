#!/usr/bin/env python3
"""
EMI Detection via Accelerometer/Gyroscope
==========================================

While the accelerometer isn't ideal for EMI, it CAN detect:
1. Motor vibrations (60 Hz from AC motors, fans)
2. Transformer hum (50/60 Hz)
3. Speaker/device vibrations from nearby electronics
4. Coil whine from power supplies

The GYROSCOPE might be more sensitive to EMI because:
- Gyros use vibrating structures that can couple with EM fields
- Some MEMS gyros have known EMI sensitivity (a security concern!)

This script tests both accel and gyro for EMI signatures.

Research: "Gyroscope-based EMI side-channel attack" papers show
that gyroscopes can pick up electromagnetic emanations from
nearby electronics, potentially leaking information.
"""

import mmap
import os
import struct
import sys
import time
import numpy as np
from pathlib import Path

# Shared memory names
SHM_ACCEL = "vib_detect_shm"
SHM_GYRO = "vib_detect_shm_gyro"
SHM_COMPASS = "vib_detect_shm_compass"  # NEW: Magnetometer for EMI
SHM_HEADER_SIZE = 16
SHM_ENTRY_SIZE = 12
SHM_RING_SIZE = 8000


def connect_shm(name: str):
    """Connect to shared memory."""
    try:
        import posix_ipc
        shm_path = "/" + name if not name.startswith("/") else name
        shm = posix_ipc.SharedMemory(shm_path)
        size = SHM_HEADER_SIZE + (SHM_RING_SIZE * SHM_ENTRY_SIZE)
        mm = mmap.mmap(shm.fd, size)
        return mm
    except Exception as e:
        print(f"Failed to connect to {name}: {e}")
        return None


def read_samples(mm, n_samples: int = 1000) -> tuple[list, int]:
    """Read samples from shared memory ring buffer."""
    mm.seek(0)
    header = mm.read(SHM_HEADER_SIZE)
    write_idx = struct.unpack('<I', header[0:4])[0]
    total = struct.unpack('<Q', header[4:12])[0]
    
    samples = []
    for i in range(min(n_samples, SHM_RING_SIZE)):
        pos = (write_idx - n_samples + i) % SHM_RING_SIZE
        if pos < 0:
            pos += SHM_RING_SIZE
        offset = SHM_HEADER_SIZE + (pos * SHM_ENTRY_SIZE)
        mm.seek(offset)
        data = mm.read(SHM_ENTRY_SIZE)
        x, y, z = struct.unpack('<iii', data)
        samples.append((x, y, z))
    
    return samples, total


def analyze_emi_frequencies(samples: list, sample_rate: float, label: str):
    """Analyze frequency content for EMI signatures."""
    if sample_rate <= 0:
        print(f"\n{label}: No data (0 Hz sample rate)")
        return None, None
    
    from scipy.fft import fft, fftfreq
    from scipy import signal
    
    # Extract magnitude
    magnitudes = np.array([np.sqrt(x*x + y*y + z*z) for x, y, z in samples])
    
    # Remove DC
    magnitudes = magnitudes - np.mean(magnitudes)
    
    if len(magnitudes) < 10:
        print(f"  Not enough samples for {label}")
        return
    
    # FFT
    N = len(magnitudes)
    yf = fft(magnitudes)
    xf = fftfreq(N, 1/sample_rate)[:N//2]
    power = 2.0/N * np.abs(yf[0:N//2])
    
    print(f"\n{label} Analysis:")
    print("-" * 50)
    
    # Look for specific EMI frequencies
    emi_freqs = {
        "50 Hz (EU mains)": (48, 52),
        "60 Hz (US mains)": (58, 62),
        "100 Hz (2nd harmonic EU)": (98, 102),
        "120 Hz (2nd harmonic US)": (118, 122),
        "Power line harmonics": (170, 190),  # 3rd harmonic region
    }
    
    print(f"Sample rate: {sample_rate:.1f} Hz")
    print(f"Frequency resolution: {sample_rate/N:.2f} Hz")
    print(f"Max detectable frequency: {sample_rate/2:.1f} Hz")
    print()
    
    for name, (low, high) in emi_freqs.items():
        if high <= sample_rate / 2:
            mask = (xf >= low) & (xf <= high)
            if np.any(mask):
                band_power = np.max(power[mask])
                avg_power = np.mean(power)
                snr = band_power / avg_power if avg_power > 0 else 0
                
                indicator = "**DETECTED**" if snr > 2.0 else ""
                print(f"  {name}: SNR = {snr:.2f} {indicator}")
        else:
            print(f"  {name}: Above Nyquist limit")
    
    # Find dominant frequencies
    peaks, _ = signal.find_peaks(power, height=np.max(power)*0.1)
    if len(peaks) > 0:
        print("\nDominant frequencies:")
        for peak in peaks[:10]:
            print(f"  {xf[peak]:.1f} Hz (power: {power[peak]:.4f})")
    
    return xf, power


def main():
    print("=" * 60)
    print("EMI DETECTOR - Accelerometer/Gyroscope Based")
    print("=" * 60)
    print()
    print("Checking for electromagnetic interference signatures...")
    print("Make sure 'sudo sensord' is running!")
    print()
    
    # Connect to sensors
    accel_mm = connect_shm(SHM_ACCEL)
    gyro_mm = connect_shm(SHM_GYRO)
    compass_mm = connect_shm(SHM_COMPASS)  # NEW
    
    if not accel_mm and not gyro_mm and not compass_mm:
        print("No sensors available.")
        print("Run: sudo ~/go/bin/sensord-emi --debug")
        sys.exit(1)
    
    if compass_mm:
        print("COMPASS/MAGNETOMETER DETECTED - Best for EMI!")
    else:
        print("No compass detected. Run 'sudo ~/go/bin/sensord-emi' for compass support.")
    
    # Calibrate sample rate
    print("Calibrating sample rate...")
    
    if accel_mm:
        _, start_total = read_samples(accel_mm, 1)
        time.sleep(1.0)
        _, end_total = read_samples(accel_mm, 1)
        accel_rate = end_total - start_total
        print(f"Accelerometer: {accel_rate} Hz")
    else:
        accel_rate = 0
    
    if gyro_mm:
        _, start_total = read_samples(gyro_mm, 1)
        time.sleep(1.0)
        _, end_total = read_samples(gyro_mm, 1)
        gyro_rate = end_total - start_total
        print(f"Gyroscope: {gyro_rate} Hz")
    else:
        gyro_rate = 0
    
    if compass_mm:
        _, start_total = read_samples(compass_mm, 1)
        time.sleep(1.0)
        _, end_total = read_samples(compass_mm, 1)
        compass_rate = end_total - start_total
        print(f"Compass/Magnetometer: {compass_rate} Hz")
    else:
        compass_rate = 0
    
    # Collect samples
    print("\nCollecting samples for analysis...")
    time.sleep(2)  # Wait for buffer to fill
    
    if accel_mm:
        accel_samples, _ = read_samples(accel_mm, min(2000, SHM_RING_SIZE))
        analyze_emi_frequencies(accel_samples, accel_rate, "ACCELEROMETER")
    
    if gyro_mm:
        gyro_samples, _ = read_samples(gyro_mm, min(2000, SHM_RING_SIZE))
        analyze_emi_frequencies(gyro_samples, gyro_rate, "GYROSCOPE")
    
    if compass_mm:
        compass_samples, _ = read_samples(compass_mm, min(2000, SHM_RING_SIZE))
        analyze_emi_frequencies(compass_samples, compass_rate, "COMPASS/MAGNETOMETER")
    
    print()
    print("=" * 60)
    print("EMI DETECTION NOTES")
    print("=" * 60)
    print("""
What this CAN detect:
- 50/60 Hz power line coupling (if sample rate > 120 Hz)
- Motor/fan vibrations
- Transformer hum
- Nearby speaker activity
- Coil whine from power supplies

What it CANNOT detect (with current setup):
- High-frequency EMI (RF, WiFi, cellular)
- Subtle emanations from CPUs/memory
- Encrypted signal content

For better EMI detection:
1. The COMPASS/MAGNETOMETER would be more sensitive to EM fields
   (but sensord doesn't expose it yet)
2. Higher sample rate accelerometer/gyro
3. External SDR dongle for RF spectrum analysis

EMI Intelligence Applications:
- Detect if electronic devices are powered on nearby
- Identify type of equipment from vibration signature
- Monitor power grid fluctuations (50/60 Hz variations)
- Detect when motors/fans start/stop
""")
    
    if accel_mm:
        accel_mm.close()
    if gyro_mm:
        gyro_mm.close()
    if compass_mm:
        compass_mm.close()


if __name__ == "__main__":
    main()
