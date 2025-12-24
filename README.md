# ASUS ProArt H5600QM Fan Control for Linux

Control both CPU and GPU fans on ASUS ProArt StudioBook H5600QM under Linux.

## Features

- **Automatic fan profiles** - Temperature-based fan curves with hysteresis (like ASUS ProArt Creator Hub)
- **Manual fan control** - Set fan speed from 10% to 100%
- **Separate CPU/GPU control** - Control each fan independently
- **5 preset profiles** - Silent, Quiet, Balanced, Performance, Turbo
- **Curve visualization** - Right-click on profiles to see the fan curve graph
- **Dark/Light theme** - Choose your preferred appearance
- **CPU Boost toggle** - Enable/disable AMD CPU boost
- **System tray support** - Minimize to tray, quick access menu
- **Temperature display** - Real-time CPU and GPU temperatures
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
sudo dnf install dkms kernel-devel python3-qt5 git

# Ubuntu/Debian
sudo apt install acpi-call-dkms python3-pyqt5 git

# Arch
sudo pacman -S acpi_call python-pyqt5 git
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
- Theme selector (System/Dark/Light)

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
