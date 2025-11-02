#!/usr/bin/env python3
"""
Sony Audio Control Integration Driver for Unfolded Circle Remote.

Main integration driver that handles device discovery, setup, and control.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Add src directory to Python path to support imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import ucapi
from ucapi import remote

from config import save_device_config
from discovery import discover_sony_devices, verify_device
from remote_entity import create_remote_entity, discover_all_sources, get_input_uri_from_command
from settings_cache import DeviceSettingsCache
from sony_client import SonyApiError, SonyAudioDevice

_LOG = logging.getLogger(__name__)

# Global state
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
api = ucapi.IntegrationAPI(loop)

# Device instances keyed by entity_id
devices: dict[str, SonyAudioDevice] = {}
device_sources: dict[str, list[dict[str, Any]]] = {}
device_settings_caches: dict[str, DeviceSettingsCache] = {}
polling_tasks: dict[str, asyncio.Task] = {}


async def poll_device_state(entity_id: str, device: SonyAudioDevice, interval: int = 30):
    """
    Periodically poll device state and update entity attributes.

    Detects external changes made via physical remote or other apps.

    Args:
        entity_id: Entity identifier
        device: Device instance
        interval: Polling interval in seconds
    """
    while entity_id in devices:
        try:
            await asyncio.sleep(interval)

            # Get power status
            status = await device.get_power_status()
            new_state = remote.States.ON if status == "active" else remote.States.OFF

            # Update if changed
            current_entity = api.configured_entities.get(entity_id)
            if current_entity and current_entity.attributes.get(remote.Attributes.STATE) != new_state:
                _LOG.info("Device %s state changed externally to %s", entity_id, new_state)
                api.configured_entities.update_attributes(
                    entity_id,
                    {remote.Attributes.STATE: new_state}
                )
        except Exception as e:
            _LOG.debug("Error polling device %s: %s", entity_id, e)


async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Handle driver setup requests.

    Args:
        msg: Setup request message

    Returns:
        Setup action to continue the setup process
    """
    if isinstance(msg, ucapi.DriverSetupRequest):
        return await handle_driver_setup(msg)
    if isinstance(msg, ucapi.UserDataResponse):
        return await handle_user_data_response(msg)

    return ucapi.SetupError()


async def handle_driver_setup(msg: ucapi.DriverSetupRequest) -> ucapi.SetupAction:
    """
    Start driver setup process.

    Args:
        msg: Driver setup request

    Returns:
        Setup action
    """
    if msg.reconfigure:
        _LOG.info("Reconfiguring driver")
        # For reconfiguration, clear existing entities
        api.configured_entities.clear()

    # Check discovery mode from initial setup data
    discovery_mode = msg.setup_data.get("discovery_mode", "auto")

    if discovery_mode == "manual":
        # Manual IP entry
        manual_ip = msg.setup_data.get("manual_ip", "").strip()

        if not manual_ip:
            return ucapi.SetupError()

        # Verify device
        _LOG.info("Verifying device at %s", manual_ip)
        device_info = await verify_device(manual_ip)

        if not device_info:
            return ucapi.SetupError()

        # Show device confirmation
        return await show_device_confirmation(device_info)

    else:
        # Auto-discovery mode
        _LOG.info("Starting auto-discovery")
        discovered = await discover_sony_devices(timeout=5)

        if not discovered:
            return ucapi.RequestUserInput(
                {"en": "No devices found"},
                [
                    {
                        "id": "info",
                        "label": {"en": "Discovery Result"},
                        "field": {
                            "label": {
                                "value": {
                                    "en": "No Sony Audio devices were found on the network.\n\n"
                                    "Please ensure:\n"
                                    "- Device is powered on\n"
                                    "- Device is on the same network\n"
                                    "- Network allows multicast traffic"
                                }
                            }
                        },
                    },
                    {
                        "id": "retry",
                        "label": {"en": "Try again?"},
                        "field": {"checkbox": {"value": False}},
                    },
                ],
            )

        # Create dropdown items from discovered devices
        dropdown_items = [
            {
                "id": dev["ip"],
                "label": {"en": f"{dev['name']} ({dev['model']}) - {dev['ip']}"},
            }
            for dev in discovered
        ]

        return ucapi.RequestUserInput(
            {"en": "Select Device"},
            [
                {
                    "id": "discovered_device",
                    "label": {"en": "Discovered Devices"},
                    "field": {"dropdown": {"value": discovered[0]["ip"], "items": dropdown_items}},
                }
            ],
        )


async def show_device_confirmation(device_info: dict[str, Any]) -> ucapi.SetupAction:
    """
    Show device confirmation screen.

    Args:
        device_info: Device information

    Returns:
        Setup action
    """
    return ucapi.RequestUserInput(
        {"en": "Confirm Device"},
        [
            {
                "id": "device_info",
                "label": {"en": "Device Information"},
                "field": {
                    "label": {
                        "value": {
                            "en": f"**Model:** {device_info.get('model', 'Unknown')}\n"
                            f"**Version:** {device_info.get('version', 'Unknown')}\n"
                            f"**IP Address:** {device_info['ip']}"
                        }
                    }
                },
            },
            {
                "id": "device_ip",
                "label": {"en": "IP Address"},
                "field": {"text": {"value": device_info["ip"]}},
            },
            {
                "id": "device_name",
                "label": {"en": "Device Name (optional)"},
                "field": {"text": {"value": device_info.get("model", "Sony Audio")}},
            },
        ],
    )


async def handle_user_data_response(msg: ucapi.UserDataResponse) -> ucapi.SetupAction:
    """
    Handle user data response during setup.

    Args:
        msg: User data response

    Returns:
        Setup action
    """
    _LOG.info("Received user data response: %s", msg.input_values)

    # Check if this is device confirmation (has both device_ip and discovered_device)
    # or initial selection (only discovered_device)
    if "device_ip" in msg.input_values and "discovered_device" in msg.input_values:
        # User confirmed device
        ip_address = msg.input_values["device_ip"]
        device_name = msg.input_values.get("device_name", "Sony Audio")

        _LOG.info("Confirming device setup: IP=%s, Name=%s", ip_address, device_name)

        # Create device and entity
        device = None
        try:
            device = SonyAudioDevice(ip_address)
            connected = await device.connect()

            if not connected:
                _LOG.error("Failed to connect to device at %s", ip_address)
                await device.close()
                return ucapi.SetupError(error_type=ucapi.IntegrationSetupError.CONNECTION_REFUSED)

            # Get device info for entity_id
            info = await device.get_device_info()
            entity_id = f"sony_{info.get('serialNumber', ip_address.replace('.', '_'))}"

            _LOG.info("Creating entity %s for device %s", entity_id, info.get('model'))

            # Create and initialize settings cache
            settings_cache = DeviceSettingsCache(device)
            await settings_cache.refresh()
            _LOG.info("Initialized settings cache for %s", entity_id)

            # Create remote entity with settings cache
            entity = await create_remote_entity(device, entity_id, cmd_handler, settings_cache)

            # Store device and cache
            devices[entity_id] = device
            device_settings_caches[entity_id] = settings_cache

            # Get and store complete sources for command handling
            sources = await discover_all_sources(device)
            device_sources[entity_id] = sources

            # Add entity to available AND configured entities
            # This makes it immediately usable after setup
            api.available_entities.add(entity)
            api.configured_entities.add(entity)

            # Get initial state
            try:
                status = await device.get_power_status()
                state = remote.States.ON if status == "active" else remote.States.OFF
                api.configured_entities.update_attributes(entity_id, {remote.Attributes.STATE: state})
            except Exception as e:
                _LOG.warning("Could not get initial state: %s", e)

            # Save configuration
            save_device_config(
                entity_id,
                {
                    "ip": ip_address,
                    "name": device_name,
                    "model": info.get("model", "Unknown"),
                    "serial": info.get("serialNumber", ""),
                },
            )

            # Start state polling task
            polling_tasks[entity_id] = asyncio.create_task(poll_device_state(entity_id, device))

            _LOG.info("Setup complete for device %s", entity_id)
            return ucapi.SetupComplete()

        except Exception as e:
            _LOG.error("Error during setup: %s", e, exc_info=True)
            if device:
                await device.close()
            return ucapi.SetupError(error_type=ucapi.IntegrationSetupError.OTHER)

    elif "discovered_device" in msg.input_values:
        # User selected a discovered device (initial selection)
        ip_address = msg.input_values["discovered_device"]
        _LOG.info("User selected device: %s", ip_address)
        device_info = await verify_device(ip_address)

        if not device_info:
            _LOG.error("Failed to verify device at %s", ip_address)
            return ucapi.SetupError()

        return await show_device_confirmation(device_info)

    elif "retry" in msg.input_values:
        # User wants to retry discovery
        if msg.input_values["retry"] == "true":
            # Start discovery again
            return await handle_driver_setup(ucapi.DriverSetupRequest(False, {}))

    _LOG.warning("Unhandled user data response, input_values: %s", msg.input_values)
    return ucapi.SetupError(error_type=ucapi.IntegrationSetupError.OTHER)


async def cmd_handler(entity: ucapi.Remote, cmd_id: str, params: dict[str, Any] | None) -> ucapi.StatusCodes:
    """
    Handle remote entity commands.

    Args:
        entity: Remote entity
        cmd_id: Command ID
        params: Command parameters

    Returns:
        Status code
    """
    _LOG.info("Command: %s for entity %s, params: %s", cmd_id, entity.id, params)

    device = devices.get(entity.id)
    if not device:
        _LOG.error("Device not found for entity %s", entity.id)
        return ucapi.StatusCodes.SERVER_ERROR

    try:
        # Handle power commands
        if cmd_id == remote.Commands.ON:
            await device.set_power_status("active")
            api.configured_entities.update_attributes(entity.id, {remote.Attributes.STATE: remote.States.ON})
            return ucapi.StatusCodes.OK

        elif cmd_id == remote.Commands.OFF:
            await device.set_power_status("standby")
            api.configured_entities.update_attributes(entity.id, {remote.Attributes.STATE: remote.States.OFF})
            return ucapi.StatusCodes.OK

        elif cmd_id == remote.Commands.TOGGLE:
            # Get current state
            current_state = entity.attributes.get(remote.Attributes.STATE)
            if current_state == remote.States.OFF:
                await device.set_power_status("active")
                new_state = remote.States.ON
            else:
                await device.set_power_status("standby")
                new_state = remote.States.OFF

            api.configured_entities.update_attributes(entity.id, {remote.Attributes.STATE: new_state})
            return ucapi.StatusCodes.OK

        elif cmd_id == remote.Commands.SEND_CMD:
            if not params:
                return ucapi.StatusCodes.BAD_REQUEST

            command = params.get("command")
            if not command:
                return ucapi.StatusCodes.BAD_REQUEST

            # Handle different command types
            if command == "POWER_ON":
                await device.set_power_status("active")
                api.configured_entities.update_attributes(entity.id, {remote.Attributes.STATE: remote.States.ON})

            elif command == "POWER_OFF":
                await device.set_power_status("standby")
                api.configured_entities.update_attributes(entity.id, {remote.Attributes.STATE: remote.States.OFF})

            elif command == "POWER_TOGGLE":
                current_state = entity.attributes.get(remote.Attributes.STATE)
                if current_state == remote.States.OFF:
                    await device.set_power_status("active")
                    new_state = remote.States.ON
                else:
                    await device.set_power_status("standby")
                    new_state = remote.States.OFF
                api.configured_entities.update_attributes(entity.id, {remote.Attributes.STATE: new_state})

            elif command == "VOLUME_UP":
                repeat = params.get("repeat", 1)
                for _ in range(repeat):
                    await device.set_volume("+1")

            elif command == "VOLUME_DOWN":
                repeat = params.get("repeat", 1)
                for _ in range(repeat):
                    await device.set_volume("-1")

            elif command == "MUTE_ON":
                await device.set_mute(True)

            elif command == "MUTE_OFF":
                await device.set_mute(False)

            elif command == "MUTE_TOGGLE":
                # Get current mute state
                vol_info = await device.get_volume_info()
                if vol_info and len(vol_info) > 0:
                    current_mute = vol_info[0].get("mute", "off")
                    await device.set_mute(current_mute == "off")

            # Handle settings refresh command
            elif command == "REFRESH_SETTINGS":
                settings_cache = device_settings_caches.get(entity.id)
                if settings_cache:
                    await settings_cache.refresh()
                    _LOG.info("Settings cache refreshed for device %s", entity.id)
                return ucapi.StatusCodes.OK

            # Dynamic sound settings (Sound Field, 360SSM, calibration, etc.)
            elif command.startswith("SOUND_"):
                settings_cache = device_settings_caches.get(entity.id)
                if not settings_cache:
                    _LOG.warning("No settings cache found for device %s", entity.id)
                    return ucapi.StatusCodes.SERVER_ERROR

                # Parse command: SOUND_<TARGET>_<VALUE> or SOUND_FIELD_<VALUE>
                if command.startswith("SOUND_FIELD_"):
                    # Extract value from SOUND_FIELD_<VALUE>
                    value = command.replace("SOUND_FIELD_", "").lower()
                    # Validate against settings cache
                    if settings_cache.validate_setting_value("soundField", value):
                        await device.set_sound_setting("soundField", value)
                    else:
                        _LOG.warning("Invalid sound field value: %s", value)
                        return ucapi.StatusCodes.BAD_REQUEST

                else:
                    # Parse SOUND_<TARGET>_<VALUE>
                    parts = command.split("_", 2)
                    if len(parts) >= 3:
                        target = parts[1].lower()
                        value = parts[2].lower()

                        # Validate setting exists and value is valid
                        if settings_cache.validate_setting_value(target, value):
                            await device.set_sound_setting(target, value)
                        else:
                            _LOG.warning("Invalid sound setting: %s = %s", target, value)
                            return ucapi.StatusCodes.BAD_REQUEST

            # Dynamic speaker level adjustments
            elif command.startswith("SPEAKER_"):
                settings_cache = device_settings_caches.get(entity.id)
                if not settings_cache:
                    _LOG.warning("No settings cache found for device %s", entity.id)
                    return ucapi.StatusCodes.SERVER_ERROR

                # Parse: SPEAKER_<NAME>_UP or SPEAKER_<NAME>_DOWN
                if not (command.endswith("_UP") or command.endswith("_DOWN")):
                    return ucapi.StatusCodes.BAD_REQUEST

                direction = "up" if command.endswith("_UP") else "down"
                # Remove SPEAKER_ prefix and _UP/_DOWN suffix
                speaker_name = command[8:].rsplit("_", 1)[0]  # Remove "SPEAKER_" and "_UP"/"_DOWN"

                # Find matching speaker setting in cache
                speaker_controls = settings_cache.get_available_speaker_controls()
                for target, title, min_val, max_val, step in speaker_controls:
                    # Match target by removing "Level" suffix and comparing uppercase
                    target_name = target.replace("Level", "").replace("level", "").upper()
                    if target_name == speaker_name:
                        # Get current value from cache
                        current_value_str = settings_cache.get_current_value(target)
                        if current_value_str is None:
                            _LOG.warning("Could not get current value for %s", target)
                            return ucapi.StatusCodes.SERVER_ERROR

                        current_value = float(current_value_str)

                        # Calculate new value
                        if direction == "up":
                            new_value = min(current_value + step, max_val)
                        else:
                            new_value = max(current_value - step, min_val)

                        # Set new value
                        await device.set_speaker_level(target, new_value)
                        _LOG.info("Set %s to %.1f dB", target, new_value)

                        # Refresh cache to get new value
                        await settings_cache.refresh()
                        return ucapi.StatusCodes.OK

                _LOG.warning("Unknown speaker control: %s", speaker_name)
                return ucapi.StatusCodes.BAD_REQUEST

            # Dynamic multi-zone controls
            elif command.startswith("ZONE"):
                settings_cache = device_settings_caches.get(entity.id)
                if not settings_cache:
                    _LOG.warning("No settings cache found for device %s", entity.id)
                    return ucapi.StatusCodes.SERVER_ERROR

                # Extract zone number from ZONE<N>_<CMD>
                try:
                    zone = int(command[4])
                    cmd_type = command[6:]  # Skip "ZONE<N>_"
                except (ValueError, IndexError):
                    _LOG.warning("Invalid zone command format: %s", command)
                    return ucapi.StatusCodes.BAD_REQUEST

                # Validate zone exists on this device
                if zone not in settings_cache.zones:
                    _LOG.warning("Zone %d not available on this device", zone)
                    return ucapi.StatusCodes.BAD_REQUEST

                # Handle zone commands
                if cmd_type == "VOLUME_UP":
                    await device.set_zone_volume(zone, "+1")
                elif cmd_type == "VOLUME_DOWN":
                    await device.set_zone_volume(zone, "-1")
                elif cmd_type == "MUTE_TOGGLE":
                    vol_info = await device.get_zone_volume(zone)
                    current_mute = vol_info.get("mute", "off")
                    await device.set_zone_mute(zone, current_mute == "off")
                elif cmd_type == "ACTIVATE":
                    zone_uri = f"extOutput:zone?zone={zone}"
                    await device.set_active_terminal(zone_uri, True)
                elif cmd_type == "DEACTIVATE":
                    zone_uri = f"extOutput:zone?zone={zone}"
                    await device.set_active_terminal(zone_uri, False)
                else:
                    _LOG.warning("Unknown zone command type: %s", cmd_type)
                    return ucapi.StatusCodes.BAD_REQUEST

            # Dynamic system controls (dimmer, HDMI output)
            # These are actually sound settings, handled dynamically
            elif command.startswith("SYSTEM_"):
                settings_cache = device_settings_caches.get(entity.id)
                if not settings_cache:
                    _LOG.warning("No settings cache found for device %s", entity.id)
                    return ucapi.StatusCodes.SERVER_ERROR

                # Parse SYSTEM_<TARGET>_<VALUE>
                if command.startswith("SYSTEM_DIMMER_"):
                    target = "dimmer"
                    value = command.replace("SYSTEM_DIMMER_", "").lower()
                elif command.startswith("SYSTEM_HDMI_OUTPUT_"):
                    target = "hdmiOutput"
                    value = command.replace("SYSTEM_HDMI_OUTPUT_", "").lower()
                    # Handle special case mappings for HDMI output
                    value_map = {"a": "hdmi_A", "b": "hdim_B", "ab": "hdmi_AB", "off": "off"}
                    value = value_map.get(value, value)
                else:
                    _LOG.warning("Unknown system command: %s", command)
                    return ucapi.StatusCodes.BAD_REQUEST

                # Validate and set
                if settings_cache.validate_setting_value(target, value):
                    await device.set_sound_setting(target, value)
                else:
                    _LOG.warning("Invalid system setting: %s = %s", target, value)
                    return ucapi.StatusCodes.BAD_REQUEST

            elif command.startswith("INPUT_"):
                # Handle input switching
                sources = device_sources.get(entity.id, [])
                uri = get_input_uri_from_command(command, sources)

                if uri:
                    await device.switch_input(uri)
                else:
                    _LOG.warning("Unknown input command: %s", command)
                    return ucapi.StatusCodes.BAD_REQUEST

            else:
                _LOG.warning("Unknown command: %s", command)
                return ucapi.StatusCodes.BAD_REQUEST

            return ucapi.StatusCodes.OK

        else:
            _LOG.warning("Unsupported command: %s", cmd_id)
            return ucapi.StatusCodes.NOT_IMPLEMENTED

    except SonyApiError as e:
        _LOG.error("Sony API error: %s", e)
        return ucapi.StatusCodes.SERVER_ERROR
    except Exception as e:
        _LOG.error("Error handling command: %s", e)
        return ucapi.StatusCodes.SERVER_ERROR


@api.listens_to(ucapi.Events.CONNECT)
async def on_connect() -> None:
    """Handle connection from Remote."""
    _LOG.info("Remote connected")
    await api.set_device_state(ucapi.DeviceStates.CONNECTED)


@api.listens_to(ucapi.Events.DISCONNECT)
async def on_disconnect() -> None:
    """Handle disconnection from Remote."""
    _LOG.info("Remote disconnected")


@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_standby() -> None:
    """Handle Remote entering standby."""
    _LOG.info("Remote entering standby")


@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_exit_standby() -> None:
    """Handle Remote exiting standby."""
    _LOG.info("Remote exiting standby")


@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """
    Handle entity subscription.

    Args:
        entity_ids: List of entity IDs to subscribe to
    """
    _LOG.info("Subscribed to entities: %s", entity_ids)
    # Update entity states
    for entity_id in entity_ids:
        device = devices.get(entity_id)
        if device:
            try:
                status = await device.get_power_status()
                state = remote.States.ON if status == "active" else remote.States.OFF
                api.configured_entities.update_attributes(entity_id, {remote.Attributes.STATE: state})
            except Exception as e:
                _LOG.error("Error updating entity %s state: %s", entity_id, e)


@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """
    Handle entity unsubscription.

    Args:
        entity_ids: List of entity IDs to unsubscribe from
    """
    _LOG.info("Unsubscribed from entities: %s", entity_ids)


async def main() -> None:
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    _LOG.info("Starting Sony Audio Control integration driver")

    # Initialize the integration API
    # driver.json is in the parent directory
    driver_json_path = Path(__file__).parent.parent / "driver.json"
    await api.init(str(driver_json_path), driver_setup_handler)

    # Load previously configured devices
    from config import get_all_devices

    configured = get_all_devices()
    for device_id, config in configured.items():
        try:
            ip_address = config["ip"]
            device = SonyAudioDevice(ip_address)

            if await device.connect():
                # Create and initialize settings cache
                settings_cache = DeviceSettingsCache(device)
                await settings_cache.refresh()
                _LOG.info("Initialized settings cache for %s", device_id)

                # Create remote entity with settings cache
                entity = await create_remote_entity(device, device_id, cmd_handler, settings_cache)
                devices[device_id] = device
                device_settings_caches[device_id] = settings_cache
                
                # Get and store complete sources for command handling
                sources = await discover_all_sources(device)
                device_sources[device_id] = sources
                
                # Add to both available and configured entities
                api.available_entities.add(entity)
                api.configured_entities.add(entity)
                
                # Set initial state
                try:
                    status = await device.get_power_status()
                    state = remote.States.ON if status == "active" else remote.States.OFF
                    api.configured_entities.update_attributes(device_id, {remote.Attributes.STATE: state})
                except Exception as e:
                    _LOG.warning("Could not get initial state for %s: %s", device_id, e)
                
                # Start state polling task
                polling_tasks[device_id] = asyncio.create_task(poll_device_state(device_id, device))
                
                _LOG.info("Restored device %s from configuration", device_id)
            else:
                _LOG.warning("Could not reconnect to device %s at %s", device_id, ip_address)
                await device.close()

        except Exception as e:
            _LOG.error("Error restoring device %s: %s", device_id, e)


if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        _LOG.info("Shutting down...")
    finally:
        # Cancel polling tasks
        for task in polling_tasks.values():
            task.cancel()
        
        # Clean up device connections
        for device in devices.values():
            try:
                loop.run_until_complete(device.close())
            except Exception:
                pass
