#!/bin/bash
# setup_deps.sh — Install system-level dependencies

set -e

echo "Checking system dependencies..."

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    DISTRO="unknown"
fi

# Python 3.10+
if ! command -v python3 &> /dev/null; then
    echo "Installing Python 3..."
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" || "$DISTRO" == "linuxmint" ]]; then
        sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-venv
    elif [[ "$DISTRO" == "arch" || "$DISTRO" == "manjaro" ]]; then
        sudo pacman -S --noconfirm python python-pip
    elif [[ "$DISTRO" == "fedora" ]]; then
        sudo dnf install -y python3 python3-pip
    else
        echo "⚠ Could not detect distro. Install Python 3.10+ manually."
    fi
else
    echo "✓ Python 3 found: $(python3 --version)"
fi

# xdotool (for window management on Linux)
if ! command -v xdotool &> /dev/null; then
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" || "$DISTRO" == "linuxmint" ]]; then
        sudo apt-get install -y -qq xdotool 2>/dev/null || echo "⚠ xdotool install failed (optional)"
    elif [[ "$DISTRO" == "arch" ]]; then
        sudo pacman -S --noconfirm xdotool 2>/dev/null || echo "⚠ xdotool install failed (optional)"
    else
        echo "⚠ xdotool not found (optional, for window management)"
    fi
else
    echo "✓ xdotool found"
fi

# Git (for cloning if needed)
if ! command -v git &> /dev/null; then
    echo "Installing git..."
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        sudo apt-get install -y -qq git
    elif [[ "$DISTRO" == "arch" ]]; then
        sudo pacman -S --noconfirm git
    fi
else
    echo "✓ git found"
fi

# curl (for downloads)
if ! command -v curl &> /dev/null; then
    echo "Installing curl..."
    if [[ "$DISTRO" == "ubuntu" || "$DISTRO" == "debian" ]]; then
        sudo apt-get install -y -qq curl
    elif [[ "$DISTRO" == "arch" ]]; then
        sudo pacman -S --noconfirm curl
    fi
else
    echo "✓ curl found"
fi

echo "✅ System dependencies ready"
