# Unfolded Circle Remote Integration Development Guide

**For AI Agents Building New Integrations**

This guide captures the complete journey of building the Sony Audio Control integration, from initial API exploration to production deployment. Use it as a blueprint for developing integrations for any device or platform.

---

## Table of Contents

1. [Introduction & Quick Reference](#1-introduction--quick-reference)
2. [Development Workflow](#2-development-workflow)
3. [Key Components Deep Dive](#3-key-components-deep-dive)
4. [Critical Gotchas & Solutions](#4-critical-gotchas--solutions)
5. [Best Practices](#5-best-practices-from-sony-integration)
6. [Code Templates & Patterns](#6-code-templates--patterns)
7. [Resources & References](#7-resources--references)
8. [Step-by-Step Checklist](#8-step-by-step-checklist)
9. [Common Patterns](#9-common-patterns)
10. [Debugging Tips](#10-debugging-tips)

---

## 1. Introduction & Quick Reference

### What is the Unfolded Circle Remote?

The Unfolded Circle Remote (R2/R3) is a premium universal remote with:
- **7" touchscreen** for custom UI
- **Physical buttons** that can be programmed
- **Python-based integration framework** (`ucapi`)
- **Local network control** (no cloud required)
- **Extensible architecture** via custom integrations

### Integration Types

The `ucapi` framework supports multiple entity types:

| Entity Type | Use Case | Examples |
|-------------|----------|----------|
| **Remote** | Simple IR/button-style control | Sony Audio, Cable Box |
| **Media Player** | Playback with transport controls | Apple TV, Sonos |
| **Light** | Dimming, color control | Philips Hue |
| **Climate** | Temperature control | Nest, Ecobee |
| **Switch** | On/off devices | Smart plugs |
| **Cover** | Window shades, blinds | Somfy |

**For this guide, we focus on the Remote entity type**, which is the most flexible for devices with many commands.

### Quick Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Unfolded Circle Remote                      │
│  ┌────────────────────────────────────────────────────┐     │
│  │  Your Integration (Python + ucapi)                 │     │
│  │                                                     │     │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  │     │
│  │  │   Driver    │─▶│  API Client  │─▶│  Device  │  │     │
│  │  │ (Setup/UI)  │  │  (Commands)  │  │   API    │  │     │
│  │  └─────────────┘  └──────────────┘  └──────────┘  │     │
│  │         │                                           │     │
│  │         ▼                                           │     │
│  │  ┌─────────────┐                                   │     │
│  │  │   Entity    │                                   │     │
│  │  │  (Remote)   │                                   │     │
│  │  └─────────────┘                                   │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Essential Resources

- **Official Documentation**: [Unfolded Circle Docs](https://github.com/unfoldedcircle)
- **Reference Integration**: [LG TV Integration](https://github.com/albaintor/integration-lgtv)
- **This Integration**: Sony Audio Control (you're here!)
- **ucapi Library**: Python Integration API
- **Example Projects**: Check GitHub for `unfoldedcircle` repos

---

## 2. Development Workflow

### The Journey We Followed

Here's the exact process we used to build the Sony Audio Control integration:

#### Phase 1: API Discovery (Days 1-2)
```
1. Get device IP address
2. Read API documentation
3. Create test scripts to explore endpoints
4. Document working API calls
5. Identify required parameters and quirks
```

**Example from Sony integration:**
```python
# Initial test script to verify API works
import aiohttp
import asyncio

async def test_sony_api():
    async with aiohttp.ClientSession() as session:
        # Test getDeviceInfo
        payload = {
            "method": "getSystemInformation",
            "id": 1,
            "params": [],
            "version": "1.0"
        }
        async with session.post(
            "http://192.168.1.201:10000/sony/system",
            json=payload
        ) as response:
            data = await response.json(content_type=None)  # Sony quirk!
            print(data)

asyncio.run(test_sony_api())
```

**Key Learning**: Create throwaway test scripts first. Don't jump into the integration structure until you understand the API.

#### Phase 2: Client Library (Days 2-3)
```
1. Create async API client class
2. Implement core methods (power, volume, input)
3. Add error handling
4. Test connection and basic commands
```

**Example structure:**
```python
class DeviceAPIClient:
    def __init__(self, ip_address: str):
        self.base_url = f"http://{ip_address}:PORT"
        self.session = None
    
    async def connect(self) -> bool:
        """Test connection to device"""
        
    async def _call(self, service, method, params, version):
        """Internal API call handler"""
        
    async def set_power(self, state: str):
        """Power control"""
        
    async def set_volume(self, volume):
        """Volume control"""
```

#### Phase 3: Integration Scaffolding (Day 3)
```
1. Create project structure
2. Set up driver.json metadata
3. Implement basic driver.py
4. Test mDNS discovery
```

**Project structure:**
```
your-integration/
├── driver.json          # Integration metadata
├── src/
│   ├── __init__.py
│   ├── driver.py        # Main integration entry point
│   ├── client.py        # API client
│   ├── discovery.py     # Device discovery
│   ├── config.py        # Configuration storage
│   └── entity.py        # Entity creation
├── pyproject.toml       # Python dependencies
├── driver.spec          # PyInstaller build config
├── build.sh             # Local build script
├── package.sh           # Package creation
└── .github/
    └── workflows/
        ├── build.yml    # CI/CD for releases
        └── python-check.yml  # Code quality
```

#### Phase 4: Setup Flow (Days 4-5)
```
1. Design setup screens in driver.json
2. Implement setup handler
3. Add auto-discovery
4. Add manual IP fallback
5. Handle device verification
6. Store configuration
```

#### Phase 5: Entity Creation (Days 5-6)
```
1. Choose entity type (Remote for us)
2. Create entity with basic commands
3. Add button mappings
4. Design UI pages
5. Test on device
```

#### Phase 6: Advanced Features (Days 7-10)
```
1. Discover additional API capabilities
2. Implement dynamic command generation
3. Add settings cache
4. Create multiple UI pages
5. Add state polling
```

#### Phase 7: Polish & Deploy (Days 10-12)
```
1. Refactor for maintainability
2. Add error handling
3. Configure GitHub Actions
4. Build and test binary
5. Create release
```

### Total Timeline: ~12 days
- **Week 1**: API discovery → Working basic integration
- **Week 2**: Advanced features → Production ready

---

## 3. Key Components Deep Dive

### A. API Client Pattern (`src/sony_client.py`)

**Purpose**: Encapsulate all device API communication in one place.

**Key Design Decisions**:
1. **Async/await**: All I/O operations are non-blocking
2. **Session management**: Reuse HTTP session for performance
3. **Error handling**: Convert API errors to exceptions
4. **Type hints**: Make code self-documenting

**Complete Example**:

```python
import aiohttp
import logging
from typing import Any, Optional

_LOG = logging.getLogger(__name__)

class SonyAudioDevice:
    """Async client for Sony Audio Control API."""
    
    def __init__(self, ip_address: str, port: int = 10000):
        """Initialize client.
        
        Args:
            ip_address: Device IP address
            port: API port (default 10000)
        """
        self.ip_address = ip_address
        self.base_url = f"http://{ip_address}:{port}/sony"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def connect(self) -> bool:
        """Establish connection to device.
        
        Returns:
            True if connection successful
        """
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            # Test connection with getSystemInformation
            await self.get_device_info()
            _LOG.info("Connected to Sony device at %s", self.ip_address)
            return True
            
        except Exception as e:
            _LOG.error("Failed to connect: %s", e)
            return False
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _call(
        self,
        service: str,
        method: str,
        params: list[Any],
        version: str = "1.0"
    ) -> dict[str, Any]:
        """Make API call to device.
        
        Args:
            service: API service (e.g., "system", "audio", "avContent")
            method: API method name
            params: Method parameters
            version: API version
            
        Returns:
            API response dict
            
        Raises:
            SonyApiError: If API returns an error
        """
        if not self.session:
            raise Exception("Not connected")
        
        url = f"{self.base_url}/{service}"
        payload = {
            "method": method,
            "id": 1,
            "params": params,
            "version": version
        }
        
        try:
            async with self.session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                # CRITICAL: Sony returns JSON without proper Content-Type
                data = await response.json(content_type=None)
                
                # Check for API errors
                if "error" in data:
                    error = data["error"]
                    code = error[0] if isinstance(error, list) else error
                    message = error[1] if isinstance(error, list) and len(error) > 1 else "Unknown"
                    raise SonyApiError(code, message, method)
                
                return data
                
        except aiohttp.ClientError as e:
            _LOG.error("Connection error calling %s: %s", method, e)
            raise
    
    # Public API methods
    
    async def get_device_info(self) -> dict[str, Any]:
        """Get device information."""
        result = await self._call("system", "getSystemInformation", [], "1.0")
        return result["result"][0]
    
    async def set_power_status(self, status: str):
        """Set power status.
        
        Args:
            status: "active" or "standby"
        """
        await self._call("system", "setPowerStatus", [{"status": status}], "1.0")
    
    async def get_power_status(self) -> str:
        """Get current power status.
        
        Returns:
            "active" or "standby"
        """
        result = await self._call("system", "getPowerStatus", [], "1.0")
        return result["result"][0]["status"]
    
    async def set_volume(self, volume: int | str, zone: str = ""):
        """Set volume level.
        
        Args:
            volume: Absolute level (0-100) or relative ("+1", "-1")
            zone: Zone identifier (default "" for main zone)
        """
        params = [{"output": zone, "volume": str(volume)}]
        await self._call("audio", "setAudioVolume", params, "1.1")
    
    async def get_volume_info(self, zone: str = "") -> list[dict[str, Any]]:
        """Get volume information for zone.
        
        Args:
            zone: Zone identifier
            
        Returns:
            List of volume info dicts with keys:
            - volume: Current level
            - mute: "on" or "off"
            - minVolume: Minimum level
            - maxVolume: Maximum level
        """
        params = [{"output": zone}] if zone else []
        result = await self._call("audio", "getVolumeInformation", params, "1.1")
        return result["result"][0]

class SonyApiError(Exception):
    """Sony API error exception."""
    
    def __init__(self, code: int | str, message: str, method: str):
        self.code = code
        self.message = message
        self.method = method
        super().__init__(f"Sony API error {code} in {method}: {message}")
```

**Key Patterns**:

1. **Session reuse**: Create session once, close on cleanup
2. **Content-Type workaround**: `content_type=None` for broken servers
3. **Error extraction**: Convert API error format to exceptions
4. **Type safety**: Use type hints everywhere
5. **Logging**: Log at appropriate levels (debug for details, info for key events, error for failures)

---

### B. Device Discovery Pattern (`src/discovery.py`)

**Purpose**: Automatically find devices on the network using SSDP/mDNS.

**Why this matters**: Users love "it just works" - auto-discovery is magical!

**Complete Example**:

```python
import asyncio
import logging
from typing import Optional
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncZeroconf

_LOG = logging.getLogger(__name__)

class DeviceDiscovery(ServiceListener):
    """SSDP/mDNS device discovery."""
    
    def __init__(self):
        self.discovered_devices: list[dict] = []
    
    def add_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service is discovered."""
        info = zeroconf.get_service_info(service_type, name)
        if info:
            # Parse service info
            ip = self._parse_ip(info.addresses)
            port = info.port
            properties = self._parse_properties(info.properties)
            
            device = {
                "name": name,
                "ip": ip,
                "port": port,
                "model": properties.get("model", "Unknown"),
                "friendly_name": properties.get("friendlyName", name)
            }
            self.discovered_devices.append(device)
            _LOG.info("Discovered device: %s at %s", name, ip)
    
    def remove_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service disappears."""
        pass
    
    def update_service(self, zeroconf: Zeroconf, service_type: str, name: str):
        """Called when a service updates."""
        pass
    
    def _parse_ip(self, addresses: list) -> str:
        """Convert address bytes to IP string."""
        if addresses:
            return ".".join(str(b) for b in addresses[0])
        return ""
    
    def _parse_properties(self, props: dict) -> dict:
        """Parse mDNS properties."""
        result = {}
        for key, value in props.items():
            try:
                result[key.decode()] = value.decode()
            except:
                pass
        return result

async def discover_devices(timeout: int = 5) -> list[dict]:
    """Discover devices on network.
    
    Args:
        timeout: Discovery timeout in seconds
        
    Returns:
        List of discovered devices
    """
    aiozc = AsyncZeroconf()
    listener = DeviceDiscovery()
    
    # Browse for Sony Audio Control API services
    # Adjust service type for your device!
    browser = ServiceBrowser(
        aiozc.zeroconf,
        "_sony-audio._tcp.local.",  # Service type
        listener
    )
    
    try:
        # Wait for discoveries
        await asyncio.sleep(timeout)
        return listener.discovered_devices
        
    finally:
        await browser.async_cancel()
        await aiozc.async_close()

async def verify_device(ip: str) -> bool:
    """Verify device at IP is the correct type.
    
    Args:
        ip: Device IP address
        
    Returns:
        True if device is valid
    """
    try:
        device = SonyAudioDevice(ip)
        if await device.connect():
            info = await device.get_device_info()
            model = info.get("model", "")
            await device.close()
            
            # Check if it's a supported model
            supported = ["TA-AN1000", "STR-DN1080", "HT-A9"]
            return any(m in model for m in supported)
    except:
        pass
    
    return False
```

**Alternative: SSDP Discovery** (for devices using UPnP):

```python
import socket
import struct

def discover_ssdp(service_type: str, timeout: int = 3) -> list[str]:
    """Discover devices using SSDP.
    
    Args:
        service_type: Service URN (e.g., "urn:schemas-sony-com:service:ScalarWebAPI:1")
        timeout: Search timeout
        
    Returns:
        List of device locations (URLs)
    """
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    
    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
        "MAN: \"ssdp:discover\"\r\n"
        f"ST: {service_type}\r\n"
        "MX: 1\r\n"
        "\r\n"
    )
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(timeout)
    
    locations = []
    
    try:
        sock.sendto(msg.encode(), (SSDP_ADDR, SSDP_PORT))
        
        while True:
            try:
                data, addr = sock.recvfrom(2048)
                response = data.decode()
                
                # Parse LOCATION header
                for line in response.split("\r\n"):
                    if line.startswith("LOCATION:"):
                        locations.append(line.split(":", 1)[1].strip())
                        
            except socket.timeout:
                break
                
    finally:
        sock.close()
    
    return locations
```

---

### C. Driver Setup Pattern (`src/driver.py`)

**Purpose**: Handle integration lifecycle and setup flow.

**This is the heart of your integration!**

**Key Components**:

1. **Integration API initialization**
2. **Setup flow state machine**
3. **User input handling**
4. **Entity lifecycle**
5. **Command routing**

**Complete Example**:

```python
import asyncio
import logging
from typing import Any

import ucapi
from ucapi import remote

from client import SonyAudioDevice
from discovery import discover_devices, verify_device
from entity import create_remote_entity
from config import save_device_config

_LOG = logging.getLogger(__name__)

# Initialize event loop and API
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
api = ucapi.IntegrationAPI(loop)

# Global device storage
devices: dict[str, SonyAudioDevice] = {}

# Setup flow handler
@api.listens_to(ucapi.Events.SETUP_DRIVER)
async def handle_setup_driver(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup initiation.
    
    First screen: Choose discovery method
    """
    if msg.reconfigure:
        # User is reconfiguring - show current settings
        # For simplicity, we'll restart from scratch
        pass
    
    # Return first setup screen
    return ucapi.RequestUserInput(
        title="Setup Sony Audio Control",
        settings=[
            {
                "id": "discovery_method",
                "label": "Discovery Method",
                "field": {
                    "dropdown": {
                        "value": "auto",
                        "items": [
                            {"id": "auto", "label": "Auto-discover"},
                            {"id": "manual", "label": "Manual IP address"}
                        ]
                    }
                }
            },
            {
                "id": "device_ip",
                "label": "IP Address",
                "field": {
                    "text": {
                        "value": ""
                    }
                }
            }
        ]
    )

@api.listens_to(ucapi.Events.SETUP_DRIVER_USER_DATA)
async def handle_user_data_response(msg: ucapi.SetupDriverUserData) -> ucapi.SetupAction:
    """
    Handle user input from setup screens.
    
    State machine for multi-step setup.
    """
    input_values = msg.input_values
    
    # State 1: Discovery method chosen
    if "discovery_method" in input_values and "device_ip" not in input_values:
        method = input_values["discovery_method"]
        
        if method == "auto":
            # Run auto-discovery
            api.set_setup_progress(ucapi.SetupProgress.CONNECTING)
            discovered = await discover_devices(timeout=5)
            
            if not discovered:
                return ucapi.SetupError(
                    error_type=ucapi.IntegrationSetupError.NOT_FOUND,
                    error_msg="No devices found"
                )
            
            # Show discovered devices
            return ucapi.RequestUserInput(
                title="Select Device",
                settings=[
                    {
                        "id": "discovered_device",
                        "label": "Device",
                        "field": {
                            "dropdown": {
                                "value": discovered[0]["ip"],
                                "items": [
                                    {
                                        "id": d["ip"],
                                        "label": f"{d['friendly_name']} ({d['ip']})"
                                    }
                                    for d in discovered
                                ]
                            }
                        }
                    },
                    {
                        "id": "device_name",
                        "label": "Device Name",
                        "field": {
                            "text": {
                                "value": discovered[0]["friendly_name"]
                            }
                        }
                    }
                ]
            )
        else:
            # Manual IP - show input field
            return ucapi.RequestUserInput(
                title="Enter IP Address",
                settings=[
                    {
                        "id": "device_ip",
                        "label": "IP Address",
                        "field": {
                            "text": {
                                "value": ""
                            }
                        }
                    },
                    {
                        "id": "device_name",
                        "label": "Device Name",
                        "field": {
                            "text": {
                                "value": "Sony Audio"
                            }
                        }
                    }
                ]
            )
    
    # State 2: Device selected/entered, create entity
    if "device_ip" in input_values or "discovered_device" in input_values:
        ip = input_values.get("device_ip") or input_values.get("discovered_device")
        name = input_values.get("device_name", "Sony Audio")
        
        if not ip:
            return ucapi.SetupError(
                error_type=ucapi.IntegrationSetupError.OTHER,
                error_msg="Please enter an IP address"
            )
        
        # Verify device
        api.set_setup_progress(ucapi.SetupProgress.CONNECTING)
        
        try:
            device = SonyAudioDevice(ip)
            if not await device.connect():
                return ucapi.SetupError(
                    error_type=ucapi.IntegrationSetupError.CONNECTION_REFUSED,
                    error_msg=f"Could not connect to {ip}"
                )
            
            # Get device info for entity_id
            info = await device.get_device_info()
            entity_id = f"sony_{info.get('serialNumber', ip.replace('.', '_'))}"
            
            # Create entity
            entity = await create_remote_entity(device, entity_id, cmd_handler)
            
            # Store device
            devices[entity_id] = device
            
            # Add to available AND configured entities
            api.available_entities.add(entity)
            api.configured_entities.add(entity)
            
            # Save configuration
            save_device_config(entity_id, {"ip": ip, "name": name})
            
            _LOG.info("Setup complete for %s", entity_id)
            return ucapi.SetupComplete()
            
        except Exception as e:
            _LOG.error("Setup error: %s", e)
            return ucapi.SetupError(
                error_type=ucapi.IntegrationSetupError.OTHER,
                error_msg=str(e)
            )

# Command handler
async def cmd_handler(entity: ucapi.Remote, cmd_id: str, params: dict[str, Any] | None) -> ucapi.StatusCodes:
    """
    Handle remote entity commands.
    
    Routes commands to appropriate device methods.
    """
    _LOG.info("Command: %s for entity %s", cmd_id, entity.id)
    
    device = devices.get(entity.id)
    if not device:
        return ucapi.StatusCodes.SERVER_ERROR
    
    try:
        # Handle standard remote commands
        if cmd_id == remote.Commands.ON:
            await device.set_power_status("active")
            api.configured_entities.update_attributes(
                entity.id,
                {remote.Attributes.STATE: remote.States.ON}
            )
            return ucapi.StatusCodes.OK
        
        elif cmd_id == remote.Commands.OFF:
            await device.set_power_status("standby")
            api.configured_entities.update_attributes(
                entity.id,
                {remote.Attributes.STATE: remote.States.OFF}
            )
            return ucapi.StatusCodes.OK
        
        elif cmd_id == remote.Commands.SEND_CMD:
            command = params.get("command")
            
            if command == "VOLUME_UP":
                await device.set_volume("+1")
            elif command == "VOLUME_DOWN":
                await device.set_volume("-1")
            elif command == "MUTE_TOGGLE":
                # Get current mute state and toggle
                vol_info = await device.get_volume_info()
                current_mute = vol_info[0].get("mute", "off")
                await device.set_mute(current_mute == "off")
            else:
                _LOG.warning("Unknown command: %s", command)
                return ucapi.StatusCodes.BAD_REQUEST
            
            return ucapi.StatusCodes.OK
        
        return ucapi.StatusCodes.NOT_IMPLEMENTED
        
    except Exception as e:
        _LOG.error("Command error: %s", e)
        return ucapi.StatusCodes.SERVER_ERROR

# Event handlers
@api.listens_to(ucapi.Events.CONNECT)
async def on_connect():
    """Remote connected."""
    _LOG.info("Remote connected")
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)

@api.listens_to(ucapi.Events.DISCONNECT)
async def on_disconnect():
    """Remote disconnected."""
    _LOG.info("Remote disconnected")

@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_standby():
    """Remote entering standby."""
    _LOG.info("Remote entering standby")

@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_resume():
    """Remote exiting standby."""
    _LOG.info("Remote exiting standby")

# Main entry point
def main():
    """Start the integration."""
    _LOG.info("Starting Sony Audio Control integration")
    
    try:
        # Load saved devices and recreate entities
        from config import get_all_devices
        
        configured = get_all_devices()
        for device_id, config in configured.items():
            try:
                ip = config["ip"]
                device = SonyAudioDevice(ip)
                
                if loop.run_until_complete(device.connect()):
                    entity = loop.run_until_complete(
                        create_remote_entity(device, device_id, cmd_handler)
                    )
                    devices[device_id] = device
                    api.available_entities.add(entity)
                    api.configured_entities.add(entity)
                    _LOG.info("Restored device: %s", device_id)
                    
            except Exception as e:
                _LOG.error("Failed to restore %s: %s", device_id, e)
        
        # Run the API
        loop.run_until_complete(api.init("driver.json"))
        loop.run_forever()
        
    finally:
        # Clean up
        for device in devices.values():
            try:
                loop.run_until_complete(device.close())
            except:
                pass

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    main()
```

**Key Patterns**:

1. **State Machine**: Setup is multi-step, track state via input_values
2. **Progress Updates**: Use `api.set_setup_progress()` for long operations
3. **Error Handling**: Return appropriate SetupError types
4. **Entity Lifecycle**: Add to both available_entities AND configured_entities
5. **Configuration Persistence**: Save config to restore devices on restart

---

### D. Entity Creation Pattern (`src/entity.py`)

**Purpose**: Create the entity object that represents your device.

**For Remote entities**, you define:
- Simple commands (strings like "VOLUME_UP")
- Button mappings (physical button → command)
- UI pages (touchscreen layouts)

**Example**:

```python
import ucapi
from ucapi import remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_icon, create_ui_text

async def create_remote_entity(device, entity_id: str, cmd_handler) -> ucapi.Remote:
    """
    Create a remote entity for the device.
    
    Args:
        device: API client instance
        entity_id: Unique entity identifier
        cmd_handler: Command handler function
        
    Returns:
        Remote entity instance
    """
    # Get device info
    info = await device.get_device_info()
    device_name = info.get("model", "Device")
    
    # Define simple commands
    simple_commands = [
        "POWER_ON",
        "POWER_OFF",
        "VOLUME_UP",
        "VOLUME_DOWN",
        "MUTE_TOGGLE",
        "INPUT_HDMI1",
        "INPUT_HDMI2",
        "INPUT_BLUETOOTH",
    ]
    
    # Define button mappings (physical remote buttons)
    button_mapping = [
        create_btn_mapping(Buttons.POWER, "POWER_TOGGLE"),
        create_btn_mapping(Buttons.VOLUME_UP, "VOLUME_UP"),
        create_btn_mapping(Buttons.VOLUME_DOWN, "VOLUME_DOWN"),
        create_btn_mapping(Buttons.MUTE, "MUTE_TOGGLE"),
        create_btn_mapping(Buttons.DPAD_UP, "INPUT_HDMI1"),
        create_btn_mapping(Buttons.DPAD_DOWN, "INPUT_HDMI2"),
    ]
    
    # Create UI pages (touchscreen)
    ui_pages = []
    
    # Main control page
    main_page = UiPage("main", "Controls")
    main_page.add(create_ui_text(device_name, 0, 0, size=Size(4, 1)))
    
    # Power buttons (row, col)
    main_page.add(create_ui_icon("uc:power-on", 0, 1, cmd="POWER_ON"))
    main_page.add(create_ui_icon("uc:power-off", 1, 1, cmd="POWER_OFF"))
    
    # Volume controls
    main_page.add(create_ui_icon("uc:volume-up", 0, 2, cmd="VOLUME_UP"))
    main_page.add(create_ui_icon("uc:volume-down", 1, 2, cmd="VOLUME_DOWN"))
    main_page.add(create_ui_icon("uc:mute", 2, 2, cmd="MUTE_TOGGLE"))
    
    ui_pages.append(main_page)
    
    # Inputs page
    inputs_page = UiPage("inputs", "Inputs")
    inputs_page.add(create_ui_text("Select Input", 0, 0, size=Size(4, 1)))
    inputs_page.add(create_ui_icon("uc:hdmi", 0, 1, cmd="INPUT_HDMI1"))
    inputs_page.add(create_ui_text("HDMI 1", 0, 2, size=Size(1, 1)))
    inputs_page.add(create_ui_icon("uc:hdmi", 1, 1, cmd="INPUT_HDMI2"))
    inputs_page.add(create_ui_text("HDMI 2", 1, 2, size=Size(1, 1)))
    inputs_page.add(create_ui_icon("uc:bluetooth", 2, 1, cmd="INPUT_BLUETOOTH"))
    inputs_page.add(create_ui_text("Bluetooth", 2, 2, size=Size(1, 1)))
    
    ui_pages.append(inputs_page)
    
    # Create the entity
    entity = ucapi.Remote(
        entity_id,
        device_name,
        [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
        {remote.Attributes.STATE: remote.States.UNKNOWN},
        simple_commands=simple_commands,
        button_mapping=button_mapping,
        ui_pages=ui_pages,
        cmd_handler=cmd_handler
    )
    
    return entity
```

**UI Layout**:
- Grid is **4 columns × unlimited rows**
- Each item has (col, row, size)
- Icons use "uc:iconname" from [Unfolded Circle icon set](https://www.unfoldedcircle.com/support/remote-two/dock-hardware-integration/custom-icons/)

---

### E. Settings Cache Pattern (`src/settings_cache.py`)

**Purpose**: Dynamically discover device capabilities instead of hardcoding.

**Why this matters**: Your integration becomes **universal** - works with any model, any firmware version, any user customization.

**Example**:

```python
from datetime import datetime
from typing import Any, Optional
import logging

_LOG = logging.getLogger(__name__)

class DeviceSettingsCache:
    """Cache for dynamically discovered device settings."""
    
    def __init__(self, device):
        self.device = device
        self.sound_settings: list[dict[str, Any]] = []
        self.speaker_settings: list[dict[str, Any]] = []
        self.zones: list[int] = []
        self.last_refresh: Optional[datetime] = None
    
    async def refresh(self) -> None:
        """Discover all device capabilities."""
        _LOG.info("Refreshing settings cache...")
        
        # Discover sound settings
        try:
            self.sound_settings = await self.device.get_sound_settings()
            _LOG.info("Found %d sound settings", len(self.sound_settings))
        except Exception as e:
            _LOG.warning("Could not get sound settings: %s", e)
        
        # Discover speaker settings
        try:
            self.speaker_settings = await self.device.get_speaker_settings()
            _LOG.info("Found %d speaker settings", len(self.speaker_settings))
        except Exception as e:
            _LOG.warning("Could not get speaker settings: %s", e)
        
        # Discover zones
        try:
            self.zones = await self._discover_zones()
            _LOG.info("Found %d zones", len(self.zones))
        except Exception as e:
            _LOG.warning("Could not discover zones: %s", e)
        
        self.last_refresh = datetime.now()
    
    async def _discover_zones(self) -> list[int]:
        """Discover available zones."""
        zones = [1]  # Main zone always exists
        
        for zone_num in [2, 3, 4]:
            try:
                # Try to get volume info for this zone
                await self.device.get_zone_volume(zone_num)
                zones.append(zone_num)
            except:
                pass
        
        return zones
    
    def get_setting_by_name(self, name: str) -> Optional[dict]:
        """Find a setting by name."""
        for setting in self.sound_settings + self.speaker_settings:
            if setting.get("target") == name:
                return setting
        return None
    
    def validate_setting_value(self, setting_name: str, value: str) -> bool:
        """Check if a value is valid for a setting."""
        setting = self.get_setting_by_name(setting_name)
        if not setting:
            return False
        
        # Check if value is in candidates
        candidates = setting.get("candidate", [])
        valid_values = [c.get("value") for c in candidates]
        return value in valid_values
```

**Usage in entity creation**:

```python
async def create_remote_entity(device, entity_id, cmd_handler):
    # Create and refresh cache
    cache = DeviceSettingsCache(device)
    await cache.refresh()
    
    # Generate commands dynamically from cache
    simple_commands = ["POWER_ON", "POWER_OFF"]
    
    # Add sound field commands from discovered settings
    sound_field = cache.get_setting_by_name("soundField")
    if sound_field:
        for candidate in sound_field.get("candidate", []):
            value = candidate["value"]
            cmd = f"SOUND_FIELD_{value.upper()}"
            simple_commands.append(cmd)
    
    # Add zone commands from discovered zones
    for zone in cache.zones:
        simple_commands.extend([
            f"ZONE{zone}_VOLUME_UP",
            f"ZONE{zone}_VOLUME_DOWN",
            f"ZONE{zone}_MUTE_TOGGLE"
        ])
    
    # Create entity...
```

**Result**: Your integration automatically supports:
- Different device models with different features
- Firmware updates that add new capabilities
- User-customized settings

---

## 4. Critical Gotchas & Solutions

### Import Issues

**Problem**: Relative imports fail in PyInstaller builds.

```python
# ❌ DON'T DO THIS
from .sony_client import SonyAudioDevice
from .config import save_config

# ✅ DO THIS
from sony_client import SonyAudioDevice
from config import save_config
```

**Why**: PyInstaller changes the module structure. Use absolute imports from `src/`.

---

### Event Loop Management

**Problem**: `RuntimeError: There is no current event loop`

```python
# ❌ OLD WAY (deprecated)
loop = asyncio.get_event_loop()

# ✅ NEW WAY
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
```

**Why**: Python 3.10+ deprecated implicit event loop creation.

---

### API Quirks

**Problem 1**: Server returns JSON without `Content-Type: application/json`

```python
# ❌ This fails with "Attempt to decode JSON with unexpected mimetype"
data = await response.json()

# ✅ Force JSON parsing
data = await response.json(content_type=None)
```

**Problem 2**: API requires empty string parameters

```python
# ❌ Omitting parameter causes "Illegal Argument"
await self._call("audio", "getVolume", [], "1.0")

# ✅ Pass empty string explicitly
await self._call("audio", "getVolume", [{"output": ""}], "1.0")
```

**Lesson**: Test thoroughly! APIs often have undocumented requirements.

---

### Build & Packaging

**Problem**: PyInstaller can't find your modules.

**Solution**: Create a `driver.spec` file:

```python
# driver.spec
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(
    ['src/driver.py'],
    pathex=['src'],  # Critical!
    binaries=[],
    datas=[('driver.json', '.')],
    hiddenimports=[
        'config',
        'discovery',
        'remote_entity',
        'settings_cache',
        'sony_client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='driver',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='driver',
)
```

**Build script** (`build.sh`):

```bash
#!/bin/bash
set -e

echo "Building Sony Audio Control Integration..."

# Use Unfolded Circle's Docker image for aarch64
docker run --rm -v "$(pwd)":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11 \
    bash -c "cd /workspace && pyinstaller driver.spec"

echo "Build complete!"
```

---

### Setup Flow Pitfalls

**Problem**: Entity not showing up after setup.

```python
# ❌ Only adds to available_entities
api.available_entities.add(entity)

# ✅ Add to BOTH
api.available_entities.add(entity)
api.configured_entities.add(entity)
```

**Why**: `available_entities` = what *can* be added. `configured_entities` = what *is* added.

**Problem**: Setup screen loops.

```python
# ❌ Checking wrong fields
if "discovered_device" in input_values:
    # Show confirmation
    return ucapi.RequestUserInput(...)

# ✅ Check both fields to detect confirmation state
if "discovered_device" in input_values and "device_name" in input_values:
    # User confirmed, create entity
    ...
elif "discovered_device" in input_values:
    # Just selected, show confirmation
    ...
```

---

### GitHub Actions

**Problem**: Workflow not triggering.

```yaml
# ❌ If your branch is 'master'
on:
  push:
    branches: [main]  # Won't trigger!

# ✅ Match your actual branch
on:
  push:
    branches: [master]
```

**Problem**: "Resource not accessible by integration"

```yaml
# ❌ Missing permissions
jobs:
  build:
    runs-on: ubuntu-latest

# ✅ Add permissions
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write  # For creating releases
```

---

## 5. Best Practices from Sony Integration

### Architecture Decisions

**1. Dynamic Discovery Over Hardcoding**

We started with hardcoded sound modes:

```python
# ❌ Version 0.1.0 - Hardcoded
commands = [
    "SOUND_FIELD_2CH_STEREO",
    "SOUND_FIELD_DOLBY_MODE",
    "SOUND_FIELD_DTS_MODE",
]
```

We evolved to dynamic discovery:

```python
# ✅ Version 0.3.0 - Dynamic
cache = DeviceSettingsCache(device)
await cache.refresh()

commands = []
for setting in cache.sound_settings:
    if setting["target"] == "soundField":
        for candidate in setting["candidate"]:
            cmd = f"SOUND_FIELD_{candidate['value'].upper()}"
            commands.append(cmd)
```

**Why**: Works with ANY Sony model, ANY firmware version, ANY user customization.

**2. Separation of Concerns**

```
src/
├── sony_client.py      # API communication only
├── discovery.py        # Device discovery only
├── settings_cache.py   # Capability discovery only
├── remote_entity.py    # Entity creation only
├── driver.py           # Orchestration only
└── config.py           # Persistence only
```

**Why**: Each file has ONE responsibility. Easy to test, debug, and modify.

**3. Error Handling Philosophy**

```python
# ❌ Silent failures
try:
    await device.set_volume(50)
except:
    pass  # User has no idea what went wrong!

# ✅ Graceful degradation with logging
try:
    await device.set_volume(50)
except Exception as e:
    _LOG.warning("Could not set volume: %s", e)
    # Feature disabled, but integration still works
```

**Why**: Integration should never crash. Log errors, handle gracefully, continue operation.

---

### Testing Strategy

**Phase 1: API Exploration** (scripts)

```python
# test_api.py - Throwaway script
import asyncio
from sony_client import SonyAudioDevice

async def main():
    device = SonyAudioDevice("192.168.1.201")
    await device.connect()
    
    # Test each API method
    print(await device.get_device_info())
    print(await device.get_volume_info())
    print(await device.get_sound_settings())
    
    await device.close()

asyncio.run(main())
```

**Phase 2: Local Testing** (with uv)

```bash
# Run integration locally
uv run src/driver.py

# Check logs
# Connect from Remote app
# Test all features
```

**Phase 3: Device Testing**

```bash
# Build binary
./build.sh
./package.sh

# Upload to Remote
# Install integration
# Full end-to-end testing
```

**Phase 4: Real-World Testing**

- Test with physical remote buttons
- Test with touchscreen UI
- Test power cycles
- Test network interruptions
- Test multiple zones/features

---

## 6. Code Templates & Patterns

### Template: Minimal Remote Integration

Here's a complete, minimal integration in one file:

```python
#!/usr/bin/env python3
"""Minimal Remote Integration Template."""
import asyncio
import logging
import aiohttp
import ucapi
from ucapi import remote

_LOG = logging.getLogger(__name__)

# Device API Client
class DeviceClient:
    def __init__(self, ip: str):
        self.ip = ip
        self.session = None
    
    async def connect(self) -> bool:
        self.session = aiohttp.ClientSession()
        # Test connection
        return True
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def power_on(self):
        # Implement your API call
        pass
    
    async def power_off(self):
        # Implement your API call
        pass

# Setup integration
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
api = ucapi.IntegrationAPI(loop)
devices = {}

# Setup handler
@api.listens_to(ucapi.Events.SETUP_DRIVER)
async def setup(msg: ucapi.SetupDriver):
    return ucapi.RequestUserInput(
        title="Setup Device",
        settings=[{
            "id": "ip",
            "label": "IP Address",
            "field": {"text": {"value": ""}}
        }]
    )

@api.listens_to(ucapi.Events.SETUP_DRIVER_USER_DATA)
async def setup_data(msg: ucapi.SetupDriverUserData):
    ip = msg.input_values.get("ip")
    
    device = DeviceClient(ip)
    if not await device.connect():
        return ucapi.SetupError(
            error_type=ucapi.IntegrationSetupError.CONNECTION_REFUSED
        )
    
    entity_id = f"device_{ip.replace('.', '_')}"
    
    # Create entity
    entity = ucapi.Remote(
        entity_id,
        "My Device",
        [remote.Features.ON_OFF],
        {remote.Attributes.STATE: remote.States.UNKNOWN},
        simple_commands=["POWER_ON", "POWER_OFF"],
        cmd_handler=cmd_handler
    )
    
    devices[entity_id] = device
    api.available_entities.add(entity)
    api.configured_entities.add(entity)
    
    return ucapi.SetupComplete()

# Command handler
async def cmd_handler(entity, cmd_id, params):
    device = devices.get(entity.id)
    
    if cmd_id == remote.Commands.ON:
        await device.power_on()
        return ucapi.StatusCodes.OK
    elif cmd_id == remote.Commands.OFF:
        await device.power_off()
        return ucapi.StatusCodes.OK
    
    return ucapi.StatusCodes.NOT_IMPLEMENTED

# Main
def main():
    logging.basicConfig(level=logging.INFO)
    loop.run_until_complete(api.init("driver.json"))
    loop.run_forever()

if __name__ == "__main__":
    main()
```

That's it! A complete working integration in ~100 lines.

---

### Pattern: Paginated API Results

Some APIs return results in pages:

```python
async def get_all_items(self) -> list[dict]:
    """Get all items from paginated API."""
    all_items = []
    page = 0
    
    while True:
        result = await self._call(
            "content",
            "getContentList",
            [{"start": page * 100, "count": 100}],
            "1.0"
        )
        
        items = result["result"][0]
        if not items:
            break
        
        all_items.extend(items)
        page += 1
    
    return all_items
```

---

### Pattern: WebSocket Notifications

For real-time updates:

```python
async def subscribe_to_notifications(self):
    """Subscribe to device notifications via WebSocket."""
    ws_url = f"ws://{self.ip}:10000/sony/audio"
    
    async with self.session.ws_connect(ws_url) as ws:
        # Enable notifications
        await ws.send_json({
            "method": "switchNotifications",
            "id": 1,
            "params": [{
                "enabled": [
                    {"name": "notifyVolumeInformation", "version": "1.0"},
                    {"name": "notifyPowerStatus", "version": "1.0"}
                ],
                "disabled": []
            }],
            "version": "1.0"
        })
        
        # Listen for notifications
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.json()
                if "method" in data:
                    # Handle notification
                    method = data["method"]
                    params = data["params"][0]
                    
                    if method == "notifyVolumeInformation":
                        self._handle_volume_change(params)
                    elif method == "notifyPowerStatus":
                        self._handle_power_change(params)
```

---

### Pattern: State Polling

When WebSocket isn't available:

```python
async def poll_device_state(entity_id: str, device, interval: int = 30):
    """Poll device state periodically."""
    while entity_id in devices:
        try:
            await asyncio.sleep(interval)
            
            # Get current state
            status = await device.get_power_status()
            new_state = remote.States.ON if status == "active" else remote.States.OFF
            
            # Update if changed
            current_entity = api.configured_entities.get(entity_id)
            if current_entity:
                current_state = current_entity.attributes.get(remote.Attributes.STATE)
                if current_state != new_state:
                    api.configured_entities.update_attributes(
                        entity_id,
                        {remote.Attributes.STATE: new_state}
                    )
                    _LOG.info("State changed to %s", new_state)
                    
        except Exception as e:
            _LOG.debug("Poll error: %s", e)

# Start polling task
polling_task = asyncio.create_task(poll_device_state(entity_id, device))
```

---

## 7. Resources & References

### Official Documentation

- **Unfolded Circle**: https://github.com/unfoldedcircle
- **Integration API**: https://github.com/unfoldedcircle/integration-python-library
- **Remote Core API**: https://github.com/unfoldedcircle/core-api

### Example Integrations

- **LG TV**: https://github.com/albaintor/integration-lgtv (comprehensive, production-ready)
- **Sony Audio**: This project! (dynamic discovery, multi-zone)
- **Home Assistant**: https://github.com/unfoldedcircle/integration-home-assistant

### Python Libraries

- **ucapi**: `pip install ucapi` - Integration framework
- **aiohttp**: `pip install aiohttp` - Async HTTP client
- **zeroconf**: `pip install zeroconf` - mDNS/SSDP discovery

### Build Tools

- **PyInstaller**: Package Python apps
- **Docker**: Unfolded Circle provides aarch64 build image
- **GitHub Actions**: Automated builds and releases

---

## 8. Step-by-Step Checklist

Use this checklist for your next integration:

### Planning Phase
- [ ] Research target device API
- [ ] Identify authentication requirements
- [ ] Document all endpoints and parameters
- [ ] Test API calls manually (curl, Postman, etc.)
- [ ] Decide on entity type (Remote, Media Player, etc.)

### Development Phase
- [ ] Create project structure
- [ ] Set up Python environment (pyproject.toml, uv)
- [ ] Create API client class
- [ ] Test API client with throwaway scripts
- [ ] Implement device discovery (SSDP/mDNS)
- [ ] Create driver.json metadata
- [ ] Implement setup flow handler
- [ ] Create entity type
- [ ] Implement command handler
- [ ] Design UI pages
- [ ] Add error handling
- [ ] Add logging

### Testing Phase
- [ ] Test locally with `uv run`
- [ ] Test all commands
- [ ] Test error conditions
- [ ] Create PyInstaller spec
- [ ] Test build process
- [ ] Test on actual Remote device
- [ ] Test physical buttons
- [ ] Test UI touchscreen
- [ ] Test device reconnection
- [ ] Test multiple devices

### Deployment Phase
- [ ] Set up GitHub repository
- [ ] Configure GitHub Actions
- [ ] Add code quality checks (pylint, etc.)
- [ ] Create build workflow
- [ ] Test automated build
- [ ] Create release
- [ ] Write documentation
- [ ] Share with community

---

## 9. Common Patterns

### Pattern: Multi-Zone Control

Many AV devices support multiple zones (rooms):

```python
class MultiZoneDevice:
    async def get_zones(self) -> list[int]:
        """Discover available zones."""
        zones = [1]  # Main always exists
        
        for zone_num in range(2, 10):
            try:
                await self.get_zone_status(zone_num)
                zones.append(zone_num)
            except:
                break
        
        return zones
    
    async def set_zone_volume(self, zone: int, volume: int):
        """Set volume for specific zone."""
        await self._call("audio", "setVolume", [{
            "zone": zone,
            "volume": volume
        }])
    
    async def set_zone_input(self, zone: int, input_name: str):
        """Set input source for specific zone."""
        await self._call("avContent", "setInput", [{
            "zone": zone,
            "input": input_name
        }])
```

**Entity creation**:

```python
# Create commands dynamically for each zone
zones = await device.get_zones()
for zone in zones:
    commands.extend([
        f"ZONE{zone}_VOLUME_UP",
        f"ZONE{zone}_VOLUME_DOWN",
        f"ZONE{zone}_MUTE_TOGGLE",
    ])
```

---

### Pattern: Dynamic UI Generation

Instead of hardcoding UI layouts, generate them from device capabilities:

```python
def create_ui_pages(device_info: dict, commands: list[str]) -> list[UiPage]:
    """Generate UI pages based on device capabilities."""
    pages = []
    
    # Main page (always present)
    main_page = UiPage("main", "Controls")
    # ... add basic controls
    pages.append(main_page)
    
    # Only add inputs page if device has inputs
    if any(cmd.startswith("INPUT_") for cmd in commands):
        inputs_page = UiPage("inputs", "Inputs")
        
        row = 1
        col = 0
        for cmd in commands:
            if cmd.startswith("INPUT_"):
                input_name = cmd.replace("INPUT_", "").replace("_", " ")
                inputs_page.add(create_ui_icon("uc:input", col, row, cmd=cmd))
                inputs_page.add(create_ui_text(input_name, col, row+1))
                
                col += 1
                if col >= 4:
                    col = 0
                    row += 2
        
        pages.append(inputs_page)
    
    # Only add zones page if multi-zone
    if any(cmd.startswith("ZONE") for cmd in commands):
        zones_page = UiPage("zones", "Zones")
        # ... add zone controls
        pages.append(zones_page)
    
    return pages
```

---

### Pattern: Input Discovery with Labels

Many devices let users rename inputs:

```python
async def discover_inputs(self) -> list[dict]:
    """Get all inputs with user-assigned labels."""
    inputs = []
    
    # Get physical inputs
    result = await self._call("avContent", "getInputList", [], "1.0")
    
    for input_info in result["result"][0]:
        inputs.append({
            "uri": input_info["uri"],              # extInput:hdmi?port=1
            "title": input_info.get("title", ""),  # "Apple TV" (user label)
            "connection": input_info.get("connection", ""),  # "hdmi"
            "label": input_info.get("label", "")   # "HDMI 1" (default)
        })
    
    return inputs

# Use in entity creation
async def create_entity(device, entity_id, cmd_handler):
    inputs = await device.discover_inputs()
    
    commands = []
    for input_info in inputs:
        # Use URI as stable identifier
        uri = input_info["uri"]
        # Use user's label for display
        title = input_info["title"] or input_info["label"]
        
        # Create command
        cmd = f"INPUT_{uri.upper().replace(':', '_').replace('?', '_')}"
        commands.append(cmd)
        
        # Store mapping
        input_map[cmd] = uri
    
    # ...
```

---

## 10. Debugging Tips

### Reading Remote Logs

1. **Enable integration logging** on Remote:
   - Settings → Integrations → Your Integration → Settings
   - Enable "Debug Logging"

2. **Download logs**:
   - Settings → Integrations → Your Integration → Download Logs
   - Logs are in `/tmp/` on the device

3. **Log format**:
```
2024-11-02 14:32:15 | INFO     | __main__ | Command: VOLUME_UP
2024-11-02 14:32:15 | DEBUG    | sony_client | Calling setAudioVolume
2024-11-02 14:32:15 | ERROR    | sony_client | API error: 12 (No Such Method)
```

### Common Error Patterns

**"Module not found" errors**:
- Check `driver.spec` includes all modules in `hiddenimports`
- Use absolute imports, not relative
- Verify all files have `__init__.py` in directories

**"Connection refused"**:
- Check device IP address
- Check firewall rules
- Verify device is on same network
- Test with curl/wget first

**"No Such Method" API errors**:
- Check API version number
- Check method name spelling
- Check required parameters
- Read API documentation carefully

**Setup screen loops**:
- Add debug logging to setup handlers
- Check input_values keys
- Verify state machine logic
- Test with different input combinations

### Network Troubleshooting

**Test device reachability**:
```bash
# Ping device
ping 192.168.1.201

# Test HTTP port
nc -zv 192.168.1.201 10000

# Test API endpoint
curl -X POST http://192.168.1.201:10000/sony/system \
  -H "Content-Type: application/json" \
  -d '{"method":"getSystemInformation","id":1,"params":[],"version":"1.0"}'
```

**Capture network traffic**:
```bash
# On macOS/Linux
sudo tcpdump -i any -A host 192.168.1.201

# With Wireshark
# Filter: ip.addr == 192.168.1.201 && http
```

### Build Issues

**PyInstaller errors**:
```bash
# Clean build
rm -rf build/ dist/ *.spec

# Rebuild
pyinstaller --clean driver.spec

# Check included files
pyinstaller --onefile --collect-all ucapi src/driver.py
```

**Docker build errors**:
```bash
# Pull latest image
docker pull docker.io/unfoldedcircle/r2-pyinstaller:3.11

# Build with verbose output
docker run --rm -v "$(pwd)":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11 \
    bash -c "cd /workspace && pyinstaller --log-level DEBUG driver.spec"
```

---

## Appendix: Lessons Learned from Sony Integration

### What Went Well

1. **API Discovery First**: We spent 2 days just exploring the API before writing integration code. This saved time later.

2. **Dynamic Discovery**: Refactoring from hardcoded to dynamic (v0.2.0 → v0.3.0) made the integration universal.

3. **Iterative Development**: We shipped v0.1.0 with basic features, then added advanced features in v0.2.0 and v0.3.0.

4. **Reference Implementation**: Using the LG TV integration as a reference saved days of trial and error.

### What We'd Do Differently

1. **Start with Settings Cache**: We wish we'd implemented dynamic discovery from day 1 instead of refactoring later.

2. **More Test Scripts**: We should have created more throwaway test scripts to explore edge cases.

3. **Documentation Inline**: We added documentation at the end. Should have documented while coding.

4. **Error Handling Earlier**: We added proper error handling after encountering bugs. Should have done it upfront.

### Key Insights

1. **Every API is Different**: Don't assume your device works like others. Test everything.

2. **Users Customize**: Users rename inputs, change settings, update firmware. Your integration must adapt.

3. **Network is Unreliable**: Devices reboot, networks drop, IPs change. Handle gracefully.

4. **Logging is Critical**: You can't debug issues without logs. Log everything important.

5. **Start Simple**: Get basic power/volume working, then add advanced features.

---

## Final Thoughts for AI Agents

Building an Unfolded Circle integration is a journey:

- **Week 1**: You're learning the API, fighting with imports, confused by setup flows
- **Week 2**: Things click into place, features come together, it actually works!
- **Week 3**: Polish, refine, ship something you're proud of

**The most important advice**: Don't try to build everything at once. Ship a minimal working version (power + volume + input), then iterate with advanced features.

The Sony Audio integration went through 3 major versions:
- **v0.1.0**: Basic controls (power, volume, inputs)
- **v0.2.0**: Advanced features (sound modes, zones, speakers)
- **v0.3.0**: Dynamic discovery (universal device support)

Each version was fully functional and useful. We learned and improved with each iteration.

**You can do this!** This guide captures everything we learned. Follow the patterns, avoid the gotchas, and you'll have a working integration faster than you think.

Good luck, and happy coding! 🚀

---

*This guide was created from the actual development of the Sony Audio Control integration for Unfolded Circle Remote.*

*Questions? Check the resources section or study the Sony integration code!*

