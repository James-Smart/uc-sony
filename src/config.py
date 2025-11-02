"""
Configuration management for Sony Audio integration.

Handles loading and saving device configurations.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)

# Configuration file name
CONFIG_FILE = "sony_audio_config.json"


def get_config_dir() -> Path:
    """
    Get configuration directory path.

    Uses UC_CONFIG_HOME environment variable if set, otherwise defaults to
    current directory or home directory.

    Returns:
        Path to configuration directory
    """
    config_home = os.getenv("UC_CONFIG_HOME")
    if config_home:
        return Path(config_home)

    home = os.getenv("HOME")
    if home:
        return Path(home) / ".config" / "sony_audio"

    return Path.cwd()


def get_config_path() -> Path:
    """
    Get full path to configuration file.

    Returns:
        Path to configuration file
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / CONFIG_FILE


def load_config() -> dict[str, Any]:
    """
    Load configuration from file.

    Returns:
        Configuration dictionary, empty dict if file doesn't exist
    """
    config_path = get_config_path()

    if not config_path.exists():
        _LOG.info("No configuration file found at %s", config_path)
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        _LOG.info("Loaded configuration from %s", config_path)
        return config
    except Exception as e:
        _LOG.error("Error loading configuration: %s", e)
        return {}


def save_config(config: dict[str, Any]) -> bool:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary to save

    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_path()

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        _LOG.info("Saved configuration to %s", config_path)
        return True
    except Exception as e:
        _LOG.error("Error saving configuration: %s", e)
        return False


def get_device_config(device_id: str) -> dict[str, Any] | None:
    """
    Get configuration for a specific device.

    Args:
        device_id: Device identifier (usually IP address or serial number)

    Returns:
        Device configuration dictionary or None if not found
    """
    config = load_config()
    devices = config.get("devices", {})
    return devices.get(device_id)


def save_device_config(device_id: str, device_config: dict[str, Any]) -> bool:
    """
    Save configuration for a specific device.

    Args:
        device_id: Device identifier
        device_config: Device configuration to save

    Returns:
        True if successful, False otherwise
    """
    config = load_config()

    if "devices" not in config:
        config["devices"] = {}

    config["devices"][device_id] = device_config

    return save_config(config)


def remove_device_config(device_id: str) -> bool:
    """
    Remove configuration for a specific device.

    Args:
        device_id: Device identifier

    Returns:
        True if successful, False otherwise
    """
    config = load_config()

    if "devices" in config and device_id in config["devices"]:
        del config["devices"][device_id]
        return save_config(config)

    return True


def get_all_devices() -> dict[str, dict[str, Any]]:
    """
    Get all configured devices.

    Returns:
        Dictionary of device_id -> device_config
    """
    config = load_config()
    return config.get("devices", {})
