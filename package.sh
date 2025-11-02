#!/usr/bin/env bash
# Package script for Sony Audio Control integration
# Creates a .tar.gz package ready for upload to Remote

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if build exists
if [ ! -d "dist/driver" ]; then
    echo "Error: Build not found. Run ./build.sh first"
    exit 1
fi

# Get version from driver.json
VERSION=$(jq -r .version driver.json)
INTG_NAME="sony"
ARTIFACT_NAME="uc-intg-${INTG_NAME}-v${VERSION}-aarch64"

echo "======================================"
echo "Packaging Sony Audio Control Integration"
echo "Version: ${VERSION}"
echo "======================================"

# Create artifacts directory
rm -rf artifacts/
mkdir -p artifacts/bin

# Copy files
echo "Copying files..."
cp -r dist/driver/* artifacts/bin/
cp driver.json artifacts/
echo "${VERSION}" > artifacts/version.txt

# Create tarball
echo "Creating package: ${ARTIFACT_NAME}.tar.gz"
tar czf "${ARTIFACT_NAME}.tar.gz" -C artifacts .

echo ""
echo "======================================"
echo "Package created successfully!"
echo "======================================"
echo "File: ${ARTIFACT_NAME}.tar.gz"
echo "Size: $(ls -lh ${ARTIFACT_NAME}.tar.gz | awk '{print $5}')"
echo ""
echo "Upload this file to your Remote via:"
echo "  Configuration → Integrations → Add Integration → Upload"

