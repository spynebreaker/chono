#!/bin/bash
# Removes Chono from this Mac. The search index and settings (data/) are kept unless --all.
#   bash uninstall.sh [--root DIR] [--apps DIR] [--all]
ROOT="$HOME/Library/Application Support/Chono"; APPS="$HOME/Applications"; ALL=0
while [ $# -gt 0 ]; do
    case "$1" in
        --root) ROOT="$2"; shift 2 ;;
        --apps) APPS="$2"; shift 2 ;;
        --all) ALL=1; shift ;;
        *) shift ;;
    esac
done
LSREG=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister
[ -d "$APPS/Chono.app" ] && "$LSREG" -u "$APPS/Chono.app" 2>/dev/null
[ -d "$ROOT/libreoffice/LibreOffice.app" ] && "$LSREG" -u "$ROOT/libreoffice/LibreOffice.app" 2>/dev/null
launchctl bootout "gui/$(id -u)/io.github.spynebreaker.chono.update" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/io.github.spynebreaker.chono.update.plist"
rm -rf "$APPS/Chono.app"
if [ -d "$ROOT" ]; then
    if [ "$ALL" = 1 ]; then rm -rf "$ROOT"; else find "$ROOT" -mindepth 1 -maxdepth 1 ! -name data -exec rm -rf {} +; fi
fi
echo "UNINSTALL DONE"
