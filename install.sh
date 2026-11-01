#!/usr/bin/env bash
set -e
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${HOME}/.local/share/blackhole-screensaver"
DESKTOP_DIR="${HOME}/.local/share/applications/screensavers"
APP_DIR="${HOME}/.local/share/applications"
ICON="${PREFIX}/blackhole.png"

install() {
  mkdir -p "$PREFIX"
  cp "$SRC_DIR"/*.py "$PREFIX/"
  cp "$SRC_DIR"/*.bin "$PREFIX/" 2>/dev/null || true
  cp "$SRC_DIR/plugin/blackhole.png" "$PREFIX/" 2>/dev/null || true
  python3 "$PREFIX/blackhole-daemon.py" --install
  mkdir -p "$DESKTOP_DIR"
  sed -e "s|@BH_GL@|$PREFIX/bh_gl.py|" "$SRC_DIR/blackhole.desktop.in" > "$DESKTOP_DIR/blackhole.desktop"
  mkdir -p "$APP_DIR"
  sed -e "s|@BH_GL@|$PREFIX/bh_gl.py|" -e "s|@ICON@|$ICON|" "$SRC_DIR/blackhole-app.desktop.in" > "$APP_DIR/blackhole-screensaver.desktop"
  if [ -d "${HOME}/Desktop" ]; then
    cp "$APP_DIR/blackhole-screensaver.desktop" "${HOME}/Desktop/blackhole-screensaver.desktop"
    chmod +x "${HOME}/Desktop/blackhole-screensaver.desktop"
  fi
  update-desktop-database "$APP_DIR" 2>/dev/null || true
  echo "Installed. Idle launches Black Hole; menu (Graphics) and Desktop shortcut created."
}

uninstall() {
  python3 "$PREFIX/blackhole-daemon.py" --uninstall 2>/dev/null || true
  rm -f "$DESKTOP_DIR/blackhole.desktop" "$APP_DIR/blackhole-screensaver.desktop" "${HOME}/Desktop/blackhole-screensaver.desktop"
  rm -rf "$PREFIX"
  echo "Uninstalled."
}

case "$1" in
  --uninstall) uninstall ;;
  *) install ;;
esac
