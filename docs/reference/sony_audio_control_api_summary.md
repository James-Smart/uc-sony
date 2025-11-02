# 🎛️ Sony Audio Control API — Integration Summary

## Overview
The **Audio Control API** allows external applications to control compatible Sony audio products (e.g., STR-DN1080) over the **network** using:
- **HTTP** and **JSON-RPC** for commands  
- **WebSockets** for real-time notifications  
- **SSDP/UPnP/DLNA** for discovery and media browsing  

The API provides control over:
- Power  
- Volume / Mute  
- Input source  
- Playback / Mode / Tuner / Zone  

---

## Key Concepts

### API Architecture
| Service | Path | Purpose |
|----------|------|----------|
| `/audio` | `/sony/audio` | Get/set audio settings (volume, mute, sound mode, etc.) |
| `/system` | `/sony/system` | Power control, device info, system configuration |
| `/avContent` | `/sony/avContent` | Input selection, playback control, content browsing |

### Protocols Used
- **HTTP POST** (for sending JSON-RPC commands)
- **WebSocket** (`ws://<ip>:10000/sony/<service>`) for event notifications  
- **SSDP (UPnP)** for device discovery  
- **DLNA** for accessing local media  

---

## Device Discovery (UPnP/SSDP)
Send an M-SEARCH broadcast:

```http
M-SEARCH * HTTP/1.1
HOST: 239.255.255.250:1900
MAN: "ssdp:discover"
MX: 3
ST: urn:schemas-sony-com:service:ScalarWebAPI:1
```

Typical response:

```
LOCATION: http://192.168.0.1:61000/dd.xml
ST: urn:schemas-sony-com:service:ScalarWebAPI:1
```

From the XML at `LOCATION`, extract:
- `<av:X_ScalarWebAPI_BaseURL>` → Base API URL (e.g. `http://192.168.1.123:10000/sony`)
- `<av:X_ScalarWebAPI_ServiceType>` → Available service endpoints

Then form URLs like:
```
http://192.168.1.123:10000/sony/audio
http://192.168.1.123:10000/sony/system
http://192.168.1.123:10000/sony/avContent
```

---

## Example HTTP Commands (JSON-RPC)

**General format:**
```json
{
  "method": "<methodName>",
  "params": [ { ... } ],
  "id": 1,
  "version": "1.x"
}
```

### Get System Info
```bash
curl -i -d '{"method":"getSystemInformation","id":1,"params":[],"version":"1.4"}' \
http://192.168.1.123:10000/sony/system
```

### Power On/Off
```json
{"method":"setPowerStatus","params":[{"status":true}],"id":1,"version":"1.1"}
```

### Volume Control
```json
{"method":"setAudioVolume","params":[{"volume":"+1","ui":"on","target":"speaker"}],"id":1,"version":"1.1"}
```

### Mute
```json
{"method":"setAudioMute","params":[{"status":true}],"id":1,"version":"1.1"}
```

### Change Input
```json
{"method":"setPlayContent","params":[{"uri":"extInput:hdmi?port=1"}],"id":1,"version":"1.2"}
```

---

## Device Resource URIs

Common URIs for **AVRs**:
| Type | URI Example | Description |
|------|--------------|-------------|
| HDMI input | `extInput:hdmi?port=1` | HDMI input 1 |
| Bluetooth | `extInput:btAudio` | Bluetooth input |
| TV | `extInput:tv` | TV ARC input |
| USB | `storage:usb1` | USB music storage |
| DLNA | `dlna:music` | Network music source |
| Output Zone | `extOutput:zone?zone=1` | Main Zone output |

---

## WebSocket Notifications

Use `switchNotifications` to subscribe:
```json
{
  "method": "switchNotifications",
  "id": 1,
  "params": [{
    "enabled": [{"name": "notifyPlayingContentInfo", "version": "1.0"}],
    "disabled": []
  }],
  "version": "1.0"
}
```

**Example event message:**
```json
{
  "method": "notifyPlayingContentInfo",
  "params": [{
    "contentKind": "input",
    "output": "extOutput:zone?zone=1",
    "source": "extInput:hdmi?port=1"
  }],
  "version": "1.0"
}
```

---

## Error Codes

| Code | Meaning | Example |
|------|----------|----------|
| `401` | Unauthorized | API access denied |
| `403` | Forbidden | Permission denied |
| `404` | Not Found | API not supported |
| `40800` | Target Not Supported | Invalid control target |
| `40801` | Volume Out of Range | Invalid volume value |
| `14` | Unsupported Version | Incorrect `"version"` |
| `12` | No Such Method | Invalid method name |

---

## Supported Devices
- HT-ST5000, HT-CT800, HT-MT500, HT-Z9F/ZF9  
- STR-DN1080 receiver (✅ primary AVR target)  
- SRS-ZR5 speaker  

---

## Key Design Considerations
- **Port:** 10000 for home audio, 54480 for personal audio  
- **Authentication:** Usually not required (may vary by model)  
- **Multi-zone:** Use `?zone=1`, `?zone=2`, etc. for zone targeting  
- **JSON-RPC versioning:** Each API has its own version number (e.g., `"1.1"`, `"1.4"`)  
- **WebSocket:** Required for event-driven features like `notifyPlayingContentInfo`  

---

## References
- API Discovery via SSDP: `urn:schemas-sony-com:service:ScalarWebAPI:1`  
- Typical Base URL: `http://<device_ip>:10000/sony`  
- Common services: `/system`, `/audio`, `/avContent`
