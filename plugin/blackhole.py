# Cinnamon screensaver plugin: embeds the native GL black-hole renderer
# via XEmbed (Gtk.Socket / Gtk.Plug). All GL/shader code stays in bh_gl.py.
# Nothing is hardcoded to a machine: the renderer path is resolved at runtime
# (env / config / conventional dirs) and the CScreensaver typelib is located
# dynamically so the plugin loads whether or not the host pre-set GI_TYPELIB_PATH.
import os, glob, subprocess

def _ensure_cscreensaver_typelib():
    name = "CScreensaver-1.0.typelib"
    cur = os.environ.get("GI_TYPELIB_PATH", "")
    if "CScreensaver" in cur:
        return
    roots = [
        "/usr/libexec/cinnamon-screensaver/girepository-1.0",
        "/usr/lib/cinnamon-screensaver/girepository-1.0",
        "/usr/lib/x86_64-linux-gnu/cinnamon-screensaver/girepository-1.0",
    ]
    for r in roots:
        if os.path.isfile(os.path.join(r, name)):
            os.environ["GI_TYPELIB_PATH"] = (r + ":" + cur).rstrip(":")
            return
    for hit in glob.glob("/usr/libexec/**/" + name, recursive=True):
        os.environ["GI_TYPELIB_PATH"] = (os.path.dirname(hit) + ":" + cur).rstrip(":")
        return


def _find_bh_gl():
    env = os.environ.get("BLACKHOLE_GL")
    if env and os.path.isfile(env):
        return env
    cfg = os.path.expanduser("~/.config/blackhole/config")
    if os.path.isfile(cfg):
        try:
            for line in open(cfg):
                line = line.strip()
                if line.startswith("BH_GL="):
                    p = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if p and os.path.isfile(p):
                        return p
        except Exception:
            pass
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(here, "bh_gl.py"),
        os.path.join(here, "screensaver_native", "bh_gl.py"),
        os.path.expanduser("~/.local/share/blackhole/bh_gl.py"),
        "/opt/blackhole/bh_gl.py",
        "/usr/local/share/blackhole/bh_gl.py",
    ]
    for c in cands:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return None


_ensure_cscreensaver_typelib()
import ctypes

def _ensure_cscreensaver_lib():
    for r in ['/usr/libexec/cinnamon-screensaver','/usr/lib/x86_64-linux-gnu','/usr/lib']:
        lp=os.path.join(r,'libcscreensaver.so')
        if os.path.isfile(lp):
            try:
                ctypes.CDLL(lp)
                return
            except Exception:
                pass
    for hit in glob.glob('/usr/libexec/**/libcscreensaver.so', recursive=True):
        try:
            ctypes.CDLL(hit)
            return
        except Exception:
            pass

_ensure_cscreensaver_lib()
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("CScreensaver", "1.0")
from gi.repository import GObject, Gtk, CScreensaver

BH_GL = _find_bh_gl()


class Screensaver(CScreensaver.ScreenSaver):
    def __init__(self, container):
        super(Screensaver, self).__init__(container)
        self.socket = Gtk.Socket()
        self.socket.set_hexpand(True)
        self.socket.set_vexpand(True)
        self.socket.show()
        self.proc = None

    def do_get_widget(self):
        return self.socket

    def _spawn(self):
        self.socket.realize()
        xid = self.socket.get_id()
        if not xid:
            return False
        if self.proc is not None:
            return False
        if not BH_GL or not os.path.isfile(BH_GL):
            return False
        env = dict(os.environ)
        self.proc = subprocess.Popen(
            ["python3", BH_GL, "--plug-id", str(xid)], env=env)
        return False

    def do_start(self):
        if self.proc is not None:
            return
        if not self._spawn():
            GObject.idle_add(self._spawn)

    def do_stop(self):
        if self.proc is not None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.proc = None

    def do_pause(self):
        pass

    def do_resume(self):
        pass
