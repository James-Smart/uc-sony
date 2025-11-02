#!/bin/bash
# Start the Sony Audio Control integration

cd "$(dirname "$0")"

echo "Starting Sony Audio Control integration..."
echo "Press Ctrl+C to stop"
echo ""

# Check if dependencies are installed
if ! uv run python -c "import ucapi, aiohttp" 2>/dev/null; then
    echo "Installing dependencies..."
    uv pip install ucapi aiohttp
    echo ""
fi

# Start the driver
uv run python src/driver.py

