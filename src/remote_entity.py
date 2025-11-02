"""
Remote entity builder for Sony Audio devices.

Creates remote entities with dynamic commands based on device capabilities.
"""

import logging
from typing import Any

import ucapi
from ucapi import remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_icon, create_ui_text

from sony_client import SonyAudioDevice

_LOG = logging.getLogger(__name__)


def create_simple_commands(sources: list[dict[str, Any]]) -> list[str]:
    """
    Create list of simple commands for remote entity.

    Args:
        sources: List of input sources from get_source_list()

    Returns:
        List of command strings
    """
    commands = [
        # Power commands
        "POWER_ON",
        "POWER_OFF",
        "POWER_TOGGLE",
        # Volume commands
        "VOLUME_UP",
        "VOLUME_DOWN",
        "MUTE_ON",
        "MUTE_OFF",
        "MUTE_TOGGLE",
    ]

    # Add input commands dynamically
    for source in sources:
        source_uri = source.get("source", "")
        title = source.get("title", "")

        if not source_uri or not title:
            continue

        # Create command name from source URI
        if "hdmi" in source_uri:
            # Extract port number from URI like "extInput:hdmi?port=1"
            if "port=" in source_uri:
                port = source_uri.split("port=")[1].split("&")[0]
                commands.append(f"INPUT_HDMI{port}")
        elif "tv" in source_uri:
            commands.append("INPUT_TV")
        elif "btAudio" in source_uri:
            commands.append("INPUT_BLUETOOTH")
        elif "line" in source_uri:
            commands.append("INPUT_ANALOG")
        elif "airPlay" in source_uri:
            commands.append("INPUT_AIRPLAY")
        elif "usb" in source_uri:
            commands.append("INPUT_USB")

    return commands


def create_button_mappings(sources: list[dict[str, Any]]) -> list[Any]:
    """
    Create button mappings for physical remote buttons.

    Maps physical buttons to Sony soundbar commands with sensible defaults:
    - Power button → Power toggle
    - Volume buttons → Volume up/down
    - Mute button → Mute toggle
    - Channel buttons → Input cycling
    - Dpad → Input navigation/selection
    - Home → Switch to TV input (most common)
    - Back → Previous input

    Args:
        sources: List of input sources for input cycling

    Returns:
        List of button mapping configurations
    """
    mappings = [
        # === Power Control ===
        create_btn_mapping(Buttons.POWER, "POWER_TOGGLE"),
        # === Volume Controls ===
        create_btn_mapping(Buttons.VOLUME_UP, "VOLUME_UP"),
        create_btn_mapping(Buttons.VOLUME_DOWN, "VOLUME_DOWN"),
        create_btn_mapping(Buttons.MUTE, "MUTE_TOGGLE"),
    ]

    # === Input Selection with Channel Buttons ===
    # Channel up/down to cycle through inputs
    # Get input commands in order
    input_commands = []
    for source in sources:
        source_uri = source.get("source", "")
        if "hdmi" in source_uri and "port=" in source_uri:
            port = source_uri.split("port=")[1].split("&")[0]
            input_commands.append(f"INPUT_HDMI{port}")
        elif "tv" in source_uri:
            input_commands.append("INPUT_TV")
        elif "btAudio" in source_uri:
            input_commands.append("INPUT_BLUETOOTH")
        elif "line" in source_uri:
            input_commands.append("INPUT_ANALOG")
        elif "airPlay" in source_uri:
            input_commands.append("INPUT_AIRPLAY")

    # Map channel buttons to cycle through inputs if we have multiple
    if len(input_commands) >= 2:
        # Channel up → next input (e.g., TV → HDMI1 → HDMI2 → BT)
        mappings.append(create_btn_mapping(Buttons.CHANNEL_UP, input_commands[1]))
        # Channel down → previous input (or first input)
        mappings.append(create_btn_mapping(Buttons.CHANNEL_DOWN, input_commands[0]))

    # === Quick Access Buttons ===
    # Home button → TV input (most common usage)
    if "INPUT_TV" in input_commands:
        mappings.append(create_btn_mapping(Buttons.HOME, "INPUT_TV"))

    # Back button → HDMI 1 (second most common)
    if "INPUT_HDMI1" in input_commands:
        mappings.append(create_btn_mapping(Buttons.BACK, "INPUT_HDMI1"))

    # === Dpad Navigation for Inputs ===
    # Use dpad for quick input selection
    if len(input_commands) >= 1:
        # Dpad Up → TV
        if "INPUT_TV" in input_commands:
            mappings.append(create_btn_mapping(Buttons.DPAD_UP, "INPUT_TV"))

        # Dpad Left → HDMI 1
        if "INPUT_HDMI1" in input_commands:
            mappings.append(create_btn_mapping(Buttons.DPAD_LEFT, "INPUT_HDMI1"))

        # Dpad Right → HDMI 2
        if "INPUT_HDMI2" in input_commands:
            mappings.append(create_btn_mapping(Buttons.DPAD_RIGHT, "INPUT_HDMI2"))

        # Dpad Down → Bluetooth
        if "INPUT_BLUETOOTH" in input_commands:
            mappings.append(create_btn_mapping(Buttons.DPAD_DOWN, "INPUT_BLUETOOTH"))

        # Dpad Center → Toggle mute (easy thumb access)
        mappings.append(create_btn_mapping(Buttons.DPAD_MIDDLE, "MUTE_TOGGLE"))

    return mappings


def create_ui_pages(sources: list[dict[str, Any]], device_name: str) -> list[UiPage]:
    """
    Create UI pages for remote entity.

    Args:
        sources: List of input sources from get_source_list()
        device_name: Name of the device

    Returns:
        List of UI page objects
    """
    pages = []

    # Main control page
    main_page = UiPage("main", "Controls")
    main_page.add(create_ui_text(device_name, 0, 0, size=Size(4, 1)))

    # Power buttons
    main_page.add(create_ui_icon("uc:power-on", 0, 1, cmd="POWER_ON"))
    main_page.add(create_ui_icon("uc:power-off", 1, 1, cmd="POWER_OFF"))

    # Volume controls
    main_page.add(create_ui_icon("uc:volume-up", 0, 2, cmd="VOLUME_UP"))
    main_page.add(create_ui_icon("uc:volume-down", 1, 2, cmd="VOLUME_DOWN"))
    main_page.add(create_ui_icon("uc:mute", 2, 2, cmd="MUTE_TOGGLE"))

    pages.append(main_page)

    # Inputs page
    if sources:
        inputs_page = UiPage("inputs", "Inputs")
        inputs_page.add(create_ui_text("Select Input", 0, 0, size=Size(4, 1)))

        row = 1
        col = 0

        for source in sources:
            source_uri = source.get("source", "")
            title = source.get("title", "Unknown")

            if not source_uri:
                continue

            # Determine command and icon
            cmd = None
            icon = "uc:input"

            if "hdmi" in source_uri and "port=" in source_uri:
                port = source_uri.split("port=")[1].split("&")[0]
                cmd = f"INPUT_HDMI{port}"
                icon = "uc:hdmi"
            elif "tv" in source_uri:
                cmd = "INPUT_TV"
                icon = "uc:tv"
            elif "btAudio" in source_uri:
                cmd = "INPUT_BLUETOOTH"
                icon = "uc:bluetooth"
            elif "line" in source_uri:
                cmd = "INPUT_ANALOG"
                icon = "uc:line-in"
            elif "airPlay" in source_uri:
                cmd = "INPUT_AIRPLAY"
                icon = "uc:airplay"

            if cmd:
                # Create button with icon and label
                inputs_page.add(create_ui_icon(icon, col, row, cmd=cmd))
                inputs_page.add(
                    create_ui_text(
                        title[:12],  # Truncate long titles
                        col,
                        row + 1,
                        size=Size(1, 1),
                        cmd=cmd,
                    )
                )

                col += 1
                if col >= 4:
                    col = 0
                    row += 2

        pages.append(inputs_page)

    return pages


async def create_remote_entity(device: SonyAudioDevice, entity_id: str, cmd_handler) -> ucapi.Remote:
    """
    Create a remote entity for a Sony Audio device.

    Args:
        device: Sony Audio device instance
        entity_id: Entity identifier
        cmd_handler: Command handler function

    Returns:
        Remote entity instance
    """
    try:
        # Get device info
        info = await device.get_device_info()
        device_name = info.get("model", "Sony Audio")

        # Get available sources
        sources = await device.get_source_list("extInput")

        # Create simple commands list
        simple_commands = create_simple_commands(sources)

        # Create button mappings with input sources
        button_mapping = create_button_mappings(sources)

        # Create UI pages
        ui_pages = create_ui_pages(sources, device_name)

        # Create remote entity
        entity = ucapi.Remote(
            entity_id,
            device_name,
            [remote.Features.ON_OFF, remote.Features.TOGGLE, remote.Features.SEND_CMD],
            {remote.Attributes.STATE: remote.States.UNKNOWN},
            simple_commands=simple_commands,
            button_mapping=button_mapping,
            ui_pages=ui_pages,
            cmd_handler=cmd_handler,
        )

        _LOG.info("Created remote entity '%s' with %d inputs", entity_id, len(sources))
        return entity

    except Exception as e:
        _LOG.error("Error creating remote entity: %s", e)
        raise


def get_input_uri_from_command(command: str, sources: list[dict[str, Any]]) -> str | None:
    """
    Get input source URI from command string.

    Args:
        command: Command string (e.g., "INPUT_HDMI1")
        sources: List of input sources

    Returns:
        Source URI or None if not found
    """
    # Map command to source
    for source in sources:
        source_uri = source.get("source", "")

        if command == "INPUT_TV" and "tv" in source_uri:
            return source_uri
        elif command.startswith("INPUT_HDMI") and "hdmi" in source_uri:
            # Extract port number from command
            port = command.replace("INPUT_HDMI", "")
            if f"port={port}" in source_uri:
                return source_uri
        elif command == "INPUT_BLUETOOTH" and "btAudio" in source_uri:
            return source_uri
        elif command == "INPUT_ANALOG" and "line" in source_uri:
            return source_uri
        elif command == "INPUT_AIRPLAY" and "airPlay" in source_uri:
            return source_uri
        elif command == "INPUT_USB" and "usb" in source_uri:
            return source_uri

    return None
