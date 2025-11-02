"""
Sony device discovery via SSDP/UPnP.

Discovers Sony Audio Control API compatible devices on the local network.
"""

import asyncio
import logging
import socket
import xml.etree.ElementTree as ET
from typing import Any

import aiohttp

_LOG = logging.getLogger(__name__)

# SSDP discovery constants
SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_MX = 3  # Max wait time for responses

# Service types to search for
# Some Sony devices (like TA-AN1000) only respond to MediaRenderer
SSDP_SERVICE_TYPES = [
    "urn:schemas-sony-com:service:ScalarWebAPI:1",  # Sony API (receivers)
    "urn:schemas-upnp-org:device:MediaRenderer:1",  # Media Renderer (soundbars)
]


async def discover_sony_devices(timeout: int = 5) -> list[dict[str, Any]]:
    """
    Discover Sony Audio Control API devices on the network via SSDP.

    Args:
        timeout: Discovery timeout in seconds

    Returns:
        List of discovered devices with metadata:
        [{
            "model": "TA-AN1000",
            "name": "Sony Soundbar",
            "ip": "192.168.1.201",
            "base_url": "http://192.168.1.201:10000/sony",
            "location": "http://192.168.1.201:61000/dd.xml"
        }, ...]
    """
    devices = []
    found_locations = set()

    try:
        _LOG.info("Starting SSDP discovery for Sony devices...")

        # Search for each service type
        for service_type in SSDP_SERVICE_TYPES:
            _LOG.debug("Searching for service type: %s", service_type)

            # Create M-SEARCH message for this service type
            msearch_msg = (
                "M-SEARCH * HTTP/1.1\r\n"
                f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
                'MAN: "ssdp:discover"\r\n'
                f"MX: {SSDP_MX}\r\n"
                f"ST: {service_type}\r\n"
                "\r\n"
            ).encode("utf-8")

            # Create UDP socket for SSDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(timeout / len(SSDP_SERVICE_TYPES))  # Split timeout across service types

            try:
                # Send M-SEARCH request
                sock.sendto(msearch_msg, (SSDP_ADDR, SSDP_PORT))

                # Collect responses
                start_time = asyncio.get_event_loop().time()
                search_timeout = timeout / len(SSDP_SERVICE_TYPES)
                while (asyncio.get_event_loop().time() - start_time) < search_timeout:
                    try:
                        data, addr = sock.recvfrom(4096)
                        response = data.decode("utf-8", errors="ignore")

                        # Parse SSDP response
                        location = None
                        st = None
                        server = None
                        for line in response.split("\r\n"):
                            line_lower = line.lower()
                            if line_lower.startswith("location:"):
                                location = line.split(":", 1)[1].strip()
                            elif line_lower.startswith("st:"):
                                st = line.split(":", 1)[1].strip()
                            elif line_lower.startswith("server:"):
                                server = line.split(":", 1)[1].strip()

                        # Check if this is a Sony device and we haven't seen it yet
                        # Accept if it matches our service type OR if it's clearly a Sony device
                        is_sony = (
                            (st and st in SSDP_SERVICE_TYPES)
                            or (server and "sony" in server.lower())
                            or (location and "sony" in location.lower())
                        )

                        if location and is_sony and location not in found_locations:
                            found_locations.add(location)
                            _LOG.info("Found potential Sony device at %s (from %s)", location, addr[0])

                            # Fetch and parse device descriptor
                            device_info = await _fetch_device_info(location, addr[0])
                            if device_info:
                                devices.append(device_info)

                    except socket.timeout:
                        break
                    except Exception as e:
                        _LOG.debug("Error receiving SSDP response: %s", e)

            finally:
                sock.close()

    except Exception as e:
        _LOG.error("SSDP discovery error: %s", e)

    _LOG.info("Discovery complete, found %d device(s)", len(devices))
    return devices


async def _fetch_device_info(location: str, known_ip: str | None = None) -> dict[str, Any] | None:
    """
    Fetch and parse device descriptor XML.

    Args:
        location: URL to device descriptor XML
        known_ip: Known IP address from SSDP response (fallback)

    Returns:
        Device info dictionary or None if parsing fails
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(location, timeout=aiohttp.ClientTimeout(total=3)) as response:
                xml_data = await response.text()

        # Parse XML to extract device information
        root = ET.fromstring(xml_data)

        # Define namespaces
        namespaces = {
            "": "urn:schemas-upnp-org:device-1-0",
            "av": "urn:schemas-sony-com:av",
        }

        # Extract device info
        device = root.find(".//device", namespaces)
        if device is None:
            _LOG.warning("No device element found in descriptor")
            return None

        friendly_name = device.findtext("friendlyName", "", namespaces)
        model_name = device.findtext("modelName", "", namespaces)
        manufacturer = device.findtext("manufacturer", "", namespaces)

        # Check if this is actually a Sony device
        is_sony_device = (manufacturer and "sony" in manufacturer.lower()) or (
            model_name and any(sony_model in model_name.upper() for sony_model in ["TA-", "STR-", "HT-", "SRS-"])
        )

        if not is_sony_device:
            _LOG.debug("Device doesn't appear to be a Sony audio device: %s", model_name)
            return None

        # Extract Sony-specific API base URL
        base_url = None

        # First try X_ScalarWebAPI_DeviceInfo (TA-AN1000 and newer devices)
        device_info = device.find(".//av:X_ScalarWebAPI_DeviceInfo", namespaces)
        if device_info is not None:
            base_url_elem = device_info.find(".//av:X_ScalarWebAPI_BaseURL", namespaces)
            if base_url_elem is not None and base_url_elem.text:
                base_url = base_url_elem.text
                _LOG.debug("Found base URL in X_ScalarWebAPI_DeviceInfo: %s", base_url)

        # Fallback: try old X_ScalarWebAPI_ServiceList format (older receivers)
        if not base_url:
            service_list = device.find(".//av:X_ScalarWebAPI_ServiceList", namespaces)
            if service_list is not None:
                for service in service_list.findall(".//av:X_ScalarWebAPI_Service", namespaces):
                    base_url_elem = service.find(".//av:X_ScalarWebAPI_BaseURL", namespaces)
                    if base_url_elem is not None and base_url_elem.text:
                        base_url = base_url_elem.text
                        _LOG.debug("Found base URL in X_ScalarWebAPI_ServiceList: %s", base_url)
                        break

        # If no base URL in descriptor, try to construct it from known IP
        # (common for MediaRenderer descriptors which don't include ScalarWebAPI info)
        if not base_url and known_ip:
            _LOG.info("No API URL in descriptor, using default for Sony device at %s", known_ip)
            base_url = f"http://{known_ip}:10000/sony"

        if not base_url:
            _LOG.warning("Could not determine API base URL for device")
            return None

        # Extract IP from base URL
        import re

        ip_match = re.search(r"//([^:]+)", base_url)
        ip_address = ip_match.group(1) if ip_match else None

        # Fallback to known IP if we can't extract from base URL
        if not ip_address:
            if known_ip:
                _LOG.debug("Using known IP %s as fallback", known_ip)
                ip_address = known_ip
                # Construct base URL with default port
                base_url = f"http://{known_ip}:10000/sony"
            else:
                _LOG.warning("Could not extract IP address from base URL: %s", base_url)
                return None

        device_info = {
            "name": friendly_name or model_name or "Sony Device",
            "model": model_name or "Unknown",
            "manufacturer": manufacturer or "Sony",
            "ip": ip_address,
            "base_url": base_url,
            "location": location,
        }

        _LOG.debug("Parsed device info: %s", device_info)
        return device_info

    except Exception as e:
        _LOG.error("Error fetching device info from %s: %s", location, e)
        return None


async def verify_device(ip_address: str) -> dict[str, Any] | None:
    """
    Verify that a Sony Audio Control API device exists at the given IP.

    Args:
        ip_address: IP address to check

    Returns:
        Device metadata dictionary or None if verification fails
        {
            "model": "TA-AN1000",
            "version": "001.478",
            "serial": "6601788",
            "ip": "192.168.1.201"
        }
    """
    try:
        # Attempt to connect and get device info
        from sony_client import SonyAudioDevice

        device = SonyAudioDevice(ip_address)
        try:
            info = await device.get_device_info()
            return {
                "model": info.get("model", "Unknown"),
                "version": info.get("version", ""),
                "serial": info.get("serialNumber", ""),
                "ip": ip_address,
                "mac": info.get("macAddr", ""),
            }
        finally:
            await device.close()

    except Exception as e:
        _LOG.error("Failed to verify device at %s: %s", ip_address, e)
        return None
