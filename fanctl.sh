#!/bin/bash
# ASUS ProArt H5600QM Fan Control
# Contrôle les DEUX ventilateurs (CPU + GPU)

enable_manual_mode() {
    # Activer mode manuel pour CPU et GPU fans
    echo "\\_SB.ATKD.CWAP 0x00110013 1" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.ATKD.CWAP 0x00110014 1" | sudo tee /proc/acpi/call > /dev/null
}

disable_manual_mode() {
    # Désactiver mode manuel (retour auto)
    echo "\\_SB.ATKD.CWAP 0x00110013 0" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.ATKD.CWAP 0x00110014 0" | sudo tee /proc/acpi/call > /dev/null
}

set_fans() {
    local value=$1
    echo "\\_SB.PCI0.SBRG.EC0.ST84 0 $value" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.PCI0.SBRG.EC0.ST84 1 $value" | sudo tee /proc/acpi/call > /dev/null
}

case "$1" in
    max|turbo)
        echo "Mode TURBO - Fans 100%"
        enable_manual_mode
        set_fans 0xFF
        ;;
    high|perf)
        echo "Mode PERFORMANCE - Fans 80%"
        enable_manual_mode
        set_fans 0xCC
        ;;
    medium|balanced)
        echo "Mode BALANCED - Fans 50%"
        enable_manual_mode
        set_fans 0x80
        ;;
    low|quiet)
        echo "Mode QUIET - Fans 30%"
        enable_manual_mode
        set_fans 0x4D
        ;;
    silent)
        echo "Mode SILENT - Fans minimum"
        enable_manual_mode
        set_fans 0x20
        ;;
    auto)
        echo "Mode AUTO - Retour contrôle automatique"
        disable_manual_mode
        echo 1 | sudo tee /sys/devices/platform/h5600_fan/thermal_policy > /dev/null 2>&1
        ;;
    set)
        if [ -z "$2" ]; then
            echo "Usage: fanctl set <0-100>"
            exit 1
        fi
        percent=$2
        hex=$(printf "0x%02X" $((percent * 255 / 100)))
        echo "Fans à $percent% ($hex)"
        enable_manual_mode
        set_fans $hex
        ;;
    status)
        echo "Lecture vitesse fans..."
        sudo python3 /tmp/read_fan_raw.py 2>/dev/null || echo "Script non disponible"
        ;;
    *)
        echo "ASUS H5600QM Fan Control"
        echo ""
        echo "Usage: fanctl <mode>"
        echo ""
        echo "Modes:"
        echo "  max, turbo    - Fans 100%"
        echo "  high, perf    - Fans 80%"
        echo "  medium        - Fans 50%"
        echo "  low, quiet    - Fans 30%"
        echo "  silent        - Fans minimum"
        echo "  auto          - Contrôle automatique"
        echo "  set <0-100>   - Définir pourcentage"
        echo "  status        - Voir vitesse actuelle"
        ;;
esac
