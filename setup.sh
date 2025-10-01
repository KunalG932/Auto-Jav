#!/usr/bin/env bash

# A minimal setup script for Debian/Ubuntu systems.
# It installs build tools, Python, ffmpeg, libtorrent and pip packages used by the project.
# Run as a user with sudo privileges: sudo ./setup.sh

set -euo pipefail

echo "Updating apt and installing build essentials..."
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
	libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev software-properties-common

echo "Installing Python 3.11 (from deadsnakes)..."
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

echo "Ensuring pip is up-to-date for Python 3.11..."
sudo python3.11 -m pip install --upgrade pip setuptools wheel

echo "Installing ffmpeg (required for remuxing/compression)..."
sudo apt install -y ffmpeg

echo "Installing libtorrent (system package) and other helpers..."
sudo apt install -y python3-libtorrent || echo "python3-libtorrent not available in apt; you may need to build libtorrent from source or install via pip/libtorrent-binaries" 

echo "Creating virtualenv and installing pip requirements..."
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -U -r requirements.txt || echo "pip install may have failed; inspect output and install missing packages manually"

echo "Optional: html-telegraph-poster and lxml_html_clean are included in requirements; if they failed to build, install system libxml2/libxslt dev packages:"
echo "  sudo apt install -y libxml2-dev libxslt1-dev"

echo "Setup complete. Activate virtualenv with: source .venv/bin/activate"

echo "If you are on Windows, install ffmpeg and Python 3.11 separately and create a virtualenv using Python's venv module." 
