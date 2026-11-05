#!/usr/bin/env python3
# 空闲自动全屏黑洞（替代 Cinnamon 屏保选择器，因其在本机无法加载插件）
# 平时仅轮询 X 空闲时间，零 GPU 负载；空闲到阈值启动 bh_gl.py，有输入即关闭。
import os, sys, time, subprocess

BH_GL = os.environ.get('BH_GL') or \
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bh_gl.py')
IDLE_MIN = float(os.environ.get('IDLE_MIN', '5'))   # 空闲多少分钟触发
POLL = 2                                           # 轮询秒数
ACTIVE_RESET_MS = 2000                             # 空闲低于此值视为“用户回来了”

from Xlib import display as Xdisplay
from Xlib.ext import screensaver

d = Xdisplay.Display()
root = d.screen().root

def get_idle_ms():
    return root.screensaver_query_info().idle

def is_locked():
    try:
        out = subprocess.run(
            ['dbus-send','--session','--dest=org.cinnamon.ScreenSaver',
             '--print-reply','/org/cinnamon/ScreenSaver',
             'org.cinnamon.ScreenSaver.GetActive'],
            capture_output=True, text=True, timeout=3).stdout
        return 'true' in out.lower()
    except Exception:
        return False

def bh_running():
    return subprocess.run(['pgrep','-f','bh_gl[.]py'],
                          capture_output=True).returncode == 0

proc = None
print('blackhole-idle: 监听中（空闲 %d 分钟触发）' % IDLE_MIN, flush=True)
while True:
    try:
        idle = get_idle_ms()
    except Exception:
        idle = 0
    if proc is not None:
        if proc.poll() is not None:
            proc = None
        # 敲键 / 鼠标移动不再退出屏保；退出只由 bh_gl 自身 Esc 触发。
    else:
        if idle >= IDLE_MIN*60000 and not is_locked() and not bh_running():
            try:
                proc = subprocess.Popen(['python3', BH_GL])
            except Exception as e:
                print('launch fail:', e, flush=True)
    time.sleep(POLL)
