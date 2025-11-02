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

    async def get_sound_settings(self, target: str = "", output: str = "") -> list[dict[str, Any]]:
        """
        Get current sound settings.

        NOTE: TA-AN1000 requires target="" (empty string) to work correctly.

        Args:
            target: Target identifier (default "" for all - required for TA-AN1000)
            output: Output zone identifier (default "" for main zone)

        Returns:
            List of sound settings including:
            - 360SSM (360 Spatial Sound Mapping)
            - dsdNative (DSD Native)
            - pureDirect (Pure Direct)
            - calibrationType (Full Flat, Engineer, Front Reference, Off)
            - sceneSelection (Movie, Music, Undo)
            - soundField (8 sound field modes)
            - dimmer (Bright, Dark, Off)
            - hdmiOutput (HDMI A, A+B, B, Off)
        """
        params = [{"target": target}]
        if output:
            params[0]["output"] = output
        result = await self._call("audio", "getSoundSettings", params, "1.1")
        return result["result"][0]

    async def set_sound_setting(self, target: str, value: str, output: str = "") -> None:
        """
        Set a specific sound setting.

        Args:
            target: Setting to change (e.g., "soundField", "360SSM", "pureDirect")
            value: New value for the setting
            output: Output zone identifier (default "" for main zone)

        Examples:
            - set_sound_setting("soundField", "2chStereo")
            - set_sound_setting("360SSM", "on")
            - set_sound_setting("pureDirect", "on")
            - set_sound_setting("calibrationType", "fullFlat")
        """
        params = [{"settings": [{"target": target, "value": value}]}]
        if output:
            params[0]["output"] = output
        await self._call("audio", "setSoundSettings", params, "1.1")

    async def get_speaker_settings(self, target: str = "") -> list[dict[str, Any]]:
        """
        Get speaker configuration settings.

        NOTE: TA-AN1000 requires target="" (empty string) to work correctly.

        Args:
            target: Target identifier (default "" for all - required for TA-AN1000)

        Returns:
            List of speaker settings including individual speaker levels:
            - Front L/R Level
            - Center Level
            - Height L/R Level
            - Surround L/R Level
            - Subwoofer Level
            - Speaker Selection
        """
        result = await self._call("audio", "getSpeakerSettings", [{"target": target}], "1.0")
        return result["result"][0]

    async def set_speaker_level(self, target: str, value: float) -> None:
        """
        Set individual speaker level.

        Args:
            target: Speaker to adjust (e.g., "subwooferLevel", "centerLevel")
            value: Level in dB (-10.0 to +10.0, step 0.5)

        Examples:
            - set_speaker_level("subwooferLevel", 2.0)
            - set_speaker_level("centerLevel", -1.5)
            - set_speaker_level("surroundLLevel", -0.5)
        """
        params = [{"settings": [{"target": target, "value": str(value)}]}]
        await self._call("audio", "setSpeakerSettings", params, "1.0")

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

    async def get_external_terminals_status(self, output: str = "") -> list[dict[str, Any]]:
        """
        Get external terminal status including labeled inputs.

        Args:
            output: Output zone identifier (default "" for all)

        Returns:
            List of terminal status dictionaries
        """
        result = await self._call(
            "avContent",
            "getCurrentExternalTerminalsStatus",
            [{"output": output}],
            "1.2"
        )
        return result["result"][0]

    async def set_active_terminal(self, uri: str, active: bool) -> None:
        """
        Activate or deactivate a zone or output.

        Args:
            uri: Zone URI (e.g., "extOutput:zone?zone=2")
            active: True to activate, False to deactivate

        Examples:
            - set_active_terminal("extOutput:zone?zone=2", True)  # Activate Zone 2
            - set_active_terminal("extOutput:zone?zone=3", False) # Deactivate Zone 3
        """
        status = "active" if active else "inactive"
        params = [{"active": status, "uri": uri}]
        await self._call("avContent", "setActiveTerminal", params, "1.0")

    async def get_zone_volume(self, zone: int) -> dict[str, Any]:
        """
        Get volume information for a specific zone.

        Args:
            zone: Zone number (1=Main, 2=Zone 2, 3=Zone 3)

        Returns:
            Volume info dict with volume, mute, min/max
        """
        zone_uri = f"extOutput:zone?zone={zone}"
        result = await self.get_volume_info(zone_uri)
        return result[0] if result else {}

    async def set_zone_volume(self, zone: int, volume: int | str) -> None:
        """
        Set volume for a specific zone.

        Args:
            zone: Zone number (1=Main, 2=Zone 2, 3=Zone 3)
            volume: Absolute level (0-74) or relative ("+1", "-2")
        """
        zone_uri = f"extOutput:zone?zone={zone}"
        await self.set_volume(volume, zone_uri)

    async def set_zone_mute(self, zone: int, mute: bool) -> None:
        """
        Set mute status for a specific zone.

        Args:
            zone: Zone number (1=Main, 2=Zone 2, 3=Zone 3)
            mute: True for mute on, False for mute off
        """
        zone_uri = f"extOutput:zone?zone={zone}"
        await self.set_mute(mute, zone_uri)


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
