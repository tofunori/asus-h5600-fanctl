#!/bin/bash
# ASUS ProArt H5600QM Fan Control - Installation Script
# Supports: Fedora, Ubuntu/Debian, Arch Linux

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== ASUS H5600QM Fan Control - Installation ===${NC}"
echo ""

# Detect distribution
if [ -f /etc/fedora-release ]; then
    DISTRO="fedora"
elif [ -f /etc/debian_version ]; then
    DISTRO="debian"
elif [ -f /etc/arch-release ]; then
    DISTRO="arch"
else
    echo -e "${RED}Distribution non supportée. Installation manuelle requise.${NC}"
    exit 1
fi

echo -e "${YELLOW}Distribution détectée: $DISTRO${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Ne pas exécuter en tant que root. Utilisez un utilisateur normal avec sudo.${NC}"
    exit 1
fi

# Step 1: Install dependencies
echo -e "${GREEN}[1/5] Installation des dépendances...${NC}"
case $DISTRO in
    fedora)
        sudo dnf install -y dkms kernel-devel python3-qt5 git
        ;;
    debian)
        sudo apt update
        sudo apt install -y dkms linux-headers-$(uname -r) python3-pyqt5 git
        ;;
    arch)
        sudo pacman -S --noconfirm dkms linux-headers python-pyqt5 git
        ;;
esac

# Step 2: Install acpi_call module
echo ""
echo -e "${GREEN}[2/5] Installation du module acpi_call...${NC}"

# Check if already installed
if modinfo acpi_call &>/dev/null; then
    echo -e "${YELLOW}acpi_call déjà installé, skip...${NC}"
else
    case $DISTRO in
        fedora)
            # Fedora: compile from source
            ACPI_CALL_DIR=$(mktemp -d)
            git clone https://github.com/nix-community/acpi_call.git "$ACPI_CALL_DIR"
            cd "$ACPI_CALL_DIR"

            # Get version from dkms.conf.in
            VERSION=$(grep 'PACKAGE_VERSION' dkms.conf.in | cut -d'"' -f2)

            sudo mkdir -p "/usr/src/acpi_call-$VERSION"
            sudo cp -r * "/usr/src/acpi_call-$VERSION/"
            sudo dkms add "acpi_call/$VERSION" 2>/dev/null || true
            sudo dkms build "acpi_call/$VERSION"
            sudo dkms install "acpi_call/$VERSION"

            rm -rf "$ACPI_CALL_DIR"
            ;;
        debian)
            sudo apt install -y acpi-call-dkms
            ;;
        arch)
            sudo pacman -S --noconfirm acpi_call
            ;;
    esac
fi

# Step 3: Load module
echo ""
echo -e "${GREEN}[3/5] Chargement du module acpi_call...${NC}"
sudo modprobe acpi_call
echo "acpi_call" | sudo tee /etc/modules-load.d/acpi_call.conf > /dev/null
echo -e "${YELLOW}Module chargé et configuré pour démarrer au boot${NC}"

# Step 4: Install scripts
echo ""
echo -e "${GREEN}[4/5] Installation des scripts...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo cp "$SCRIPT_DIR/fanctl.sh" /usr/local/bin/fanctl
sudo cp "$SCRIPT_DIR/fanctl-gui.py" /usr/local/bin/fanctl-gui
sudo chmod +x /usr/local/bin/fanctl /usr/local/bin/fanctl-gui

# Install desktop entry
sudo cp "$SCRIPT_DIR/fanctl-gui.desktop" /usr/share/applications/ 2>/dev/null || true

# Install polkit policy for passwordless execution
if [ -f "$SCRIPT_DIR/org.fanctl.policy" ]; then
    sudo cp "$SCRIPT_DIR/org.fanctl.policy" /usr/share/polkit-1/actions/
fi

echo -e "${YELLOW}Scripts installés dans /usr/local/bin/${NC}"

# Step 5: Configure autostart (optional)
echo ""
echo -e "${GREEN}[5/5] Configuration de l'autostart...${NC}"
mkdir -p ~/.config/autostart

cat > ~/.config/autostart/fanctl-gui.desktop << 'EOF'
[Desktop Entry]
Name=ASUS Fan Control
Comment=Control CPU and GPU fans on ASUS ProArt H5600QM
Exec=/usr/local/bin/fanctl-gui
Icon=preferences-system-power
Terminal=false
Type=Application
Categories=System;Settings;HardwareSettings;
X-GNOME-Autostart-enabled=true
EOF

echo -e "${YELLOW}Autostart configuré${NC}"

# Done
echo ""
echo -e "${GREEN}=== Installation terminée ! ===${NC}"
echo ""
echo "Commandes disponibles:"
echo "  fanctl        - Contrôle en ligne de commande"
echo "  fanctl-gui    - Interface graphique"
echo ""
echo -e "${YELLOW}Note: Pour le contrôle sans mot de passe, exécutez:${NC}"
echo '  echo "$USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/$USER'
echo ""
echo -e "${GREEN}Lancement du GUI...${NC}"
nohup fanctl-gui &>/dev/null &
