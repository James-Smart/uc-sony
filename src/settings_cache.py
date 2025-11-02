"""
Dynamic settings cache for Sony Audio devices.

Discovers and caches device capabilities dynamically from the Sony API,
eliminating hardcoded settings and enabling support for any Sony audio device.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from sony_client import SonyAudioDevice

_LOG = logging.getLogger(__name__)


class DeviceSettingsCache:
    """Cache for dynamically discovered device settings."""

    def __init__(self, device: SonyAudioDevice):
        """
        Initialize settings cache for a device.

        Args:
            device: Sony Audio device instance
        """
        self.device = device
        self.sound_settings: list[dict[str, Any]] = []
        self.speaker_settings: list[dict[str, Any]] = []
        self.zones: list[int] = []
        self.last_refresh: Optional[datetime] = None

    async def refresh(self) -> None:
        """
        Discover and cache all device capabilities.

        Queries the Sony API for:
        - Sound settings (sound fields, 360SSM, calibration, dimmer, HDMI output)
        - Speaker settings (which speakers exist and their adjustment ranges)
        - Available zones for multi-zone audio
        """
        _LOG.info("Refreshing device settings cache...")

        try:
            # Discover sound settings
            self.sound_settings = await self.device.get_sound_settings(target="")
            _LOG.info("Discovered %d sound settings", len(self.sound_settings))

            # Discover speaker settings
            self.speaker_settings = await self.device.get_speaker_settings(target="")
            _LOG.info("Discovered %d speaker settings", len(self.speaker_settings))

            # Discover available zones
            self.zones = await self._discover_zones()
            _LOG.info("Discovered %d zones", len(self.zones))

            self.last_refresh = datetime.now()
            _LOG.info("Settings cache refresh complete")

        except Exception as e:
            _LOG.error("Error refreshing settings cache: %s", e)
            # Keep existing cache if refresh fails
            raise

    async def _discover_zones(self) -> list[int]:
        """
        Discover available audio zones.

        Returns:
            List of zone numbers (e.g., [1, 2, 3])
        """
        zones = [1]  # Main zone always exists

        # Try to get volume info for zones 2 and 3
        for zone_num in [2, 3]:
            try:
                zone_uri = f"extOutput:zone?zone={zone_num}"
                vol_info = await self.device.get_volume_info(zone_uri)
                if vol_info and len(vol_info) > 0:
                    zones.append(zone_num)
                    _LOG.debug("Zone %d is available", zone_num)
            except Exception as e:
                _LOG.debug("Zone %d not available: %s", zone_num, e)

        return zones

    def get_setting_by_target(self, target: str) -> Optional[dict[str, Any]]:
        """
        Find a setting by its target identifier.

        Args:
            target: Setting target (e.g., "soundField", "centerLevel")

        Returns:
            Setting dictionary or None if not found
        """
        # Search in sound settings
        for setting in self.sound_settings:
            if setting.get("target") == target:
                return setting

        # Search in speaker settings
        for setting in self.speaker_settings:
            if setting.get("target") == target:
                return setting

        return None

    def get_available_sound_field_values(self) -> list[tuple[str, str]]:
        """
        Get available sound field modes.

        Returns:
            List of (value, title) tuples for each available sound field
        """
        sound_field = self.get_setting_by_target("soundField")
        if not sound_field:
            return []

        values = []
        for candidate in sound_field.get("candidate", []):
            if candidate.get("isAvailable", True):
                value = candidate.get("value", "")
                title = candidate.get("title", value)
                values.append((value, title))

        return values

    def get_available_boolean_settings(self) -> list[tuple[str, str, list[str]]]:
        """
        Get available boolean/enum settings.

        Returns:
            List of (target, title, values) tuples for toggle settings
        """
        settings = []
        for setting in self.sound_settings:
            if setting.get("type") in ["booleanTarget", "enumTarget"]:
                if not setting.get("isAvailable", True):
                    continue

                target = setting.get("target", "")
                title = setting.get("title", target)
                values = [c.get("value", "") for c in setting.get("candidate", [])]

                settings.append((target, title, values))

        return settings

    def get_available_speaker_controls(self) -> list[tuple[str, str, float, float, float]]:
        """
        Get available speaker level controls.

        Returns:
            List of (target, title, min, max, step) tuples for each adjustable speaker
        """
        speakers = []
        for setting in self.speaker_settings:
            if setting.get("type") != "doubleNumberTarget":
                continue
            if not setting.get("isAvailable", True):
                continue

            target = setting.get("target", "")
            title = setting.get("title", target)

            # Get range info
            candidate = setting.get("candidate", [{}])[0]
            min_val = float(candidate.get("min", -10))
            max_val = float(candidate.get("max", 10))
            step = float(candidate.get("step", 0.5))

            speakers.append((target, title, min_val, max_val, step))

        return speakers

    def get_current_value(self, target: str) -> Optional[str]:
        """
        Get current value for a setting.

        Args:
            target: Setting target identifier

        Returns:
            Current value as string, or None if not found
        """
        setting = self.get_setting_by_target(target)
        if setting:
            return setting.get("currentValue")
        return None

    def is_setting_available(self, target: str) -> bool:
        """
        Check if a setting is available on this device.

        Args:
            target: Setting target identifier

        Returns:
            True if setting exists and is available
        """
        setting = self.get_setting_by_target(target)
        if not setting:
            return False
        return setting.get("isAvailable", True)

    def validate_setting_value(self, target: str, value: str) -> bool:
        """
        Validate a value for a specific setting.

        Args:
            target: Setting target identifier
            value: Value to validate

        Returns:
            True if value is valid for this setting
        """
        setting = self.get_setting_by_target(target)
        if not setting:
            return False

        candidates = setting.get("candidate", [])
        valid_values = [c.get("value") for c in candidates]

        return value in valid_values

