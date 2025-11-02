# Quick Start Guide - Sony Audio Control Integration

## Fixed Issues

✅ **Deprecation warning fixed** - No more `asyncio.get_event_loop()` warning  
✅ **Service name conflict fixed** - Now properly handles existing services

## Starting the Integration

### Option 1: Use the startup script
```bash
cd intg-sony
./start.sh
```

### Option 2: Run directly
```bash
cd intg-sony
uv run python driver.py
```

You should see:
```
2025-11-01 14:30:17 | INFO | __main__ | Starting Sony Audio Control integration driver
2025-11-01 14:30:17 | DEBUG | ucapi.api | Publishing driver: sony_audio._uc-integration._tcp.local.
2025-11-01 14:30:18 | INFO | ucapi.api | Driver is up: sony_audio, version: 0.1.0
2025-11-01 14:30:18 | INFO | websockets.server | server listening on 0.0.0.0:9095
```

## Adding to Unfolded Circle Remote

### Method 1: Auto-Discovery (Recommended)

1. **Start the integration** (using one of the methods above)

2. **On your Unfolded Circle Remote:**
   - Open **Settings**
   - Go to **Integrations**
   - Look for **Sony Audio Control** or **sony_audio**
   - Tap to add it

3. **If you don't see it:**
   - Pull down to refresh the integrations list
   - Wait 10-20 seconds and refresh again
   - Make sure Remote and computer are on same network

### Method 2: Manual Connection (If Auto-Discovery Fails)

1. **Find your computer's IP address:**
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```
   Example output: `inet 192.168.1.234`

2. **On your Unfolded Circle Remote:**
   - Go to **Settings** → **Integrations**
   - Tap **Add Integration** (or similar)
   - Select **Custom Integration** or **Custom WebSocket**
   
3. **Enter connection details:**
   - **URL**: `ws://192.168.1.234:9095` (use your actual IP)
   - **Name**: Sony Audio Control

## Setup Your Sony Device

Once the integration is added:

### Step 1: Choose Discovery Method
- **Auto-discover**: Let it find your Sony device automatically (recommended)
- **Manual**: Enter your Sony device's IP address

### Step 2: Select Device
- If auto-discovery: Select your TA-AN1000 from the list
- If manual: Enter `192.168.1.201` (or your device's IP)

### Step 3: Confirm
- Review device information (model, version)
- Optionally customize the device name
- Tap **Complete**

## What You Get

After setup, you'll have a remote entity with:

### Physical Button Controls
- **Power button** → Power toggle
- **Volume up/down** → Volume control
- **Mute button** → Mute toggle
- **Channel up/down** → Volume control (alternative)

### Touchscreen UI Pages

**Main Controls Page:**
- Power On/Off buttons
- Volume Up/Down buttons
- Mute toggle button

**Inputs Page:**
- TV (ARC)
- HDMI 1
- HDMI 2
- Bluetooth Audio
- Analog (Line In)
- AirPlay

## Troubleshooting

### Integration Not Showing Up

1. **Check both devices are on same network:**
   ```bash
   # Your computer
   ifconfig | grep "inet "
   
   # Should be same subnet as Remote (e.g., both 192.168.1.x)
   ```

2. **Check firewall isn't blocking:**
   - macOS: System Preferences → Security & Privacy → Firewall
   - Allow Python or driver.py

3. **Check port 9095 is available:**
   ```bash
   lsof -i :9095
   # Should be empty or show driver.py
   ```

4. **Verify mDNS is working:**
   ```bash
   dns-sd -B _uc-integration._tcp
   # Should show: sony_audio
   ```

5. **Try manual connection** (see Method 2 above)

### "NonUniqueNameException" Error

This means another instance is running:
```bash
# Kill all driver.py processes
pkill -f driver.py

# Wait a moment
sleep 2

# Try again
./start.sh
```

### Device Not Connecting

1. **Check Sony device is powered on**
2. **Verify Sony device IP address:**
   ```bash
   cd intg-sony
   uv run python test_device.py
   ```
3. **Update IP in setup** if it changed

### Remote Says "Unavailable"

The integration might have crashed. Check logs:
```bash
# Run in foreground to see errors
cd intg-sony
uv run python driver.py
```

## Testing Commands

Once connected, test these:

1. **Power**: Toggle power on/off
2. **Volume**: Adjust volume using remote buttons
3. **Mute**: Toggle mute
4. **Inputs**: Switch between HDMI 1, HDMI 2, Bluetooth, etc.

## Stopping the Integration

Press `Ctrl+C` in the terminal where driver.py is running.

## Running as Background Service

For permanent installation, you can set up the integration as a system service:

### macOS (launchd)
Create file: `~/Library/LaunchAgents/com.unfoldedcircle.sony.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.unfoldedcircle.sony</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/james/Development/uc-sony/intg-sony/start.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/sony-audio-integration.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/sony-audio-integration.log</string>
</dict>
</plist>
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.unfoldedcircle.sony.plist
```

### Linux (systemd)
Create file: `~/.config/systemd/user/sony-audio.service`

```ini
[Unit]
Description=Sony Audio Control Integration
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/user/intg-sony
ExecStart=/home/user/intg-sony/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

Enable it:
```bash
systemctl --user enable sony-audio.service
systemctl --user start sony-audio.service
```

## Getting Help

1. **Check logs** - Run driver.py in foreground
2. **Test device connection** - Run `test_device.py`
3. **Verify discovery** - Run `test_discovery.sh`
4. **Read full docs** - See `README.md` and `TESTING.md`

## Success! 

Once everything is working, you should be able to:
- ✅ Control power, volume, and mute
- ✅ Switch inputs seamlessly
- ✅ Use both physical buttons and touchscreen
- ✅ See real-time state updates on the Remote

Enjoy your Sony Audio integration! 🎉

