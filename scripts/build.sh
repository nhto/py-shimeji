#!/usr/bin/env bash
# Build a shareable py-shimeji folder under dist/py-shimeji/
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -d .venv ]]; then
    python -m venv .venv
fi

# Git Bash on Windows: use Scripts/python.exe; Unix: bin/python
if [[ -x .venv/Scripts/python.exe ]]; then
    PYTHON=.venv/Scripts/python.exe
    PYINSTALLER=.venv/Scripts/pyinstaller.exe
else
    PYTHON=.venv/bin/python
    PYINSTALLER=.venv/bin/pyinstaller
fi

"$PYTHON" -m pip install -q -r requirements-dev.txt
"$PYINSTALLER" --noconfirm --clean py-shimeji.spec
cp -f .env.example dist/py-shimeji/.env.example

echo ""
echo "Build complete: dist/py-shimeji/py-shimeji.exe"
echo "Zip dist/py-shimeji to share the app."
