#!/bin/bash
# ASUS ProArt H5600QM Fan Control
# Contrôle les DEUX ventilateurs (CPU + GPU)
# NOTE: L'EC reprend le contrôle après ~1-2s, utiliser 'maintain' pour garder le contrôle

enable_manual_mode() {
    # Activer mode manuel pour CPU et GPU fans
    echo "\\_SB.ATKD.CWAP 0x00110013 1" | sudo tee /proc/acpi/call > /dev/null
    # Force GPU active bit et manual mode via écriture directe EC
    # (CWAP 0x00110014 échoue car bit 0x02 non actif dans registre 0xCC10)
    echo "\\_SB.PCI0.SBRG.EC0.WRAM 0xCD 0x10 0x03" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.PCI0.SBRG.EC0.WRAM 0xCD 0x30 0x41" | sudo tee /proc/acpi/call > /dev/null
}

disable_manual_mode() {
    # Désactiver mode manuel (retour auto)
    echo "\\_SB.ATKD.CWAP 0x00110013 0" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.ATKD.CWAP 0x00110014 0" | sudo tee /proc/acpi/call > /dev/null
    # Reset EC registers to return control to EC
    echo "\\_SB.PCI0.SBRG.EC0.WRAM 0xCD 0x10 0x00" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.PCI0.SBRG.EC0.WRAM 0xCD 0x30 0x30" | sudo tee /proc/acpi/call > /dev/null
}

set_fans() {
    local cpu_value=$1
    local gpu_value=${2:-$1}  # Si pas de 2e arg, utiliser la même valeur
    echo "\\_SB.PCI0.SBRG.EC0.ST84 0 $cpu_value" | sudo tee /proc/acpi/call > /dev/null
    echo "\\_SB.PCI0.SBRG.EC0.ST84 1 $gpu_value" | sudo tee /proc/acpi/call > /dev/null
}

maintain_fans() {
    local cpu_value=$1
    local gpu_value=${2:-$1}
    echo "Maintien des fans (Ctrl+C pour arrêter)..."
    echo "CPU: $cpu_value, GPU: $gpu_value"
    trap "echo 'Arrêt...'; disable_manual_mode; exit 0" INT
    while true; do
        enable_manual_mode
        set_fans $cpu_value $gpu_value
        sleep 0.1
    done
}

case "$1" in
    max|turbo)
        echo "Mode TURBO - Fans 100%"
        enable_manual_mode
        set_fans 0xFF
        echo "Note: Utiliser 'fanctl maintain 100' pour garder le contrôle"
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
            echo "Maintient les fans à la vitesse spécifiée (boucle continue)"
            exit 1
        fi
        cpu_percent=$2
        gpu_percent=${3:-$2}
        cpu_hex=$(printf "0x%02X" $((cpu_percent * 255 / 100)))
        gpu_hex=$(printf "0x%02X" $((gpu_percent * 255 / 100)))
        maintain_fans $cpu_hex $gpu_hex
        ;;
    status)
        echo "=== Températures ==="
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
        echo "  auto            - Contrôle automatique"
        echo "  set <cpu> [gpu] - Définir pourcentage (0-100)"
        echo "  maintain <cpu> [gpu] - Maintenir vitesse en boucle"
        echo "  status          - Voir températures"
        echo ""
        echo "Exemples:"
        echo "  fanctl set 50        - Les deux fans à 50%"
        echo "  fanctl set 30 80     - CPU 30%, GPU 80%"
        echo "  fanctl maintain 50   - Maintenir à 50% (boucle)"
        ;;
esac
