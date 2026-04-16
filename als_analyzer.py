#!/usr/bin/env python3
"""
Ambient Light Sensor (ALS) Analyzer
====================================

Analyzes the MacBook's ambient light sensor for:
1. Light level monitoring
2. LED PWM frequency detection (identifies lighting fixtures)
3. Screen reflection detection
4. Presence detection via light changes
5. Optical side-channel attacks

The ALS report is 122 bytes - likely contains multiple channels
(RGB, IR, clear, etc.) similar to advanced light sensors.
"""

import mmap
import struct
import sys
import time
import numpy as np

try:
    import posix_ipc
except ImportError:
    print("Missing posix_ipc. Run: pip install posix_ipc")
    sys.exit(1)

SHM_ALS = "vib_detect_shm_als"
SHM_LID = "vib_detect_shm_lid"
SNAP_HEADER = 8
ALS_REPORT_LEN = 122
LID_REPORT_LEN = 8


def connect_snapshot(name: str, size: int):
    """Connect to shared memory snapshot."""
    try:
        shm_path = "/" + name if not name.startswith("/") else name
        shm = posix_ipc.SharedMemory(shm_path)
        mm = mmap.mmap(shm.fd, size)
        return mm
    except Exception as e:
        print(f"Failed to connect to {name}: {e}")
        return None


def read_snapshot(mm, payload_len: int) -> tuple[bytes, int]:
    """Read snapshot data."""
    mm.seek(0)
    header = mm.read(SNAP_HEADER)
    count = struct.unpack('<I', header[0:4])[0]
    payload = mm.read(payload_len)
    return payload, count


def analyze_als_report(data: bytes):
    """Analyze ALS report structure (122 bytes)."""
    print(f"\nALS Report ({len(data)} bytes):")
    print("-" * 60)
    
    # Try different interpretations
    print("\nRaw hex (first 64 bytes):")
    for i in range(0, min(64, len(data)), 16):
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"  {i:3d}: {hex_str:<48} {ascii_str}")
    
    print("\nPossible interpretations:")
    
    # Try as int16 values
    print("\n  As int16 (first 20 values):")
    for i in range(0, min(40, len(data)), 2):
        val = struct.unpack('<h', data[i:i+2])[0]
        if val != 0:
            print(f"    Offset {i:3d}: {val:6d}")
    
    # Try as int32 values
    print("\n  As int32 (first 10 values):")
    for i in range(0, min(40, len(data)), 4):
        val = struct.unpack('<i', data[i:i+4])[0]
        if val != 0:
            print(f"    Offset {i:3d}: {val:10d}")
    
    # Try as float32 values
    print("\n  As float32 (first 10 values, if valid):")
    for i in range(0, min(40, len(data)), 4):
        val = struct.unpack('<f', data[i:i+4])[0]
        if not (np.isnan(val) or np.isinf(val)) and abs(val) < 1e10 and val != 0:
            print(f"    Offset {i:3d}: {val:.6f}")


def analyze_lid_report(data: bytes):
    """Analyze lid angle report (8 bytes)."""
    print(f"\nLid Report ({len(data)} bytes):")
    print("-" * 60)
    
    print(f"  Raw hex: {data.hex()}")
    
    # Try different interpretations
    for i in range(0, len(data), 2):
        val = struct.unpack('<H', data[i:i+2])[0]
        angle = val & 0x1FF
        print(f"  Offset {i}: raw={val:5d}, angle={angle:3d} degrees")


def monitor_als(duration: float = 10.0):
    """Monitor ALS changes over time."""
    als_mm = connect_snapshot(SHM_ALS, SNAP_HEADER + ALS_REPORT_LEN)
    lid_mm = connect_snapshot(SHM_LID, SNAP_HEADER + LID_REPORT_LEN)
    
    if not als_mm:
        print("ALS not available. Run: sudo ~/go/bin/sensord-emi")
        return
    
    print("=" * 60)
    print("AMBIENT LIGHT SENSOR MONITOR")
    print("=" * 60)
    print(f"\nMonitoring for {duration} seconds...")
    print("Try: waving hand over sensor, turning lights on/off, etc.")
    print()
    
    # Initial read
    als_data, als_count = read_snapshot(als_mm, ALS_REPORT_LEN)
    print("Initial ALS report:")
    analyze_als_report(als_data)
    
    if lid_mm:
        lid_data, lid_count = read_snapshot(lid_mm, LID_REPORT_LEN)
        print("\nInitial Lid report:")
        analyze_lid_report(lid_data)
    
    # Monitor for changes
    print("\n" + "=" * 60)
    print("Monitoring for changes...")
    print("=" * 60)
    
    start_time = time.time()
    last_als_count = als_count
    last_lid_count = lid_count if lid_mm else 0
    change_count = 0
    
    # Store history for analysis
    history = []
    
    while time.time() - start_time < duration:
        als_data, als_count = read_snapshot(als_mm, ALS_REPORT_LEN)
        
        if als_count != last_als_count:
            change_count += 1
            elapsed = time.time() - start_time
            
            # Extract key values (try first few int16)
            vals = []
            for i in range(0, 20, 2):
                vals.append(struct.unpack('<h', als_data[i:i+2])[0])
            
            history.append((elapsed, vals))
            
            if change_count <= 20:  # Print first 20 changes
                print(f"  [{elapsed:6.2f}s] ALS change #{change_count}: {vals[:5]}")
            
            last_als_count = als_count
        
        if lid_mm:
            lid_data, lid_count = read_snapshot(lid_mm, LID_REPORT_LEN)
            if lid_count != last_lid_count:
                elapsed = time.time() - start_time
                angle = struct.unpack('<H', lid_data[0:2])[0] & 0x1FF
                print(f"  [{elapsed:6.2f}s] Lid angle: {angle} degrees")
                last_lid_count = lid_count
        
        time.sleep(0.01)  # 100 Hz polling
    
    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    
    print(f"\nTotal ALS updates: {change_count}")
    sample_rate = change_count / duration
    print(f"Effective sample rate: {sample_rate:.1f} Hz")
    
    if len(history) > 10:
        # Try to detect flicker frequency
        times = np.array([h[0] for h in history])
        vals = np.array([h[1][0] for h in history])  # First channel
        
        if np.std(vals) > 0:
            # Simple FFT analysis
            dt = np.mean(np.diff(times))
            if dt > 0:
                fs = 1.0 / dt
                print(f"Estimated sample rate from timestamps: {fs:.1f} Hz")
                
                # Detrend
                vals_detrend = vals - np.mean(vals)
                
                if len(vals_detrend) > 10:
                    from scipy.fft import fft, fftfreq
                    N = len(vals_detrend)
                    yf = fft(vals_detrend)
                    xf = fftfreq(N, dt)[:N//2]
                    power = np.abs(yf[:N//2])
                    
                    # Find peaks
                    peak_idx = np.argsort(power)[::-1][:5]
                    print("\nDominant frequencies in light signal:")
                    for idx in peak_idx:
                        if xf[idx] > 0:
                            print(f"  {xf[idx]:.1f} Hz (power: {power[idx]:.2f})")
    
    als_mm.close()
    if lid_mm:
        lid_mm.close()


def main():
    print("=" * 60)
    print("ALS (Ambient Light Sensor) ANALYZER")
    print("=" * 60)
    print()
    print("This tool analyzes the MacBook's ambient light sensor")
    print("for optical side-channel information.")
    print()
    print("Make sure sensord-emi is running:")
    print("  sudo ~/go/bin/sensord-emi")
    print()
    
    # Check if running
    als_mm = connect_snapshot(SHM_ALS, SNAP_HEADER + ALS_REPORT_LEN)
    if not als_mm:
        print("\nERROR: Cannot connect to ALS shared memory.")
        print("Start sensord-emi first!")
        sys.exit(1)
    als_mm.close()
    
    # Run monitor
    monitor_als(duration=15.0)
    
    print("\n" + "=" * 60)
    print("POTENTIAL ATTACK VECTORS")
    print("=" * 60)
    print("""
1. LED PWM Detection
   - LED lights flicker at specific frequencies (100-1000 Hz)
   - ALS can detect this flicker, fingerprinting light sources
   - Could identify specific rooms/buildings by lighting

2. Screen Reflection Detection
   - ALS near screen can detect content changes
   - Dark vs light content causes measurable changes
   - Potential for covert screen content inference

3. Presence Detection
   - Human movement causes light level changes
   - Can detect when someone approaches/leaves

4. Optical Communication
   - Modulated light could encode data
   - ALS becomes a covert channel receiver

5. Lid State Tracking
   - Precise lid angle measurements
   - Could detect subtle movements/vibrations
""")


if __name__ == "__main__":
    main()
