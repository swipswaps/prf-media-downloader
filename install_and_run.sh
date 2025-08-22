#!/usr/bin/env bash
# PRF installer/runner for PRF Media Downloader — v2025.08.22
# Supported: macOS (Homebrew), Linux (apt/dnf/pacman), Windows via WSL

set -euo pipefail

echo "[PRF] Detecting Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "[PRF] Python3 not found. Please install Python 3.9+ and re-run."
  exit 1
fi

PY=python3
PIP="${PY} -m pip"

echo "[PRF] Creating venv at .venv ..."
${PY} - <<'PYCODE'
import os, sys, venv
venv_dir = ".venv"
if not os.path.isdir(venv_dir):
    venv.EnvBuilder(with_pip=True).create(venv_dir)
print("OK")
PYCODE

# shellcheck disable=SC1091
source .venv/bin/activate || { echo "[PRF] Could not activate venv"; exit 1; }

echo "[PRF] Upgrading pip ..."
pip install --upgrade pip >/dev/null

echo "[PRF] Installing dependencies ..."
pip install requests pillow beautifulsoup4 >/dev/null
# tkinter note: on many Linux distros, tkinter is packaged separately.
# We attempt best-effort guidance:
if python - <<'PY'
try:
    import tkinter as tk  # noqa
    import PIL  # noqa
    print("OK")
except Exception as e:
    print("NEED_TK")
PY
then
  :
else
  echo "[PRF] Tkinter and/or Pillow preview may be missing."
  echo "      If GUI fails, install Tk:"
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "      Debian/Ubuntu: sudo apt-get install python3-tk"
    echo "      Fedora/RHEL:   sudo dnf install python3-tkinter"
    echo "      Arch:          sudo pacman -S tk"
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "      macOS usually ships Tk; for issues: brew install python-tk@3.12 (or matching)"
  fi
fi

echo "[PRF] Ready."
echo
echo "Usage (headless):"
echo "  . .venv/bin/activate"
echo "  python prf_media_downloader.py -q \"nature\" -n 12 -s unsplash,pexels,pixabay,coverr,mixkit,videvo -o downloads"
echo
echo "Usage (GUI with previews):"
echo "  . .venv/bin/activate"
echo "  python prf_media_downloader.py --gui -q \"city skyline\" -n 8 -s pexels,coverr,mixkit,videvo -o downloads"
echo
echo "API keys (optional, for APIs):"
echo "  export UNSPLASH_KEY=...  export PEXELS_KEY=...  export PIXABAY_KEY=..."
echo
echo "[PRF] Launching a sample GUI now (no keys required for scrape sources) ..."
python prf_media_downloader.py --gui -q "nature" -n 6 -s coverr,mixkit,videvo -o downloads || true
