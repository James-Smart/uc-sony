"""
Remote entity builder for Sony Audio devices.

Creates remote entities with dynamic commands based on device capabilities.
"""

import logging
from typing import Any

import ucapi
from ucapi import remote
from ucapi.ui import Buttons, Size, UiPage, create_btn_mapping, create_ui_icon, create_ui_text

from settings_cache import DeviceSettingsCache
from sony_client import SonyAudioDevice

_LOG = logging.getLogger(__name__)


def parse_source_uri(source_uri: str) -> dict[str, str]:
    """
    Parse source URI and extract input type and identifier.

    Args:
        source_uri: Source URI string (e.g., "extInput:hdmi?port=1")

    Returns:
        Dict with 'type' and 'id' fields
    """
    if "hdmi" in source_uri and "port=" in source_uri:
        port = source_uri.split("port=")[1].split("&")[0]
        return {"type": "hdmi", "id": port}
    elif "tv" in source_uri:
        return {"type": "tv", "id": ""}
    elif "btAudio" in source_uri:
        return {"type": "bluetooth", "id": ""}
    elif "line" in source_uri:
        return {"type": "analog", "id": ""}
    elif "airPlay" in source_uri:
        return {"type": "airplay", "id": ""}
    elif "usb" in source_uri:
        return {"type": "usb", "id": ""}
    elif source_uri.startswith("extInput:"):
        input_name = source_uri.split("extInput:")[1].split("?")[0]
        return {"type": "labeled", "id": input_name}
    return {"type": "unknown", "id": ""}


async def discover_all_sources(device: SonyAudioDevice) -> list[dict[str, Any]]:
    """
    Discover all available sources from device using multiple methods.

    Combines results from getSourceList and getCurrentExternalTerminalsStatus
    to return complete list including generic and labeled inputs.

    Args:
        device: Sony Audio device instance

    Returns:
        Complete list of source dictionaries
    """
    sources = []

    # Method 1: getSourceList
    try:
        basic_sources = await device.get_source_list("extInput")
        _LOG.info("getSourceList found %d sources", len(basic_sources))
        sources.extend(basic_sources)
    except Exception as e:
        _LOG.warning("Could not get source list: %s", e)

    # Method 2: getCurrentExternalTerminalsStatus
    try:
        terminals = await device.get_external_terminals_status("")
        input_terminals = [t for t in terminals if t.get("uri", "").startswith("extInput:")]
        _LOG.info("Terminal status found %d input terminals", len(input_terminals))

        existing_uris = {s.get("source") for s in sources}
        for terminal in input_terminals:
            uri = terminal.get("uri")
            if uri and uri not in existing_uris:
                source = {
                    "source": uri,
                    "title": terminal.get("title", ""),
                    "meta": terminal.get("meta", ""),
                    "iconUrl": terminal.get("iconUrl", ""),
                    "isPlayable": True,
                    "isBrowsable": False,
                }
                sources.append(source)
                existing_uris.add(uri)
                _LOG.info("Added labeled input: %s (%s)", terminal.get("title"), uri)
    except Exception as e:
        _LOG.debug("Could not get terminal status: %s", e)

    return sources


def create_simple_commands(sources: list[dict[str, Any]], settings_cache: DeviceSettingsCache) -> list[str]:
    """
    Create list of simple commands for remote entity (dynamically generated).

    Args:
        sources: List of input sources from get_source_list()
        settings_cache: Device settings cache with discovered capabilities

    Returns:
        List of command strings based on device capabilities
    """
    commands = [
        # Basic commands (always available)
        "POWER_ON",
        "POWER_OFF",
        "POWER_TOGGLE",
        "VOLUME_UP",
        "VOLUME_DOWN",
        "MUTE_ON",
        "MUTE_OFF",
        "MUTE_TOGGLE",
    ]

    # Dynamic sound field commands
    sound_field_values = settings_cache.get_available_sound_field_values()
    for value, title in sound_field_values:
        cmd = f"SOUND_FIELD_{value.upper()}"
        commands.append(cmd)
        _LOG.debug("Added sound field command: %s (%s)", cmd, title)

    # Dynamic boolean/enum settings (360SSM, DSD Native, Pure Direct, Calibration, Dimmer, HDMI)
    boolean_settings = settings_cache.get_available_boolean_settings()
    for target, title, values in boolean_settings:
        for value in values:
            cmd = f"SOUND_{target.upper()}_{value.upper()}"
            commands.append(cmd)
            _LOG.debug("Added sound setting command: %s", cmd)

    # Dynamic speaker level commands
    speaker_controls = settings_cache.get_available_speaker_controls()
    for target, title, min_val, max_val, step in speaker_controls:
        # Create friendly name by removing "Level" suffix
        base_name = target.replace("Level", "").replace("level", "")
        # Convert camelCase to UPPER_SNAKE_CASE
        base_cmd = f"SPEAKER_{base_name.upper()}"
        commands.extend([f"{base_cmd}_UP", f"{base_cmd}_DOWN"])
        _LOG.debug("Added speaker commands: %s_UP/DOWN (%s)", base_cmd, title)

    # Dynamic zone commands
    for zone in settings_cache.zones:
        commands.extend([
            f"ZONE{zone}_VOLUME_UP",
            f"ZONE{zone}_VOLUME_DOWN",
            f"ZONE{zone}_MUTE_TOGGLE",
        ])
        if zone > 1:  # Only non-main zones can be activated/deactivated
            commands.extend([f"ZONE{zone}_ACTIVATE", f"ZONE{zone}_DEACTIVATE"])
        _LOG.debug("Added zone %d commands", zone)

    # Add input commands dynamically
    for source in sources:
        source_uri = source.get("source", "")
        title = source.get("title", "")

        if not source_uri:
            continue

        # Create command name from source URI
        if "hdmi" in source_uri and "port=" in source_uri:
            # Extract port number from URI like "extInput:hdmi?port=1"
            port = source_uri.split("port=")[1].split("&")[0]
            commands.append(f"INPUT_HDMI{port}")
        elif "tv" in source_uri or source_uri == "extInput:tv":
            commands.append("INPUT_TV")
        elif "btAudio" in source_uri:
            commands.append("INPUT_BLUETOOTH")
        elif "line" in source_uri:
            commands.append("INPUT_ANALOG")
        elif "airPlay" in source_uri:
            commands.append("INPUT_AIRPLAY")
        elif "usb" in source_uri:
            commands.append("INPUT_USB")
        elif source_uri.startswith("extInput:"):
            # Handle labeled inputs like game, bd-dvd, sat-catv, mediaBox, etc.
            # Extract the name after "extInput:" and convert to command format
            input_name = source_uri.split("extInput:")[1].split("?")[0]
            # Convert to uppercase and replace hyphens/special chars with underscores
            command_name = input_name.upper().replace("-", "_").replace(" ", "_")
            commands.append(f"INPUT_{command_name}")

    # Add settings refresh command
    commands.append("REFRESH_SETTINGS")

    _LOG.info("Generated %d total commands from device capabilities", len(commands))
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


def create_ui_pages(
    sources: list[dict[str, Any]], device_name: str, settings_cache: DeviceSettingsCache
) -> list[UiPage]:
    """
    Create UI pages for remote entity (dynamically generated).

    Args:
        sources: List of input sources from get_source_list()
        device_name: Name of the device
        settings_cache: Device settings cache with discovered capabilities

    Returns:
        List of UI page objects based on device capabilities
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
            elif source_uri.startswith("extInput:"):
                # Handle labeled inputs (game, bd-dvd, mediaBox, etc.)
                input_name = source_uri.split("extInput:")[1].split("?")[0]
                command_name = input_name.upper().replace("-", "_").replace(" ", "_")
                cmd = f"INPUT_{command_name}"
                # Use appropriate icon based on input name
                if "game" in input_name.lower():
                    icon = "uc:gaming"
                elif "bd" in input_name.lower() or "dvd" in input_name.lower():
                    icon = "uc:disc"
                elif "sat" in input_name.lower() or "catv" in input_name.lower() or "cable" in input_name.lower():
                    icon = "uc:satellite"
                elif "cd" in input_name.lower():
                    icon = "uc:music"
                elif "video" in input_name.lower():
                    icon = "uc:video"
                else:
                    icon = "uc:input"

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

    # Sound Settings page (only if device supports sound settings)
    if settings_cache.sound_settings:
        sound_page = UiPage("sound", "Sound")
        sound_page.add(create_ui_text("Sound Settings", 0, 0, size=Size(4, 1)))
        current_row = 1

        # Dynamically add sound field buttons
        sound_field_values = settings_cache.get_available_sound_field_values()
        if sound_field_values:
            sound_page.add(create_ui_text("Sound Field", 0, current_row, size=Size(2, 1)))
            current_row += 1

            col = 0
            for value, title in sound_field_values[:4]:  # Show top 4 sound fields
                cmd = f"SOUND_FIELD_{value.upper()}"
                # Pick appropriate icon
                icon = "uc:sound"
                if "stereo" in value.lower():
                    icon = "uc:music"
                elif "dolby" in value.lower() or "dts" in value.lower():
                    icon = "uc:speaker"

                sound_page.add(create_ui_icon(icon, col, current_row, cmd=cmd, size=Size(1, 1)))
                # Truncate long titles
                display_title = title[:8] if len(title) > 8 else title
                sound_page.add(create_ui_text(display_title, col, current_row + 1, size=Size(1, 1)))
                col += 1

            current_row += 2

        # Dynamically add boolean/enum settings
        boolean_settings = settings_cache.get_available_boolean_settings()
        if boolean_settings:
            sound_page.add(create_ui_text("Settings", 0, current_row, size=Size(2, 1)))
            current_row += 1

            col = 0
            for target, title, values in boolean_settings[:6]:  # Show up to 6 settings
                for value in values[:2]:  # Show first 2 values (e.g., on/off)
                    cmd = f"SOUND_{target.upper()}_{value.upper()}"
                    # Truncate long titles and add value
                    display_title = f"{title[:6]} {value[:3]}"
                    sound_page.add(create_ui_icon("uc:settings", col, current_row, cmd=cmd, size=Size(1, 1)))
                    sound_page.add(create_ui_text(display_title, col, current_row + 1, size=Size(1, 1)))
                    col += 1
                    if col >= 4:
                        col = 0
                        current_row += 2

        pages.append(sound_page)
        _LOG.info("Created dynamic sound settings page with %d settings", len(boolean_settings))

    # Speaker Levels page (only if device supports speaker settings)
    speaker_controls = settings_cache.get_available_speaker_controls()
    if speaker_controls:
        speaker_page = UiPage("speakers", "Speakers")
        speaker_page.add(create_ui_text("Speaker Levels", 0, 0, size=Size(4, 1)))

        row = 1
        col = 0

        # Dynamically add speaker level controls
        for target, title, min_val, max_val, step in speaker_controls:
            # Create friendly command name
            base_name = target.replace("Level", "").replace("level", "")
            base_cmd = f"SPEAKER_{base_name.upper()}"

            # Truncate long titles
            display_title = title[:10] if len(title) > 10 else title

            # Add speaker control (takes 2 columns)
            speaker_page.add(create_ui_text(display_title, col, row, size=Size(2, 1)))
            speaker_page.add(create_ui_icon("uc:up", col, row + 1, cmd=f"{base_cmd}_UP"))
            speaker_page.add(create_ui_icon("uc:down", col + 1, row + 1, cmd=f"{base_cmd}_DOWN"))

            # Move to next position (2 speakers per row)
            col += 2
            if col >= 4:
                col = 0
                row += 2

        pages.append(speaker_page)
        _LOG.info("Created dynamic speaker levels page with %d speakers", len(speaker_controls))

    # Multi-Zone page (only if device supports multiple zones)
    if len(settings_cache.zones) > 1:
        zones_page = UiPage("zones", "Zones")
        zones_page.add(create_ui_text("Multi-Zone Control", 0, 0, size=Size(4, 1)))

        row = 1

        # Dynamically add zone controls
        for zone in settings_cache.zones:
            zone_name = "Main Zone" if zone == 1 else f"Zone {zone}"
            zones_page.add(create_ui_text(zone_name, 0, row, size=Size(2, 1)))
            row += 1

            # Volume controls (all zones)
            zones_page.add(create_ui_icon("uc:volume-up", 0, row, cmd=f"ZONE{zone}_VOLUME_UP"))
            zones_page.add(create_ui_icon("uc:volume-down", 1, row, cmd=f"ZONE{zone}_VOLUME_DOWN"))
            zones_page.add(create_ui_icon("uc:mute", 2, row, cmd=f"ZONE{zone}_MUTE_TOGGLE"))
            row += 1

            # Power controls (only for non-main zones)
            if zone > 1:
                zones_page.add(create_ui_icon("uc:power-on", 0, row, cmd=f"ZONE{zone}_ACTIVATE"))
                zones_page.add(create_ui_icon("uc:power-off", 1, row, cmd=f"ZONE{zone}_DEACTIVATE"))
                row += 1

        pages.append(zones_page)
        _LOG.info("Created dynamic zones page with %d zones", len(settings_cache.zones))

    # System Settings page
    system_page = UiPage("system", "System")
    system_page.add(create_ui_text("System Settings", 0, 0, size=Size(4, 1)))

    # Dimmer controls
    system_page.add(create_ui_text("Display Dimmer", 0, 1, size=Size(2, 1)))
    system_page.add(create_ui_icon("uc:brightness-max", 0, 2, cmd="SYSTEM_DIMMER_BRIGHT"))
    system_page.add(create_ui_text("Bright", 0, 3, size=Size(1, 1)))
    system_page.add(create_ui_icon("uc:brightness-medium", 1, 2, cmd="SYSTEM_DIMMER_DARK"))
    system_page.add(create_ui_text("Dark", 1, 3, size=Size(1, 1)))
    system_page.add(create_ui_icon("uc:brightness-off", 2, 2, cmd="SYSTEM_DIMMER_OFF"))
    system_page.add(create_ui_text("Off", 2, 3, size=Size(1, 1)))

    # HDMI Output controls
    system_page.add(create_ui_text("HDMI Output", 0, 4, size=Size(2, 1)))
    system_page.add(create_ui_icon("uc:hdmi", 0, 5, cmd="SYSTEM_HDMI_OUTPUT_A"))
    system_page.add(create_ui_text("HDMI A", 0, 6, size=Size(1, 1)))
    system_page.add(create_ui_icon("uc:hdmi", 1, 5, cmd="SYSTEM_HDMI_OUTPUT_B"))
    system_page.add(create_ui_text("HDMI B", 1, 6, size=Size(1, 1)))
    system_page.add(create_ui_icon("uc:hdmi", 2, 5, cmd="SYSTEM_HDMI_OUTPUT_AB"))
    system_page.add(create_ui_text("A + B", 2, 6, size=Size(1, 1)))
    system_page.add(create_ui_icon("uc:close", 3, 5, cmd="SYSTEM_HDMI_OUTPUT_OFF"))
    system_page.add(create_ui_text("Off", 3, 6, size=Size(1, 1)))

    pages.append(system_page)

    return pages


async def create_remote_entity(
    device: SonyAudioDevice, entity_id: str, cmd_handler, settings_cache: DeviceSettingsCache
) -> ucapi.Remote:
    """
    Create a remote entity for a Sony Audio device.

    Args:
        device: Sony Audio device instance
        entity_id: Entity identifier
        cmd_handler: Command handler function
        settings_cache: Device settings cache with discovered capabilities

    Returns:
        Remote entity instance
    """
    try:
        # Get device info
        info = await device.get_device_info()
        device_name = info.get("model", "Sony Audio")

        # Discover all available sources (generic and labeled inputs)
        sources = await discover_all_sources(device)

        _LOG.info("Total discovered sources: %d", len(sources))
        for idx, source in enumerate(sources):
            _LOG.info("  [%d] %s → %s", idx + 1, source.get("title", "N/A"), source.get("source", "N/A"))

        # Create simple commands list dynamically from device capabilities
        simple_commands = create_simple_commands(sources, settings_cache)
        _LOG.info("Created %d simple commands", len(simple_commands))

        # Create button mappings with input sources
        button_mapping = create_button_mappings(sources)

        # Create UI pages dynamically from device capabilities
        ui_pages = create_ui_pages(sources, device_name, settings_cache)

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
        command: Command string (e.g., "INPUT_HDMI1", "INPUT_GAME", "INPUT_BD_DVD")
        sources: List of input sources

    Returns:
        Source URI or None if not found
    """
    # Map command to source
    for source in sources:
        source_uri = source.get("source", "")

        if command == "INPUT_TV" and "tv" in source_uri:
            return source_uri
        elif command.startswith("INPUT_HDMI") and "hdmi" in source_uri and "port=" in source_uri:
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
        elif command.startswith("INPUT_") and source_uri.startswith("extInput:"):
            # Handle labeled inputs (GAME, BD_DVD, SAT_CATV, etc.)
            # Convert command like "INPUT_BD_DVD" back to "bd-dvd"
            input_name = command.replace("INPUT_", "").replace("_", "-").lower()
            if source_uri == f"extInput:{input_name}":
                return source_uri

    return None
