# Sony TA-AN1000 - Complete API Reference

This document contains all discovered working API methods for the Sony TA-AN1000 soundbar.

## Device Information

- **Model**: TA-AN1000
- **Product Category**: homeTheaterSystem
- **Product Name**: SoundBar
- **Interface Version**: 6.1.0
- **API Port**: 10000
- **Base URL**: `http://<device_ip>:10000/sony`

## Supported API Versions

| Service | Versions |
|---------|----------|
| system | 1.0, 1.1, 1.2, 1.4, 1.6 |
| audio | 1.0, 1.1, 1.2 |
| avContent | 1.0, 1.1, 1.2, 1.3, 1.4 |

---

## System Service (`/sony/system`)

### getSystemInformation
**Version**: 1.4  
**Parameters**: `[]`

Returns device model, MAC addresses, serial number, and firmware version.

```python
call("system", "getSystemInformation", [], version="1.4")
```

**Response**:
```json
{
  "bdAddr": "04:7b:cb:db:83:7b",
  "bleID": "972e4c09",
  "macAddr": "f8:4e:17:21:ca:31",
  "model": "TA-AN1000",
  "serialNumber": "6601788",
  "version": "001.478",
  "wirelessMacAddr": "04:7b:cb:db:83:77"
}
```

### getInterfaceInformation
**Version**: 1.0  
**Parameters**: `[]`

Returns interface version and product information.

```python
call("system", "getInterfaceInformation", [], version="1.0")
```

**Response**:
```json
{
  "interfaceVersion": "6.1.0",
  "modelName": "TA-AN1000",
  "productCategory": "homeTheaterSystem",
  "productName": "SoundBar",
  "serverName": ""
}
```

### getPowerStatus
**Version**: 1.1  
**Parameters**: `[]`

Returns current power status.

```python
call("system", "getPowerStatus", [], version="1.1")
```

**Response**:
```json
{
  "status": "active",  // or "standby"
  "standbyDetail": ""
}
```

### setPowerStatus
**Version**: 1.1  
**Parameters**: `[{"status": "active"}]` or `[{"status": "standby"}]`

Changes power status.

```python
call("system", "setPowerStatus", [{"status": "active"}], version="1.1")
```

### getVersions
**Version**: 1.0  
**Parameters**: `[]`

Returns supported API versions for the service.

```python
call("system", "getVersions", [], version="1.0")
```

---

## Audio Service (`/sony/audio`)

### getVolumeInformation
**Version**: 1.1  
**Parameters**: `[{}]` or `[{"output": ""}]`

Returns volume information for all zones or specific zone.

```python
# All zones
call("audio", "getVolumeInformation", [{}], version="1.1")

# Specific zone
call("audio", "getVolumeInformation", 
     [{"output": "extOutput:zone?zone=1"}], version="1.1")
```

**Response**:
```json
[
  {
    "output": "extOutput:zone?zone=1",
    "volume": 17,
    "mute": "off",
    "minVolume": 0,
    "maxVolume": 74,
    "step": 1
  },
  // ... zones 2 and 3
]
```

### setAudioVolume
**Version**: 1.1  
**Parameters**: `[{"output": "", "volume": "20"}]`

Sets volume (absolute or relative).

```python
# Absolute volume
call("audio", "setAudioVolume", 
     [{"output": "", "volume": "20"}], version="1.1")

# Relative volume
call("audio", "setAudioVolume", 
     [{"output": "", "volume": "+2"}], version="1.1")
call("audio", "setAudioVolume", 
     [{"output": "", "volume": "-1"}], version="1.1")
```

### setAudioMute
**Version**: 1.1  
**Parameters**: `[{"output": "", "mute": "on"}]` or `[{"output": "", "mute": "off"}]`

Sets mute status.

```python
call("audio", "setAudioMute", 
     [{"output": "", "mute": "on"}], version="1.1")
```

### getSoundSettings
**Version**: 1.1  
**Parameters**: `[{"target": ""}]`

Returns available sound settings and their current values.

```python
call("audio", "getSoundSettings", [{"target": ""}], version="1.1")
```

**Response**: Returns settings like:
- Voice enhancement modes
- Night mode
- Sound optimizer
- Sound field settings

### getSpeakerSettings
**Version**: 1.0  
**Parameters**: `[{"target": ""}]`

Returns speaker configuration options.

```python
call("audio", "getSpeakerSettings", [{"target": ""}], version="1.0")
```

**Response**: Returns speaker layout options like:
- Front & Center
- In-ceiling configurations
- Speaker size settings

### getCustomEqualizerSettings
**Version**: 1.0  
**Parameters**: `[{"target": ""}]`

Returns equalizer settings.

```python
call("audio", "getCustomEqualizerSettings", [{"target": ""}], version="1.0")
```

**Response**: Returns EQ bands with min/max/step values (-10 to +10 range).

### getVersions
**Version**: 1.0  
**Parameters**: `[]`

Returns supported API versions for the audio service.

---

## AV Content Service (`/sony/avContent`)

### getSchemeList
**Version**: 1.0  
**Parameters**: `[]`

Returns available URI schemes for content sources.

```python
call("avContent", "getSchemeList", [], version="1.0")
```

**Response**:
```json
[
  {"scheme": "extInput"},
  {"scheme": "storage"},
  {"scheme": "dlna"},
  {"scheme": "netservice"}
]
```

### getSourceList
**Version**: 1.2  
**Parameters**: `[{"scheme": "extInput"}]`

Returns available input sources with metadata.

```python
call("avContent", "getSourceList", 
     [{"scheme": "extInput"}], version="1.2")
```

**Response**:
```json
[
  {
    "source": "extInput:tv",
    "title": "TV",
    "meta": "meta:tv",
    "isPlayable": true,
    "isBrowsable": false,
    "playAction": "changeSource"
  },
  {
    "source": "extInput:hdmi?port=1",
    "title": "HDMI1",
    "meta": "meta:hdmi",
    "isPlayable": false,
    "isBrowsable": true
  },
  {
    "source": "extInput:hdmi?port=2",
    "title": "HDMI2",
    "meta": "meta:hdmi"
  },
  {
    "source": "extInput:btAudio",
    "title": "Bluetooth Audio",
    "meta": "meta:btaudio",
    "isPlayable": true,
    "playAction": "changeSource"
  },
  {
    "source": "extInput:line",
    "title": "Analog",
    "meta": "meta:linemini",
    "isPlayable": true,
    "playAction": "changeSource"
  },
  {
    "source": "extInput:airPlay",
    "title": "AirPlay",
    "meta": "meta:airplay",
    "isPlayable": true,
    "playAction": "startPlay",
    "protocols": []
  }
]
```

### getPlayingContentInfo
**Version**: 1.2  
**Parameters**: `[{}]` or `[{"output": ""}]`

Returns information about currently playing content.

```python
call("avContent", "getPlayingContentInfo", [{}], version="1.2")
```

**Response**:
```json
{
  "output": "extOutput:zone?zone=1",
  "source": "extInput:tv",
  "parentUri": "extInput:tv",
  "contentKind": "music",
  "mediaType": "music"
}
```

### setPlayContent
**Version**: 1.2  
**Parameters**: `[{"output": "", "uri": "<source_uri>"}]`

Switches to a different input source.

```python
call("avContent", "setPlayContent", 
     [{"output": "", "uri": "extInput:hdmi?port=1"}], version="1.2")
```

**Available URIs**:
- `extInput:tv` - TV (ARC)
- `extInput:hdmi?port=1` - HDMI 1
- `extInput:hdmi?port=2` - HDMI 2
- `extInput:btAudio` - Bluetooth Audio
- `extInput:line` - Analog input
- `extInput:airPlay` - AirPlay

### getVersions
**Version**: 1.0  
**Parameters**: `[]`

Returns supported API versions for the avContent service.

---

## Common Patterns

### Output Parameter
Most commands require an `"output"` parameter:
- Use `""` (empty string) for the main zone (zone 1)
- Use `"extOutput:zone?zone=N"` for specific zones (N = 1, 2, or 3)

### Target Parameter
Audio settings commands use a `"target"` parameter:
- Use `""` (empty string) to get all targets
- Specific targets are device-dependent

### Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 3 | Illegal Argument | Check parameter format and values |
| 12 | No Such Method | Method doesn't exist or wrong service |
| 14 | Unsupported Version | Use a different API version |

### Version Strategy
If a method fails with error 14, try different versions:
1. Check supported versions with `getVersions`
2. Start with the highest supported version
3. Try progressively lower versions

---

## Example Code

### Complete Control Example

```python
import requests

AVR_IP = "192.168.1.201"
BASE = f"http://{AVR_IP}:10000/sony"

def call(service, method, params=None, version="1.0"):
    url = f"{BASE}/{service}"
    payload = {
        "method": method,
        "id": 1,
        "params": params or [],
        "version": version,
    }
    r = requests.post(url, json=payload, timeout=3)
    return r.json()

# Get device info
info = call("system", "getSystemInformation", [], "1.4")
print(f"Model: {info['result'][0]['model']}")

# Get available inputs
sources = call("avContent", "getSourceList", 
               [{"scheme": "extInput"}], "1.2")
for source in sources['result'][0]:
    print(f"- {source['title']}: {source['source']}")

# Get current state
volume = call("audio", "getVolumeInformation", [{}], "1.1")
print(f"Volume: {volume['result'][0][0]['volume']}")

playing = call("avContent", "getPlayingContentInfo", [{}], "1.2")
print(f"Source: {playing['result'][0][0]['source']}")

# Control the device
call("audio", "setAudioVolume", 
     [{"output": "", "volume": "25"}], "1.1")
call("avContent", "setPlayContent", 
     [{"output": "", "uri": "extInput:hdmi?port=1"}], "1.2")
```

---

## Notes

1. **Discovery**: The `getSupportedApiInfo` and `getMethodTypes` methods don't work on this device
2. **Zones**: Device reports 3 zones but zones 2 and 3 functionality is untested
3. **Sound Settings**: Advanced audio settings are available but require proper target parameters
4. **WebSocket**: WebSocket support for notifications was not tested
5. **AirPlay**: AirPlay input exists but functionality depends on network configuration

---

## Testing

Use the provided discovery scripts to test methods:
- `discover.py` - Basic method discovery
- `discover_full.py` - Comprehensive API exploration
- `main.py` - Working examples with clean API

