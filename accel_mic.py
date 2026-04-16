#!/usr/bin/env python3
"""
Accelerometer Microphone - Proof of Concept
============================================

Attempts to use the MacBook's accelerometer as a makeshift microphone.
Based on the "Gyrophone" attack concept.

Theory:
- Sound waves create vibrations that the accelerometer can detect
- The Bosch BMI286 IMU samples at ~400-800 Hz
- Human speech is primarily 80-3000 Hz
- We can only capture frequencies up to Nyquist (sample_rate/2)
- This means we might capture LOW frequency components of speech

Limitations:
- Sample rate is likely 400-800 Hz, so Nyquist limit is 200-400 Hz
- This captures bass/rumble but not intelligible speech
- Male fundamental frequency: 85-180 Hz (might capture!)
- Female fundamental frequency: 165-255 Hz (partially)

Requirements:
- Run sensord with sudo in another terminal
- This script reads from shared memory

Usage:
    sudo sensord &
    python3 accel_mic.py --duration 10 --output recording.wav
"""

import argparse
import ctypes
import mmap
import os
import struct
import sys
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import numpy as np

# Shared memory layout from sensord (taigrr/apple-silicon-accelerometer)
# Header: [0..3] write_idx u32, [4..11] total u64, [12..15] restarts u32
# Ring: 8000 entries × 12 bytes (3× int32: x, y, z)
SHM_HEADER_SIZE = 16
SHM_ENTRY_SIZE = 12  # 3 × int32 (x, y, z)
SHM_RING_SIZE = 8000  # RingCap in Go code
ACCEL_SCALE = 65536.0  # Q16 raw -> g

# These are the ACTUAL names used by taigrr/apple-silicon-accelerometer sensord
SHM_ACCEL_NAME = "vib_detect_shm"
SHM_GYRO_NAME = "vib_detect_shm_gyro"


@dataclass
class AccelSample:
    """A single accelerometer reading."""
    x: float
    y: float
    z: float
    timestamp: float


class SharedMemoryReader:
    """Read accelerometer data from sensord's shared memory."""
    
    def __init__(self, shm_name: str = SHM_ACCEL_NAME):
        self.shm_name = shm_name
        self.fd = None
        self.mm = None
        self.last_read_idx = 0
        
    def connect(self) -> bool:
        """Connect to shared memory."""
        try:
            # Open POSIX shared memory
            import posix_ipc
            # posix_ipc wants the name WITH leading slash
            shm_path = "/" + self.shm_name if not self.shm_name.startswith("/") else self.shm_name
            print(f"Connecting to shared memory: {shm_path}")
            shm = posix_ipc.SharedMemory(shm_path)
            self.fd = shm.fd
            
            # Memory map it
            size = SHM_HEADER_SIZE + (SHM_RING_SIZE * SHM_ENTRY_SIZE)
            self.mm = mmap.mmap(self.fd, size)
            print(f"Connected! Mapped {size} bytes")
            return True
        except ImportError:
            print("Installing posix_ipc...")
            os.system(f"{sys.executable} -m pip install posix_ipc")
            return self.connect()
        except Exception as e:
            if "permission" in str(e).lower():
                print(f"Permission denied accessing shared memory.")
                print("")
                print("The shared memory was created by root (sensord runs with sudo).")
                print("You have two options:")
                print("")
                print("  Option 1: Run this script with sudo:")
                print("    sudo python3 accel_mic.py --duration 10 --output test.wav --analyze")
                print("")
                print("  Option 2: Fix permissions on the shared memory (in sensord terminal):")
                print("    # After starting sensord, in another root shell:")
                print("    sudo chmod 666 /dev/shm/vib_detect_shm")
                print("")
            else:
                print(f"Failed to connect to shared memory: {e}")
                print("Make sure 'sudo ~/go/bin/sensord' is running in another terminal")
            return False
    
    def read_header(self) -> tuple[int, int, int]:
        """Read ring buffer header.
        
        Returns: (write_idx, total_samples, restarts)
        """
        if not self.mm:
            return (0, 0, 0)
        self.mm.seek(0)
        data = self.mm.read(SHM_HEADER_SIZE)
        # Header format: [0..3] write_idx u32, [4..11] total u64, [12..15] restarts u32
        write_idx = struct.unpack('<I', data[0:4])[0]
        total = struct.unpack('<Q', data[4:12])[0]
        restarts = struct.unpack('<I', data[12:16])[0]
        return (write_idx, total, restarts)
    
    def debug_header(self):
        """Print debug info about the header."""
        if not self.mm:
            print("Not connected")
            return
        self.mm.seek(0)
        data = self.mm.read(SHM_HEADER_SIZE)
        print(f"Raw header bytes: {data.hex()}")
        write_idx = struct.unpack('<I', data[0:4])[0]
        total = struct.unpack('<Q', data[4:12])[0]
        restarts = struct.unpack('<I', data[12:16])[0]
        print(f"write_idx: {write_idx} (should be 0-7999)")
        print(f"total_samples: {total}")
        print(f"restarts: {restarts}")
    
    def read_samples(self, count: int = 100) -> list[tuple[int, int, int]]:
        """Read raw samples from ring buffer."""
        if not self.mm:
            return []
        
        write_idx, _ = self.read_header()
        samples = []
        
        for i in range(count):
            idx = (write_idx - count + i) % SHM_RING_SIZE
            offset = SHM_HEADER_SIZE + (idx * SHM_ENTRY_SIZE)
            self.mm.seek(offset)
            data = self.mm.read(SHM_ENTRY_SIZE)
            x, y, z = struct.unpack('<iii', data)
            samples.append((x, y, z))
        
        return samples
    
    def close(self):
        """Clean up."""
        if self.mm:
            self.mm.close()
        if self.fd:
            os.close(self.fd)


class AccelMicrophone:
    """Use accelerometer as a microphone."""
    
    def __init__(self):
        self.reader = SharedMemoryReader()
        self.samples: list[float] = []
        self.sample_rate = 400  # Estimated, will calibrate
        
    def calibrate_sample_rate(self, duration: float = 1.0) -> float:
        """Estimate actual sample rate."""
        print("Calibrating sample rate...")
        
        _, start_total, _ = self.reader.read_header()
        time.sleep(duration)
        _, end_total, _ = self.reader.read_header()
        
        samples = end_total - start_total
        
        rate = samples / duration
        self.sample_rate = int(rate)
        print(f"Samples in {duration}s: {samples}")
        print(f"Estimated sample rate: {self.sample_rate} Hz")
        print(f"Nyquist frequency: {self.sample_rate // 2} Hz")
        return rate
    
    def record(self, duration: float = 5.0, verbose: bool = True) -> np.ndarray:
        """Record accelerometer data as audio."""
        if verbose:
            print(f"Recording for {duration} seconds...")
        
        all_samples = []
        start_time = time.time()
        
        # Initialize with current total count
        _, last_total, _ = self.reader.read_header()
        if verbose:
            print(f"Starting at total sample count: {last_total}")
        
        poll_count = 0
        while time.time() - start_time < duration:
            write_idx, current_total, _ = self.reader.read_header()
            poll_count += 1
            
            # Calculate how many new samples
            n_new = current_total - last_total
            
            if n_new > 0:
                # Don't try to read more than the ring buffer holds
                if n_new > SHM_RING_SIZE:
                    n_new = SHM_RING_SIZE
                
                # Read samples from ring buffer
                # Start position is (write_idx - n_new) wrapped
                start_pos = (write_idx - n_new + SHM_RING_SIZE) % SHM_RING_SIZE
                
                for i in range(n_new):
                    pos = (start_pos + i) % SHM_RING_SIZE
                    offset = SHM_HEADER_SIZE + (pos * SHM_ENTRY_SIZE)
                    self.reader.mm.seek(offset)
                    data = self.reader.mm.read(SHM_ENTRY_SIZE)
                    x, y, z = struct.unpack('<iii', data)
                    
                    # Use Z-axis (most sensitive to surface vibrations)
                    # Scale from Q16 to real units
                    magnitude = z / ACCEL_SCALE
                    all_samples.append(magnitude)
                
                if verbose and len(all_samples) % 1000 == 0 and len(all_samples) > 0:
                    print(f"  Captured {len(all_samples)} samples...")
                
                last_total = current_total
            
            time.sleep(0.0002)  # 0.2ms polling for high sample rates
        
        if verbose:
            print(f"Collected {len(all_samples)} samples in {poll_count} polls")
            if len(all_samples) > 0:
                print(f"Effective sample rate: {len(all_samples) / duration:.1f} Hz")
        
        return np.array(all_samples, dtype=np.float32)
    
    def process_audio(self, samples: np.ndarray) -> np.ndarray:
        """Process raw accelerometer data into audio."""
        if len(samples) == 0:
            print("WARNING: No samples to process!")
            return np.array([0.0], dtype=np.float32)
        
        # Remove DC offset
        samples = samples - np.mean(samples)
        
        # Normalize
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples = samples / max_val
        
        # High-pass filter to remove gravity/drift
        # (Simple first-order filter)
        alpha = 0.98
        filtered = np.zeros_like(samples)
        for i in range(1, len(samples)):
            filtered[i] = alpha * (filtered[i-1] + samples[i] - samples[i-1])
        
        return filtered
    
    def save_wav(self, samples: np.ndarray, filename: str):
        """Save processed samples as WAV file."""
        # Convert to 16-bit PCM
        samples_16bit = (samples * 32767).astype(np.int16)
        
        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(samples_16bit.tobytes())
        
        print(f"Saved to {filename}")
        print(f"Sample rate: {self.sample_rate} Hz")
        print(f"Duration: {len(samples) / self.sample_rate:.2f} seconds")


def analyze_frequency_content(samples: np.ndarray, sample_rate: int):
    """Analyze frequency content of recording."""
    if len(samples) < 10:
        print("Not enough samples for frequency analysis")
        return
    
    try:
        from scipy import signal
        from scipy.fft import fft, fftfreq
        
        # Compute FFT
        N = len(samples)
        yf = fft(samples)
        xf = fftfreq(N, 1/sample_rate)[:N//2]
        power = 2.0/N * np.abs(yf[0:N//2])
        
        # Find dominant frequencies
        peaks, _ = signal.find_peaks(power, height=np.max(power)*0.1)
        
        print("\nFrequency Analysis:")
        print("-" * 40)
        print(f"Frequency range: 0 - {sample_rate//2} Hz")
        
        if len(peaks) > 0:
            print("Dominant frequencies:")
            for peak in peaks[:5]:
                print(f"  {xf[peak]:.1f} Hz (power: {power[peak]:.4f})")
        
        # Check for speech-like frequencies
        speech_power = np.sum(power[(xf >= 80) & (xf <= 300)])
        total_power = np.sum(power)
        speech_ratio = speech_power / total_power if total_power > 0 else 0
        
        print(f"\nSpeech band (80-300 Hz) power ratio: {speech_ratio:.2%}")
        
    except ImportError:
        print("scipy not available for frequency analysis")


def main():
    parser = argparse.ArgumentParser(description="Accelerometer Microphone PoC")
    parser.add_argument("--duration", type=float, default=5.0, help="Recording duration in seconds")
    parser.add_argument("--output", type=str, default="accel_recording.wav", help="Output WAV file")
    parser.add_argument("--analyze", action="store_true", help="Analyze frequency content")
    parser.add_argument("--axis", choices=["x", "y", "z", "mag"], default="z", help="Which axis to record")
    args = parser.parse_args()
    
    print("=" * 60)
    print("ACCELEROMETER MICROPHONE - Proof of Concept")
    print("=" * 60)
    print()
    print("IMPORTANT: Run 'sudo sensord' in another terminal first!")
    print()
    
    mic = AccelMicrophone()
    
    if not mic.reader.connect():
        print("\nFailed to connect. Make sure sensord is running with sudo.")
        sys.exit(1)
    
    # Debug header
    print("\nDebug - checking shared memory header:")
    mic.reader.debug_header()
    print()
    
    # Calibrate
    mic.calibrate_sample_rate(1.0)
    
    print()
    print(f"Recording {args.duration} seconds...")
    print("Speak loudly near the laptop, tap the surface, or play music")
    print()
    
    # Record
    raw_samples = mic.record(args.duration)
    
    # Process
    processed = mic.process_audio(raw_samples)
    
    # Save
    mic.save_wav(processed, args.output)
    
    # Analyze
    if args.analyze:
        analyze_frequency_content(processed, mic.sample_rate)
    
    mic.reader.close()
    
    print()
    print("=" * 60)
    print("ANALYSIS:")
    print("=" * 60)
    print(f"""
The accelerometer samples at ~{mic.sample_rate} Hz.
This means we can theoretically capture frequencies up to {mic.sample_rate//2} Hz.

Human speech fundamentals:
- Male voice: 85-180 Hz (DETECTABLE)
- Female voice: 165-255 Hz (PARTIALLY DETECTABLE)

What this CAN detect:
- Bass/subwoofer vibrations
- Footsteps
- Door slams
- Low-frequency voice components (pitch/prosody)
- Typing patterns
- Phone vibrations

What this CANNOT detect clearly:
- Intelligible speech (most phonemes are >300 Hz)
- Music melodies (most musical content is >400 Hz)

INTELLIGENCE APPLICATIONS:
1. Presence detection (someone talking nearby)
2. Typing pattern analysis (keylogger via vibration)
3. Voice activity detection (not content)
4. Physical activity monitoring
5. Device proximity detection (vibration correlation)

To improve:
- Use gyroscope (may have higher sample rate)
- Combine multiple sensors
- Use ML to reconstruct higher frequencies
""")


if __name__ == "__main__":
    main()
