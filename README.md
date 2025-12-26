# ASUS ProArt H5600QM Fan Control for Linux

Control both CPU and GPU fans on ASUS ProArt StudioBook H5600QM under Linux.

## Features

### Fan Control
- **Automatic fan profiles** - Temperature-based fan curves with hysteresis (like ASUS ProArt Creator Hub)
- **Manual fan control** - Set fan speed from 10% to 100%
- **Separate CPU/GPU control** - Control each fan independently
- **5 preset profiles** - Silent, Quiet, Balanced, Performance, Turbo
- **Custom fan curves** - Create your own curves with drag & drop editor (like g-helper)
- **Curve visualization** - Right-click on profiles to see the fan curve graph

### Power Management
- **Power Profiles** - Performance, Balanced, Power Saver (controls CPU energy, GPU power, CPU boost)
- **Battery Charge Limit** - Limit charging to 60%, 80%, or 100% for battery longevity
- **CPU Boost toggle** - Enable/disable AMD CPU boost
- **Sleep/Wake handling** - Automatically stops fan control before suspend and restores after wake

### Interface
- **Dark/Light theme** - Choose your preferred appearance
- **System tray support** - Minimize to tray, quick access menu
- **Temperature display** - Real-time CPU and GPU temperatures with color coding
- **Temperature alerts** - Notification when CPU/GPU exceeds 85°C
- **Autostart option** - Start with system from settings
- **HiDPI support** - Sharp rendering on high-resolution displays
- **Logging** - Minimal logging always on, verbose mode on-demand for debugging
- **GUI and CLI** - Both graphical and command-line interfaces

## Supported Hardware

- ASUS ProArt StudioBook 16 OLED H5600QM
- May work on similar models: H5600QE, H5600QR, W5600

## Quick Install

```bash
git clone https://github.com/tofunori/asus-h5600-fanctl.git
cd asus-h5600-fanctl
./install.sh
```

The install script automatically:
- Detects your distribution (Fedora, Ubuntu/Debian, Arch)
- Installs dependencies
- Compiles acpi_call module (from source on Fedora)
- Configures module to load at boot
- Installs scripts to `/usr/local/bin/`
- Configures autostart
- Launches the GUI

### Optional: Passwordless sudo

For seamless operation without password prompts:
```bash
echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/$USER
```

## Manual Installation

### 1. Install dependencies

```bash
# Fedora
sudo dnf install dkms kernel-devel python3-qt5 python3-dbus git

# Ubuntu/Debian
sudo apt install acpi-call-dkms python3-pyqt5 python3-dbus git

# Arch
sudo pacman -S acpi_call python-pyqt5 python-dbus git
```

### 2. Install acpi_call (Fedora only - compile from source)

```bash
git clone https://github.com/nix-community/acpi_call.git /tmp/acpi_call
cd /tmp/acpi_call
sudo mkdir -p /usr/src/acpi_call-1.2.2
sudo cp -r * /usr/src/acpi_call-1.2.2/
sudo dkms add acpi_call/1.2.2
sudo dkms build acpi_call/1.2.2
sudo dkms install acpi_call/1.2.2
```

### 3. Load the module

```bash
sudo modprobe acpi_call
echo "acpi_call" | sudo tee /etc/modules-load.d/acpi_call.conf
```

### 4. Install fan control scripts

```bash
git clone https://github.com/tofunori/asus-h5600-fanctl.git
cd asus-h5600-fanctl
sudo cp fanctl.sh /usr/local/bin/fanctl
sudo cp fanctl-gui.py /usr/local/bin/fanctl-gui
sudo chmod +x /usr/local/bin/fanctl /usr/local/bin/fanctl-gui
```

## Usage

### Command Line (fanctl)

```bash
fanctl max          # Fans 100%
fanctl perf         # Fans 80%
fanctl balanced     # Fans 50%
fanctl quiet        # Fans 30%
fanctl silent       # Fans minimum (~12%)
fanctl set 60       # Both fans at 60%
fanctl set 30 80    # CPU 30%, GPU 80%
fanctl maintain 50  # Maintain at 50% (continuous loop)
fanctl auto         # Return to automatic control
fanctl status       # Show temperatures
```

### GUI

```bash
fanctl-gui
# or from desktop menu: "ASUS Fan Control"
```

**GUI Features:**
- Minimize to system tray (click X)
- Right-click tray icon for quick presets
- Double-click tray icon to show window
- Separate sliders for CPU and GPU fans
- Link/unlink fans for individual control
- **Right-click on profile buttons** to see fan curve graph

**Power Tab:**
- Power Profiles: Performance / Balanced / Power Saver
- Battery Charge Limit: 60% / 80% / 100%
- Autostart toggle
- Temperature alerts toggle
- Theme selector (System/Dark/Light)
- Verbose logging: Enable for 1h/2h/5h/12h/24h to debug temperature/fan behavior

## Automatic Fan Profiles

Temperature-based profiles with **5°C hysteresis** and **very progressive curves** to prevent fan oscillations:

| Profile | 0-45°C | 50°C | 55°C | 60°C | 65°C | 70°C | 80°C | 85°C | 90°C |
|---------|--------|------|------|------|------|------|------|------|------|
| **Silent** | 0% | 8% | 12% | 18% | 28% | 40% | 60% | 80% | 100% |
| **Quiet** | 0% | 10% | 15% | 22% | 32% | 45% | 65% | 85% | 100% |
| **Balanced** | 0% | 12% | 18% | 26% | 38% | 50% | 70% | 88% | 100% |
| **Performance** | 15% | 20% | 28% | 38% | 50% | 62% | 80% | 95% | 100% |
| **Turbo** | 20% | 28% | 38% | 50% | 62% | 75% | 90% | 100% | 100% |

- **Progressive curves**: Fans start at low speed (8-12%) from 50°C for smooth transitions
- **Hysteresis**: Fan won't slow down until temperature drops by 5°C
- **No abrupt jumps**: More temperature points eliminate oscillation around 60°C
- Uses the higher temperature between CPU and GPU

## Power Profiles

| Profile | CPU Energy | GPU Power | CPU Boost |
|---------|------------|-----------|-----------|
| **Performance** | performance | high | ON |
| **Balanced** | balance_power | auto | OFF |
| **Power Saver** | power | low | OFF |

These control:
- `/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference`
- `/sys/class/drm/card1/device/power_dpm_force_performance_level`
- `/sys/devices/system/cpu/cpufreq/boost`

## Custom Fan Curves

Create your own fan curves with the drag & drop editor (similar to g-helper on Windows):

1. Go to the **Custom** tab
2. Click **New** to create a new curve
3. Name your curve
4. **Drag points** to adjust the temperature-to-fan-speed mapping
5. **Double-click** on the graph to add new points
6. **Right-click** on a point to delete it
7. Edit **CPU and GPU curves separately** for fine-grained control
8. Click **Save**, then **Apply** to activate

Custom curves are saved in `~/.config/ASUS/FanControl.conf` and persist across restarts.

## How It Works

This tool uses ACPI calls to communicate directly with the ASUS EC (Embedded Controller).

### GPU Fan Fix

The standard ACPI method (`CWAP 0x00110014`) for GPU fan control fails on some systems because it checks a "GPU active" bit that may not be set. This tool bypasses the check by writing directly to EC registers:

```bash
# Enable GPU fan manual mode (direct EC write)
WRAM 0xCD 0x10 0x03  # Set GPU active bit
WRAM 0xCD 0x30 0x41  # Enable manual mode
```

### ACPI Methods Used

| Method | Purpose |
|--------|---------|
| `CWAP 0x00110013` | CPU fan manual mode |
| `WRAM 0xCD 0x10` | GPU active flag (direct EC) |
| `WRAM 0xCD 0x30` | Manual mode flag (direct EC) |
| `ST84 0 <value>` | Set CPU fan speed (0x00-0xFF) |
| `ST84 1 <value>` | Set GPU fan speed (0x00-0xFF) |

## Screenshots

**Right-click on a profile to view its fan curve:**

The curve visualization shows:
- Temperature (X-axis) vs Fan Speed (Y-axis)
- Grid lines for easy reading
- Color-coded by profile (Silent=green, Turbo=red)
- Points at each threshold temperature

## Warning

**Use at your own risk!** Setting fans too low while under heavy load can cause overheating. Monitor your temperatures when using Silent mode.

## License

MIT License

## Credits

Developed by reverse-engineering the ASUS DSDT/ACPI tables on the H5600QM.
