#!/bin/bash
# Script de instalación para YouTube Music Player en BeagleBone Black
# Uso: ./install.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== YouTube Music Player - Instalación para BeagleBone ===${NC}"
echo ""

# Detectar usuario actual
INSTALL_USER="${SUDO_USER:-$USER}"
INSTALL_HOME=$(eval echo ~$INSTALL_USER)

echo "Usuario de instalación: $INSTALL_USER"
echo "Directorio home: $INSTALL_HOME"
echo ""

# === PASO 1: Instalar dependencias del sistema ===
echo -e "${YELLOW}[1/4] Instalando dependencias del sistema...${NC}"

if command -v apt-get &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y mpv python3-venv python3-pyqt5 python3-pip
    # yt-dlp se instala via pip (más actualizado que el de Debian)
    echo -e "${GREEN}   ✓ Dependencias instaladas${NC}"
else
    echo -e "${RED}   ✗ No se encontró apt-get. Este script es para Debian/Ubuntu.${NC}"
    exit 1
fi

# === PASO 2: Instalar dependencias de Python ===
echo -e "${YELLOW}[2/4] Configurando entorno Python...${NC}"

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$INSTALL_DIR"

# Crear venv si no existe
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   Entorno virtual creado"
fi

# Instalar dependencias
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo -e "${GREEN}   ✓ Dependencias de Python instaladas${NC}"

# === PASO 3: Crear directorio de configuración ===
echo -e "${YELLOW}[3/4] Creando directorios de configuración...${NC}"

mkdir -p "$INSTALL_HOME/.config/ytplayer"
echo -e "${GREEN}   ✓ Directorio ~/.config/ytplayer creado${NC}"

# === PASO 4: Configuración opcional ===
echo ""
echo -e "${YELLOW}[4/4] Configuración opcional...${NC}"
echo ""

# --- Preguntar sobre auto-login ---
read -p "¿Deseas configurar auto-login para el usuario $INSTALL_USER? [s/N] " AUTOLOGIN
AUTOLOGIN=${AUTOLOGIN:-n}

if [[ "$AUTOLOGIN" =~ ^[sS]$ ]]; then
    echo "   Configurando auto-login..."

    # Crear override para getty@tty1
    sudo mkdir -p /etc/systemd/system/getty@tty1.service.d
    sudo tee /etc/systemd/system/getty@tty1.service.d/override.conf > /dev/null <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $INSTALL_USER --noclear %I \$TERM
EOF

    sudo systemctl daemon-reload
    echo -e "${GREEN}   ✓ Auto-login configurado para $INSTALL_USER en tty1${NC}"
fi

# --- Preguntar sobre auto-start de la UI ---
echo ""
read -p "¿Deseas que la UI arranque automáticamente al iniciar sesión? [s/N] " AUTOSTART
AUTOSTART=${AUTOSTART:-n}

if [[ "$AUTOSTART" =~ ^[sS]$ ]]; then
    echo "   Configurando auto-start..."

    # Opción 1: Agregar al .bashrc (más simple para consola)
    BASHRC_MARKER="# YT Music Player Auto-start"

    if ! grep -q "$BASHRC_MARKER" "$INSTALL_HOME/.bashrc" 2>/dev/null; then
        cat >> "$INSTALL_HOME/.bashrc" <<EOF

$BASHRC_MARKER
# Solo ejecutar si estamos en tty1 (no en SSH)
if [ "\$(tty)" = "/dev/tty1" ]; then
    cd "$INSTALL_DIR"
    ./launch.sh
fi
EOF
        echo -e "${GREEN}   ✓ Auto-start configurado en .bashrc${NC}"
    else
        echo -e "${YELLOW}   ⚠ Auto-start ya estaba configurado${NC}"
    fi

    # Opción 2: También crear servicio systemd (opcional, para arranque sin login)
    read -p "   ¿También crear un servicio systemd para arranque sin login? [s/N] " SYSTEMD_SERVICE
    SYSTEMD_SERVICE=${SYSTEMD_SERVICE:-n}

    if [[ "$SYSTEMD_SERVICE" =~ ^[sS]$ ]]; then
        # Crear servicio systemd
        sudo tee /etc/systemd/system/ytplayer.service > /dev/null <<EOF
[Unit]
Description=YouTube Music Player
After=network.target sound.target

[Service]
Type=simple
User=$INSTALL_USER
WorkingDirectory=$INSTALL_DIR
Environment=DISPLAY=:0
Environment=QT_QPA_PLATFORM=linuxfb
ExecStart=$INSTALL_DIR/launch.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable ytplayer.service
        echo -e "${GREEN}   ✓ Servicio systemd 'ytplayer' creado y habilitado${NC}"
        echo "      Para iniciar ahora: sudo systemctl start ytplayer"
        echo "      Para ver logs: sudo journalctl -u ytplayer -f"
    fi
fi

# === Resumen final ===
echo ""
echo -e "${GREEN}=== INSTALACIÓN COMPLETADA ===${NC}"
echo ""
echo "Para ejecutar manualmente:"
echo "   cd $INSTALL_DIR"
echo "   ./launch.sh"
echo ""

if [[ "$AUTOLOGIN" =~ ^[sS]$ ]] || [[ "$AUTOSTART" =~ ^[sS]$ ]]; then
    echo "Configuración aplicada:"
    [[ "$AUTOLOGIN" =~ ^[sS]$ ]] && echo "   ✓ Auto-login en tty1"
    [[ "$AUTOSTART" =~ ^[sS]$ ]] && echo "   ✓ Auto-start de la UI"
    echo ""
fi

echo -e "${YELLOW}IMPORTANTE:${NC}"
echo "1. Las cookies deben copiarse desde tu PC con Firefox:"
echo "   ./export_cookies.sh $INSTALL_USER@$(hostname)"
echo ""
echo "2. Reinicia la BeagleBone para probar la configuración:"
echo "   sudo reboot"
echo ""
