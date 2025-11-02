# Sony Audio Control Integration for Unfolded Circle Remote

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Unfolded Circle Remote 3 integration for Sony Audio Control API compatible devices.

## Overview

This integration enables full control of Sony audio devices (soundbars, AV receivers, speakers) that support the Sony Audio Control API through your Unfolded Circle Remote. The integration automatically discovers devices on your network and creates a customized remote control interface based on the device's capabilities.

## Supported Devices

- **Sony TA-AN1000** Soundbar (fully tested)
- Other Sony Audio devices with Audio Control API support:
  - AV Receivers (STR-series)
  - Soundbars (HT-series)
  - Wireless Speakers (SRS-series)

## Features

### Device Discovery
- **Auto-discovery**: Automatically find Sony devices on your network via SSDP/UPnP
- **Manual configuration**: Enter IP address manually if auto-discovery doesn't work
- **Verification**: Validates device compatibility before setup

### Control Features
- **Power Control**: On, Off, Toggle
- **Volume Control**: Up, Down with smooth adjustment
- **Mute Control**: On, Off, Toggle
- **Input Switching**: Dynamically discovered inputs
  - TV (ARC/eARC)
  - HDMI 1-4
  - Bluetooth
  - Analog (Line In)
  - AirPlay/Spotify Connect (if supported)

### User Interface
- **Physical Button Mappings**: Sensible defaults for remote buttons
  - Power → Power Toggle
  - Volume Up/Down → Volume control
  - Mute → Mute Toggle
  - Channel Up/Down → Input cycling
  - Dpad → Quick input selection
- **Custom UI Pages**: Touchscreen interface
  - Main Controls: Power, Volume, Mute
  - Input Selection: Grid view of all inputs

### Technical Features
- Async/await architecture for responsive control
- Robust error handling and recovery
- Session management for API calls
- Configuration persistence
- Comprehensive logging

## Installation

### Option 1: Pre-built Release (Recommended)

Download the latest pre-built release for your Remote:

1. Go to [Releases](https://github.com/James-Smart/uc-sony/releases)
2. Download the latest `uc-intg-sony-vX.X.X-aarch64.tar.gz` file
3. Extract the archive
4. Upload via Remote's web interface:
   - Navigate to **Configuration → Integrations → Add Integration → Upload**
   - Select the extracted folder or upload the tar.gz directly
5. Follow the setup wizard on your Remote

**Note**: Pre-built releases are self-contained binaries that include Python and all dependencies. No additional setup required!

### Option 2: Run from Source (Development)

For development or if you want to modify the integration:

**Requirements:**
- Python 3.11 or newer
- Unfolded Circle Remote Two or Remote 3
- Sony Audio device on the same network

**Quick Start:**

1. **Clone or download this repository**

```bash
git clone https://github.com/James-Smart/uc-sony.git
cd uc-sony
```

2. **Install dependencies**

Using `uv` (recommended):
```bash
uv sync
```

Or using `pip`:
```bash
pip install -r requirements.txt
```

3. **Run the integration**

```bash
# Using uv
uv run python src/driver.py

# Or using the convenience script
./start.sh

# Or with regular python
python3 src/driver.py
```

4. **Add to your Unfolded Circle Remote**

   - Open the Remote's web interface or app
   - Go to **Settings → Integrations**
   - Select **Add Integration**
   - Find "Sony Audio Control" in the list
   - Follow the setup wizard

### Setup Options

#### Auto-Discovery
The integration will automatically scan your network for Sony devices. Make sure:
- Your Sony device is powered on
- Device and Remote are on the same network
- Network allows multicast traffic (SSDP)

#### Manual Configuration
If auto-discovery doesn't work:
1. Find your device's IP address (check router or device network settings)
2. Select "Enter IP manually" during setup
3. Enter the IP address (e.g., `192.168.1.100`)

## Usage

### Basic Controls

Once configured, you can:
- **Power on/off** your device using the Power button
- **Adjust volume** with Volume Up/Down buttons
- **Mute/unmute** with the Mute button
- **Switch inputs** using the Input buttons or touchscreen

### Physical Button Mappings

| Remote Button | Function |
|---------------|----------|
| Power | Power Toggle |
| Volume Up | Volume Up |
| Volume Down | Volume Down |
| Mute | Mute Toggle |
| Channel Up | Next Input |
| Channel Down | Previous Input |
| Dpad Up | TV Input |
| Dpad Left | HDMI 1 |
| Dpad Right | HDMI 2 |
| Dpad Down | Bluetooth |
| Dpad Center | Mute Toggle |
| Home | TV Input |
| Back | HDMI 1 |


### Custom UI Pages

The integration provides two touchscreen pages:

1. **Main Controls**: Quick access to power, volume, and mute
2. **Inputs**: Grid of all available inputs with icons

## Troubleshooting

### Device Not Found

1. **Verify network connection**: Ensure device and Remote are on same network
2. **Check power**: Device must be powered on for discovery
3. **Check multicast**: Some networks block SSDP/multicast
   - Try connecting via Ethernet instead of Wi-Fi
   - Check router settings for IGMP snooping
4. **Try manual setup**: Use manual IP entry as fallback

### Connection Issues

1. **Verify IP address**: Check that the device IP hasn't changed
2. **Check firewall**: Ensure port 10000 is accessible
3. **Check device status**: Some devices may need a reboot
4. **Review logs**: Run with debug logging for details

### Commands Not Working

1. **API compatibility**: Verify your device supports Audio Control API
2. **Check device state**: Some commands only work when device is on
3. **Review error codes**:
   - Code 3: Illegal Argument (parameter format issue)
   - Code 12: No Such Method (command not supported)
   - Code 14: Unsupported Version (API version mismatch)

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
uv run python src/driver.py
```

## Configuration

Configuration is stored in:
- `$UC_CONFIG_HOME/sony_audio_config.json` (if UC_CONFIG_HOME is set)
- `$HOME/.config/sony_audio/sony_audio_config.json` (default)
- `./sony_audio_config.json` (fallback)

The configuration file stores:
- Device IP addresses
- Entity mappings
- Last known device state

## Development

### Project Structure

```
intg-sony/
├── src/                    # Source code
│   ├── driver.py          # Main integration driver
│   ├── sony_client.py     # Async Sony API client
│   ├── discovery.py       # SSDP device discovery
│   ├── remote_entity.py   # Remote entity builder
│   ├── config.py          # Configuration management
│   └── __init__.py        # Package initialization
├── docs/                   # Documentation
│   ├── QUICKSTART.md      # Quick start guide
│   ├── TESTING.md         # Testing guide
│   └── reference/         # API reference materials
├── driver.json            # Integration metadata
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### API Architecture

The integration uses Sony's Audio Control API with three main services:

1. **System Service** (`/sony/system`)
   - Device information
   - Power control
   - System status

2. **Audio Service** (`/sony/audio`)
   - Volume control
   - Mute control
   - Sound settings

3. **AV Content Service** (`/sony/avContent`)
   - Input switching
   - Source list
   - Content information

### Testing

To test the integration locally:

```bash
# Run the integration
uv run python src/driver.py

# In another terminal, test with your Remote
# The integration listens on port 9095 (configurable in driver.json)
```

See [docs/TESTING.md](docs/TESTING.md) for detailed testing instructions.

### Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- Code follows Python best practices
- New features include tests
- Documentation is updated
- Commit messages are clear and descriptive

## API Reference

For detailed Sony Audio Control API information, see:
- [docs/reference/API_REFERENCE.md](docs/reference/API_REFERENCE.md) - Complete API reference
- [docs/reference/sony_audio_control_api_summary.md](docs/reference/sony_audio_control_api_summary.md) - Official API docs
- [docs/reference/SOLUTION.md](docs/reference/SOLUTION.md) - Implementation notes
- [docs/reference/DISCOVERY_SUMMARY.md](docs/reference/DISCOVERY_SUMMARY.md) - Discovery methodology

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

### Built With
- [Unfolded Circle Integration API](https://github.com/unfoldedcircle/integration-python-library) - Integration framework
- [aiohttp](https://docs.aiohttp.org/) - Async HTTP client
- [zeroconf](https://github.com/python-zeroconf/python-zeroconf) - SSDP/mDNS discovery (optional)

### Inspired By
- [LG TV Integration](https://github.com/albaintor/integration-lgtv) by @albaintor

### Documentation
- [Sony Audio Control API](https://developer.sony.com/) - Official API documentation
- [Unfolded Circle Documentation](https://docs.unfoldedcircle.com/) - Remote integration guides

## Support

For issues, questions, or contributions:
- **Issues**: [GitHub Issues](https://github.com/yourusername/intg-sony/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/intg-sony/discussions)
- **Unfolded Circle Community**: [Community Forum](https://community.unfoldedcircle.com/)

## Disclaimer

This integration is not affiliated with or endorsed by Sony Corporation. Sony and all related trademarks are property of Sony Corporation.

The integration uses publicly available Sony Audio Control API endpoints and is provided as-is for personal use.
