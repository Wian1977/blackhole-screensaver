# -*- coding: utf-8 -*-
"""discrete star-field layer: native GL port of web buildStars + starMat."""

import math
import ctypes
import os

import glctypes as gl
import glext
import lenslut

_HERE = os.path.dirname(os.path.abspath(__file__))

STAR_MAX = 55000

STAR_VS = """
#version 330 core
layout(location = 0) in vec2 aPos;
layout(location = 1) in vec3 aSrcDir;
layout(location = 2) in vec3 aStar;
layout(location = 3) in float aWhich;
uniform mat4 uProj;
uniform mat4 uView;
uniform vec3 uCamPos;
uniform vec3 uBhPos;
uniform sampler2D uLutTex;
uniform float uLutN;
uniform float uStarLens;
uniform float uStarRot;
uniform float uStarBright;
uniform float uStarSize;
uniform float uDpr;
uniform vec2 uViewport;
out vec2 vQuad;
out vec3 vColor;
out float vBright;
#define STAR_DEPTH 200.0
void main() {
  vQuad = aPos;
  float ct = aStar.y;
  vColor = (ct < 0.68) ? vec3(0.92, 0.96, 1.00) : ((ct < 0.85) ? vec3(1.00, 0.84, 0.62) : vec3(0.68, 0.74, 1.00));
  vBright = aStar.x * uStarBright;
  vec3 s = normalize(aSrcDir);
  float cs = cos(uStarRot), sn = sin(uStarRot);
  s = vec3(s.x * cs - s.z * sn, s.y, s.x * sn + s.z * cs);
  vec3 ax = normalize(uBhPos - uCamPos);
  float cb = clamp(dot(s, ax), -1.0, 1.0);
  float bAbs = acos(cb);
  vec3 perp = s - cb * ax;
  float pl = length(perp);
  vec3 that = (pl > 1e-4) ? perp / pl : normalize(cross(ax, vec3(0.0, 1.0, 0.0)) + vec3(1e-3, 0.0, 0.0));
  float theta, muR, sgn = 1.0;
  if (uStarLens > 0.5) {
    float t = clamp(bAbs / 3.14159265, 0.0, 1.0) * (uLutN - 1.0);
    float fi = floor(t), fr = t - fi;
    float i0 = fi, i1 = min(fi + 1.0, uLutN - 1.0);
    vec4 A = texture(uLutTex, vec2((i0 + 0.5) / uLutN, 0.5));
    vec4 B = texture(uLutTex, vec2((i1 + 0.5) / uLutN, 0.5));
    vec4 V = mix(A, B, fr);
    if (aWhich < 0.5) { theta = V.x; muR = V.y; sgn = 1.0; }
    else {
      if (A.z < 0.0 || B.z < 0.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
      theta = V.z; muR = V.w; sgn = -1.0;
    }
    if (theta < 0.0) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
  } else {
    if (aWhich > 0.5) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
    theta = bAbs; muR = 1.0; sgn = 1.0;
  }
  float sb = max(sin(bAbs), 0.02);
  float muT = clamp(sin(theta) / sb, 0.2, 10.0);
  vec3 rd = cos(theta) * ax + sgn * sin(theta) * that;
  float mag = clamp(pow(max(muT * muR, 0.0001), 0.45), 0.06, 5.0);
  vBright *= mix(1.0, mag, uStarLens);
  float sig = aStar.z * uStarSize * uDpr;
  float wT = clamp(sig * muT, 0.85, 36.0);
  float wR = clamp(sig * muR, 0.85, 36.0);
  vec3 cw = uCamPos + rd * STAR_DEPTH;
  vec4 clipC = uProj * uView * vec4(cw, 1.0);
  vec4 clipB = uProj * uView * vec4(uBhPos, 1.0);
  float wC = max(clipC.w, 1e-6);
  vec2 nc = clipC.xy / wC;
  vec2 nb = clipB.xy / max(clipB.w, 1e-6);
  vec2 dpx = (nc - nb) * 0.5 * uViewport;
  float dl = length(dpx);
  vec2 rdN = (dl > 1e-3) ? dpx / dl : vec2(1.0, 0.0);
  vec2 tdN = vec2(-rdN.y, rdN.x);
  vec2 off = tdN * (aPos.x * wT) + rdN * (aPos.y * wR);
  gl_Position = vec4((nc + off * 2.0 / uViewport) * wC, clipC.z, wC);
}
"""

STAR_FS = """
#version 330 core
in vec2 vQuad;
in vec3 vColor;
in float vBright;
out vec4 fragColor;
void main() {
  float d2 = dot(vQuad, vQuad);
  float g = exp(-d2 * 4.5);
  float a = g * vBright;
  if (a < 0.003) discard;
  fragColor = vec4(vColor * a, 1.0);
}
"""

def build_star_catalog(n):
    dir = []
    att = []
    whi = []
    seed = 20241029
    def rnd():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
        return seed / 4294967296.0
    order = list(range(n))
    for i in range(n - 1, 0, -1):
        j = int(rnd() * (i + 1))
        order[i], order[j] = order[j], order[i]
    for a in range(n):
        i = order[a]
        y = 1.0 - 2.0 * ((i + 0.5) / n)
        rr = math.sqrt(max(0.0, 1.0 - y * y))
        ph = i * 2.399963229728653 + rnd() * 0.35
        sx = rr * math.cos(ph)
        sy = y + (rnd() - 0.5) * (1.2 / math.sqrt(n))
        sz = rr * math.sin(ph)
        il = 1.0 / max(math.hypot(sx, sy, sz), 1e-6)
        sx *= il; sy *= il; sz *= il
        br = 0.30 + pow(rnd(), 2.2) * 0.85
        ct = rnd()
        sz2 = 0.55 + pow(rnd(), 3.0) * 1.5
        for k in range(2):
            j = a * 2 + k
            dir.extend([sx, sy, sz])
            att.extend([br, ct, sz2])
            whi.append(float(k))
    return dir, att, whi
class StarLayer:
    def __init__(self, n, lut_path="lens_lut.bin"):
        self.n = n
        if not os.path.isabs(lut_path):
            lut_path = os.path.join(_HERE, lut_path)
        self.prog = gl.create_program(STAR_VS, STAR_FS)
        self.lut_tex = self._make_lut(lut_path)
        self._build_geometry(n)
        names = ["uProj", "uView", "uCamPos", "uBhPos", "uLutTex",
                 "uLutN", "uStarLens", "uStarRot", "uStarBright",
                 "uStarSize", "uDpr", "uViewport"]
        self.loc = {}
        for nm in names:
            self.loc[nm] = gl.glGetUniformLocation(self.prog, nm.encode("utf-8"))
        gl.glUseProgram(self.prog)
        gl.glUniform1i(self.loc["uLutTex"], 0)

    def _make_lut(self, path):
        data = lenslut.load(path)
        if len(data) != lenslut.LUT_N * 4:
            raise RuntimeError("lens_lut.bin float count mismatch")
        tex = gl.c_uint(0)
        gl.glGenTextures(1, ctypes.byref(tex))
        gl.glBindTexture(glext.GL_TEXTURE_2D, tex)
        arr = (gl.c_float * len(data))(*data)
        gl.glTexImage2D(glext.GL_TEXTURE_2D, 0, glext.GL_RGBA32F,
                        lenslut.LUT_N, 1, 0, glext.GL_RGBA, gl.GL_FLOAT,
                        ctypes.byref(arr))
        gl.glTexParameteri(glext.GL_TEXTURE_2D, glext.GL_TEXTURE_MIN_FILTER, glext.GL_NEAREST)
        gl.glTexParameteri(glext.GL_TEXTURE_2D, glext.GL_TEXTURE_MAG_FILTER, glext.GL_NEAREST)
        gl.glTexParameteri(glext.GL_TEXTURE_2D, glext.GL_TEXTURE_WRAP_S, glext.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(glext.GL_TEXTURE_2D, glext.GL_TEXTURE_WRAP_T, glext.GL_CLAMP_TO_EDGE)
        gl.glBindTexture(glext.GL_TEXTURE_2D, 0)
        return tex.value

    def _build_geometry(self, n):
        d, a, w = build_star_catalog(n)
        nInst = n * 2
        self.vao = gl.c_uint(0)
        gl.glGenVertexArrays(1, ctypes.byref(self.vao))
        gl.glBindVertexArray(self.vao)
        quad = [-1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0]
        pb = gl.c_uint(0)
        gl.glGenBuffers(1, ctypes.byref(pb))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, pb)
        arr = (gl.c_float * len(quad))(*quad)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(arr), ctypes.byref(arr), gl.GL_STATIC_DRAW)
        gl.glEnableVertexAttribArray(0)
        gl.glVertexAttribPointer(0, 2, gl.GL_FLOAT, 0, 0, None)
        gl.glVertexAttribDivisor(0, 0)
        db = gl.c_uint(0)
        gl.glGenBuffers(1, ctypes.byref(db))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, db)
        arr = (gl.c_float * len(d))(*d)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(arr), ctypes.byref(arr), gl.GL_STATIC_DRAW)
        gl.glEnableVertexAttribArray(1)
        gl.glVertexAttribPointer(1, 3, gl.GL_FLOAT, 0, 0, None)
        gl.glVertexAttribDivisor(1, 1)
        ab = gl.c_uint(0)
        gl.glGenBuffers(1, ctypes.byref(ab))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, ab)
        arr = (gl.c_float * len(a))(*a)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(arr), ctypes.byref(arr), gl.GL_STATIC_DRAW)
        gl.glEnableVertexAttribArray(2)
        gl.glVertexAttribPointer(2, 3, gl.GL_FLOAT, 0, 0, None)
        gl.glVertexAttribDivisor(2, 1)
        wb = gl.c_uint(0)
        gl.glGenBuffers(1, ctypes.byref(wb))
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, wb)
        arr = (gl.c_float * len(w))(*w)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(arr), ctypes.byref(arr), gl.GL_STATIC_DRAW)
        gl.glEnableVertexAttribArray(3)
        gl.glVertexAttribPointer(3, 1, gl.GL_FLOAT, 0, 0, None)
        gl.glVertexAttribDivisor(3, 1)
        ib = gl.c_uint(0)
        gl.glGenBuffers(1, ctypes.byref(ib))
        gl.glBindBuffer(gl.GL_ELEMENT_ARRAY_BUFFER, ib)
        idx = [0, 1, 2, 0, 2, 3]
        arr = (gl.c_uint * 6)(*idx)
        gl.glBufferData(gl.GL_ELEMENT_ARRAY_BUFFER, ctypes.sizeof(arr), ctypes.byref(arr), gl.GL_STATIC_DRAW)
        gl.glBindVertexArray(0)
        self.nInst = nInst

    def draw(self, proj, view, cam_pos, bh_pos, lens_on, star_rot,
             vp_w, vp_h, dpr, bright, size):
        gl.glUseProgram(self.prog)
        gl.glBindVertexArray(self.vao)
        gl.glDisable(glext.GL_DEPTH_TEST)
        gl.glEnable(glext.GL_BLEND)
        gl.glBlendFunc(glext.GL_ONE, glext.GL_ONE)
        gl.glActiveTexture(glext.GL_TEXTURE0)
        gl.glBindTexture(glext.GL_TEXTURE_2D, self.lut_tex)
        pa = (gl.c_float * 16)(*proj)
        va = (gl.c_float * 16)(*view)
        gl.glUniformMatrix4fv(self.loc["uProj"], 1, 0, ctypes.byref(pa))
        gl.glUniformMatrix4fv(self.loc["uView"], 1, 0, ctypes.byref(va))
        gl.glUniform3f(self.loc["uCamPos"], *cam_pos)
        gl.glUniform3f(self.loc["uBhPos"], *bh_pos)
        gl.glUniform1f(self.loc["uLutN"], float(lenslut.LUT_N))
        gl.glUniform1f(self.loc["uStarLens"], 1.0 if lens_on else 0.0)
        gl.glUniform1f(self.loc["uStarRot"], float(star_rot))
        gl.glUniform1f(self.loc["uStarBright"], float(bright))
        gl.glUniform1f(self.loc["uStarSize"], float(size))
        gl.glUniform1f(self.loc["uDpr"], float(dpr))
        gl.glUniform2f(self.loc["uViewport"], float(vp_w), float(vp_h))
        gl.glDrawElementsInstanced(gl.GL_TRIANGLES, 6, glext.GL_UNSIGNED_INT, None, self.nInst)
        gl.glBindVertexArray(0)
