# ASUS ProArt H5600QM Fan Control for Linux

Control both CPU and GPU fans on ASUS ProArt StudioBook H5600QM under Linux.

## Features

- **Manual fan control** - Set fan speed from 10% to 100%
- **Preset modes** - Turbo, Performance, Balanced, Quiet, Silent
- **CPU Boost toggle** - Enable/disable AMD CPU boost
- **GUI and CLI** - Both graphical and command-line interfaces
- **Both fans supported** - Controls CPU fan (left) and GPU fan (right)

## Supported Hardware

- ASUS ProArt StudioBook 16 OLED H5600QM
- May work on similar models: H5600QE, H5600QR, W5600

## Requirements

- Linux kernel with `acpi_call` module
- Python 3 with tkinter (for GUI)
- sudo access

## Installation

### 1. Install acpi_call module

```bash
# Fedora
sudo dnf install akmod-acpi_call

# Ubuntu/Debian
sudo apt install acpi-call-dkms

# Arch
sudo pacman -S acpi_call
```

### 2. Load the module

```bash
sudo modprobe acpi_call
```

### 3. Install fan control scripts

```bash
# CLI tool
sudo cp fanctl.sh /usr/local/bin/fanctl
sudo chmod +x /usr/local/bin/fanctl

# GUI tool
sudo cp fanctl-gui.py /usr/local/bin/fanctl-gui
sudo chmod +x /usr/local/bin/fanctl-gui
```

## Usage

### Command Line (fanctl)

```bash
fanctl max       # Fans 100%
fanctl perf      # Fans 80%
fanctl balanced  # Fans 50%
fanctl quiet     # Fans 30%
fanctl silent    # Fans minimum (~12%)
fanctl set 60    # Fans at 60%
fanctl auto      # Return to automatic control
fanctl status    # Show current fan speed
```

### GUI

```bash
sudo fanctl-gui
# or
sudo python3 fanctl-gui.py
```

## How It Works

This tool uses ACPI calls to communicate directly with the ASUS EC (Embedded Controller):

1. **Enable manual mode**: `\_SB.ATKD.CWAP 0x00110013 1` (CPU) and `0x00110014 1` (GPU)
2. **Set fan speed**: `\_SB.PCI0.SBRG.EC0.ST84 <fan> <speed>` where fan is 0 (CPU) or 1 (GPU)
3. **Return to auto**: Disable manual mode and set thermal policy

## Technical Details

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

⚠️ **Use at your own risk!** Setting fans too low while under heavy load can cause overheating. Monitor your temperatures when using Silent mode.

## License

MIT License

## Credits

Developed by reverse-engineering the ASUS DSDT/ACPI tables on the H5600QM.
