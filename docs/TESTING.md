# Testing Guide

## Test Results

### Module Import Tests ✓
All modules import successfully without errors:
- sony_client ✓
- discovery ✓
- config ✓
- remote_entity ✓
- driver ✓

### Syntax and Compilation ✓
All Python files compile without syntax errors.

### Device Connection Test
The device connection test (`test_device.py`) is ready but requires:
1. Sony device to be powered on
2. Device to be on the same network
3. Correct IP address configured

**Current Status**: Device not available for live testing (`Host is down`)

## Running Tests

### Prerequisites

Install dependencies using uv:
```bash
cd intg-sony
uv pip install ucapi aiohttp
```

### Import Test

```bash
uv run python test_imports.py
```

Expected output:
```
✓ sony_client imported
✓ discovery imported
✓ config imported
✓ remote_entity imported
✓ ucapi imported
✓ aiohttp imported

✓ All modules imported successfully!
```

### Device Connection Test

1. Update IP address in `test_device.py`:
```python
AVR_IP = "192.168.1.201"  # Change to your device IP
```

2. Ensure device is powered on and on the same network

3. Run test:
```bash
uv run python test_device.py
```

Expected test sequence:
1. Connection test
2. Get device information (model, version, serial)
3. Get power status
4. Get volume information
5. Get available input sources
6. Get current playing content
7. Test volume control (+1/-1)

## Running the Integration

### Start the Driver

```bash
uv run python driver.py
```

The driver will:
1. Start WebSocket server on port 9095
2. Load previously configured devices
3. Wait for connections from Unfolded Circle Remote

### Add Integration to Remote

1. Open Unfolded Circle Remote settings
2. Go to Integrations
3. Add Custom Integration
4. Enter the IP address of the machine running the driver
5. Port: 9095

### Setup Flow

The setup process will:

1. **Discovery Method Selection**
   - Auto-discover: Automatically find Sony devices via SSDP
   - Manual: Enter IP address manually

2. **Device Selection** (auto-discover mode)
   - Shows list of discovered devices
   - Select your device from the dropdown

3. **Device Confirmation**
   - Shows device model, version, IP
   - Optional: Customize device name

4. **Setup Complete**
   - Remote entity created with all discovered inputs
   - Ready to control device

## Manual Testing Checklist

When device is available:

### Basic Functionality
- [ ] Device discovery (SSDP)
- [ ] Manual IP configuration
- [ ] Device connection
- [ ] Power on/off commands
- [ ] Volume up/down
- [ ] Mute toggle
- [ ] Input switching

### UI Testing
- [ ] Main control page displays correctly
- [ ] Input selection page shows all inputs
- [ ] Button icons are correct
- [ ] Commands execute when buttons pressed

### Physical Remote Buttons
- [ ] Power button toggles power
- [ ] Volume up/down buttons work
- [ ] Mute button works
- [ ] Channel up/down (volume alternative) works

### Edge Cases
- [ ] Device reconnection after power cycle
- [ ] Network disconnection handling
- [ ] Invalid IP address handling
- [ ] Device not responding
- [ ] Multiple device support

### Integration API
- [ ] Entity subscription updates state correctly
- [ ] Configuration persists across restarts
- [ ] Setup reconfiguration works
- [ ] Entity removal works

## Troubleshooting

### Device Not Found (SSDP)
- Ensure device is powered on
- Check network allows multicast (239.255.255.250:1900)
- Try manual IP configuration

### Connection Refused
- Verify device IP address
- Check device is on same network
- Ensure port 10000 is not blocked

### Commands Not Working
- Check device supports the command
- Verify API version compatibility
- Check logs for Sony API errors

### Import Errors
- Ensure using `uv run` to execute scripts
- Verify dependencies installed: `uv pip install ucapi aiohttp`

## Test Logs

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:
```bash
export LOG_LEVEL=DEBUG
uv run python driver.py
```

## Integration Status

| Component | Status | Notes |
|-----------|--------|-------|
| Sony API Client | ✓ Complete | Async wrapper for all discovered API methods |
| Device Discovery | ✓ Complete | SSDP/UPnP implementation |
| Configuration | ✓ Complete | JSON file persistence |
| Remote Entity | ✓ Complete | Dynamic command generation |
| Setup Flow | ✓ Complete | Auto-discover & manual modes |
| Command Handler | ✓ Complete | Routes all commands to Sony API |
| UI Pages | ✓ Complete | Main controls & input selection |
| Button Mappings | ✓ Complete | Physical remote button support |

**Overall Status**: Implementation Complete, Pending Live Device Testing

## Next Steps

1. Connect Sony device to network
2. Run `test_device.py` to verify API communication
3. Start driver: `uv run python driver.py`
4. Add integration to Unfolded Circle Remote
5. Test all functions with physical remote
6. Document any device-specific quirks or limitations

