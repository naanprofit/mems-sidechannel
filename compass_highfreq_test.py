#!/usr/bin/env python3
"""
High-Frequency EMI Detection Test (400-800 Hz)
==============================================

Tests the compass sensor's ability to detect frequencies
in the 400-800 Hz range - above what the accelerometer can see.

This is the range where:
- FPV drone motors operate (400-750 Hz)
- Small attack drone blade pass frequencies
- Higher motor harmonics
- Some switching power supply noise
"""

import mmap
import struct
import sys
import time
import numpy as np

try:
    import posix_ipc
    from scipy.fft import fft, fftfreq
    from scipy import signal
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install posix_ipc scipy numpy")
    sys.exit(1)

SHM_COMPASS = "vib_detect_shm_compass"
SHM_HEADER_SIZE = 16
SHM_ENTRY_SIZE = 12
SHM_RING_SIZE = 8000

def connect_shm(name: str):
    """Connect to shared memory."""
    try:
        shm_path = "/" + name if not name.startswith("/") else name
        shm = posix_ipc.SharedMemory(shm_path)
        size = SHM_HEADER_SIZE + (SHM_RING_SIZE * SHM_ENTRY_SIZE)
        mm = mmap.mmap(shm.fd, size)
        return mm
    except Exception as e:
        print(f"Failed to connect to compass: {e}")
        print("Make sure 'sudo ~/go/bin/sensord-emi' is running!")
        return None

def read_samples(mm, n_samples: int = 2000) -> tuple[list, int]:
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

def analyze_highfreq(samples: list, sample_rate: float, duration: float):
    """Analyze the 400-800 Hz range specifically."""
    
    # Extract magnitude
    magnitudes = np.array([np.sqrt(x*x + y*y + z*z) for x, y, z in samples])
    magnitudes = magnitudes - np.mean(magnitudes)  # Remove DC
    
    N = len(magnitudes)
    yf = fft(magnitudes)
    xf = fftfreq(N, 1/sample_rate)[:N//2]
    power = 2.0/N * np.abs(yf[0:N//2])
    
    # Focus on 400-800 Hz
    highfreq_mask = (xf >= 400) & (xf <= 800)
    lowfreq_mask = (xf >= 50) & (xf < 400)
    
    if not np.any(highfreq_mask):
        print("ERROR: Sample rate too low for 400-800 Hz analysis!")
        return
    
    print("\n" + "=" * 60)
    print("HIGH FREQUENCY ANALYSIS (400-800 Hz) - COMPASS ONLY")
    print("=" * 60)
    print(f"Sample rate: {sample_rate:.0f} Hz")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Samples: {N}")
    print(f"Frequency resolution: {sample_rate/N:.2f} Hz")
    print(f"Nyquist limit: {sample_rate/2:.0f} Hz")
    
    # Baseline noise in low frequency band
    baseline_power = np.mean(power[lowfreq_mask]) if np.any(lowfreq_mask) else 1.0
    
    print("\n--- SPECIFIC FREQUENCY BANDS ---")
    
    bands = [
        ("400-450 Hz (FPV idle)", 400, 450),
        ("450-500 Hz (FPV low throttle)", 450, 500),
        ("500-550 Hz (FPV mid throttle)", 500, 550),
        ("550-600 Hz (FPV high throttle)", 550, 600),
        ("600-650 Hz (Racing drone)", 600, 650),
        ("650-700 Hz (Attack drone full)", 650, 700),
        ("700-750 Hz (Max motor)", 700, 750),
        ("750-798 Hz (Near Nyquist)", 750, 798),
    ]
    
    detected_any = False
    for name, low, high in bands:
        if high > sample_rate / 2:
            print(f"  {name}: Above Nyquist limit")
            continue
        mask = (xf >= low) & (xf <= high)
        if np.any(mask):
            band_power = np.max(power[mask])
            snr = band_power / baseline_power if baseline_power > 0 else 0
            indicator = ""
            if snr > 3.0:
                indicator = " **STRONG**"
                detected_any = True
            elif snr > 2.0:
                indicator = " *detected*"
                detected_any = True
            print(f"  {name}: SNR = {snr:.2f}{indicator}")
    
    # Find peaks in 400-800 Hz range
    highfreq_power = power[highfreq_mask]
    highfreq_freqs = xf[highfreq_mask]
    
    print("\n--- TOP 10 PEAKS (400-800 Hz) ---")
    if len(highfreq_power) > 0:
        # Find peaks
        peaks, properties = signal.find_peaks(highfreq_power, height=np.max(highfreq_power)*0.05)
        if len(peaks) > 0:
            # Sort by power
            peak_powers = highfreq_power[peaks]
            sorted_idx = np.argsort(peak_powers)[::-1][:10]
            for i, idx in enumerate(sorted_idx):
                freq = highfreq_freqs[peaks[idx]]
                pwr = peak_powers[idx]
                snr = pwr / baseline_power
                print(f"  {i+1}. {freq:.1f} Hz (power: {pwr:.4f}, SNR: {snr:.2f})")
        else:
            print("  No significant peaks found in 400-800 Hz range")
    
    # Compare to low frequency
    print("\n--- COMPARISON ---")
    lowfreq_max = np.max(power[lowfreq_mask]) if np.any(lowfreq_mask) else 0
    highfreq_max = np.max(power[highfreq_mask]) if np.any(highfreq_mask) else 0
    
    print(f"  Max power 50-400 Hz: {lowfreq_max:.4f}")
    print(f"  Max power 400-800 Hz: {highfreq_max:.4f}")
    print(f"  Ratio: {highfreq_max/lowfreq_max:.2f}x" if lowfreq_max > 0 else "  Ratio: N/A")
    
    if detected_any:
        print("\n✅ HIGH-FREQUENCY SIGNALS DETECTED!")
    else:
        print("\n⚠️  No strong high-frequency signals in 400-800 Hz range")
        print("   Try: buzzing phone, electric toothbrush, small motor, drone video on speaker")
    
    return xf, power

def main():
    print("=" * 60)
    print("COMPASS HIGH-FREQUENCY TEST (400-800 Hz)")
    print("=" * 60)
    print()
    print("This tests detection ABOVE what accelerometer can see.")
    print("Make some noise in the 400-800 Hz range!")
    print()
    print("Suggestions:")
    print("  - Electric toothbrush")
    print("  - Small motor/fan at high speed")
    print("  - Phone vibration motor")
    print("  - Play drone audio on speaker")
    print("  - Buzzing/humming sounds")
    print()
    
    mm = connect_shm(SHM_COMPASS)
    if not mm:
        sys.exit(1)
    
    # Calibrate sample rate
    print("Calibrating compass sample rate...")
    _, start_total = read_samples(mm, 1)
    time.sleep(1.0)
    _, end_total = read_samples(mm, 1)
    sample_rate = end_total - start_total
    print(f"Compass sample rate: {sample_rate} Hz")
    
    if sample_rate < 1500:
        print("WARNING: Sample rate below expected 1597 Hz!")
    
    nyquist = sample_rate / 2
    print(f"Nyquist limit: {nyquist:.0f} Hz")
    
    if nyquist < 800:
        print(f"WARNING: Can only detect up to {nyquist:.0f} Hz")
    
    # Recording loop
    duration = 5.0
    print(f"\n>>> RECORDING {duration} seconds... MAKE NOISE NOW! <<<")
    print()
    
    # Wait for buffer to fill with fresh data
    time.sleep(duration)
    
    # Read samples
    n_samples = int(sample_rate * duration)
    n_samples = min(n_samples, SHM_RING_SIZE - 100)  # Leave some margin
    samples, _ = read_samples(mm, n_samples)
    
    # Analyze
    analyze_highfreq(samples, sample_rate, duration)
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    # Offer to repeat
    print("\nRun again to test different noise sources.")
    
    mm.close()

if __name__ == "__main__":
    main()
