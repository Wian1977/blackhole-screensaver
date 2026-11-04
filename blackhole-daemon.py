#!/usr/bin/env python3
# 通用黑洞屏保守护（DE 无关，X11 / Wayland 均安全）
#
# 触发策略（尽量“真正通用”）：
#   1) 优先监听 FreeDesktop / 各桌面标准的 ScreenSaver DBus 信号 ActiveChanged。
#      这是 XDG 标准，Cinnamon / KDE / GNOME / MATE / Xfce 都会发，X11 与 Wayland 都可用。
#   2) 若当前环境根本没有屏保服务（极简 WM / 未启用屏保），退回 X11 空闲轮询
#      （仅当 DISPLAY 存在且 Xlib 可用时才启用）。
#
# 激活（锁屏 / 空闲到阈值）时拉起 bh_gl.py 全屏窗口；取消激活（解锁 / 有输入）时退出。
# 顶部不再 import Xlib，因此 Wayland 或无 X 的环境也能正常启动，不会一上来就崩。
import os, sys, subprocess, argparse

SELF = os.path.abspath(__file__)
BH_GL = os.environ.get('BH_GL') or os.path.join(os.path.dirname(SELF), 'bh_gl.py')
IDLE_MIN = float(os.environ.get('IDLE_MIN', '5'))   # 退回 X11 轮询时的空闲分钟数
POLL = 2                                           # 轮询秒数
ACTIVE_RESET_MS = 2000                             # 空闲低于此值视为“用户回来了”

import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')
from gi.repository import GLib, Gio

# ---------- Xlib 惰性导入（仅 X11 空闲回退使用）----------
_xlib = None
def _get_xdisplay():
    global _xlib
    if _xlib is not None:
        return _xlib
    try:
        from Xlib import display as Xdisplay
        from Xlib.ext import screensaver  # noqa: F401
        d = Xdisplay.Display()
        _xlib = (d, d.screen().root)
    except Exception as e:
        _xlib = False
        print('Xlib 不可用（将不启用 X11 空闲回退）:', e, flush=True)
    return _xlib

def get_idle_ms():
    r = _get_xdisplay()
    if not r:
        return 0
    try:
        return r[1].screensaver_query_info().idle
    except Exception:
        return 0

def bh_running():
    return subprocess.run(['pgrep', '-f', 'bh_gl[.]py'],
                          capture_output=True).returncode == 0

proc = None
def launch_bh():
    global proc
    if proc is not None and proc.poll() is None:
        return
    try:
        proc = subprocess.Popen(['python3', BH_GL])
        print('launched bh_gl pid=%d' % proc.pid, flush=True)
    except Exception as e:
        print('launch fail:', e, flush=True)

def stop_bh():
    global proc
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
    proc = None
    print('stopped bh_gl', flush=True)

lock_active = False
def set_active(active):
    if active:
        launch_bh()
    else:
        stop_bh()

# ---------- DBus 订阅（通用触发）----------
def on_lock_signal(conn, sender, path, iface, signal, params, user_data=None):
    try:
        active = bool(params[0])
    except Exception:
        return
    global lock_active
    lock_active = active
    print('signal %s active=%s' % (iface, active), flush=True)
    set_active(active)

bus = None
subscribed = False
def setup_dbus():
    global bus, subscribed
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    except Exception as e:
        print('DBus 初始化失败（退回 X11 空闲轮询）:', e, flush=True)
        return False
    for iface in ['org.freedesktop.ScreenSaver',
                  'org.kde.screensaver', 'org.kde.ScreenSaver',
                  'org.cinnamon.ScreenSaver', 'org.gnome.ScreenSaver',
                  'org.mate.ScreenSaver']:
        try:
            bus.signal_subscribe(None, iface, 'ActiveChanged', None, None,
                                 0, on_lock_signal, None)
            print('subscribed', iface, flush=True)
            subscribed = True
        except Exception as e:
            print('subscribe fail', iface, e, flush=True)
    return subscribed

# 仅当没有屏保 DBus 服务时才用的 X11 空闲回退
def tick():
    global proc
    if subscribed or bus is None:
        return True
    idle = get_idle_ms() if _get_xdisplay() else 0
    if proc is not None:
        if proc.poll() is not None:
            proc = None
        elif idle < ACTIVE_RESET_MS:
            stop_bh()
    else:
        if idle >= IDLE_MIN * 60000 and not bh_running():
            launch_bh()
    return True

# ---------- 安装 / 卸载（XDG 通用，无需 DISPLAY）----------
AUTOSTART = os.path.expanduser('~/.config/autostart/blackhole-daemon.desktop')
SCREENSAVER_DIR = os.path.expanduser('~/.local/share/applications/screensavers')
APP_DIR = os.path.expanduser('~/.local/share/applications')
PREFIX = os.path.dirname(SELF)

def _write_autostart():
    os.makedirs(os.path.dirname(AUTOSTART), exist_ok=True)
    with open(AUTOSTART, 'w') as f:
        f.write('[Desktop Entry]\n'
                'Type=Application\n'
                'Name=Black Hole Screensaver Daemon\n'
                'Comment=DE-independent idle/lock screensaver launcher (X11/Wayland safe)\n'
                'Exec=python3 %s\n' % SELF +
                'Terminal=false\n'
                'X-GNOME-Autostart-enabled=true\n'
                'X-KDE-autostart-enabled=true\n')
    print('installed autostart:', AUTOSTART, flush=True)


def install():
    _write_autostart()
    os.makedirs(SCREENSAVER_DIR, exist_ok=True)
    sed_src = os.path.join(PREFIX, 'blackhole.desktop.in')
    if os.path.exists(sed_src):
        with open(sed_src) as f:
            txt = f.read()
        txt = txt.replace('@BH_GL@', BH_GL)
        with open(os.path.join(SCREENSAVER_DIR, 'blackhole.desktop'), 'w') as f:
            f.write(txt)
        print('registered screensaver entry (Cinnamon/Xfce/MATE pickers)', flush=True)
    os.makedirs(APP_DIR, exist_ok=True)
    app_src = os.path.join(PREFIX, 'blackhole-app.desktop.in')
    if os.path.exists(app_src):
        icon = os.path.join(PREFIX, 'blackhole.png')
        with open(app_src) as f:
            txt = f.read()
        txt = txt.replace('@BH_GL@', BH_GL).replace('@ICON@', icon)
        with open(os.path.join(APP_DIR, 'blackhole-screensaver.desktop'), 'w') as f:
            f.write(txt)
        desk = os.path.expanduser('~/Desktop')
        if os.path.isdir(desk):
            with open(os.path.join(desk, 'blackhole-screensaver.desktop'), 'w') as f:
                f.write(txt)
            os.chmod(os.path.join(desk, 'blackhole-screensaver.desktop'), 0o755)
    print('install done. 黑洞窗口会在空闲/锁屏时自动出现。', flush=True)

def uninstall():
    for p in [AUTOSTART,
              os.path.join(SCREENSAVER_DIR, 'blackhole.desktop'),
              os.path.join(APP_DIR, 'blackhole-screensaver.desktop')]:
        if os.path.exists(p):
            os.remove(p)
    desk = os.path.expanduser('~/Desktop/blackhole-screensaver.desktop')
    if os.path.exists(desk):
        os.remove(desk)
    print('uninstalled.', flush=True)

def detect_de():
    return os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')

def main():
    global IDLE_MIN
    ap = argparse.ArgumentParser(description='Black Hole 通用屏保守护守护进程')
    ap.add_argument('--install', action='store_true', help='注册为会话自启（XDG autostart + systemd --user）')
    ap.add_argument('--uninstall', action='store_true', help='移除自启')
    ap.add_argument('--idle', type=float, help='退回 X11 轮询时的空闲分钟数(默认5)')
    ap.add_argument('--status', action='store_true', help='打印状态并退出')
    args = ap.parse_args()
    if args.idle:
        IDLE_MIN = args.idle
    if args.install:
        install(); return
    if args.uninstall:
        uninstall(); return
    if args.status:
        print('DE=%s idle_min=%.1f bh_running=%s lock_active=%s daemon_pid=%d'
              % (detect_de(), IDLE_MIN, bh_running(), lock_active, os.getpid()))
        return
    print('blackhole-daemon: DE=%s（DBus 通用触发 / X11 回退）' % detect_de(), flush=True)
    setup_dbus()
    if not subscribed:
        print('未订阅到屏保 DBus 服务，启用 X11 空闲轮询回退（仅 X11）', flush=True)
        GLib.timeout_add(POLL * 1000, tick)
    GLib.MainLoop().run()

if __name__ == '__main__':
    main()
