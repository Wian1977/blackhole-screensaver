#!/usr/bin/env bash
# 黑洞通用屏保安装脚本（Cinnamon / KDE / GNOME / Xfce / MATE；X11 与 Wayland 均安全）
# 用法: ./install.sh           安装并注册为会话自启
#       ./install.sh --uninstall  卸载
set -e
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${HOME}/.local/share/blackhole-screensaver"

# ---------- 依赖自检 ----------
need=()
if ! python3 -c 'import gi' 2>/dev/null; then need+=(python3-gi gir1.2-gtk-3.0); fi
if ! python3 -c 'import Xlib' 2>/dev/null; then need+=(python3-xlib); fi
if [ ${#need[@]} -gt 0 ]; then
  echo "缺少依赖: ${need[*]}"
  echo "Debian/Ubuntu/Mint/KDE-Neon 等可用:  sudo apt-get install ${need[*]}"
  echo "Fedora/RHEL/KDE:                   sudo dnf install ${need[*]}"
  echo "libgl 一般已随桌面环境安装; 若缺可装 libgl1-mesa-dri"
  echo "请先装好依赖后再运行本脚本。"
fi

# ---------- 复制文件 ----------
if [ "$SRC_DIR" != "$PREFIX" ]; then
  mkdir -p "$PREFIX"
  cp "$SRC_DIR"/*.py "$PREFIX/"
  cp "$SRC_DIR"/*.bin "$PREFIX/" 2>/dev/null || true
  cp "$SRC_DIR/plugin/blackhole.png" "$PREFIX/" 2>/dev/null || true
fi

# ---------- 注册自启（无需 DISPLAY）----------
python3 "$PREFIX/blackhole-daemon.py" --install
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
echo "安装完成。黑洞窗口会在空闲（默认 5 分钟）或锁屏时自动出现。"
echo "- 想立刻预览:  python3 $PREFIX/bh_gl.py"
echo "- 卸载:        $0 --uninstall"
