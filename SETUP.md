# Setup and Usage Guide

## Quick Start

### Running the Integration Locally

From the `intg-sony` directory:

```bash
# Using the convenience script
./start.sh

# Or directly with uv
uv run python src/driver.py

# Or with standard Python (ensure dependencies are installed)
python3 src/driver.py
```

The integration will:
1. Start listening on port 9095 (default)
2. Advertise itself via mDNS/zeroconf
3. Wait for connections from your Unfolded Circle Remote

### Adding to Your Remote

1. Open the Remote's web interface or app
2. Go to **Settings → Integrations**
3. Select **Add Integration**
4. Find "Sony Audio Control" in the discovered integrations
5. Follow the setup wizard to either:
   - Auto-discover your Sony device (recommended)
   - Manually enter the IP address

## Directory Structure

```
intg-sony/
├── src/                    # Source code
│   ├── driver.py          # Main entry point
│   ├── sony_client.py     # Sony API client
│   ├── discovery.py       # Device discovery
│   ├── remote_entity.py   # Entity builder
│   └── config.py          # Configuration
├── docs/                   # Documentation
│   ├── QUICKSTART.md
│   ├── TESTING.md
│   └── reference/         # API references
├── driver.json            # Integration metadata
├── requirements.txt       # Dependencies
└── README.md             # Main documentation
```

## Development

### Testing Locally

```bash
# Run with debug logging
export LOG_LEVEL=DEBUG
uv run python src/driver.py
```

### Verifying Installation

```bash
# Test all imports
uv run python -c "
import sys
sys.path.insert(0, 'src')
from driver import *
print('✓ All modules loaded successfully')
"
```

### Configuration Location

The integration stores configuration in:
- `$UC_CONFIG_HOME/sony_audio_config.json` (if set)
- `$HOME/.config/sony_audio/sony_audio_config.json` (default)
- `./sony_audio_config.json` (fallback)

## Packaging for Remote

To package the integration for deployment on the Remote itself:

1. **Ensure all dependencies are listed** in `requirements.txt`
2. **Package the integration** directory
3. **Upload via the Remote's web interface**

The Remote will:
- Extract the package
- Install dependencies
- Run `src/driver.py` automatically

## Troubleshooting

### Integration Not Discovered

If the Remote doesn't discover the integration:

1. **Check the driver is running**: Look for startup logs
2. **Check network**: Ensure Remote and host are on same network
3. **Check firewall**: Allow port 9095
4. **Check mDNS**: Some networks block multicast

### Import Errors

If you see import errors:

```bash
# Reinstall dependencies
cd intg-sony
uv pip install -r requirements.txt --force-reinstall
```

### Path Issues

The driver automatically resolves paths relative to the `src/` directory:
- `driver.json` → `../driver.json` (parent directory)
- Other modules → Same directory imports

## Next Steps

- Read [QUICKSTART.md](docs/QUICKSTART.md) for detailed setup
- Check [TESTING.md](docs/TESTING.md) for testing guide
- See [docs/reference/](docs/reference/) for API documentation
- Review [CHANGELOG.md](CHANGELOG.md) for version history

## Support

- **Issues**: Report bugs via GitHub Issues
- **Questions**: Use GitHub Discussions
- **Community**: Unfolded Circle Community Forum

Happy controlling! 🎛️

