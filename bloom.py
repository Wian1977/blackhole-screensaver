# -*- coding: utf-8 -*-
"""post composite + bloom (UnrealBloomPass equivalent), native GL."""
import ctypes

import glctypes as gl
import glext

FS_VS = """
#version 330 core
layout(location = 0) in vec2 aPos;
out vec2 vUv;
void main() {
  vUv = aPos * 0.5 + 0.5;
  gl_Position = vec4(aPos, 0.0, 1.0);
}
"""

COMPOSITE_FS = """
#version 330 core
in vec2 vUv;
uniform sampler2D tScene;
uniform sampler2D tDisk;
out vec4 fragColor;
void main() {
  vec3 s = texture(tScene, vUv).rgb;
  vec4 d = texture(tDisk, vUv);
  // premultiplied-over: result = disk.rgb + star.rgb*(1-disk.a)
  fragColor = vec4(d.rgb + s.rgb * (1.0 - d.a), 1.0);
}
"""

BRIGHT_FS = """
#version 330 core
in vec2 vUv;
uniform sampler2D tSrc;
uniform float uThreshold;
out vec4 fragColor;
void main() {
  vec3 c = texture(tSrc, vUv).rgb;
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  float k = max(l - uThreshold, 0.0) / max(l, 1e-4);
  fragColor = vec4(c * k, 1.0);
}
"""
BLUR_FS = """
#version 330 core
in vec2 vUv;
uniform sampler2D tSrc;
uniform vec2 uDir;
uniform float uRadius;
out vec4 fragColor;
void main() {
  float w0 = 0.227027;
  float w1 = 0.1945946;
  float w2 = 0.1216216;
  float w3 = 0.054054;
  float w4 = 0.016216;
  vec2 o1 = uDir * 1.0 * uRadius;
  vec2 o2 = uDir * 2.0 * uRadius;
  vec2 o3 = uDir * 3.0 * uRadius;
  vec2 o4 = uDir * 4.0 * uRadius;
  vec3 c = texture(tSrc, vUv).rgb * w0;
  c += texture(tSrc, vUv + o1).rgb * w1;
  c += texture(tSrc, vUv - o1).rgb * w1;
  c += texture(tSrc, vUv + o2).rgb * w2;
  c += texture(tSrc, vUv - o2).rgb * w2;
  c += texture(tSrc, vUv + o3).rgb * w3;
  c += texture(tSrc, vUv - o3).rgb * w3;
  c += texture(tSrc, vUv + o4).rgb * w4;
  c += texture(tSrc, vUv - o4).rgb * w4;
  fragColor = vec4(c, 1.0);
}
"""

FINAL_FS = """
#version 330 core
in vec2 vUv;
uniform sampler2D tScene;
uniform sampler2D tBloom;
uniform float uStrength;
out vec4 fragColor;
void main() {
  vec3 base = texture(tScene, vUv).rgb;
  vec3 bloom = texture(tBloom, vUv).rgb;
  fragColor = vec4(base + bloom * uStrength, 1.0);
}
"""
class PostFX:
    def __init__(self):
        self.prog_composite = gl.create_program(FS_VS, COMPOSITE_FS)
        self.prog_bright = gl.create_program(FS_VS, BRIGHT_FS)
        self.prog_blur = gl.create_program(FS_VS, BLUR_FS)
        self.prog_final = gl.create_program(FS_VS, FINAL_FS)
        self.quad = glext.ortho_quad()
        self.lc = self._loc(self.prog_composite, ["tScene", "tDisk"])
        self.lb = self._loc(self.prog_bright, ["tSrc", "uThreshold"])
        self.lu = self._loc(self.prog_blur, ["tSrc", "uDir", "uRadius"])
        self.lf = self._loc(self.prog_final, ["tScene", "tBloom", "uStrength"])
        self.scene_tex = self.disk_tex = 0
        self.comp_tex = self.bright_tex = 0
        self.blurA_tex = self.blurB_tex = 0
        self.bw = self.bh = 0

    def _loc(self, prog, names):
        d = {}
        for nm in names:
            d[nm] = gl.glGetUniformLocation(prog, nm.encode("utf-8"))
        return d

    def _make_fbo(self, name, w, h):
        fbo, tex, drb = glext.make_fbo(w, h, depth=False)
        setattr(self, name + "_fbo", fbo)
        setattr(self, name + "_tex", tex)

    def resize(self, w, h, disk_scale=0.5, bloom_cap=1080):
        bw = max(1, int(w * 0.5))
        bh = max(1, int(h * 0.5))
        if bh > bloom_cap:
            bw = max(1, int(bw * bloom_cap / bh))
            bh = bloom_cap
        self.bw = bw
        self.bh = bh
        self.disk_w = max(1, int(w * disk_scale))
        self.disk_h = max(1, int(h * disk_scale))
        self._make_fbo("scene", w, h)
        self._make_fbo("disk", self.disk_w, self.disk_h)
        self._make_fbo("comp", w, h)
        self._make_fbo("bright", bw, bh)
        self._make_fbo("blurA", bw, bh)
        self._make_fbo("blurB", bw, bh)

    def _draw_quad(self):
        gl.glBindVertexArray(self.quad[0])
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)
        gl.glBindVertexArray(0)

    def render(self, w, h, strength, radius, threshold, win_fbo=0):
        gl.glDisable(gl.GL_BLEND)
        gl.glDisable(glext.GL_DEPTH_TEST)
        gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, self.comp_fbo)
        gl.glViewport(0, 0, w, h)
        gl.glUseProgram(self.prog_composite)
        gl.glActiveTexture(glext.GL_TEXTURE0)
        gl.glBindTexture(glext.GL_TEXTURE_2D, self.scene_tex)
        gl.glUniform1i(self.lc["tScene"], 0)
        gl.glActiveTexture(glext.GL_TEXTURE1)
        gl.glBindTexture(glext.GL_TEXTURE_2D, self.disk_tex)
        gl.glUniform1i(self.lc["tDisk"], 1)
        self._draw_quad()
        gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, self.bright_fbo)
        gl.glViewport(0, 0, self.bw, self.bh)
        gl.glUseProgram(self.prog_bright)
        gl.glActiveTexture(glext.GL_TEXTURE0)
        gl.glBindTexture(glext.GL_TEXTURE_2D, self.comp_tex)
        gl.glUniform1i(self.lb["tSrc"], 0)
        gl.glUniform1f(self.lb["uThreshold"], float(threshold))
        self._draw_quad()
        gl.glUseProgram(self.prog_blur)
        gl.glUniform1f(self.lu["uRadius"], float(radius) * 6.0)
        self._blur_pass(self.bright_tex, self.blurA_fbo, 1.0 / self.bw, 0.0)
        self._blur_pass(self.blurA_tex, self.blurB_fbo, 0.0, 1.0 / self.bh)
        self._blur_pass(self.blurB_tex, self.blurA_fbo, 1.0 / self.bw, 0.0)
        self._blur_pass(self.blurA_tex, self.blurB_fbo, 0.0, 1.0 / self.bh)
        self._blur_pass(self.blurB_tex, self.blurA_fbo, 1.0 / self.bw, 0.0)
        self._blur_pass(self.blurA_tex, self.blurB_fbo, 0.0, 1.0 / self.bh)
        gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, win_fbo)
        if win_fbo == 0:
            gl.glDrawBuffer(glext.GL_BACK)
        gl.glViewport(0, 0, w, h)
        gl.glUseProgram(self.prog_final)
        gl.glActiveTexture(glext.GL_TEXTURE0)
        gl.glBindTexture(glext.GL_TEXTURE_2D, self.comp_tex)
        gl.glUniform1i(self.lf["tScene"], 0)
        gl.glActiveTexture(glext.GL_TEXTURE1)
        gl.glBindTexture(glext.GL_TEXTURE_2D, self.blurB_tex)
        gl.glUniform1i(self.lf["tBloom"], 1)
        gl.glUniform1f(self.lf["uStrength"], float(strength))
        self._draw_quad()

    def _blur_pass(self, src_tex, dst_fbo, dx, dy):
        gl.glBindFramebuffer(glext.GL_FRAMEBUFFER, dst_fbo)
        gl.glViewport(0, 0, self.bw, self.bh)
        gl.glActiveTexture(glext.GL_TEXTURE0)
        gl.glBindTexture(glext.GL_TEXTURE_2D, src_tex)
        gl.glUniform1i(self.lu["tSrc"], 0)
        gl.glUniform2f(self.lu["uDir"], float(dx), float(dy))
        self._draw_quad()
