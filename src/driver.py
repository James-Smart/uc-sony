#!/usr/bin/env python3
"""
Sony Audio Control Integration Driver for Unfolded Circle Remote.

Main integration driver that handles device discovery, setup, and control.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add src directory to Python path to support imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import ucapi
from ucapi import remote

from config import get_device_config, save_device_config
from discovery import discover_sony_devices, verify_device
from remote_entity import create_remote_entity, get_input_uri_from_command
from sony_client import SonyApiError, SonyAudioDevice

_LOG = logging.getLogger(__name__)

# Global state
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
api = ucapi.IntegrationAPI(loop)

# Device instances keyed by entity_id
devices: dict[str, SonyAudioDevice] = {}
device_sources: dict[str, list[dict[str, Any]]] = {}


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
                        "field": {
                            "checkbox": {"value": False}
                        },
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
    # Check if this is a device selection or confirmation
    if "discovered_device" in msg.input_values:
        # User selected a discovered device
        ip_address = msg.input_values["discovered_device"]
        device_info = await verify_device(ip_address)

        if not device_info:
            return ucapi.SetupError()

        return await show_device_confirmation(device_info)

    elif "device_ip" in msg.input_values:
        # User confirmed device
        ip_address = msg.input_values["device_ip"]
        device_name = msg.input_values.get("device_name", "Sony Audio")

        # Create device and entity
        try:
            device = SonyAudioDevice(ip_address)
            connected = await device.connect()

            if not connected:
                await device.close()
                return ucapi.SetupError()

            # Get device info for entity_id
            info = await device.get_device_info()
            entity_id = f"sony_{info.get('serialNumber', ip_address.replace('.', '_'))}"

            # Create remote entity
            entity = await create_remote_entity(device, entity_id, cmd_handler)

            # Store device
            devices[entity_id] = device

            # Get and store sources for command handling
            sources = await device.get_source_list("extInput")
            device_sources[entity_id] = sources

            # Add entity to available entities
            api.available_entities.add(entity)

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

            _LOG.info("Setup complete for device %s", entity_id)
            return ucapi.SetupComplete()

        except Exception as e:
            _LOG.error("Error during setup: %s", e)
            if device:
                await device.close()
            return ucapi.SetupError()

    elif "retry" in msg.input_values:
        # User wants to retry discovery
        if msg.input_values["retry"] == "true":
            # Start discovery again
            return await handle_driver_setup(ucapi.DriverSetupRequest(False, {}))

    return ucapi.SetupError()


async def cmd_handler(
    entity: ucapi.Remote, cmd_id: str, params: dict[str, Any] | None
) -> ucapi.StatusCodes:
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
            api.configured_entities.update_attributes(
                entity.id, {remote.Attributes.STATE: remote.States.ON}
            )
            return ucapi.StatusCodes.OK

        elif cmd_id == remote.Commands.OFF:
            await device.set_power_status("standby")
            api.configured_entities.update_attributes(
                entity.id, {remote.Attributes.STATE: remote.States.OFF}
            )
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

            api.configured_entities.update_attributes(
                entity.id, {remote.Attributes.STATE: new_state}
            )
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
                api.configured_entities.update_attributes(
                    entity.id, {remote.Attributes.STATE: remote.States.ON}
                )

            elif command == "POWER_OFF":
                await device.set_power_status("standby")
                api.configured_entities.update_attributes(
                    entity.id, {remote.Attributes.STATE: remote.States.OFF}
                )

            elif command == "POWER_TOGGLE":
                current_state = entity.attributes.get(remote.Attributes.STATE)
                if current_state == remote.States.OFF:
                    await device.set_power_status("active")
                    new_state = remote.States.ON
                else:
                    await device.set_power_status("standby")
                    new_state = remote.States.OFF
                api.configured_entities.update_attributes(
                    entity.id, {remote.Attributes.STATE: new_state}
                )

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
                api.configured_entities.update_attributes(
                    entity_id, {remote.Attributes.STATE: state}
                )
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
                entity = await create_remote_entity(device, device_id, cmd_handler)
                devices[device_id] = device
                sources = await device.get_source_list("extInput")
                device_sources[device_id] = sources
                api.available_entities.add(entity)
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
        # Clean up device connections
        for device in devices.values():
            try:
                loop.run_until_complete(device.close())
            except Exception:
                pass

