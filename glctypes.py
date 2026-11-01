# -*- coding: utf-8 -*-
"""极简 ctypes 封装：直接调用 libGL.so.1，零第三方依赖（PyOpenGL 都不需要）。

只暴露本程序用到的几十个 GL 函数。在 Gtk.GLArea 已 make_current 的上下文里调用即可。
"""
import ctypes

lib = ctypes.CDLL("libGL.so.1")

c_uint = ctypes.c_uint
c_int = ctypes.c_int
c_float = ctypes.c_float
c_char_p = ctypes.c_char_p
c_void_p = ctypes.c_void_p
c_size_t = ctypes.c_size_t

LP_c_char_p = ctypes.POINTER(c_char_p)
LP_int = ctypes.POINTER(c_int)
LP_uint = ctypes.POINTER(c_uint)


def _f(name, restype, *argtypes):
    fn = getattr(lib, name)
    fn.restype = restype
    fn.argtypes = argtypes
    return fn


GL_VERTEX_SHADER = 0x8B31
GL_FRAGMENT_SHADER = 0x8B30
GL_COMPILE_STATUS = 0x8B81
GL_LINK_STATUS = 0x8B82
GL_ARRAY_BUFFER = 0x8892
GL_STATIC_DRAW = 0x88E4
GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_COLOR_BUFFER_BIT = 0x4000

glCreateShader = _f("glCreateShader", c_uint, c_uint)
glShaderSource = _f("glShaderSource", None, c_uint, c_int, LP_c_char_p, c_void_p)
glCompileShader = _f("glCompileShader", None, c_uint)
glGetShaderiv = _f("glGetShaderiv", None, c_uint, c_uint, LP_int)
glGetShaderInfoLog = _f("glGetShaderInfoLog", None, c_uint, c_int, LP_int, c_char_p)
glDeleteShader = _f("glDeleteShader", None, c_uint)
glCreateProgram = _f("glCreateProgram", c_uint)
glAttachShader = _f("glAttachShader", None, c_uint, c_uint)
glLinkProgram = _f("glLinkProgram", None, c_uint)
glGetProgramiv = _f("glGetProgramiv", None, c_uint, c_uint, LP_int)
glGetProgramInfoLog = _f("glGetProgramInfoLog", None, c_uint, c_int, LP_int, c_char_p)
glDeleteProgram = _f("glDeleteProgram", None, c_uint)
glUseProgram = _f("glUseProgram", None, c_uint)
glGetAttribLocation = _f("glGetAttribLocation", c_int, c_uint, c_char_p)
glGetUniformLocation = _f("glGetUniformLocation", c_int, c_uint, c_char_p)
glGenBuffers = _f("glGenBuffers", None, c_int, LP_uint)
glBindBuffer = _f("glBindBuffer", None, c_uint, c_uint)
glBufferData = _f("glBufferData", None, c_uint, c_size_t, c_void_p, c_uint)
glGenVertexArrays = _f("glGenVertexArrays", None, c_int, LP_uint)
glBindVertexArray = _f("glBindVertexArray", None, c_uint)
glEnableVertexAttribArray = _f("glEnableVertexAttribArray", None, c_uint)
glVertexAttribPointer = _f("glVertexAttribPointer", None, c_uint, c_int, c_uint, c_uint, c_int, c_void_p)
glDrawArrays = _f("glDrawArrays", None, c_uint, c_int, c_int)
glClearColor = _f("glClearColor", None, c_float, c_float, c_float, c_float)
glClear = _f("glClear", None, c_uint)
glViewport = _f("glViewport", None, c_int, c_int, c_int, c_int)
glUniform1f = _f("glUniform1f", None, c_int, c_float)
glUniform1i = _f("glUniform1i", None, c_int, c_int)
glUniform2f = _f("glUniform2f", None, c_int, c_float, c_float)
glUniform3f = _f("glUniform3f", None, c_int, c_float, c_float, c_float)
glFlush = _f("glFlush", None)
glGetError = _f("glGetError", c_uint)


def create_shader(src, shader_type):
    sh = glCreateShader(shader_type)
    buf = src.encode("utf-8")
    arr = (c_char_p * 1)(c_char_p(buf))
    glShaderSource(sh, 1, arr, None)
    glCompileShader(sh)
    ok = c_int(0)
    glGetShaderiv(sh, GL_COMPILE_STATUS, ctypes.byref(ok))
    if not ok.value:
        log = ctypes.create_string_buffer(8192)
        glGetShaderInfoLog(sh, 8192, ctypes.byref(c_int(0)), log)
        raise RuntimeError("shader compile error: " + log.value.decode("utf-8", "replace"))
    return sh


def create_program(vs_src, fs_src):
    vs = create_shader(vs_src, GL_VERTEX_SHADER)
    fs = create_shader(fs_src, GL_FRAGMENT_SHADER)
    prog = glCreateProgram()
    glAttachShader(prog, vs)
    glAttachShader(prog, fs)
    glLinkProgram(prog)
    ok = c_int(0)
    glGetProgramiv(prog, GL_LINK_STATUS, ctypes.byref(ok))
    if not ok.value:
        log = ctypes.create_string_buffer(8192)
        glGetProgramInfoLog(prog, 8192, ctypes.byref(c_int(0)), log)
        raise RuntimeError("program link error: " + log.value.decode("utf-8", "replace"))
    glDeleteShader(vs)
    glDeleteShader(fs)
    return prog
GL_RGB = 0x1907
GL_UNSIGNED_BYTE = 0x1401
GL_COLOR_ATTACHMENT0 = 0x8CE0
glReadBuffer = _f("glReadBuffer", None, c_uint)
glReadPixels = _f("glReadPixels", None, c_int, c_int, c_int, c_int, c_uint, c_uint, c_void_p)
