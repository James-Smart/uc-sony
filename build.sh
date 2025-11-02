#!/usr/bin/env bash
# Local build script for Sony Audio Control integration
# This builds the integration binary locally for testing

set -e

PYTHON_VER="3.11.6-0.2.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "Building Sony Audio Control Integration"
echo "======================================"

# Check if running on Mac (for Docker platform)
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM_FLAG="--platform=linux/arm64"
else
    PLATFORM_FLAG=""
fi

# Clean previous build
echo "Cleaning previous build..."
rm -rf dist/ build/

# Build using Unfolded Circle's PyInstaller Docker image
echo "Starting PyInstaller build in Docker..."
docker run --rm \
    $PLATFORM_FLAG \
    --user="$(id -u):$(id -g)" \
    -v "${SCRIPT_DIR}:/workspace" \
    docker.io/unfoldedcircle/r2-pyinstaller:${PYTHON_VER} \
    bash -c "cd /workspace && \
        python -m pip install -q -r requirements.txt && \
        pyinstaller --clean driver.spec"

echo ""
echo "======================================"
echo "Build complete!"
echo "======================================"
echo "Binary location: dist/driver/"
echo ""
echo "To create distribution package:"
echo "  ./package.sh"

