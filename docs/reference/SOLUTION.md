# Sony TA-AN1000 API Solution

## Problem
The initial script was getting error code `12` ("No Such Method") on all control commands, even though the device was successfully discovered.

## Root Cause
The Sony TA-AN1000 requires specific parameter formats that differ from the general documentation:

1. **Missing `output` parameter**: Most commands require an `"output"` parameter (use empty string `""` for main zone)
2. **Wrong API versions**: Version numbers must match exactly what the device expects
3. **Parameter naming**: Some parameters use different names than documented

## Working Commands

### Device Information
```python
# System info - version 1.4
call("system", "getSystemInformation", [], version="1.4")

# Power status - version 1.1
call("system", "getPowerStatus", [], version="1.1")
```

### Volume Control
```python
# Get volume info - requires output parameter, version 1.1
call("audio", "getVolumeInformation", [{"output": ""}], version="1.1")

# Set absolute volume - version 1.1
call("audio", "setAudioVolume", [{"output": "", "volume": "25"}], version="1.1")

# Relative volume changes - version 1.1
call("audio", "setAudioVolume", [{"output": "", "volume": "+2"}], version="1.1")
call("audio", "setAudioVolume", [{"output": "", "volume": "-1"}], version="1.1")
```

### Mute Control
```python
# Mute on/off - version 1.1
call("audio", "setAudioMute", [{"output": "", "mute": "on"}], version="1.1")
call("audio", "setAudioMute", [{"output": "", "mute": "off"}], version="1.1")
```

### Input Switching
```python
# Switch input - version 1.2
call("avContent", "setPlayContent", 
     [{"output": "", "uri": "extInput:hdmi?port=1"}], version="1.2")
call("avContent", "setPlayContent", 
     [{"output": "", "uri": "extInput:hdmi?port=2"}], version="1.2")
call("avContent", "setPlayContent", 
     [{"output": "", "uri": "extInput:btAudio"}], version="1.2")
```

## Device Capabilities

### Zones
The TA-AN1000 reports 3 zones:
- `extOutput:zone?zone=1` (main zone)
- `extOutput:zone?zone=2`
- `extOutput:zone?zone=3`

### Volume Range
- Min: 0
- Max: 74
- Step: 1

### Supported Inputs
- ✅ HDMI 1 (`extInput:hdmi?port=1`)
- ✅ HDMI 2 (`extInput:hdmi?port=2`)
- ❌ HDMI 3 (returns error)
- ✅ Bluetooth (`extInput:btAudio`)

## Key Differences from Documentation

| Feature | Documentation | TA-AN1000 Actual |
|---------|--------------|------------------|
| Volume parameters | `{"volume": "+1", "ui": "on", "target": "speaker"}` | `{"output": "", "volume": "+1"}` |
| Mute parameters | `{"status": true}` | `{"output": "", "mute": "on"}` |
| Power parameters | `{"status": true}` | Not tested (always returns error 3) |
| Volume info | `getVolumeInformation` with no params | Requires `{"output": ""}` |
| API discovery | `getSupportedApiInfo` | Not supported (returns error 12) |

## Testing Results

All commands tested successfully:
- ✅ System information retrieval
- ✅ Power status reading
- ✅ Volume information for all zones
- ✅ Absolute volume setting
- ✅ Relative volume adjustment (+/-)
- ✅ Mute on/off
- ✅ Input switching (HDMI 1, 2, Bluetooth)

## Usage

Run the script to test all functionality:
```bash
uv run main.py
```

Or import the functions in your own code:
```python
from main import set_volume, set_mute, switch_input, get_volume_info

# Set volume to 30
set_volume(30)

# Increase by 5
set_volume("+5")

# Mute
set_mute(True)

# Switch to HDMI 1
switch_input("extInput:hdmi?port=1")

# Get current volume info
zones = get_volume_info()
print(f"Current volume: {zones[0]['volume']}")
```

