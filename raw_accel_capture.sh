#!/bin/bash
# Raw accelerometer data capture

OUTPUT_DIR="./captures"
mkdir -p "$OUTPUT_DIR"

DURATION=${1:-10}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=============================================="
echo "RAW ACCELEROMETER CAPTURE"
echo "=============================================="
echo ""
echo "Duration: ${DURATION} seconds"
echo "Output: $OUTPUT_DIR"
echo ""
echo "Start sensord in another terminal:"
echo "  sudo sensord"
echo ""
echo "Then run:"
echo "  python3 accel_mic.py --duration $DURATION --output $OUTPUT_DIR/accel_${TIMESTAMP}.wav --analyze"
