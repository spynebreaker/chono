#!/bin/bash
# Short installer for Chono on a Mac, typed in Terminal:
#   curl -fsSL https://raw.githubusercontent.com/spynebreaker/chono/main/get.sh | bash
# Downloads the current main branch with curl (so macOS doesn't block the program) and runs
# installer/mac/install.sh. Extra options go to the installer: ... | bash -s -- --no-handwriting
set -e
T="$(mktemp -d)"
echo "Bajando Chono..."
curl -fsSL -o "$T/chono.zip" https://github.com/spynebreaker/chono/archive/refs/heads/main.zip
unzip -q "$T/chono.zip" -d "$T"
echo "Instalando Chono (10 a 15 minutos)..."
bash "$T/chono-main/installer/mac/install.sh" "$@"
rm -rf "$T"
