"""
Sony Audio Control API Client.

Async wrapper for Sony Audio Control API supporting TA-AN1000 and similar devices.
"""

import logging
from typing import Any

import aiohttp

_LOG = logging.getLogger(__name__)


class SonyAudioDevice:
    """Sony Audio Control API client."""

    def __init__(self, ip_address: str, port: int = 10000):
        """
        Initialize Sony Audio Device client.

        Args:
            ip_address: IP address of the Sony device
            port: API port (default: 10000)
        """
        self.ip_address = ip_address
        self.port = port
        self.base_url = f"http://{ip_address}:{port}/sony"
        self._session: aiohttp.ClientSession | None = None
        self._device_info: dict[str, Any] | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure HTTP session exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _call(
        self,
        service: str,
        method: str,
        params: list | None = None,
        version: str = "1.0",
        req_id: int = 1,
        timeout: int = 3,
    ) -> dict[str, Any]:
        """
        Make a JSON-RPC call to the Sony Audio Control API.

        Args:
            service: Service name (system, audio, avContent)
            method: Method name
            params: Method parameters
            version: API version
            req_id: Request ID
            timeout: Request timeout in seconds

        Returns:
            API response as dictionary

        Raises:
            aiohttp.ClientError: On connection errors
            SonyApiError: On API errors
        """
        url = f"{self.base_url}/{service}"
        payload = {
            "method": method,
            "id": req_id,
            "params": params or [],
            "version": version,
        }

        session = await self._ensure_session()
        try:
            async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                response.raise_for_status()
                # Sony devices sometimes don't set correct content-type, force JSON parsing
                data = await response.json(content_type=None)

                if "error" in data:
                    error_code = data["error"][0] if data["error"] else "unknown"
                    error_msg = data["error"][1] if len(data["error"]) > 1 else ""
                    _LOG.warning(
                        "Sony API error: code=%s, msg=%s, method=%s",
                        error_code,
                        error_msg,
                        method,
                    )
                    raise SonyApiError(error_code, error_msg, method)

                return data
        except aiohttp.ClientError as e:
            _LOG.error("Connection error calling %s.%s: %s", service, method, e)
            raise

    async def connect(self) -> bool:
        """
        Test connection to the device.

        Returns:
            True if device is reachable and responds correctly
        """
        try:
            info = await self.get_device_info()
            return info is not None
        except Exception as e:
            _LOG.error("Failed to connect to device at %s: %s", self.ip_address, e)
            return False

    # System Service Methods

    async def get_device_info(self) -> dict[str, Any]:
        """Get device model and version information."""
        if self._device_info is None:
            result = await self._call("system", "getSystemInformation", [], "1.4")
            self._device_info = result["result"][0]
        return self._device_info

    async def get_interface_info(self) -> dict[str, Any]:
        """Get interface version and product information."""
        result = await self._call("system", "getInterfaceInformation", [], "1.0")
        return result["result"][0]

    async def get_power_status(self) -> str:
        """
        Get current power status.

        Returns:
            "active" or "standby"
        """
        result = await self._call("system", "getPowerStatus", [], "1.1")
        return result["result"][0]["status"]

    async def set_power_status(self, status: str) -> None:
        """
        Set power status.

        Args:
            status: "active" or "standby"
        """
        await self._call("system", "setPowerStatus", [{"status": status}], "1.1")

    async def get_versions(self, service: str) -> list[str]:
        """
        Get supported API versions for a service.

        Args:
            service: Service name (system, audio, avContent)

        Returns:
            List of supported version strings
        """
        result = await self._call(service, "getVersions", [], "1.0")
        return result["result"][0]

    # Audio Service Methods

    async def get_volume_info(self, zone: str = "") -> list[dict[str, Any]]:
        """
        Get volume information for all zones or specific zone.

        Args:
            zone: Zone identifier (default "" for all zones)

        Returns:
            List of volume info dictionaries
        """
        if zone:
            params = [{"output": zone}]
        else:
            params = [{}]
        result = await self._call("audio", "getVolumeInformation", params, "1.1")
        return result["result"][0]

    async def set_volume(self, volume: int | str, zone: str = "") -> None:
        """
        Set volume level.

        Args:
            volume: Absolute level (e.g., 25) or relative ("+1", "-2")
            zone: Zone identifier (default "" for main zone)
        """
        params = [{"output": zone, "volume": str(volume)}]
        await self._call("audio", "setAudioVolume", params, "1.1")

    async def set_mute(self, mute: bool, zone: str = "") -> None:
        """
        Set mute status.

        Args:
            mute: True for mute on, False for mute off
            zone: Zone identifier (default "" for main zone)
        """
        mute_str = "on" if mute else "off"
        params = [{"output": zone, "mute": mute_str}]
        await self._call("audio", "setAudioMute", params, "1.1")

    async def get_sound_settings(self, target: str = "") -> list[dict[str, Any]]:
        """
        Get current sound settings.

        Args:
            target: Target identifier (default "" for all)

        Returns:
            List of sound settings
        """
        result = await self._call("audio", "getSoundSettings", [{"target": target}], "1.1")
        return result["result"][0]

    async def get_speaker_settings(self, target: str = "") -> list[dict[str, Any]]:
        """
        Get speaker configuration settings.

        Args:
            target: Target identifier (default "" for all)

        Returns:
            List of speaker settings
        """
        result = await self._call("audio", "getSpeakerSettings", [{"target": target}], "1.0")
        return result["result"][0]

    async def get_equalizer_settings(self, target: str = "") -> list[dict[str, Any]]:
        """
        Get equalizer settings.

        Args:
            target: Target identifier (default "" for all)

        Returns:
            List of equalizer settings
        """
        result = await self._call("audio", "getCustomEqualizerSettings", [{"target": target}], "1.0")
        return result["result"][0]

    # AV Content Service Methods

    async def get_scheme_list(self) -> list[dict[str, str]]:
        """
        Get list of available URI schemes.

        Returns:
            List of scheme dictionaries
        """
        result = await self._call("avContent", "getSchemeList", [], "1.0")
        return result["result"][0]

    async def get_source_list(self, scheme: str = "extInput") -> list[dict[str, Any]]:
        """
        Get list of available sources for a scheme.

        Args:
            scheme: URI scheme (default "extInput" for inputs)

        Returns:
            List of source dictionaries with metadata
        """
        result = await self._call("avContent", "getSourceList", [{"scheme": scheme}], "1.2")
        return result["result"][0]

    async def get_playing_content_info(self, zone: str = "") -> list[dict[str, Any]]:
        """
        Get information about currently playing content.

        Args:
            zone: Zone identifier (default "" for main zone)

        Returns:
            List of content info dictionaries
        """
        if zone:
            params = [{"output": zone}]
        else:
            params = [{}]
        result = await self._call("avContent", "getPlayingContentInfo", params, "1.2")
        return result["result"][0]

    async def switch_input(self, uri: str, zone: str = "") -> None:
        """
        Switch to a different input source.

        Args:
            uri: Input source URI (e.g., "extInput:hdmi?port=1")
            zone: Zone identifier (default "" for main zone)
        """
        params = [{"output": zone, "uri": uri}]
        await self._call("avContent", "setPlayContent", params, "1.2")


class SonyApiError(Exception):
    """Sony API error exception."""

    def __init__(self, code: int | str, message: str, method: str):
        """
        Initialize Sony API error.

        Args:
            code: Error code from API
            message: Error message
            method: Method that caused the error
        """
        self.code = code
        self.message = message
        self.method = method
        super().__init__(f"Sony API error {code} in {method}: {message}")
