#!/bin/bash
# ASUS ProArt H5600QM Fan Control
# Controls BOTH fans (CPU + GPU)
# NOTE: EC regains control after ~1-2s, use 'maintain' to keep control

enable_manual_mode() {
    # Enable manual mode for CPU and GPU fans
    echo "\\_SB.ATKD.CWAP 0x00110013 1" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.ATKD.CWAP 0x00110014 1" | sudo tee /proc/acpi/call > /dev/null
}

disable_manual_mode() {
    # Disable manual mode (return to auto)
    echo "\\_SB.ATKD.CWAP 0x00110013 0" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.ATKD.CWAP 0x00110014 0" | sudo tee /proc/acpi/call > /dev/null
}

set_fans() {
    local cpu_value=$1
    local gpu_value=${2:-$1}  # If no 2nd arg, use same value
    echo "\\_SB.PCI0.SBRG.EC0.ST84 0 $cpu_value" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.PCI0.SBRG.EC0.ST84 1 $gpu_value" | sudo tee /proc/acpi/call > /dev/null
}

maintain_fans() {
    local cpu_value=$1
    local gpu_value=${2:-$1}
    echo "Maintaining fans (Ctrl+C to stop)..."
    echo "CPU: $cpu_value, GPU: $gpu_value"
    trap "echo 'Stopping...'; disable_manual_mode; exit 0" INT
    while true; do
        enable_manual_mode
        set_fans $cpu_value $gpu_value
        sleep 0.1
    done
}

case "$1" in
    max|turbo)
        echo "TURBO mode - Fans 100%"
        enable_manual_mode
        set_fans 0xFF
        echo "Note: Use 'fanctl maintain 100' to keep control"
        ;;
    high|perf)
        echo "PERFORMANCE mode - Fans 80%"
        enable_manual_mode
        set_fans 0xCC
        ;;
    medium|balanced)
        echo "BALANCED mode - Fans 50%"
        enable_manual_mode
        set_fans 0x80
        ;;
    low|quiet)
        echo "QUIET mode - Fans 30%"
        enable_manual_mode
        set_fans 0x4D
        ;;
    silent)
        echo "SILENT mode - Fans minimum"
        enable_manual_mode
        set_fans 0x20
        ;;
    auto)
        echo "AUTO mode - Returning to automatic control"
        disable_manual_mode
        echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1
        ;;
    set)
        if [ -z "$2" ]; then
            echo "Usage: fanctl set <0-100> [gpu_percent]"
            exit 1
        fi
        cpu_percent=$2
        gpu_percent=${3:-$2}
        cpu_hex=$(printf "0x%02X" $((cpu_percent * 255 / 100)))
        gpu_hex=$(printf "0x%02X" $((gpu_percent * 255 / 100)))
        echo "CPU fan: $cpu_percent% ($cpu_hex), GPU fan: $gpu_percent% ($gpu_hex)"
        enable_manual_mode
        set_fans $cpu_hex $gpu_hex
        ;;
    maintain)
        if [ -z "$2" ]; then
            echo "Usage: fanctl maintain <0-100> [gpu_percent]"
            echo "Maintains fans at specified speed (continuous loop)"
            exit 1
        fi
        cpu_percent=$2
        gpu_percent=${3:-$2}
        cpu_hex=$(printf "0x%02X" $((cpu_percent * 255 / 100)))
        gpu_hex=$(printf "0x%02X" $((gpu_percent * 255 / 100)))
        maintain_fans $cpu_hex $gpu_hex
        ;;
    status)
        echo "=== Temperatures ==="
        cpu_temp=$(cat /sys/class/hwmon/hwmon6/temp1_input 2>/dev/null)
        gpu_temp=$(cat /sys/class/hwmon/hwmon5/temp1_input 2>/dev/null)
        [ -n "$cpu_temp" ] && echo "CPU: $((cpu_temp/1000))°C"
        [ -n "$gpu_temp" ] && echo "GPU: $((gpu_temp/1000))°C"
        ;;
    *)
        echo "ASUS H5600QM Fan Control"
        echo ""
        echo "Usage: fanctl <mode>"
        echo ""
        echo "Modes:"
        echo "  max, turbo      - Fans 100%"
        echo "  high, perf      - Fans 80%"
        echo "  medium          - Fans 50%"
        echo "  low, quiet      - Fans 30%"
        echo "  silent          - Fans minimum"
        echo "  auto            - Automatic control"
        echo "  set <cpu> [gpu] - Set percentage (0-100)"
        echo "  maintain <cpu> [gpu] - Maintain speed in loop"
        echo "  status          - Show temperatures"
        echo ""
        echo "Examples:"
        echo "  fanctl set 50        - Both fans at 50%"
        echo "  fanctl set 30 80     - CPU 30%, GPU 80%"
        echo "  fanctl maintain 50   - Maintain at 50% (loop)"
        ;;
esac
