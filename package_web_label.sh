#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.build-venv"
PYTHON_EXE="$VENV_DIR/bin/python"

if [ ! -x "$PYTHON_EXE" ]; then
  echo "[1/4] Creating build virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

echo "[2/4] Installing build dependencies..."
"$PYTHON_EXE" -m pip install --upgrade pip
"$PYTHON_EXE" -m pip install -r requirements.txt pyinstaller

echo "[3/4] Building standalone app..."
"$PYTHON_EXE" -m PyInstaller --clean web_label.spec

echo "[4/4] Build complete."
echo "Executable output:"
echo "  $SCRIPT_DIR/dist/web_label"
