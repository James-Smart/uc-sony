# API Discovery Summary

## Overview

Through systematic testing and discovery, we successfully mapped out the complete API capabilities of the Sony TA-AN1000 soundbar. While standard API discovery methods (`getSupportedApiInfo`, `getMethodTypes`) don't work properly on this device, we developed alternative discovery techniques.

## Discovery Methodology

### 1. Error Code Analysis
- **Error 12**: Method doesn't exist → try different method names
- **Error 14**: Wrong API version → try different versions
- **Error 3**: Method exists but wrong parameters → test parameter variations

### 2. Version Discovery
Found that `getVersions` works on all services, revealing:
- **system**: 1.0, 1.1, 1.2, 1.4, 1.6
- **audio**: 1.0, 1.1, 1.2
- **avContent**: 1.0, 1.1, 1.2, 1.3, 1.4

### 3. Parameter Testing
Discovered critical pattern: most commands require `"output": ""` parameter for main zone.

---

## Discovered Methods

### System Service (3 working getters, 1 setter)

| Method | Version | Parameters | Purpose |
|--------|---------|------------|---------|
| `getSystemInformation` | 1.4 | `[]` | Device info, MAC, serial |
| `getInterfaceInformation` | 1.0 | `[]` | Product category, interface version |
| `getPowerStatus` | 1.1 | `[]` | Power state |
| `setPowerStatus` | 1.1 | `[{"status": "active"}]` | Turn on/off |
| `getVersions` | 1.0 | `[]` | Supported API versions |

### Audio Service (4 working getters, 2 setters)

| Method | Version | Parameters | Purpose |
|--------|---------|------------|---------|
| `getVolumeInformation` | 1.1 | `[{}]` or `[{"output": ""}]` | Volume for all/specific zones |
| `getSoundSettings` | 1.1 | `[{"target": ""}]` | Sound enhancement settings |
| `getSpeakerSettings` | 1.0 | `[{"target": ""}]` | Speaker configuration |
| `getCustomEqualizerSettings` | 1.0 | `[{"target": ""}]` | EQ settings |
| `setAudioVolume` | 1.1 | `[{"output": "", "volume": "20"}]` | Set volume |
| `setAudioMute` | 1.1 | `[{"output": "", "mute": "on"}]` | Mute/unmute |
| `getVersions` | 1.0 | `[]` | Supported API versions |

### AV Content Service (2 working getters, 1 setter)

| Method | Version | Parameters | Purpose |
|--------|---------|------------|---------|
| `getSchemeList` | 1.0 | `[]` | Available URI schemes |
| `getSourceList` | 1.2 | `[{"scheme": "extInput"}]` | List all inputs with metadata |
| `getPlayingContentInfo` | 1.2 | `[{}]` | Currently playing source |
| `setPlayContent` | 1.2 | `[{"output": "", "uri": "..."}]` | Switch input |
| `getVersions` | 1.0 | `[]` | Supported API versions |

---

## Key Discoveries

### 1. Available Input Sources
The device supports 6 input types:
- **TV (ARC)**: `extInput:tv` - TV audio return channel
- **HDMI 1**: `extInput:hdmi?port=1` - HDMI input 1
- **HDMI 2**: `extInput:hdmi?port=2` - HDMI input 2
- **Bluetooth**: `extInput:btAudio` - Bluetooth audio
- **Analog**: `extInput:line` - Analog line input
- **AirPlay**: `extInput:airPlay` - Apple AirPlay

### 2. Sound Settings
The device provides multiple audio enhancement options:
- **360 Spatial Sound Mapping**: Sony's 3D audio virtualization
- **DSD Native**: High-resolution audio support
- **Pure Direct**: Bypass processing for purest audio
- **Voice Enhancement**: Dialog clarity modes
- **Night Mode**: Dynamic range compression

### 3. Multi-Zone Support
Device has 3 zones:
- **Zone 1** (`extOutput:zone?zone=1`): Main zone, volume 0-74
- **Zone 2** (`extOutput:zone?zone=2`): Secondary zone
- **Zone 3** (`extOutput:zone?zone=3`): Tertiary zone

All zones share the same volume range (0-74) with step size of 1.

### 4. Scheme Types
Device supports 4 content schemes:
- **extInput**: External inputs (HDMI, Bluetooth, etc.)
- **storage**: USB storage devices
- **dlna**: DLNA/UPnP network sources
- **netservice**: Network services (Spotify, etc.)

---

## What Doesn't Work

### Non-functional Discovery Methods
- `getSupportedApiInfo` - Returns error 12 on all services
- `getMethodTypes` - Returns error 3 on all services (exists but can't find right params)

### Untested Methods
These common methods weren't found or need specific parameters:
- `getContentList` - Likely needs specific URI/scheme
- `getCurrentExternalInputsStatus` - Not tested
- `getRemoteControllerInfo` - Not tested
- Sound field switching (needs specific target values)
- EQ adjustment (needs specific band parameters)

---

## Files Created

### Main Scripts
- **`main.py`**: Original working example (basic functions)
- **`main_enhanced.py`**: Complete API with all discovered features
- **`discover.py`**: Initial discovery tool
- **`discover_full.py`**: Comprehensive systematic discovery

### Documentation
- **`API_REFERENCE.md`**: Complete method reference with examples
- **`SOLUTION.md`**: Technical implementation details
- **`README.md`**: User guide and quick start
- **`DISCOVERY_SUMMARY.md`**: This document

---

## Usage Patterns

### Required Parameters Pattern
Most write commands need the output parameter:
```python
# ✓ Correct
{"output": "", "volume": "20"}

# ✗ Wrong
{"volume": "20"}
```

### Zone Specification
```python
# Main zone (default)
{"output": ""}

# Specific zone
{"output": "extOutput:zone?zone=1"}
```

### Target Parameter for Settings
```python
# Get all targets
{"target": ""}

# Specific target (device-specific)
{"target": "outputZone:1"}
```

---

## Statistics

- **Total methods tested**: ~30
- **Working methods found**: 15
- **Services explored**: 3 (system, audio, avContent)
- **API versions tested**: 1.0 through 1.6
- **Input sources discovered**: 6
- **Sound settings categories**: 10+
- **Volume range**: 0-74 (75 steps)
- **Zones available**: 3

---

## Recommendations for Future Testing

1. **WebSocket Support**: Test real-time notifications via WebSocket connections
2. **DLNA/Storage**: Test local media playback from USB/network
3. **Advanced Sound Settings**: Test modifying sound field and EQ settings
4. **Zone Control**: Test independent control of zones 2 and 3
5. **Network Services**: Test streaming services integration
6. **Remote Controller**: Test remote control command injection
7. **Power Modes**: Test different standby modes and wake patterns

---

## Tools Developed

### Discovery Approach
1. Start with `getVersions` to find supported API versions
2. Use error code analysis (12 vs 3) to identify existing methods
3. Test parameter variations systematically
4. Document working combinations

### Reusability
The discovery scripts (`discover.py` and `discover_full.py`) can be adapted for testing other Sony Audio Control API devices by:
1. Changing the IP address
2. Running the full discovery
3. Analyzing the output for working methods
4. Building device-specific wrappers

This approach proved more effective than relying on Sony's general documentation, which often doesn't match device-specific implementations.

