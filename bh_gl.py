# -*- coding: utf-8 -*-
"""黑洞原生 GL 屏保：Gtk.GLArea + 桌面 GLSL 3.3 core，复用源 HTML 的着色器。

零第三方依赖：GL 调用走 ctypes 直连 libGL；GTK/Gio 随 Cinnamon 自带。
监听 org.cinnamon.ScreenSaver 的 ActiveChanged 信号，锁屏时拉起全屏 GL 窗口，解锁时关闭。

渲染管线（与网页版一致）：
  1) 黑洞盘着色器 -> 半分辨率 FBO（背景透明，便于星层透出）
  2) 离散星场层（含引力透镜）-> 全分辨率 FBO，加色混合
  3) 合成（盘叠加在星上）-> 辉光（UnrealBloomPass 等效）-> 屏幕

用法：
  python3 bh_gl.py              # 立即全屏运行（测试：Esc 退出）
  python3 bh_gl.py --daemon     # 常驻，监听锁屏信号自动显隐
  python3 bh_gl.py --quality mid --renderscale 0.75
"""
import math
import sys
import os
import argparse
import ctypes
import struct
import zlib
import traceback
import random

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Gio

import glctypes as gl
import glext
import shaders
from webvals import PARAMS, QUALITY_BY_NAME
import stars as stars_mod
import bloom as bloom_mod

BASE_FOV = 42.0
MAX_FOV = 78.0

AUTO_ROT_DEG_PER_SEC = 4.0
STAR_ROT_RATE = 0.03

AUTO_ORBIT_AMP = 0.5
AUTO_ORBIT_RATE = 0.035
AUTO_ROLL_AMP = 0.18
AUTO_ROLL_RATE = 0.022
AUTO_BREATH_AMP = 0.35
AUTO_BREATH_RATE = 0.05

# 大漂移（对齐 web 版 v2.155）：每 DRIFT_INTERVAL 秒 yaw 强制参与的大转向，smoothstep 缓动
DRIFT_INTERVAL = 300.0   # 秒
DRIFT_DUR = 28.0         # 秒，缓动过渡时长
DRIFT_AMP_FRAC = 0.10    # 变化幅度 ≤ 全量程 10%（roll/yaw）；tilt 用绝对 ±10°
PARAM_RANGES = {"yaw": (-180.0, 180.0), "roll": (-180.0, 180.0), "tiltDeg": (73.0, 93.0)}


def write_png(path, w, h, rgb):
    """rgb: bytes of length w*h*3, row-major, top-left origin (caller already flipped)."""
    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))
    raw = bytearray()
    for y in range(h - 1, -1, -1):
        raw.append(0)
        raw.extend(rgb[y * w * 3:(y + 1) * w * 3])
    comp = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", comp))
        f.write(chunk(b"IEND", b""))


def gl_check(label):
    if not os.environ.get("BH_GL_DEBUG"):
        return
    try:
        e = gl.glGetError()
        if e != 0:
            with open("/tmp/bh_gl_error.log", "a") as f:
                f.write("GL_ERROR " + str(label) + ": 0x%X\n" % e)
    except Exception:
        pass


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vscale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vlen(a):
    return math.sqrt(vdot(a, a))


def vnorm(a):
    l = vlen(a)
    return (0.0, 0.0, 0.0) if l < 1e-9 else (a[0] / l, a[1] / l, a[2] / l)


def q_from_axis(axis, angle):
    axis = vnorm(axis)
    s = math.sin(angle / 2.0)
    return (math.cos(angle / 2.0), axis[0] * s, axis[1] * s, axis[2] * s)


def q_mul(a, b):
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def q_rotate(v, q):
    qw, qx, qy, qz = q
    u = (qx, qy, qz)
    t = vscale(vcross(u, v), 2.0)
    return vadd(vadd(v, vscale(t, qw)), vcross(u, t))


def compute_camera(aspect, t=0.0, auto_motion=True):
    camDir = vnorm((0.0, 1.4, 9.0))
    orbit = AUTO_ORBIT_AMP * math.sin(t * AUTO_ORBIT_RATE) if auto_motion else 0.0
    if orbit != 0.0:
        cy = math.cos(orbit); sy = math.sin(orbit)
        camDir = (camDir[0] * cy + camDir[2] * sy, camDir[1],
                  -camDir[0] * sy + camDir[2] * cy)
    breath = AUTO_BREATH_AMP * math.sin(t * AUTO_BREATH_RATE + 0.7) if auto_motion else 0.0
    camPos = vscale(camDir, PARAMS["distance"] + breath)
    fwd = vnorm(vscale(camPos, -1.0))
    world_up = (0.0, 1.0, 0.0)
    right = vnorm(vcross(fwd, world_up))
    up = vcross(right, fwd)

    bh = (0.0, 0.0, 0.0)
    vt = vsub(bh, camPos)
    depth = max(vdot(vt, fwd), 0.001)
    perp = vsub(vt, vscale(fwd, depth))
    offH = abs(vdot(perp, right))
    offV = abs(vdot(perp, up))
    outer = PARAMS["outer"]
    ringIn = PARAMS["ringIn"]
    needH = offH + max(outer * 1.25, ringIn * 1.45)
    needV = offV + ringIn * 1.05 + outer * 0.20 + 0.35
    tanNeed = max(needV, needH / aspect) / depth
    fov = 2.0 * math.atan(tanNeed) * 180.0 / math.pi
    fov = max(BASE_FOV, min(MAX_FOV, fov))
    tanHalf = math.tan(fov * 0.5 * math.pi / 180.0)

    tilt = math.radians(PARAMS["tiltDeg"])
    n0 = (0.0, -math.sin(tilt), math.cos(tilt))
    ax0 = (1.0, 0.0, 0.0)
    ay0 = (0.0, math.cos(tilt), math.sin(tilt))
    qYaw = q_from_axis((0.0, 1.0, 0.0), math.radians(PARAMS["yaw"]))
    viewAxis = vnorm(camPos)
    roll_d = AUTO_ROLL_AMP * math.sin(t * AUTO_ROLL_RATE + 1.3) if auto_motion else 0.0
    qRoll = q_from_axis(viewAxis, math.radians(PARAMS["roll"] + roll_d))
    q = q_mul(qRoll, qYaw)
    uDiskN = q_rotate(n0, q)
    uDiskAx = q_rotate(ax0, q)
    uDiskAy = q_rotate(ay0, q)

    return {
        "camPos": camPos, "fwd": fwd, "right": right, "up": up,
        "tanHalf": tanHalf, "aspect": aspect,
        "diskN": uDiskN, "diskAx": uDiskAx, "diskAy": uDiskAy,
    }


def camera_matrices(cam, near=0.1, far=300.0):
    """从相机基（fwd/right/up/camPos/tanHalf/aspect）构造列主序 proj/view，
    与黑洞盘着色器的 vNdc 重建射线完全一致，保证星层与盘对齐。"""
    fwd = cam["fwd"]
    right = cam["right"]
    up = cam["up"]
    camPos = cam["camPos"]
    tanHalf = cam["tanHalf"]
    aspect = cam["aspect"]
    z = (-fwd[0], -fwd[1], -fwd[2])
    tx = -vdot(right, camPos)
    ty = -vdot(up, camPos)
    tz = -vdot(z, camPos)
    view = [
        right[0], up[0], z[0], 0.0,
        right[1], up[1], z[1], 0.0,
        right[2], up[2], z[2], 0.0,
        tx, ty, tz, 1.0,
    ]
    f = 1.0 / tanHalf
    nf = near - far
    viewproj_far_near = (far + near) / nf
    viewproj_fn2 = (2.0 * far * near) / nf
    proj = [
        f / aspect, 0.0, 0.0, 0.0,
        0.0, f, 0.0, 0.0,
        0.0, 0.0, viewproj_far_near, -1.0,
        0.0, 0.0, viewproj_fn2, 0.0,
    ]
    return proj, view


HELP_MARKUP = chr(10).join([
    '<b>黑洞屏保 快捷键</b>',
    'M   自动运镜 开/关',
    'L   星空引力透镜 开/关',
    '空格   暂停 / 继续',
    'S   声音 静音 / 开',
    '1 / 2 / 3   画质 高 / 中 / 低',
    '[ ]   距离 远 / 近',
    'B   盘面亮度 开 / 关',
    'H   显示 / 隐藏本帮助',
    'Esc   退出',
])


import sys as _sys
_PLUG_MODE = any(a == "--plug-id" for a in _sys.argv)


class BlackHoleWindow(Gtk.Plug if _PLUG_MODE else Gtk.Window):
    def __init__(self, quality="mid", renderscale=1.0, hint="", daemon=False, plug_id=None, windowed=False):
        super(BlackHoleWindow, self).__init__()
        self.daemon = daemon
        self.quality = quality
        self.renderscale = renderscale
        self.hint = hint
        self.prog = -1
        self.vao = 0
        self.aPos = -1
        self.loc = {}
        self.start_t = 0
        self.t = 0.0
        self.failed = False
        self.postfx = None
        self.star_layer = None
        self.disk_w = 0
        self.disk_h = 0
        self.last_w = 0
        self.last_h = 0
        self.dpr = 1.0
        self.auto_motion = True
        self.star_lens = True
        self.disk_bright = True
        self.drift_keys = ["roll", "yaw", "tiltDeg"]
        self.drift_timer = DRIFT_INTERVAL - (15.0 + random.random() * 30.0)
        self.drift_t = DRIFT_DUR
        self.drift_from = {}
        self.drift_to = {}
        self.drift_active = {}
        self.paused = False
        self.muted = True
        self.t = 0.0
        self.last_now = 0
        self.player = None
        self.vol_elem = None
        self.help_visible = True
        self._flash_timer = 0
        self.disk_scale = QUALITY_BY_NAME[quality]["disk"]
        self._pending_quality = None

        self.plug_id = plug_id
        if plug_id is None:
            self.set_title("Black Hole Screensaver")
            self.set_app_paintable(True)
            if windowed:
                self.set_default_size(1280, 720)
            else:
                self.fullscreen()
                self.set_keep_above(True)

        self.glarea = Gtk.GLArea()
        self.glarea.set_use_es(False)
        self.glarea.set_required_version(3, 3)
        self.glarea.set_auto_render(False)
        self.glarea.set_can_focus(True)

        self.overlay = Gtk.Overlay()
        self.add(self.overlay)
        self.overlay.add(self.glarea)
        self._build_help_overlay()

        self.glarea.connect("realize", self.on_realize)
        self.glarea.connect("render", self.on_render)
        self.connect("destroy", self.on_destroy)
        self.connect("key-press-event", self.on_key)
        self.connect("button-press-event", self.on_button)

    def on_realize(self, area):
        try:
            area.make_current()
            self.init_gl()
            GLib.timeout_add(16, self.tick)
        except Exception as e:
            self.failed = True
            self.show_error("GL 初始化失败", traceback.format_exc())

    def init_gl(self):
        q = QUALITY_BY_NAME[self.quality]
        self.prog = gl.create_program(shaders.VERT, shaders.FRAG)

        vbo = gl.c_uint(0)
        gl.glGenBuffers(1, ctypes.byref(vbo))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        arr = (gl.c_float * 6)(-1.0, -1.0, 3.0, -1.0, -1.0, 3.0)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(arr), ctypes.byref(arr), gl.GL_STATIC_DRAW)

        vao = gl.c_uint(0)
        gl.glGenVertexArrays(1, ctypes.byref(vao))
        gl.glBindVertexArray(vao)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
        ap = gl.glGetAttribLocation(self.prog, b"aPos")
        gl.glEnableVertexAttribArray(ap)
        gl.glVertexAttribPointer(ap, 2, gl.GL_FLOAT, 0, 0, None)
        self.vao = vao
        self.aPos = ap

        names = ["uTime", "uCamPos", "uCamFwd", "uCamRight", "uCamUp",
                 "uTanFov", "uAspect", "uDiskN", "uDiskAx", "uDiskAy",
                 "uInner", "uOuter", "uBrightness", "uRotSpeed", "uRs",
                 "uArc", "uTempK", "uMaxSteps", "uRefine"]
        for n in names:
            self.loc[n] = gl.glGetUniformLocation(self.prog, n.encode("utf-8"))

        gl.glUseProgram(self.prog)
        gl.glUniform1f(self.loc["uInner"], PARAMS["inner"])
        gl.glUniform1f(self.loc["uOuter"], PARAMS["outer"])
        gl.glUniform1f(self.loc["uBrightness"], PARAMS["brightness"])
        gl.glUniform1f(self.loc["uRotSpeed"], PARAMS["rotSpeed"])
        # v2.155: bCrit = 2.598076 * uRs，且 ringIn 锁定为 bCrit，故 uRs = ringIn/2.598076
        gl.glUniform1f(self.loc["uRs"], float(PARAMS["ringIn"]) / 2.598076)
        gl.glUniform1f(self.loc["uArc"], PARAMS["ring"])
        gl.glUniform1f(self.loc["uTempK"], PARAMS["tempK"])
        gl.glUniform1f(self.loc["uMaxSteps"], float(q["maxSteps"]))
        gl.glUniform1f(self.loc["uRefine"], float(q["refine"]))

        gl.glDisable(glext.GL_DEPTH_TEST)

        n_stars = int(round(PARAMS["stars"] * q["star"]))
        self.star_layer = stars_mod.StarLayer(n_stars, "lens_lut.bin")
        self.postfx = bloom_mod.PostFX()
        self.start_t = GLib.get_monotonic_time()
        self.last_now = self.start_t
        self._setup_sound()

    def _dump_fbo(self, fbo, w, h, path):
        try:
            gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, fbo)
            gl.glReadBuffer(glext.GL_COLOR_ATTACHMENT0)
            buf = (ctypes.c_ubyte * (w * h * 3))()
            gl.glReadPixels(0, 0, w, h, glext.GL_RGB, glext.GL_UNSIGNED_BYTE, buf)
            gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, self._win_fbo)
            with open(path, "wb") as f:
                nl = chr(10)
                hdr = "P6" + nl + str(w) + " " + str(h) + nl + "255" + nl
                f.write(hdr.encode("ascii"))
                f.write(buf)
        except Exception as e:
            sys.stderr.write("dump failed: " + str(e) + chr(10))

    def _ensure_size(self, w, h):
        if w == self.last_w and h == self.last_h and self.postfx.scene_tex != 0:
            return
        self.last_w = w
        self.last_h = h
        self.postfx.resize(w, h, self.disk_scale)
        self.disk_w = self.postfx.disk_w
        self.disk_h = self.postfx.disk_h

    def screenshot(self, path):
        """读取最终帧缓冲（含辉光）保存为 PNG；优先 GL_FRONT，全黑时回退 GL_BACK。"""
        try:
            self.glarea.make_current()
        except Exception:
            pass
        w = self.last_w or self.glarea.get_allocated_width()
        h = self.last_h or self.glarea.get_allocated_height()
        if w <= 0 or h <= 0:
            w, h = 1280, 720

        fb = getattr(self, "_win_fbo", 0) or 0

        def readbuf(rb):
            gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, fb)
            gl.glReadBuffer(rb)
            buf = (ctypes.c_ubyte * (w * h * 3))()
            gl.glReadPixels(0, 0, w, h, glext.GL_RGB, glext.GL_UNSIGNED_BYTE, buf)
            return bytes(buf)

        try:
            data = readbuf(glext.GL_COLOR_ATTACHMENT0)
            if sum(data[0:min(len(data), 4000)]) == 0:
                data = readbuf(glext.GL_BACK)
            write_png(path, w, h, data)
            print("screenshot saved:", path, "%dx%d" % (w, h))
        except Exception as e:
            sys.stderr.write("screenshot failed: " + str(e) + chr(10))
        return True
        self.disk_w = self.postfx.disk_w
        self.disk_h = self.postfx.disk_h

    def on_render(self, area, ctx):
        try:
            if self.prog is None or self.prog < 0:
                return True
            area.make_current()
            dfb = ctypes.c_int(0)
            gl.glGetIntegerv(glext.GL_FRAMEBUFFER_BINDING, ctypes.byref(dfb))
            self._win_fbo = dfb.value
            w = area.get_allocated_width()
            h = area.get_allocated_height()
            if w <= 0 or h <= 0:
                return True
            self._ensure_size(w, h)
            gl.glDisable(glext.GL_DEPTH_TEST)

            aspect = w / float(h)
            now = GLib.get_monotonic_time()
            dt = (now - self.last_now) / 1e6
            self.last_now = now
            if not self.paused:
                self.t += dt
                self._update_drift(dt)
            cam = compute_camera(aspect, self.t, self.auto_motion)
            proj, view = camera_matrices(cam)
            camPos = cam["camPos"]

            if self._pending_quality is not None:
                self._apply_quality(self._pending_quality)
                self._pending_quality = None

            # 1) 黑洞盘 -> 半分辨率 diskFBO（背景透明）
            gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, self.postfx.disk_fbo)
            gl.glViewport(0, 0, self.disk_w, self.disk_h)
            gl.glDisable(gl.GL_BLEND)
            gl.glClearColor(0.0, 0.0, 0.0, 0.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            gl.glUseProgram(self.prog)
            gl.glUniform1f(self.loc["uTime"], self.t)
            gl.glUniform3f(self.loc["uCamPos"], *camPos)
            gl.glUniform3f(self.loc["uCamFwd"], *cam["fwd"])
            gl.glUniform3f(self.loc["uCamRight"], *cam["right"])
            gl.glUniform3f(self.loc["uCamUp"], *cam["up"])
            gl.glUniform1f(self.loc["uTanFov"], cam["tanHalf"])
            gl.glUniform1f(self.loc["uAspect"], aspect)
            gl.glUniform1f(self.loc["uBrightness"], PARAMS["brightness"] if self.disk_bright else 0.0)
            gl.glUniform3f(self.loc["uDiskN"], *cam["diskN"])
            gl.glUniform3f(self.loc["uDiskAx"], *cam["diskAx"])
            gl.glUniform3f(self.loc["uDiskAy"], *cam["diskAy"])
            gl.glBindVertexArray(self.vao)
            gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)
            gl.glBindVertexArray(0)
            gl_check("disk_draw")

            # 2) 离散星场 -> 全分辨率 sceneFBO（加色混合）
            gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, self.postfx.scene_fbo)
            gl.glViewport(0, 0, w, h)
            gl.glClearColor(0.0, 0.0, 0.0, 0.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            self.star_layer.draw(
                proj, view, camPos, (0.0, 0.0, 0.0),
                self.star_lens, self.t * STAR_ROT_RATE,
                w, h, self.dpr, 1.4, 2.4)
            gl_check("stars_draw")

            # 3) 合成 + 辉光 -> 屏幕
            self.postfx.render(w, h, float(PARAMS["bloom"]), 0.55, 0.45, self._win_fbo)
            if os.environ.get("BH_GL_DUMP"):
                self._dump_fbo(self.postfx.disk_fbo, self.disk_w, self.disk_h, "/tmp/bh_dump.ppm")
            gl_check("final")
            gl.glFlush()
        except Exception as e:
            sys.stderr.write("render error: " + traceback.format_exc())
            try:
                with open("/tmp/bh_gl_error.log", "a") as f:
                    f.write("render error: " + traceback.format_exc())
            except Exception:
                pass
        return True

    def tick(self):
        if self.prog is not None and self.prog >= 0:
            self.glarea.queue_render()
        return True

    def on_key(self, widget, event):
        try:
            self._handle_key(event)
        except Exception as e:
            sys.stderr.write("key handler error: " + str(e) + chr(10))
            try:
                with open("/tmp/bh_gl_error.log", "a") as f:
                    f.write("key handler error: " + str(e) + chr(10))
            except Exception:
                pass
        return True

    def _handle_key(self, event):
        k = event.keyval
        try:
            keyname = Gdk.keyval_name(k)
        except Exception:
            keyname = None
        if keyname in ("h", "H"):
            self.toggle_help()
            return
        if keyname == "Escape":
            if not self.daemon:
                Gtk.main_quit()
            return
        if keyname in ("m", "M"):
            self.auto_motion = not self.auto_motion
            self._flash("自动运镜: " + ("开" if self.auto_motion else "关"))
        elif keyname in ("l", "L"):
            self.star_lens = not self.star_lens
            self._flash("星空透镜: " + ("开" if self.star_lens else "关"))
        elif k == Gdk.KEY_space:
            self.paused = not self.paused
            self._flash("暂停" if self.paused else "继续")
        elif keyname in ("s", "S"):
            self._set_muted(not self.muted)
            self._flash("声音: " + ("静音" if self.muted else "开"))
        elif keyname in ("1", "2", "3"):
            name = {"1": "high", "2": "mid", "3": "low"}[keyname]
            self.set_quality(name)
            self._flash("画质: " + name)
        elif keyname in ("bracketleft", "bracketright"):
            step = 1.0 if keyname == "bracketright" else -1.0
            PARAMS["distance"] = min(60.0, max(19.0, PARAMS["distance"] + step))
            self._flash("距离: " + ("%.1f" % PARAMS["distance"]))

        elif keyname in ("b", "B"):
            self.disk_bright = not self.disk_bright
            self._flash("盘面亮度: " + ("开" if self.disk_bright else "关"))

    def on_button(self, widget, event):
        # 仅 ESC 退出屏保（见 on_key），点击不退出，避免与快捷键冲突
        return True

    def _trigger_drift(self):
        for k in self.drift_keys:
            lo, hi = PARAM_RANGES[k]
            active = (k == "yaw") or (random.random() < 0.6)
            self.drift_active[k] = active
            if active:
                cur = PARAMS[k]
                rng = (hi - lo) * DRIFT_AMP_FRAC
                self.drift_from[k] = cur
                self.drift_to[k] = min(hi, max(lo, cur + (random.random() * 2.0 - 1.0) * rng))
        # 保证 yaw 必参与 + 至少再 1 项（共 ≥2）
        active_cnt = sum(1 for k in self.drift_keys if self.drift_active[k])
        if active_cnt < 2:
            inactive = [k for k in self.drift_keys if not self.drift_active[k]]
            while inactive and active_cnt < 2:
                k = inactive.pop(int(random.random() * len(inactive)))
                lo, hi = PARAM_RANGES[k]
                cur = PARAMS[k]
                rng = (hi - lo) * 0.10
                self.drift_from[k] = cur
                self.drift_to[k] = min(hi, max(lo, cur + (random.random() * 2.0 - 1.0) * rng))
                self.drift_active[k] = True
                active_cnt += 1
        self.drift_t = 0.0

    def _update_drift(self, dt):
        if not self.auto_motion:
            return
        self.drift_timer += dt
        if self.drift_timer >= DRIFT_INTERVAL:
            self.drift_timer -= DRIFT_INTERVAL
            self._trigger_drift()
        if self.drift_t < DRIFT_DUR:
            self.drift_t += dt
            tt = min(self.drift_t / DRIFT_DUR, 1.0)
            e = tt * tt * (3.0 - 2.0 * tt)
            for k in self.drift_keys:
                if not self.drift_active[k]:
                    continue
                v = self.drift_from[k] + (self.drift_to[k] - self.drift_from[k]) * e
                PARAMS[k] = v

    def toggle_help(self):
        self.help_visible = not self.help_visible
        if self.help_visible:
            self.help_label.set_markup(HELP_MARKUP)
        self.help_label.set_visible(self.help_visible)

    def _flash(self, text):
        self.help_label.set_markup("<span size='medium'>" + text + "</span>")
        self.help_label.set_visible(True)
        if self._flash_timer:
            GLib.source_remove(self._flash_timer)
        self._flash_timer = GLib.timeout_add(1200, self._restore_help)

    def _restore_help(self):
        self._flash_timer = 0
        if self.help_visible:
            self.help_label.set_markup(HELP_MARKUP)
        else:
            self.help_label.set_visible(False)
        return False

    def _build_help_overlay(self):
        self.help_label = Gtk.Label()
        self.help_label.set_markup(HELP_MARKUP)
        self.help_label.set_halign(Gtk.Align.START)
        self.help_label.set_valign(Gtk.Align.START)
        self.help_label.set_margin_start(24)
        self.help_label.set_margin_top(24)
        self.help_label.set_visible(self.help_visible)
        try:
            css = b"label.bh-help{background-color:rgba(0,0,0,0.55);color:#e8e8e8;padding:14px 18px;border-radius:8px;font-family:monospace;font-size:13px;}"
            prov = Gtk.CssProvider()
            prov.load_from_data(css)
            ctx = self.help_label.get_style_context()
            ctx.add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            ctx.add_class("bh-help")
        except Exception:
            pass
        self.overlay.add_overlay(self.help_label)

    def set_quality(self, name):
        if name not in QUALITY_BY_NAME:
            return
        self._pending_quality = name

    def _apply_quality(self, name):
        q = QUALITY_BY_NAME[name]
        try:
            gl.glUseProgram(self.prog)
            gl.glUniform1f(self.loc["uMaxSteps"], float(q["maxSteps"]))
            gl.glUniform1f(self.loc["uRefine"], float(q["refine"]))
            self.quality = name
            self.disk_scale = q["disk"]
            self.postfx.resize(self.last_w, self.last_h, self.disk_scale)
            self.disk_w = self.postfx.disk_w
            self.disk_h = self.postfx.disk_h
            n_stars = int(round(PARAMS["stars"] * q["star"]))
            self.star_layer = stars_mod.StarLayer(n_stars, "lens_lut.bin")
        except Exception as e:
            sys.stderr.write("apply_quality failed: " + str(e) + chr(10))
            try:
                with open("/tmp/bh_gl_error.log", "a") as f:
                    f.write("apply_quality failed: " + str(e) + chr(10))
            except Exception:
                pass

    def _setup_sound(self):
        self.player = None
        self.vol_elem = None
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
        except Exception:
            return
        try:
            Gst.init(None)
        except Exception:
            return
        base = max(0.04, min(0.30, float(PARAMS.get("ambVol", 0.35)))) * 0.45
        descs = [
            "audiotestsrc wave=sine freq=110 ! volume volume=%.3f ! mix. "
            "audiotestsrc wave=sine freq=164.81 ! volume volume=%.3f ! mix. "
            "audiotestsrc wave=sine freq=220 ! volume volume=%.3f ! mix. "
            "audiotestsrc wave=pink-noise ! volume volume=%.3f ! mix. "
            "audiomixer name=mix ! audioresample ! autoaudiosink"
            % (base, base * 0.6, base * 0.4, base * 0.25),
            "audiotestsrc wave=sine freq=110 ! volume volume=%.3f ! autoaudiosink" % base,
        ]
        for desc in descs:
            try:
                self.player = Gst.parse_launch(desc)
                self.player.set_state(Gst.State.PAUSED if self.muted else Gst.State.PLAYING)
                return
            except Exception as e:
                self.player = None
                try:
                    with open("/tmp/bh_gl_error.log", "a") as f:
                        f.write("sound pipeline failed: " + str(e) + chr(10))
                except Exception:
                    pass

    def _set_muted(self, m):
        self.muted = m
        if self.player is None:
            return
        try:
            import gi
            gi.require_version("Gst", "1.0")
            from gi.repository import Gst
            self.player.set_state(Gst.State.PAUSED if m else Gst.State.PLAYING)
        except Exception:
            pass

    def on_destroy(self, widget):
        if not self.daemon:
            Gtk.main_quit()

    def show_error(self, title, msg):
        try:
            with open("/tmp/bh_gl_error.log", "w") as f:
                f.write(title + chr(10) + str(msg) + chr(10))
        except Exception:
            pass
        try:
            sys.stderr.write(title + chr(10) + str(msg) + chr(10))
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass
        try:
            dlg = Gtk.MessageDialog(transient_for=None, flags=0,
                                    message_type=Gtk.MessageType.ERROR,
                                    buttons=Gtk.ButtonsType.CLOSE,
                                    text=title)
            dlg.format_secondary_text(str(msg)[:4000])
            dlg.set_keep_above(True)
            dlg.run()
            dlg.destroy()
        except Exception:
            pass
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description="native GL black hole screensaver")
    ap.add_argument("--daemon", action="store_true", help="daemon mode, show only on lock")
    ap.add_argument("--quality", choices=["high", "mid", "low"], default="mid")
    ap.add_argument("--renderscale", type=float, default=1.0)
    ap.add_argument("--plug-id", type=int, default=None, help="XEmbed socket id (plugin mode)")
    ap.add_argument("--hint", default="")
    ap.add_argument("--screenshot", default=None, help="render N frames then save PNG to this path and quit")
    ap.add_argument("--frames", type=int, default=60, help="frames to render before screenshot")
    ap.add_argument("--no-disk", action="store_true", help="start with disk brightness off")
    ap.add_argument("--no-star-lens", action="store_true", help="start with star lensing off")
    ap.add_argument("--tilt", type=float, default=None, help="override tiltDeg")
    args = ap.parse_args()
    if args.tilt is not None:
        PARAMS["tiltDeg"] = args.tilt

    win = BlackHoleWindow(quality=args.quality, renderscale=args.renderscale,
                          hint=args.hint, daemon=args.daemon, plug_id=args.plug_id,
                          windowed=(args.screenshot is not None))
    win.star_lens = not args.no_star_lens
    win.disk_bright = not args.no_disk
    win.show_all()
    win.present()
    win.set_focus(win.glarea)

    if args.screenshot:
        win.help_visible = False
        try:
            win.help_label.set_visible(False)
        except Exception:
            pass
        path = args.screenshot
        frames = max(1, args.frames)

        def _shoot():
            win.screenshot(path)
            Gtk.main_quit()
            return False

        # 渲染若干帧让星空/透镜/盘稳定后截图
        GLib.timeout_add(int(frames * 16.7) + 200, _shoot)
        Gtk.main()
        return

    if args.daemon:
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            proxy = Gio.DBusProxy.new_sync(
                bus, Gio.DBusProxyFlags.NONE, None,
                "org.cinnamon.ScreenSaver", "/org/cinnamon/ScreenSaver",
                "org.cinnamon.ScreenSaver", None)

            def on_active(proxy, sender, signal, params):
                if signal != "ActiveChanged":
                    return
                active = params.unpack()[0]
                if active:
                    win.show_all()
                    win.present()
                    win.set_focus(win.glarea)
                else:
                    win.hide()

            proxy.connect("g-signal", on_active)
            win.hide()
        except Exception as e:
            sys.stderr.write("DBus listen failed: " + str(e) + chr(10))

    Gtk.main()


if __name__ == "__main__":
    main()
