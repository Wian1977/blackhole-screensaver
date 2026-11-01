# Black Hole Screensaver

原生 OpenGL 黑洞引力透镜屏保，作为系统屏保跨桌面运行。

## 特性
- DE 无关：Cinnamon / Xfce / MATE / GNOME / KDE 等 X11 桌面通用（不依赖任何 DE 的插件框架）
- 空闲自动全屏，锁屏时保留在锁屏界面之下，用户有输入即退出
- 平时零 GPU 负载（仅轻量轮询 X 空闲 + 监听锁屏 DBus）
- 黑洞渲染为独立 GTK3+OpenGL 全屏程序，桌面无关

## 依赖
- python3, PyGObject (python3-gi) + GTK3, python3-xlib, Mesa/OpenGL
- Debian/Ubuntu/Mint: sudo apt install python3-gi python3-xlib gir1.2-gtk-3.0

## 安装
    ./install.sh
装到 ~/.local/share/blackhole-screensaver/，注册登录自启，并在支持原生选择的桌面(Xfce/MATE)注册屏保项。

## 使用
- 手动全屏：python3 bh_gl.py （Esc/Q 或点击退出）
- 守护状态：python3 blackhole-daemon.py --status
- 改阈值：python3 blackhole-daemon.py --idle 3 （分钟）
- 卸载：./install.sh --uninstall

## 各桌面适配
- Xfce / MATE：设置 -> 屏保 里可选 Black Hole（由 xfce4-screensaver / mate-screensaver 调度）
- Cinnamon：该 DE 屏保框架缺陷（基类无法子类化、无内置屏保模块），黑洞靠 DE 无关守护兜底
- GNOME：无原生可选屏保，靠守护
- KDE：X11 会话下靠守护（空闲触发 + freedesktop/kde 锁屏信号）；Wayland 会话暂不支持（见下方限制）
- 通用：黑洞守护监听 X 空闲与锁屏信号，任何 X11 DE 都自动工作

## 已知限制
- 仅支持 X11 会话。Wayland（现代 GNOME/KDE 默认）下 Xlib 查不到真实空闲、X11 全屏盖不到锁屏，故无法工作；需改用 logind/portal 空闲检测与合成器接管（待做）。
- 因此 Windows / macOS 亦不支持（渲染核心 GTK3+OpenGL 可手动运行，但无屏保整合）。

## 架构
- bh_gl.py：渲染核心（GTK3+OpenGL 全屏，桌面无关）
- blackhole-daemon.py：DE 无关屏保守护（X 空闲 + 锁屏 DBus）
- blackhole.desktop.in：桌面屏保注册模板

## 许可证
MIT（见 LICENSE）

## 计划 / Roadmap
- Wayland 支持：用 ext-session-lock-v1 接管锁屏（KDE/GNOME Wayland 会话）
- 原生 KDE QML 插件（壁纸/锁屏），通过 KDE Store / GHNS 一键装
- Flathub (Flatpak) 打包，进 KDE Discover / GNOME 软件中心
- 上架包见 `store/`（KDE Store 文案 + 打包脚本）；当前主分发渠道为 GitHub Releases + .deb
