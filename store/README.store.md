# Black Hole Screensaver — KDE Store 上架物料

本目录为 #1（KDE Store 上架现有 GTK/Python 包）的准备物料。

## 1) 上架文案（直接复制到商店对应输入框）

标题 (Title):
  Black Hole Screensaver

一句话摘要 (Summary):
  Native OpenGL black-hole gravitational-lensing screensaver for Linux desktops.

描述 (Description) — 整段复制:
  Black Hole Screensaver is a native OpenGL visualization of a Schwarzschild
  black hole with real-time gravitational lensing, an accretion disk, relativistic
  beaming, and chromatic Doppler/gravitational redshift. A small DE-independent
  daemon auto-launches it full-screen on idle/lock; it stays under the lock screen
  and exits on any input. Works on any X11 Linux desktop (Cinnamon, Xfce, MATE,
  GNOME, KDE). Near-zero GPU load when idle.

  Features:
  - Real geodesic light-bending (Schwarzschild lensing) of disk + background stars
  - Accretion disk with relativistic beaming and chromatic redshift (blue approach / red recede)
  - Lensed Einstein-ring star field (toggleable); quality tiers for star density
  - Idle auto-launch, persists under lock screen, exits on input
  - Adjustable distance, brightness, redshift, drift; 3 quality tiers

  Install: extract, run ./install.sh (installs to ~/.local/share/blackhole-screensaver,
  registers autostart + desktop entries).
  Requires: python3, PyGObject (GTK3), python3-xlib, Mesa/OpenGL.
  License: MIT.

许可证 (License): MIT

## 2) 依赖（填到 Dependencies / Comments）
  python3, python3-gi (GTK3), python3-xlib, gir1.2-gtk-3.0, Mesa/OpenGL

## 3) 给最终用户的安装说明（放 Install / Comments）
  tar xzf blackhole-screensaver-*.tar.gz
  cd blackhole-screensaver
  ./install.sh
  锁屏或空闲即出现黑洞；Esc 或任意输入退出。卸载：./install.sh --uninstall

## 4) 截图（必须，自己截一张）
  在桌面机锁屏前截一张运行图，上架时上传（商店要求至少 1 张）。

## 5) 已知限制（建议也写进描述或评论）
  - 当前 X11 守护路径为 DE 无关；Wayland 原生集成（Plasma 插件）在计划中。
  - 非 KDE 的 X11 桌面同样可用（走通用 freedesktop 锁屏信号）。
