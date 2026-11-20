#!/bin/bash
# Chono installer for macOS (Apple silicon and Intel), no administrator rights, no Homebrew.
#
#   bash installer/mac/install.sh [--root DIR] [--apps DIR] [--no-handwriting] [--no-app]
#
# Everything goes under ROOT (default ~/Library/Application Support/Chono):
#   mm/         micromamba (package manager, one program)
#   env/        Python 3.12 with Tk, Tesseract and Ghostscript (conda-forge) and the pip packages
#   tessdata/   Spanish, old Spanish, English and orientation models
#   pdfcraft/   Chono's build of PdfCraft (viewer and forms), ad hoc signed
#   kraken/     handwriting engine (own Python environment)
#   models/     handwriting model
#   app/        the Chono program
#   data/       search index and settings (kept by updates and by uninstall.sh)
# and Chono.app goes into APPS (default ~/Applications): open it from Finder, Launchpad or
# the Dock, and choose it in Open With for PDF files.
#
# Files are downloaded with curl, which marks nothing as "downloaded from the internet",
# so macOS opens Chono without the warning for programs not notarized by Apple.
set -euo pipefail

ROOT="$HOME/Library/Application Support/Chono"
APPS="$HOME/Applications"
HANDWRITING=1
MAKE_APP=1
while [ $# -gt 0 ]; do
    case "$1" in
        --root) ROOT="$2"; shift 2 ;;
        --apps) APPS="$2"; shift 2 ;;
        --no-handwriting) HANDWRITING=0; shift ;;
        --no-app) MAKE_APP=0; shift ;;
        *) echo "unknown option $1" >&2; exit 2 ;;
    esac
done

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
APP_NAME="Chono"
PATCHED_TAG="pdfcraft-0.21.1-chono9"
PATCHED_SHA="523e786e026d282f2a42b7ba9505d09f3d344eb5a9d36b60b762cba683cbbc6a"
MODEL_SHA="15313b51ace64cbfa81f8f6ef25ad64f04e5a6fb7f7823e67b107527bc081ac9"

mkdir -p "$ROOT" "$ROOT/tmp"
# keep pip's downloads off the system disk and out of caches that are never cleaned
export PIP_NO_CACHE_DIR=1 TMPDIR="$ROOT/tmp"
LOG="$ROOT/install.log"
step() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
get() { curl -fsSL --retry 3 -o "$2" "$1"; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
step "install start, root=$ROOT"

case "$(uname -m)" in
    arm64) PLAT=osx-arm64 ;;
    x86_64) PLAT=osx-64 ;;
    *) echo "unsupported processor $(uname -m)" >&2; exit 1 ;;
esac

# 1. micromamba
MM="$ROOT/mm/micromamba"
if [ ! -x "$MM" ]; then
    mkdir -p "$ROOT/mm"
    get "https://github.com/mamba-org/micromamba-releases/releases/latest/download/micromamba-$PLAT" "$MM"
    chmod +x "$MM"
fi
export MAMBA_ROOT_PREFIX="$ROOT/mm/root"
step "micromamba ok"

# 2. Python, Tk, Tesseract, Ghostscript and the pip packages
ENV="$ROOT/env"
PY="$ENV/bin/python"
if [ ! -x "$PY" ]; then
    "$MM" create -y -q -p "$ENV" -c conda-forge python=3.12 tk tesseract ghostscript >> "$LOG" 2>&1
fi
"$PY" -m pip install -q --disable-pip-version-check -r "$REPO/installer/requirements.txt" >> "$LOG" 2>&1
step "environment ok"

# 3. OCR models (the same as on Windows) and Tesseract's config files
TD="$ROOT/tessdata"
mkdir -p "$TD"
for m in spa spa_old eng; do
    [ -f "$TD/$m.traineddata" ] || get "https://github.com/tesseract-ocr/tessdata_best/raw/main/$m.traineddata" "$TD/$m.traineddata"
done
[ -f "$TD/osd.traineddata" ] || get "https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata" "$TD/osd.traineddata"
CONF="$(find "$ENV/share" -type d -path '*tessdata/configs' | head -1)"
[ -n "$CONF" ] || { echo "tesseract configs not found in environment" >&2; exit 1; }
cp -R "$(dirname "$CONF")/." "$TD/"
step "tessdata ok"

# 4. Chono's build of PdfCraft (universal, ad hoc signed), checksum verified
PC="$ROOT/pdfcraft"
if ! grep -qs "$PATCHED_TAG" "$PC/CHONO_PATCHED.txt"; then
    Z="$ROOT/pdfcraft-chono.zip"
    get "https://github.com/spynebreaker/chono/releases/download/pdfcraft-macos/pdfcraft-chono-macos-universal.zip" "$Z"
    if [ "$(sha "$Z")" != "$PATCHED_SHA" ]; then rm -f "$Z"; echo "PdfCraft checksum mismatch" >&2; exit 1; fi
    rm -rf "$PC"; mkdir -p "$PC"
    unzip -q -o "$Z" -d "$PC"
    rm -f "$Z"
fi
step "pdfcraft ($(head -1 "$PC/CHONO_PATCHED.txt")) ok"

# 4b. handwriting engine (about 1.1 GB, a few minutes) and its model
KR="$ROOT/kraken"
MODEL="$ROOT/models/medium.safetensors"
if [ "$HANDWRITING" = 1 ]; then
    if [ ! -x "$KR/bin/kraken" ]; then
        "$PY" -m venv "$KR"
        "$KR/bin/python" -m pip install -q --disable-pip-version-check -r "$REPO/installer/kraken-requirements.txt" >> "$LOG" 2>&1
    fi
    mkdir -p "$ROOT/models"
    [ -f "$MODEL" ] || get "https://zenodo.org/api/records/21788410/files/medium.safetensors/content" "$MODEL"
    if [ "$(sha "$MODEL")" != "$MODEL_SHA" ]; then rm -f "$MODEL"; echo "handwriting model checksum mismatch" >&2; exit 1; fi
    rm -f "$ROOT/models/small.safetensors"
    step "handwriting ok"
fi

# 5. the program itself (data/ is left alone)
rm -rf "$ROOT/app"
cp -R "$REPO/app" "$ROOT/app"
cp "$REPO/installer/mac/update.sh" "$ROOT/update.sh"
step "app ok"

# 6. self-test
export TESSDATA_PREFIX="$TD"
LANGS="$("$ENV/bin/tesseract" --list-langs 2>&1 | tr '\n' ' ')"
case "$LANGS" in *spa*) ;; *) echo "self-test failed: $LANGS" >&2; exit 1 ;; esac
(cd "$ROOT/app" && "$PY" -c "import chono.launcher, chono.tools") || { echo "self-test failed: app" >&2; exit 1; }
"$PC/pdfcraft-cli" info "$REPO/installer/mac/selftest.pdf" > /dev/null || { echo "self-test failed: pdfcraft" >&2; exit 1; }
if [ "$HANDWRITING" = 1 ]; then LANGS="$LANGS; $("$KR/bin/kraken" --version 2>&1 | tail -1)"; fi
step "self-test ok ($LANGS)"

# 7. Chono.app: the icon to open it, and Open With for PDF files
if [ "$MAKE_APP" = 1 ]; then
    A="$APPS/$APP_NAME.app"
    rm -rf "$A"
    mkdir -p "$A/Contents/MacOS" "$A/Contents/Resources"
    cat > "$A/Contents/MacOS/$APP_NAME" <<EOF
#!/bin/bash
cd "$ROOT/app"
exec "$PY" -m chono "\$@"
EOF
    chmod +x "$A/Contents/MacOS/$APP_NAME"
    VER="$(cat "$REPO/VERSION")"
    cat > "$A/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$APP_NAME</string>
  <key>CFBundleDisplayName</key><string>$APP_NAME</string>
  <key>CFBundleIdentifier</key><string>io.github.spynebreaker.chono</string>
  <key>CFBundleExecutable</key><string>$APP_NAME</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VER</string>
  <key>CFBundleVersion</key><string>$VER</string>
  <key>LSMinimumSystemVersion</key><string>11.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>CFBundleDocumentTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeName</key><string>PDF</string>
      <key>CFBundleTypeRole</key><string>Viewer</string>
      <key>LSHandlerRank</key><string>Alternate</string>
      <key>LSItemContentTypes</key><array><string>com.adobe.pdf</string></array>
    </dict>
  </array>
</dict>
</plist>
EOF
    codesign --force --sign - "$A" >> "$LOG" 2>&1 || true
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$A" >> "$LOG" 2>&1 || true
    step "app bundle ok ($A)"
fi

echo "$APPS" > "$ROOT/apps.txt"
cp "$REPO/VERSION" "$ROOT/VERSION"
step "INSTALL DONE"
