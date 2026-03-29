#!/bin/bash

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_EXE="$VENV_DIR/bin/python"

pause_on_error() {
  local exit_code="$1"
  if [ "$exit_code" -ne 0 ]; then
    echo
    echo "The web label tool exited with an error."
    read -r -p "Press Enter to close..."
  fi
  exit "$exit_code"
}

trap 'pause_on_error $?' EXIT

if [ ! -x "$PYTHON_EXE" ]; then
  echo "[1/3] Creating local virtual environment..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv "$VENV_DIR"
  elif command -v python >/dev/null 2>&1; then
    python -m venv "$VENV_DIR"
  else
    echo "Python 3 was not found."
    echo "Install Python 3 first, then run this launcher again."
    exit 1
  fi
fi

if [ ! -x "$PYTHON_EXE" ]; then
  echo "Failed to create the virtual environment at:"
  echo "$VENV_DIR"
  exit 1
fi

echo "[2/3] Installing or updating launcher dependencies..."
"$PYTHON_EXE" -m pip install --upgrade pip
"$PYTHON_EXE" -m pip install -r requirements.txt

echo "[3/3] Starting web label tool..."
if [ "$#" -gt 0 ]; then
  "$PYTHON_EXE" web_label.py --label_video_path "$1"
else
  "$PYTHON_EXE" web_label.py
fi
