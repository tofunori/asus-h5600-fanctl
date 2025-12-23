# ASUS ProArt H5600QM Fan Control for Linux

Control both CPU and GPU fans on ASUS ProArt StudioBook H5600QM under Linux.

## Features

- **Automatic fan profiles** - Temperature-based fan curves (like ASUS ProArt Creator Hub)
- **Manual fan control** - Set fan speed from 10% to 100%
- **Separate CPU/GPU control** - Control each fan independently
- **5 preset profiles** - Silent, Quiet, Balanced, Performance, Turbo
- **CPU Boost toggle** - Enable/disable AMD CPU boost
- **System tray support** - Minimize to tray, quick access menu
- **Temperature display** - Real-time CPU and GPU temperatures
- **GUI and CLI** - Both graphical and command-line interfaces
- **Aggressive maintain loop** - Prevents EC from overriding your settings

## Supported Hardware

- ASUS ProArt StudioBook 16 OLED H5600QM
- May work on similar models: H5600QE, H5600QR, W5600

## Requirements

- Linux kernel with `acpi_call` module
- Python 3 with PyQt5 (for GUI)
- sudo access

## Installation

### 1. Install dependencies

```bash
# Fedora
sudo dnf install akmod-acpi_call python3-qt5

# Ubuntu/Debian
sudo apt install acpi-call-dkms python3-pyqt5

# Arch
sudo pacman -S acpi_call python-pyqt5
```

### 2. Load the module (and auto-load at boot)

```bash
sudo modprobe acpi_call
echo "acpi_call" | sudo tee /etc/modules-load.d/acpi_call.conf
```

### 3. Install fan control scripts

```bash
git clone https://github.com/tofunori/asus-h5600-fanctl.git
cd asus-h5600-fanctl

# CLI tool
sudo cp fanctl.sh /usr/local/bin/fanctl
sudo chmod +x /usr/local/bin/fanctl

# GUI tool
sudo cp fanctl-gui.py /usr/local/bin/fanctl-gui
sudo chmod +x /usr/local/bin/fanctl-gui

# Polkit policy (allows running GUI without password prompt)
sudo cp org.fanctl.policy /usr/share/polkit-1/actions/
```

### 4. (Optional) Add desktop entry and autostart

```bash
# Desktop entry for KDE/GNOME menu
sudo cp fanctl-gui.desktop /usr/share/applications/

# Autostart at login (optional)
mkdir -p ~/.config/autostart
cp fanctl-gui.desktop ~/.config/autostart/
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
sudo fanctl-gui
# or from KDE menu: "ASUS Fan Control"
```

**GUI Features:**
- Minimize to system tray (click X or "Minimiser" button)
- Right-click tray icon for quick presets
- Double-click tray icon to show window
- Separate sliders for CPU and GPU fans
- Link/unlink fans for individual control

### Automatic Fan Profiles

The GUI includes temperature-based automatic profiles similar to ASUS ProArt Creator Hub:

| Profile | <60°C | 65°C | 70°C | 80°C | 90°C |
|---------|-------|------|------|------|------|
| **Silent** | 0% | 20% | 35% | 55% | 100% |
| **Quiet** | 0% | 25% | 40% | 65% | 100% |
| **Balanced** | 0% | 30% | 50% | 75% | 100% |
| **Performance** | 15% | 40% | 60% | 85% | 100% |
| **Turbo** | 15% | 50% | 75% | 100% | 100% |

- **Silent/Quiet/Balanced**: Fans stay at 0% until 60°C (like official "Whisper mode")
- **Performance/Turbo**: 15% minimum for sustained workloads
- Fan speed is interpolated linearly between temperature thresholds
- Uses the higher temperature between CPU and GPU

## How It Works

This tool uses ACPI calls to communicate directly with the ASUS EC (Embedded Controller).

**Important:** The EC tries to regain control every ~1-2 seconds. The GUI uses an aggressive maintain loop (every 0.1s) to keep your settings. For CLI, use `fanctl maintain` for continuous control.

### ACPI Methods Used

| Method | Purpose |
|--------|---------|
| `CWAP 0x00110013` | CPU fan manual mode (0=auto, 1=manual) |
| `CWAP 0x00110014` | GPU fan manual mode (0=auto, 1=manual) |
| `ST84 0 <value>` | Set CPU fan speed (0x00-0xFF) |
| `ST84 1 <value>` | Set GPU fan speed (0x00-0xFF) |

### Fan Speed Values

| Percent | Hex Value |
|---------|-----------|
| 100% | 0xFF |
| 80% | 0xCC |
| 50% | 0x80 |
| 30% | 0x4D |
| 12% | 0x20 |

## Warning

**Use at your own risk!** Setting fans too low while under heavy load can cause overheating. Monitor your temperatures when using Silent mode.

## License

MIT License

## Credits

Developed by reverse-engineering the ASUS DSDT/ACPI tables on the H5600QM.
