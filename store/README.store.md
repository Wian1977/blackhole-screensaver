# Black Hole Screensaver — 上架物料 / Store Listing Material

本目录为商店上架（KDE Store / Pling / 其他）准备的文案与打包脚本。
主分发渠道目前是 **GitHub Releases**（见下），KDE Store 作为可选项。

Primary distribution channel is **GitHub Releases**; KDE Store / Pling are optional.

- 仓库 Repo: https://github.com/Wian1977/blackhole-screensaver
- 发布 Release: https://github.com/Wian1977/blackhole-screensaver/releases/tag/v1.1.0
- 截图 Screenshot: 仓库根目录 `screenshot-1.png` / `screenshot-2.png`（真实运行画面，上架时直接上传其一即可）。

---

## 1) 上架文案（复制到商店输入框）

**标题 Title:** Black Hole Screensaver (黑洞屏保)

**一句话摘要 Summary:**
- EN: Native OpenGL Schwarzschild black-hole screensaver with real gravitational lensing.
- ZH: 基于真实物理参数的施瓦西黑洞原生 OpenGL 屏保。

**描述 Description（整段复制 EN）:**
Black Hole Screensaver is a native OpenGL visualization of a Schwarzschild black
hole simulated with **real physical parameters**. Light rays are bent by real-time
geodesic integration in the Schwarzschild metric (u'' = -u + 1.5·rs·u²); the
accretion disk shows relativistic beaming (I ∝ g³) and chromatic Doppler +
gravitational redshift (blue approach / red recede). Background stars are lensed
onto the Einstein ring via a baked lookup table. A tiny DE-independent daemon
auto-launches it full-screen on idle/lock, keeps it under the lock screen, and
exits on any input. Works on any Linux desktop (X11 or Wayland) across Cinnamon,
Xfce, MATE, GNOME, and KDE via a DE-independent daemon; on Wayland the window
appears beneath/before the lock screen (graceful degradation, never crashes).
Near-zero GPU load when idle.

Features:
- Real geodesic light-bending (Schwarzschild lensing) of disk + background stars
- Accretion disk with relativistic beaming and chromatic redshift
- Lensed Einstein-ring star field (toggleable) + 3 quality tiers for star density
- Idle auto-launch, persists under lock screen, exits on input
- Live controls: distance, disk brightness, star lensing, drift, pause, quality

Install: extract, run `./install.sh` (installs to ~/.local/share/blackhole-screensaver,
registers autostart + desktop entries). Requires python3, PyGObject (GTK3),
python3-xlib, Mesa/OpenGL. License: MIT.

**许可证 License:** MIT

---

## 2) 依赖（Dependencies）
python3, python3-gi (GTK3), python3-xlib, gir1.2-gtk-3.0, Mesa/OpenGL

## 3) 终端用户安装说明（Install / Comments）
```
tar xzf blackhole-screensaver-*.tar.gz
cd blackhole-screensaver
./install.sh
# 锁屏或空闲即出现黑洞；Esc 或任意输入退出
# 卸载: ./install.sh --uninstall
```

## 4) 快捷键（运行时，可放描述/评论）
| Key | Action |
|-----|--------|
| H | 帮助开关 Help |
| M | 自动运镜 Auto camera |
| L | 星空引力透镜 Star lensing |
| Space | 暂停/继续 Pause |
| S | 声音静音 Mute |
| 1/2/3 | 画质 高/中/低 Quality |
| [ / ] | 距离 远/近 Distance |
| B | 盘面亮度 Disk brightness |
| Esc | 退出 Quit (manual) |

## 5) 画质等级（Quality tiers）
| Level | Stars | Disk res | Ray steps |
|-------|-------|----------|-----------|
| High | ~32,000 | 1.0× | 512 |
| Medium | ~12,000 | 0.5× | 256 |
| Low | ~4,000 | 0.5× | 256 |

## 6) 截图（Screenshot）
仓库根目录的 `screenshot-1.png` / `screenshot-2.png` 为真实运行画面，商店通常要求 ≥1 张，直接上传其一即可。

## 7) 已知限制（建议也写进描述/评论）
- **通用**：基于 XDG / 各桌面锁屏 DBus 信号（org.freedesktop.ScreenSaver、org.kde/cinnamon/gnome/mate ScreenSaver），X11 与 Wayland 都能启动守护进程，不会一上来就崩。
- **Wayland 优雅降级**：X11 下窗口完美覆盖锁屏；Wayland 下合成器锁屏会盖住普通全屏窗口，黑洞出现在锁屏之下或之前、且不崩溃。若要 Wayland 强制覆盖锁屏需 ext-session-lock-v1 / layer-shell / KDE 锁屏插件（待做）。
- KDE 屏保选择器：KDE 不读 XDG screensavers 目录，无法在设置里手动选；KDE 下靠守护进程自动触发即可。
- Windows / macOS 无屏保整合（渲染核心可手动跑，但不建议作为屏保）。

## 8) 打包（本目录脚本）
`make_bundle.sh` 生成 `blackhole-screensaver-YYYYMMDD.tar.gz`，即上架/Release 用的安装包。
