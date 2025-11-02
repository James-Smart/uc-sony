# GitHub Actions CI/CD

This directory contains automated workflows for building, testing, and releasing the Sony Audio Control integration.

## Workflows

### Build & Release (`workflows/build.yml`)

Automatically builds and releases the integration:

- **Triggers**:
  - Push to `main` → Creates development pre-release
  - Push to version tag (e.g., `v0.1.0`) → Creates official release
  - Pull requests → Builds to verify

- **Process**:
  1. Compiles Python to standalone binary using PyInstaller
  2. Packages with driver.json and metadata
  3. Creates `.tar.gz` archive
  4. Uploads to GitHub Releases with SHA256 checksums

### Python Code Quality (`workflows/python-check.yml`)

Ensures code quality standards:

- **Checks**:
  - `pylint` - Code quality analysis
  - `flake8` - Style guide enforcement
  - `isort` - Import sorting
  - `black` - Code formatting (120 char line length)

- **Triggers**:
  - Push affecting: `src/**`, `requirements.txt`, `test-requirements.txt`, etc.
  - Pull requests

## Creating a Release

1. Update version in `driver.json`:
   ```json
   {
     "version": "0.1.0",
     ...
   }
   ```

2. Update `CHANGELOG.md` with changes

3. Commit and tag:
   ```bash
   git add driver.json CHANGELOG.md
   git commit -m "Release v0.1.0"
   git tag v0.1.0
   git push origin main --tags
   ```

4. GitHub Actions will automatically:
   - Build aarch64 binary
   - Create GitHub Release
   - Upload `uc-intg-sony-v0.1.0-aarch64.tar.gz`
   - Upload SHA256 checksums

## Development Builds

Every push to `main` creates a development build tagged as "latest":
- Filename includes timestamp: `uc-intg-sony-v0.1.0-aarch64-20251102_172530.tar.gz`
- Marked as pre-release
- Useful for testing

## Templates

### Issue Templates (`ISSUE_TEMPLATE/`)
- `bug_report.md` - For reporting bugs
- `feature_request.md` - For requesting features

### Pull Request Template (`PULL_REQUEST_TEMPLATE.md`)
Checklist for contributors including:
- Description of changes
- Type of change
- Testing checklist
- Code quality verification

## Local Testing

Before pushing, verify code quality:

```bash
# Install test dependencies
pip install -r test-requirements.txt

# Run checks
pylint src
flake8 src --count --show-source --statistics
isort src/. --check --verbose
black src --check --diff --verbose --line-length 120
```

## Build System

- **Platform**: ubuntu-22.04 (for QEMU compatibility)
- **Python**: 3.11.6 in PyInstaller container
- **Architecture**: aarch64 (ARM64) for Remote Two/3
- **Container**: `unfoldedcircle/r2-pyinstaller:3.11.6-0.2.0`

## Release Artifacts

Each release includes:
- `uc-intg-sony-vX.X.X-aarch64.tar.gz` - Integration package
- `uc-intg-sony.hash` - SHA256 checksums

Package contents:
```
├── bin/
│   └── driver              # Self-contained binary
├── driver.json             # Integration metadata
└── version.txt            # Version string
```

## Notes

- Version tag must match `driver.json` version for official releases
- Pre-built binaries are self-contained (no dependencies needed on Remote)
- Build artifacts retained for 3 days, releases are permanent

