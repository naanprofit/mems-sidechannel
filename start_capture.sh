#!/bin/bash
# Quick-start accelerometer capture

SENSORD=$(which sensord 2>/dev/null || echo "$HOME/go/bin/sensord")
DURATION=${1:-10}

echo "=============================================="
echo "MEMS SIDECHANNEL - Accelerometer Capture"
echo "=============================================="

if [ ! -f "$SENSORD" ]; then
    echo "sensord not found. Install with:"
    echo "  go install github.com/taigrr/apple-silicon-accelerometer/cmd/sensord@latest"
    exit 1
fi

echo "Starting sensord (requires sudo)..."
sudo "$SENSORD" &
SENSORD_PID=$!
sleep 3

if ! ps -p $SENSORD_PID > /dev/null 2>&1; then
    echo "Failed to start sensord"
    exit 1
fi

echo "Recording for $DURATION seconds..."
python3 accel_mic.py --duration "$DURATION" --output "captures/capture_$(date +%Y%m%d_%H%M%S).wav" --analyze

sudo kill $SENSORD_PID 2>/dev/null
echo "Done!"
