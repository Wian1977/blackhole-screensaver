#!/usr/bin/env bash
# Build a system-wide .deb for blackhole-screensaver.
# Output: /tmp/blackhole-screensaver_<ver>_all.deb
set -e
SRC="$(cd "$(dirname "$0")/.." && pwd)"
VER="$1"
if [ -z "$VER" ]; then VER=1.0.0; fi
OUT="/tmp/blackhole-screensaver_"$VER"_all.deb"
WORK="$(mktemp -d)"
APP="$WORK/usr/share/blackhole-screensaver"
mkdir -p "$APP" "$WORK/usr/share/applications/screensavers" "$WORK/etc/xdg/autostart" "$WORK/DEBIAN"

cp "$SRC"/*.py "$SRC"/*.bin "$APP"/ 2>/dev/null || true
cp "$SRC/plugin/blackhole.png" "$APP/blackhole.png"
PREFIX_BHGL="$APP/bh_gl.py"
ICON="$APP/blackhole.png"

sed -e "s|@BH_GL@|$PREFIX_BHGL|" "$SRC/blackhole.desktop.in" > "$WORK/usr/share/applications/screensavers/blackhole.desktop"
sed -e "s|@BH_GL@|$PREFIX_BHGL|" -e "s|@ICON@|$ICON|" "$SRC/blackhole-app.desktop.in" > "$WORK/usr/share/applications/blackhole-screensaver.desktop"

cat > "$WORK/etc/xdg/autostart/blackhole-daemon.desktop" <<DE
[Desktop Entry]
Type=Application
Name=Black Hole Screensaver Daemon
Comment=DE-independent idle/lock screensaver launcher
Exec=python3 $APP/blackhole-daemon.py
Terminal=false
X-GNOME-Autostart-enabled=true
DE

cat > "$WORK/DEBIAN/control" <<CTRL
Package: blackhole-screensaver
Version: $VER
Section: graphics
Priority: optional
Architecture: all
Depends: python3 (>=3.6), python3-gi, gir1.2-gtk-3.0, python3-xlib, libgl1
Recommends: mesa-utils
Maintainer: Wian1977 <blackhole@example.com>
Description: Real-physics Schwarzschild black-hole OpenGL screensaver
 A native OpenGL visualization of a Schwarzschild black hole simulated with
 real physical parameters: gravitational lensing via geodesic integration,
 an accretion disk with relativistic beaming, and Doppler/gravitational
 redshift. Ships a DE-independent daemon that launches full-screen on X11
 idle/lock and exits on any input.
CTRL

rm -f "$OUT"
dpkg-deb --build --root-owner-group "$WORK" "$OUT" >/dev/null
echo "built: $OUT ($(stat -c%s "$OUT") bytes)"
rm -rf "$WORK"
