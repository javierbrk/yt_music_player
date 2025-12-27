#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
VENV_DIR="venv"

# --- Helper Functions ---
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Pre-flight Checks ---

# 1. Check for essential system commands
if ! command_exists python3; then
    echo "ERROR: Python 3 is not installed. Please install it to continue."
    exit 1
fi

if ! command_exists mpv; then
    echo "ERROR: mpv is not installed. Please install it to continue."
    echo "On Debian/Ubuntu: sudo apt install mpv"
    echo "On Arch Linux: sudo pacman -S mpv"
    echo "On Fedora: sudo dnf install mpv"
    exit 1
fi

# 2. Check if the Python venv module is available
if ! python3 -c "import venv" >/dev/null 2>&1; then
    echo "ERROR: The Python 'venv' module is not available."
    echo "Please install it to continue. On Debian/Ubuntu, this is often in the 'python3-venv' package."
    echo "e.g., 'sudo apt install python3-venv'"
    exit 1
fi

# 3. Check for PyQt5 system libraries (optional but good practice)
echo "Checking for PyQt5 system libraries..."
if dpkg -l | grep -q "python3-pyqt5"; then
    echo "INFO: PyQt5 system libraries found (Debian/Ubuntu)."
elif rpm -q "python3-qt5-base" >/dev/null 2>&1; then
    echo "INFO: PyQt5 system libraries found (Fedora/CentOS)."
else
    echo "WARNING: System-level PyQt5 libraries not detected."
    echo "         Installation via pip (next step) should handle this, but if you encounter"
    echo "         GUI-related errors, you may need to install them manually."
    echo "         e.g., 'sudo apt install python3-pyqt5' or 'sudo dnf install python3-qt5-base'"
fi
echo "" # newline for readability


# --- Setup & Launch ---

# 1. Create the Python virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "INFO: Creating Python virtual environment in './$VENV_DIR/'..."
    python3 -m venv "$VENV_DIR"
fi

# Define paths to executables inside the venv
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# 2. Install/update dependencies using the venv's pip
echo "INFO: Installing/updating dependencies from requirements.txt..."
"$VENV_PIP" install -r requirements.txt

echo "INFO: Installation complete."
echo ""

# 3. Launch the application using the venv's python
echo "INFO: Launching YouTube Music Player..."
"$VENV_PYTHON" yt_mp_player_qt5.py

echo "INFO: Application closed."