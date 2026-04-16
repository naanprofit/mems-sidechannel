#!/usr/bin/env python3
"""
Unknown Sensor Analyzer
========================

Analyzes the unknown sensors on page 0xFF0C and 0xFF00:
- Usage 1 (0xFF0C, 5 bytes): Motion coprocessor status?
- Usage 5 (0xFF0C, 100 bytes): Force Touch/Taptic?
- Usage 255 (0xFF00, 1 byte): System status?

Run sensord-emi with --debug and pipe output here:
  sudo ~/go/bin/sensord-emi --debug 2>&1 | python3 unknown_sensors.py
"""

import sys
import re
from collections import defaultdict
import time

def parse_hex(hex_str):
    """Parse hex string to bytes."""
    return bytes.fromhex(hex_str)

def analyze_pattern(data):
    """Identify which pattern this data matches."""
    if len(data) == 5:
        if data[0] == 0x1d and data[1] == 0x01 and data[2] == 0x00:
            return "THERMAL", data[4]
        elif data[0] == 0x03 and data[1] == 0x02:
            return "STATUS", data[4]
        elif data[0] == 0x02 and data[1] == 0x01 and data[2] == 0x02:
            return "COUNTER", data[4]
        elif data[0] == 0x50:
            return "TAPTIC", int.from_bytes(data[1:], 'little')
        else:
            return "UNKNOWN", data.hex()
    elif len(data) == 1:
        return "SYSTEM", data[0]
    else:
        return "OTHER", data.hex()

def main():
    print("=" * 60)
    print("UNKNOWN SENSOR ANALYZER")
    print("=" * 60)
    print()
    print("Analyzing patterns from sensord-emi --debug output...")
    print("Press Ctrl+C to stop and see analysis.")
    print()
    
    # Pattern counters
    patterns = defaultdict(list)
    thermal_values = []
    counter_values = []
    status_values = []
    taptic_values = []
    start_time = time.time()
    
    # Regex to match debug output
    pattern = re.compile(r'\[DEBUG\] Unknown sensor report \(len=(\d+)\): ([0-9a-f]+)')
    
    try:
        for line in sys.stdin:
            line = line.strip()
            match = pattern.search(line)
            if match:
                length = int(match.group(1))
                hex_data = match.group(2)
                data = parse_hex(hex_data)
                
                ptype, value = analyze_pattern(data)
                elapsed = time.time() - start_time
                
                if ptype == "THERMAL":
                    thermal_values.append((elapsed, value))
                    if len(thermal_values) <= 10 or len(thermal_values) % 50 == 0:
                        print(f"[{elapsed:6.1f}s] THERMAL: {value:3d} (0x{value:02x})")
                elif ptype == "COUNTER":
                    counter_values.append((elapsed, value))
                elif ptype == "STATUS":
                    status_values.append((elapsed, value))
                    if value != 1:  # Only print non-standard status
                        print(f"[{elapsed:6.1f}s] STATUS: {value}")
                elif ptype == "TAPTIC":
                    taptic_values.append((elapsed, value))
                    print(f"[{elapsed:6.1f}s] TAPTIC: {value} (0x{value:08x})")
                else:
                    print(f"[{elapsed:6.1f}s] {ptype}: {value}")
                    
    except KeyboardInterrupt:
        pass
    
    # Analysis
    print()
    print("=" * 60)
    print("ANALYSIS")
    print("=" * 60)
    
    duration = time.time() - start_time
    print(f"\nDuration: {duration:.1f} seconds")
    
    if thermal_values:
        print(f"\n--- THERMAL SENSOR (1d 01 00 00 XX) ---")
        print(f"  Samples: {len(thermal_values)}")
        print(f"  Rate: {len(thermal_values)/duration:.1f} Hz")
        vals = [v[1] for v in thermal_values]
        print(f"  Min: {min(vals)} (0x{min(vals):02x})")
        print(f"  Max: {max(vals)} (0x{max(vals):02x})")
        print(f"  Avg: {sum(vals)/len(vals):.1f}")
        
        # Check if it's temperature-like
        if 20 <= sum(vals)/len(vals) <= 100:
            print(f"  INTERPRETATION: Likely temperature in Celsius")
        elif 50 <= sum(vals)/len(vals) <= 200:
            print(f"  INTERPRETATION: Likely temperature in Fahrenheit or scaled value")
        else:
            print(f"  INTERPRETATION: Unknown scaling, possibly status/index")
    
    if counter_values:
        print(f"\n--- COUNTER (02 01 02 00 XX) ---")
        print(f"  Samples: {len(counter_values)}")
        print(f"  Rate: {len(counter_values)/duration:.1f} Hz")
        vals = [v[1] for v in counter_values]
        # Check if incrementing
        diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1) if vals[i+1] > vals[i]]
        if diffs:
            print(f"  Incrementing: Yes (wraps at 256)")
            print(f"  INTERPRETATION: Sequence/frame counter")
    
    if status_values:
        print(f"\n--- STATUS (03 02 00 00 XX) ---")
        print(f"  Samples: {len(status_values)}")
        print(f"  Rate: {len(status_values)/duration:.1f} Hz")
        vals = [v[1] for v in status_values]
        unique = set(vals)
        print(f"  Unique values: {sorted(unique)}")
        print(f"  INTERPRETATION: Heartbeat/ready flag (1=ok, 2=busy?)")
    
    if taptic_values:
        print(f"\n--- TAPTIC/FORCE (50 XX XX XX XX) ---")
        print(f"  Samples: {len(taptic_values)}")
        vals = [v[1] for v in taptic_values]
        unique = set(vals)
        print(f"  Unique values: {[hex(v) for v in sorted(unique)]}")
        print(f"  INTERPRETATION: Force Touch or Taptic Engine feedback")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("""
Based on patterns observed:

1. THERMAL (1d 01 00 00 XX):
   - Varying byte likely represents temperature or thermal state
   - Could be used for thermal side-channel (detect computation)
   
2. COUNTER (02 01 02 00 XX):
   - Simple incrementing sequence counter
   - Used for frame synchronization internally
   
3. STATUS (03 02 00 00 01/02):
   - Heartbeat signal, mostly value 1
   - Value 2 might indicate busy/processing state
   
4. TAPTIC (50 XX XX XX XX):
   - Sporadic, related to Force Touch/Taptic Engine
   - Could detect user touch pressure

SIDE-CHANNEL POTENTIAL:
- Thermal: Detect when CPU is under load (crypto operations?)
- Taptic: Detect touch/click patterns on trackpad
""")

if __name__ == "__main__":
    main()
