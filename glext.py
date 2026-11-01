import ctypes
import glctypes as gl
lib = gl.lib
c_uint = ctypes.c_uint
c_int = ctypes.c_int
c_float = ctypes.c_float
c_void_p = ctypes.c_void_p
c_size_t = ctypes.c_size_t
LP_uint = ctypes.POINTER(c_uint)
LP_float = ctypes.POINTER(c_float)

def _f(name, restype, *argtypes):
    fn = getattr(lib, name)
    fn.restype = restype
    fn.argtypes = argtypes
    return fn

GL_TEXTURE_2D = 0x0DE1
GL_RGBA = 0x1908
GL_RGBA8 = 0x8058
GL_UNSIGNED_BYTE = 0x1401
GL_UNSIGNED_INT = 0x1405
GL_BACK = 0x0405
GL_FRAMEBUFFER_BINDING = 0x8CA6
gl.glReadBuffer = _f('glReadBuffer', None, c_uint)
gl.glDrawBuffer = _f('glDrawBuffer', None, c_uint)
gl.glGetIntegerv = _f('glGetIntegerv', None, c_uint, ctypes.POINTER(c_int))
GL_NEAREST = 0x2600
GL_LINEAR = 0x2601
GL_CLAMP_TO_EDGE = 0x812F
GL_TEXTURE0 = 0x84C0
GL_TEXTURE_MIN_FILTER = 0x2801
GL_TEXTURE_MAG_FILTER = 0x2800
GL_TEXTURE_WRAP_S = 0x2802
GL_TEXTURE_WRAP_T = 0x2803
GL_FRAMEBUFFER = 0x8D40
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_FRAMEBUFFER_COMPLETE = 0x8CD5
GL_RENDERBUFFER = 0x8D41
GL_DEPTH_STENCIL_ATTACHMENT = 0x821A
GL_DEPTH24_STENCIL8 = 0x88F0
GL_RGBA32F = 0x8814
GL_FLOAT = 0x1406
gl.GL_ELEMENT_ARRAY_BUFFER = 0x8893
gl.GL_BLEND = 0x0BE2
GL_TEXTURE1 = 0x84C1
GL_TRIANGLE_STRIP = 0x0005
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_ONE = 1
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_FUNC_ADD = 0x8006
gl.glTexImage2D = _f('glTexImage2D', None, c_uint, c_int, c_int, c_int, c_int, c_int, c_uint, c_uint, c_void_p)
gl.glTexParameteri = _f('glTexParameteri', None, c_uint, c_uint, c_int)
gl.glTexParameterf = _f('glTexParameterf', None, c_uint, c_uint, c_float)
gl.glGenerateMipmap = _f('glGenerateMipmap', None, c_uint)
gl.glBindTexture = _f('glBindTexture', None, c_uint, c_uint)
gl.glGenTextures = _f('glGenTextures', None, c_int, LP_uint)
gl.glActiveTexture = _f('glActiveTexture', None, c_uint)
gl.glDeleteTextures = _f('glDeleteTextures', None, c_int, LP_uint)
gl.glGenFramebuffers = _f('glGenFramebuffers', None, c_int, LP_uint)
gl.glBindFramebuffer = _f('glBindFramebuffer', None, c_uint, c_uint)
gl.glFramebufferTexture2D = _f('glFramebufferTexture2D', None, c_uint, c_uint, c_uint, c_uint, c_int)
gl.glCheckFramebufferStatus = _f('glCheckFramebufferStatus', c_uint, c_uint)
gl.glDeleteFramebuffers = _f('glDeleteFramebuffers', None, c_int, LP_uint)
gl.glGenRenderbuffers = _f('glGenRenderbuffers', None, c_int, LP_uint)
gl.glBindRenderbuffer = _f('glBindRenderbuffer', None, c_uint, c_uint)
gl.glRenderbufferStorage = _f('glRenderbufferStorage', None, c_uint, c_uint, c_int, c_int, c_int)
gl.glFramebufferRenderbuffer = _f('glFramebufferRenderbuffer', None, c_uint, c_uint, c_uint, c_uint)
gl.glDrawArraysInstanced = _f('glDrawArraysInstanced', None, c_uint, c_int, c_int, c_int)
gl.glDrawElementsInstanced = _f('glDrawElementsInstanced', None, c_uint, c_int, c_uint, c_void_p, c_int)
gl.glVertexAttribDivisor = _f('glVertexAttribDivisor', None, c_uint, c_uint)
gl.glReadPixels = _f('glReadPixels', None, c_int, c_int, c_int, c_int, c_uint, c_uint, c_void_p)
gl.glUniform1i = _f('glUniform1i', None, c_int, c_int)
gl.glUniformMatrix4fv = _f('glUniformMatrix4fv', None, c_int, c_int, c_uint, c_void_p)
gl.glUniform2fv = _f('glUniform2fv', None, c_int, c_int, c_void_p)
gl.glEnable = _f('glEnable', None, c_uint)
gl.glDisable = _f('glDisable', None, c_uint)
gl.glBlendFunc = _f('glBlendFunc', None, c_uint, c_uint)
gl.glBlendFuncSeparate = _f('glBlendFuncSeparate', None, c_uint, c_uint, c_uint, c_uint)
gl.glBlendEquation = _f('glBlendEquation', None, c_uint)
def make_fbo(w, h, depth=False):
    fbo = c_uint(0)
    tex = c_uint(0)
    drb = c_uint(0)
    gl.glGenFramebuffers(1, ctypes.byref(fbo))
    gl.glGenTextures(1, ctypes.byref(tex))
    gl.glBindTexture(GL_TEXTURE_2D, tex)
    gl.glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
    gl.glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    gl.glBindFramebuffer(GL_FRAMEBUFFER, fbo)
    gl.glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, tex, 0)
    if depth:
        gl.glGenRenderbuffers(1, ctypes.byref(drb))
        gl.glBindRenderbuffer(GL_RENDERBUFFER, drb)
        gl.glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, w, h)
        gl.glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, drb)
    status = gl.glCheckFramebufferStatus(GL_FRAMEBUFFER)
    gl.glBindFramebuffer(GL_FRAMEBUFFER, 0)
    if status != GL_FRAMEBUFFER_COMPLETE:
        raise RuntimeError('FBO incomplete: 0x%X' % status)
    return fbo.value, tex.value, drb.value
def ortho_quad():
    vao = c_uint(0)
    vbo = c_uint(0)
    gl.glGenVertexArrays(1, ctypes.byref(vao))
    gl.glGenBuffers(1, ctypes.byref(vbo))
    gl.glBindVertexArray(vao)
    gl.glBindBuffer(gl.GL_ARRAY_BUFFER, vbo)
    data = (c_float * 6)(-1, -1, 3, -1, -1, 3)
    gl.glBufferData(gl.GL_ARRAY_BUFFER, ctypes.sizeof(data), ctypes.byref(data), gl.GL_STATIC_DRAW)
    gl.glEnableVertexAttribArray(0)
    gl.glVertexAttribPointer(0, 2, GL_FLOAT, 0, 0, None)
    gl.glBindVertexArray(0)
    return vao.value, vbo.value
