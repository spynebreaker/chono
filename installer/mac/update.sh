#!/bin/bash
# Chono's updater on macOS, started by Chono when a newer VERSION is published:
#   update.sh --root ROOT --version V --wait-pid PID
# Waits for Chono to close, downloads the main branch, runs the installer over the same
# folder (data/ is kept) and opens Chono again (not with --no-launch). Log: ROOT/update.log
# The whole script is one block, read before it runs: the installer replaces this file.
{
ROOT=""; VERSION=""; WAIT=""; LAUNCH=1
while [ $# -gt 0 ]; do
    case "$1" in
        --root) ROOT="$2"; shift 2 ;;
        --version) VERSION="$2"; shift 2 ;;
        --wait-pid) WAIT="$2"; shift 2 ;;
        --no-launch) LAUNCH=0; shift ;;
        *) shift ;;
    esac
done
[ -n "$ROOT" ] || exit 2
LOG="$ROOT/update.log"
log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }
log "update to $VERSION"
if [ -n "$WAIT" ]; then
    for _ in $(seq 1 120); do kill -0 "$WAIT" 2>/dev/null || break; sleep 1; done
fi
TMP="$(mktemp -d)"
OPTS=(--root "$ROOT")
[ -x "$ROOT/kraken/bin/kraken" ] || OPTS+=(--no-handwriting)
[ -f "$ROOT/libreoffice/CHONO_VERSION.txt" ] || OPTS+=(--no-office)
# Installed without the daily update agent (--no-agent): keep it that way.
[ -f "$HOME/Library/LaunchAgents/io.github.spynebreaker.chono.update.plist" ] || OPTS+=(--no-agent)
APPS="$(cat "$ROOT/apps.txt" 2>/dev/null || echo "$HOME/Applications")"
OPTS+=(--apps "$APPS")
if curl -fsSL --retry 3 -o "$TMP/main.zip" "https://github.com/spynebreaker/chono/archive/refs/heads/main.zip" \
    && unzip -q "$TMP/main.zip" -d "$TMP"; then
    bash "$TMP/chono-main/installer/mac/install.sh" "${OPTS[@]}" >> "$LOG" 2>&1
    log "installer exit $?"
else
    log "download failed"
fi
rm -rf "$TMP"
if [ "$LAUNCH" = 1 ]; then
    open "$APPS/Chono.app" 2>/dev/null || (cd "$ROOT/app" && nohup "$ROOT/env/bin/python" -m chono >/dev/null 2>&1 &)
    log "relaunched"
fi
exit 0
}
