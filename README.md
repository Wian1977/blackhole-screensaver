# Black Hole Screensaver 黑洞屏保

基于真实物理参数的施瓦西黑洞屏保：光线按史瓦西度规实时测地线偏折，含吸积盘、相对论聚束与多普勒/引力红移，并非贴图或假特效。

## 真正通用 一键安装

- DE 无关（X11 和 Wayland 均安全）：触发逻辑基于 XDG 标准 org.freedesktop.ScreenSaver 加各桌面锁屏 DBus 信号（Cinnamon / KDE / GNOME / MATE / Xfce 都会发），X11 与 Wayland 都能启动，不会一上来就崩。
- 一键安装：./install.sh 把程序装到 HOME/.local/share/blackhole-screensaver/，注册 XDG 会话自启（Cinnamon / KDE / GNOME / Xfce / MATE 全支持），并在 Xfce / MATE / Cinnamon 的屏保选择器里登记入口。
- 平时零 GPU 负载：后台只跑一个轻量守护进程，空闲/锁屏时才拉起 OpenGL 全屏窗口，解锁或熄屏即退出。

Wayland 优雅降级：X11 下窗口完美覆盖锁屏；Wayland 下合成器（KDE/GNOME）的锁屏会盖住普通全屏窗口，黑洞窗口出现在锁屏之下或之前、且不会崩溃。若要 Wayland 强制覆盖锁屏，需要逐合成器适配（layer-shell / KDE 锁屏插件），工作量更大、不利于一键分发。

## 安装 Install

    git clone https://github.com/Wian1977/blackhole-screensaver.git && cd blackhole-screensaver
    ./install.sh

安装脚本做依赖自检（缺失会给出 apt / dnf 安装命令），无需 DISPLAY，重新登录即生效；黑洞窗口在空闲（默认 5 分钟）或锁屏时自动出现。
卸载：./install.sh --uninstall
依赖（Debian/Ubuntu/Mint/KDE-Neon）：python3-gi gir1.2-gtk-3.0 python3-xlib（Mesa/OpenGL 桌面已自带）。

## 使用 Usage

- 手动预览全屏：python3 bh_gl.py（按 Esc 退出）
- 守护进程状态：python3 blackhole-daemon.py --status
- 改空闲阈值：python3 blackhole-daemon.py --idle 3
- 环境变量：IDLE_MIN 默认 5，BH_GL 为 bh_gl.py 路径

运行中快捷键：H 帮助，M 自动运镜，L 星空透镜，Space 暂停，B 盘面亮度，1/2/3 画质，方括号键 距离，Esc 退出。

## 各桌面适配 Desktop integration

- Linux Mint Cinnamon X11：守护进程加 Cinnamon 锁屏信号，屏保选择器可见
- Xfce / MATE：守护进程加各自屏保信号，屏保选择器可见
- KDE X11：守护进程加 org.kde.screensaver 信号；KDE 不读 XDG screensavers 目录，无法在设置里手动选，但靠守护进程自动触发
- GNOME X11/Wayland：守护进程加 org.freedesktop.ScreenSaver 信号，靠守护进程自动触发
- 精简 WM 无屏保服务：退回 X11 空闲轮询（仅 X11 且 DISPLAY 存在时）
- Wayland KDE/GNOME：同上 DBus 信号，窗口出现在锁屏之下或之前

## 架构 Architecture

- bh_gl.py：渲染核心（GTK3 + OpenGL 全屏，X11/Wayland 均可用）
- blackhole-daemon.py：DE 无关守护进程（FreeDesktop/各桌面锁屏 DBus 触发；X11 空闲回退；Xlib 惰性导入）
- blackhole.desktop.in：屏保注册模板（Xfce/MATE/Cinnamon）
- blackhole-app.desktop.in：应用菜单/桌面快捷方式模板
- shaders.py / lenslut.py / stars.py / bloom.py：渲染辅助
- lens_lut.bin：星空透镜 LUT（须与盘几何 rs/r0 一致）

## 已知限制 Limitations

- Wayland 锁屏遮挡：通用方案下 Wayland 锁屏会盖住黑洞窗口，出现在锁屏之下或之前（已优雅降级，不崩溃）。若要 Wayland 强制覆盖锁屏需 ext-session-lock-v1 / layer-shell / KDE 锁屏插件（待做）。
- Windows / macOS：渲染核心可手动跑，但无屏保整合。
- KDE 屏保选择器：KDE 不读 XDG screensavers 目录，无法在 KDE 设置里手动选择；KDE 下靠守护进程自动触发即可。

## License

MIT - see LICENSE.
