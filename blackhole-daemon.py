#!/usr/bin/env python3
# Black Hole 屏保守护：DE 无关。监听 X 空闲 + 锁屏 DBus 信号，
# 任何 X11 桌面( Cinnamon / Xfce / MATE / GNOME )空闲到阈值即启动 bh_gl.py 全屏，
# 用户有输入或解锁即退出；锁屏时黑洞保留在锁屏界面之下。平时零 GPU 负载。
import os, sys, subprocess, argparse

SELF = os.path.abspath(__file__)
BH_GL = os.environ.get('BH_GL') or os.path.join(os.path.dirname(SELF), 'bh_gl.py')
IDLE_MIN = float(os.environ.get('IDLE_MIN', '5'))   # 空闲多少分钟触发
POLL = 2                                           # 轮询秒数
ACTIVE_RESET_MS = 2000                             # 空闲低于此值视为用户回来了

from Xlib import display as Xdisplay
from Xlib.ext import screensaver
import gi
gi.require_version('GLib', '2.0')
gi.require_version('Gio', '2.0')
from gi.repository import GLib, Gio

d = Xdisplay.Display()
root = d.screen().root

def get_idle_ms():
    return root.screensaver_query_info().idle

def bh_running():
    return subprocess.run(['pgrep', '-f', 'bh_gl[.]py'],
                          capture_output=True).returncode == 0

lock_active = False

def on_lock_signal(conn, sender, path, iface, signal, params):
    global lock_active
    try:
        active = bool(params[0])
    except Exception:
        return
    lock_active = active
    print('lock: active=%s' % active, flush=True)
    if not active:
        stop_bh()

bus = None
def setup_dbus():
    global bus
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    except Exception as e:
        print('DBus init fail:', e, flush=True)
        return
    for iface in ['org.freedesktop.ScreenSaver',
                  'org.kde.screensaver',
                  'org.kde.ScreenSaver',
                  'org.cinnamon.ScreenSaver',
                  'org.gnome.ScreenSaver']:
        try:
            bus.signal_subscribe(None, iface, 'ActiveChanged', None, None,
                                 0, on_lock_signal, None)
            print('subscribed', iface, flush=True)
        except Exception as e:
            print('subscribe fail', iface, e, flush=True)

proc = None
def launch_bh():
    global proc
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
        try: proc.wait(timeout=5)
        except Exception: proc.kill()
    proc = None
    print('stopped bh_gl', flush=True)

def tick():
    global proc
    try:
        idle = get_idle_ms()
    except Exception:
        idle = 0
    if proc is not None:
        if proc.poll() is not None:
            proc = None
        elif idle < ACTIVE_RESET_MS and not lock_active:
            stop_bh()
    else:
        if idle >= IDLE_MIN * 60000 and not bh_running():
            launch_bh()
    return True

def detect_de():
    return os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')

AUTOSTART = os.path.expanduser('~/.config/autostart/blackhole-daemon.desktop')

def install():
    os.makedirs(os.path.dirname(AUTOSTART), exist_ok=True)
    with open(AUTOSTART, 'w') as f:
        f.write('[Desktop Entry]\n'
                'Type=Application\n'
                'Name=Black Hole Screensaver Daemon\n'
                'Comment=DE-independent idle/lock screensaver launcher\n'
                'Exec=python3 %s\n' % SELF +
                'Terminal=false\n'
                'X-GNOME-Autostart-enabled=true\n')
    print('installed autostart:', AUTOSTART, flush=True)

def uninstall():
    if os.path.exists(AUTOSTART):
        os.remove(AUTOSTART)
        print('removed autostart', flush=True)
    else:
        print('no autostart file', flush=True)

def main():
    global IDLE_MIN
    ap = argparse.ArgumentParser(description='Black Hole DE-independent screensaver daemon')
    ap.add_argument('--install', action='store_true', help='register as session autostart')
    ap.add_argument('--uninstall', action='store_true', help='remove autostart')
    ap.add_argument('--idle', type=float, help='idle minutes before launch (default 5)')
    ap.add_argument('--status', action='store_true', help='print status and exit')
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
    print('blackhole-daemon: DE=%s idle=%.1f min' % (detect_de(), IDLE_MIN), flush=True)
    setup_dbus()
    GLib.timeout_add(POLL * 1000, tick)
    GLib.MainLoop().run()

if __name__ == '__main__':
    main()
