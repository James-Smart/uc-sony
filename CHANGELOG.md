# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- PyInstaller spec file for proper module inclusion
- Local build script (`build.sh`) for testing
- Local packaging script (`package.sh`) for distribution
- `.gitignore` for build artifacts
- Documentation for local building

### Fixed
- PyInstaller not including all modules from `src/` directory
- Missing `permissions: contents: write` in GitHub Actions workflow

### Changed
- GitHub Actions now uses `driver.spec` instead of command-line PyInstaller args

## [0.1.0] - 2025-11-02

### Added
- Initial release of Sony Audio Control integration
- Auto-discovery via SSDP/UPnP for Sony Audio Control API devices
- Manual IP configuration as fallback
- Dynamic input discovery and button creation
- Power control (On/Off/Toggle)
- Volume control (Up/Down)
- Mute control (On/Off/Toggle)
- Input switching with dynamic sources
- Remote entity with physical button mappings
- Custom UI pages for touchscreen control
- Support for Sony TA-AN1000 soundbar
- Comprehensive API reference documentation

### Technical Details
- Async Python implementation using aiohttp
- Full integration with Unfolded Circle Integration API
- Robust error handling for Sony API quirks
- Session management for API calls
- Configuration persistence

## [0.1.0] - 2025-11-02

### Added
- Initial development release
- Core functionality for Sony Audio Control API
- Basic remote control features
- Documentation and setup guides

[Unreleased]: https://github.com/yourusername/intg-sony/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/intg-sony/releases/tag/v0.1.0

