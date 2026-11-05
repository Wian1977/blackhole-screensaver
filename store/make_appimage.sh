#!/usr/bin/env bash
# Build a lightweight AppImage. GTK3 / PyGObject / Mesa come from the host
# (the same runtime deps install.sh checks for); the AppImage bundles the app.
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
VER="$1"
[ -z "$VER" ] && VER=1.1.0
OUT="$SRC/store/BlackHoleScreensaver-${VER}-x86_64.AppImage"
WORK="$(mktemp -d)"
APPDIR="$WORK/AppDir"

mkdir -p "$APPDIR/usr/share/blackhole"
cp "$SRC"/*.py "$APPDIR/usr/share/blackhole/"
cp "$SRC"/*.bin "$APPDIR/usr/share/blackhole/" 2>/dev/null || true
cp "$SRC/plugin/blackhole.png" "$APPDIR/blackhole.png"

cat > "$APPDIR/AppRun" <<'AR'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec python3 "$HERE/usr/share/blackhole/bh_gl.py" "$@"
AR
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/blackhole.desktop" <<'DE'
[Desktop Entry]
Type=Application
Name=Black Hole Screensaver
Comment=Real-physics OpenGL black hole screensaver
Exec=AppRun
Icon=blackhole
Categories=Graphics;Utility;
Terminal=false
DE

TOOL="$WORK/appimagetool"
curl -fsSL -o "$TOOL" \
  https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-x86_64.AppImage
chmod +x "$TOOL"
export APPIMAGE_EXTRACT_AND_RUN=1
"$TOOL" "$APPDIR" "$OUT"

echo "built: $OUT ($(stat -c%s "$OUT") bytes)"
